from __future__ import annotations

from typing import Any

import yaml

from scripts.artifact_io import sha256_json

from .execution_evidence import load_verified_evidence_source


MUTABLE_EVIDENCE = (
    "geometry", "analysis", "thresholds", "path_quality", "preflight",
    "validation", "scheduler", "authorization",
)


class ExecutionStateError(ValueError):
    """The decision cannot establish current, file-bound execution evidence."""


def load_live_execution_evidence(decision: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct evidence from current files, never from a caller's digest."""
    embedded = decision.get("EVIDENCE")
    if not isinstance(embedded, dict):
        raise ExecutionStateError("execution decision is stale: evidence must be a mapping")
    bindings = embedded.get("source_bindings")
    if not isinstance(bindings, dict) or set(bindings) - set(MUTABLE_EVIDENCE):
        raise ExecutionStateError("execution decision is stale: malformed source_bindings")
    live = {"climb": embedded.get("climb"), "path_reviewed": embedded.get("path_reviewed")}
    verified_bindings = {}
    for name in MUTABLE_EVIDENCE:
        snapshot = embedded.get(name)
        if not isinstance(snapshot, dict):
            raise ExecutionStateError(f"execution decision is stale: malformed {name} evidence")
        if name not in bindings:
            if snapshot:
                raise ExecutionStateError(f"execution decision is stale: unbound {name} evidence; regenerate decision")
            live[name] = {}
            continue
        try:
            live[name], verified_bindings[name] = load_verified_evidence_source(bindings[name], name, snapshot)
        except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as exc:
            raise ExecutionStateError(f"execution decision is stale: {name}: {exc}") from exc
    live["source_bindings"] = verified_bindings
    return live


def require_live_execution_state(decision: dict[str, Any]) -> dict[str, Any]:
    live = load_live_execution_evidence(decision)
    if sha256_json(live) != decision.get("state_sha256"):
        raise ExecutionStateError("execution decision is stale for the current calculation state")
    return live
