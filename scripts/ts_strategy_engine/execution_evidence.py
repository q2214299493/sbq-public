from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.artifact_io import (
    load_json_object,
    sha256_file,
    require_sha256,
    source_file_manifest_valid,
)
from scripts.scheduler_evidence import validate_stored_lsf_evidence


TRUSTED_ARTIFACTS = {
    "geometry": ("neb_path_geometry_diagnosis", "scripts.neb_agent.diagnose_path_geometry"),
    "analysis": ("neb_output_analysis", "scripts.neb_agent.analyze_neb_outputs"),
    "path_quality": ("neb_path_quality_evidence", "scripts.neb_agent.path_quality_control"),
}


def load_bound_evidence(
    request_path: Path,
    request: dict[str, Any],
    name: str,
    bindings: dict[str, dict[str, str]],
    *,
    required: bool = False,
) -> dict[str, Any] | None:
    value = request.get(f"{name}_file")
    if not value:
        if required:
            raise ValueError(f"gate request missing: {name}_file")
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (request_path.parent / path).resolve()
    if not path.is_file():
        raise ValueError(f"gate evidence file not found: {path}")
    bindings[name] = {"path": str(path), "sha256": sha256_file(path)}
    return load_evidence_source(path, name)


def evidence_binding(binding: object) -> tuple[Path, str]:
    """Validate a file reference without consulting the filesystem."""
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("source binding must contain path and sha256")
    value = binding["path"]
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("source binding path must be non-empty text")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("source binding path must be absolute")
    return path, require_sha256(binding["sha256"], label="source binding hash")


def validate_evidence_provenance(current: dict[str, Any], name: str) -> None:
    """Check declared provenance; live manifest hashes are checked by the loader."""
    if name == "scheduler":
        validate_stored_lsf_evidence(current)
    expected = TRUSTED_ARTIFACTS.get(name)
    if expected:
        if current.get("document_kind") != expected[0] or current.get("producer") != expected[1]:
            raise ValueError(f"untrusted {name} artifact")
        sources = current.get("source_files")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"{name} source file manifest missing")
        for source in sources:
            evidence_binding(source)


def source_bindings_declared(evidence: dict[str, Any], required: tuple[str, ...]) -> bool:
    """Decision reasoning only: declarations never authorize an execution."""
    bindings = evidence.get("source_bindings", {})
    if not isinstance(bindings, dict):
        return False
    try:
        for name in required:
            evidence_binding(bindings.get(name))
            current = evidence.get(name)
            if not isinstance(current, dict):
                return False
            validate_evidence_provenance(current, name)
    except (ValueError, TypeError, KeyError):
        return False
    return True


def load_verified_evidence_source(
    binding: object, name: str, snapshot: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Re-read one binding, preserving hash, payload and provenance checks."""
    path, expected_hash = evidence_binding(binding)
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError(f"{name} source hash changed")
    current = load_evidence_source(path, name)
    if current != snapshot:
        raise ValueError(f"{name} source payload differs from snapshot")
    # Detect replacement during parsing as well as changes since generation.
    if sha256_file(path) != actual_hash:
        raise ValueError(f"{name} source changed while reading")
    if current:
        validate_evidence_provenance(current, name)
        if name in TRUSTED_ARTIFACTS and not source_file_manifest_valid(current):
            raise ValueError(f"{name} source file manifest changed")
    return current, {"path": str(path), "sha256": actual_hash}


def source_bindings_valid(evidence: dict[str, Any], required: tuple[str, ...]) -> bool:
    """Live binding/provenance check for compatibility; uses the shared loader."""
    if not source_bindings_declared(evidence, required):
        return False
    try:
        for name in required:
            load_verified_evidence_source(evidence["source_bindings"][name], name, evidence[name])
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        return False
    return True


def warning_reason_codes(
    geometry: dict[str, Any],
    analysis: dict[str, Any],
    quality: dict[str, Any],
) -> list[str]:
    flags = (
        (
            analysis.get("scf_warning") and not analysis.get("scf_failure"),
            "TRANSIENT_SCF_EXHAUSTION_WARNING",
        ),
        (
            bool(analysis.get("high_force_warnings")),
            "EARLY_OR_NONPERSISTENT_HIGH_FORCE_WARNING",
        ),
        (
            bool(analysis.get("internal_minimum_warning")),
            "TRANSIENT_INTERNAL_MINIMUM_WARNING",
        ),
        (geometry.get("status") == "REVIEW", "GEOMETRY_REVIEW_WARNING"),
    )
    reasons = [*quality.get("REASON_CODES", [])]
    reasons.extend(reason for active, reason in flags if active)
    return sorted(set(reasons))


def validated_ts(validation: dict[str, Any]) -> bool:
    source_method = str(validation.get("source_method", "")).lower()
    frequency_hash_valid = validation.get("frequency_structure_hash_valid") or (
        validation.get("source_saddle_sha256")
        and validation.get("source_saddle_sha256")
        == validation.get("frequency_poscar_sha256")
    )
    connectivity_valid = source_method == "dimer" or validation.get(
        "bidirectional_connectivity_valid"
    ) or (
        validation.get("connectivity_status") == "PASS"
        and validation.get("connects_to_is") is True
        and validation.get("connects_to_fs") is True
    )
    dimer_acceptance_valid = (
        source_method != "dimer"
        or validation.get("dimer_technical_acceptance") is True
    )
    return bool(
        validation.get("frequency_grade", validation.get("grade")) == "A"
        and frequency_hash_valid
        and connectivity_valid
        and dimer_acceptance_valid
    )


def authorized_actions(
    evidence: dict[str, Any],
    *other: str,
    stop_eligible: bool = False,
    required_sources: tuple[str, ...] = (),
) -> tuple[str, ...]:
    scheduler = evidence.get("scheduler", {})
    stop_allowed = scheduler.get("status") in {"PEND", "RUN"} and bool(
        scheduler.get("job_id")
    )
    stop_allowed = (
        stop_allowed
        and stop_eligible
        and source_bindings_declared(evidence, required_sources)
    )
    return (("STOP_JOB",) if stop_allowed else ()) + tuple(other)


def diagnostic_actions(
    evidence: dict[str, Any],
    *,
    stop_eligible: bool = False,
    required_sources: tuple[str, ...] = (),
) -> tuple[str, ...]:
    preflight = evidence["preflight"]
    ready = preflight.get("passed") and preflight.get("kind") == "diagnostic_static"
    return authorized_actions(
        evidence,
        *(("SUBMIT_DIAGNOSTIC_VASP",) if ready else ()),
        stop_eligible=stop_eligible,
        required_sources=required_sources,
    )


def load_evidence_source(path: Path, name: str) -> dict[str, Any]:
    if name == "thresholds":
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("threshold evidence must be an object")
        return value
    return load_json_object(path)
