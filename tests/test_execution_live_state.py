from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from scripts.artifact_io import load_json_object, sha256_file, sha256_json, write_json
from scripts.ts_strategy_engine import execution_evidence
from scripts.ts_strategy_engine.execution_gate import decide_execution, require_action, validate_decision
from scripts.ts_strategy_engine.execution_state import MUTABLE_EVIDENCE, ExecutionStateError


@pytest.fixture
def live_gate(bound_gate, scheduler_snapshot):
    return bound_gate({
        "geometry": {"status": "PASS"}, "analysis": {"status": "NO_OUTPUT"},
        "thresholds": {"high_force_warning_threshold_eVA": 1.5},
        "path_quality": {"PATH_QUALITY_STATUS": "PASS"},
        "preflight": {"kind": "ordinary_neb", "passed": True, "bundle_sha256": "a" * 64},
        "validation": {"grade": "C"}, "scheduler": scheduler_snapshot(),
        "authorization": {"action": "SUBMIT_VASP", "source": "synthetic user authorization"},
        "climb": False, "path_reviewed": True,
    })


def _source(path, name):
    return Path(load_json_object(path)["EVIDENCE"]["source_bindings"][name]["path"])


def _rebind_hash(path, name):
    decision = load_json_object(path)
    decision["EVIDENCE"]["source_bindings"][name]["sha256"] = sha256_file(_source(path, name))
    decision["state_sha256"] = sha256_json(decision["EVIDENCE"])
    write_json(path, decision)


def test_unchanged_bound_sources_allow_action(live_gate):
    assert require_action(live_gate, "SUBMIT_VASP")["ALLOWED_ACTIONS"] == ["SUBMIT_VASP"]
    assert list(inspect.signature(require_action).parameters) == ["decision_path", "action"]
    with pytest.raises(TypeError):
        require_action(live_gate, "SUBMIT_VASP", load_json_object(live_gate)["state_sha256"])


@pytest.mark.parametrize("name", MUTABLE_EVIDENCE)
def test_each_bound_source_mutation_is_stale(live_gate, name):
    original_decision = live_gate.read_bytes()
    source = _source(live_gate, name)
    payload = load_json_object(source)
    payload["mutation"] = True
    write_json(source, payload)
    with pytest.raises(ExecutionStateError, match="stale"):
        require_action(live_gate, "SUBMIT_VASP")
    assert live_gate.read_bytes() == original_decision


@pytest.mark.parametrize("name", MUTABLE_EVIDENCE)
def test_deleted_bound_source_is_stale(live_gate, name):
    _source(live_gate, name).unlink()
    with pytest.raises(ExecutionStateError, match="stale"):
        require_action(live_gate, "SUBMIT_VASP")


@pytest.mark.parametrize("name", ["analysis", "thresholds"])
def test_malformed_json_or_yaml_fails_closed_even_with_rebound_hash(live_gate, name):
    _source(live_gate, name).write_text("[malformed", encoding="utf-8")
    _rebind_hash(live_gate, name)
    with pytest.raises(ExecutionStateError, match="stale"):
        require_action(live_gate, "SUBMIT_VASP")


def test_hash_and_parsed_snapshot_must_both_match(live_gate):
    source = _source(live_gate, "analysis")
    payload = load_json_object(source)
    payload["mutation"] = True
    write_json(source, payload)
    _rebind_hash(live_gate, "analysis")
    with pytest.raises(ExecutionStateError, match="payload differs"):
        require_action(live_gate, "SUBMIT_VASP")


def test_semantically_equal_bytes_still_stale_until_exact_content_restored(live_gate):
    source = _source(live_gate, "analysis")
    original = source.read_bytes()
    source.write_bytes(original + b"\n")
    with pytest.raises(ExecutionStateError, match="hash changed"):
        require_action(live_gate, "SUBMIT_VASP")
    source.write_bytes(original)
    require_action(live_gate, "SUBMIT_VASP")


@pytest.mark.parametrize("name", MUTABLE_EVIDENCE)
def test_nonempty_unbound_evidence_cannot_authorize(live_gate, name):
    decision = load_json_object(live_gate)
    del decision["EVIDENCE"]["source_bindings"][name]
    decision["state_sha256"] = sha256_json(decision["EVIDENCE"])
    write_json(live_gate, decision)
    with pytest.raises(ExecutionStateError, match=f"unbound {name}"):
        require_action(live_gate, "SUBMIT_VASP")


def test_inline_reasoning_decision_is_not_execution_authority(tmp_path):
    decision = decide_execution({}, {"status": "NO_OUTPUT"}, {}, climb=False, path_reviewed=True,
                                preflight={"kind": "ordinary_neb", "passed": True})
    assert decision["ALLOWED_ACTIONS"] == ["SUBMIT_VASP"]
    validate_decision(decision)
    path = write_json(tmp_path / "inline.json", decision)
    with pytest.raises(ExecutionStateError, match="unbound"):
        require_action(path, "SUBMIT_VASP")


@pytest.mark.parametrize("field,value", [
    ("EVIDENCE", {}), ("ALLOWED_ACTIONS", ["STOP_JOB"]), ("FORBIDDEN_ACTIONS", []),
    ("state_sha256", "b" * 64), ("DECISION", "STOP_USER_REQUESTED"), ("SUBMISSION_ALLOWED", False),
])
def test_snapshot_authority_tampering_still_rejected(live_gate, field, value):
    decision = load_json_object(live_gate)
    decision[field] = value
    write_json(live_gate, decision)
    with pytest.raises(ValueError):
        require_action(live_gate, "SUBMIT_VASP")


@pytest.mark.parametrize("binding", [None, [], {}, {"path": "relative", "sha256": "a" * 64},
                                     {"path": "/tmp/evidence", "sha256": "invalid"}])
def test_malformed_binding_fails_closed(live_gate, binding):
    decision = load_json_object(live_gate)
    decision["EVIDENCE"]["source_bindings"]["analysis"] = binding
    decision["state_sha256"] = sha256_json(decision["EVIDENCE"])
    write_json(live_gate, decision)
    with pytest.raises(ExecutionStateError, match="stale"):
        require_action(live_gate, "SUBMIT_VASP")


@pytest.mark.parametrize("name", ["geometry", "analysis", "path_quality"])
@pytest.mark.parametrize("field", ["producer", "document_kind", "source_files"])
def test_trusted_artifact_semantics_preserved(live_gate, name, field):
    source = _source(live_gate, name)
    payload = load_json_object(source)
    payload[field] = [] if field == "source_files" else "untrusted"
    write_json(source, payload)
    decision = load_json_object(live_gate)
    decision["EVIDENCE"][name] = payload
    write_json(live_gate, decision)
    _rebind_hash(live_gate, name)
    assert not execution_evidence.source_bindings_valid(load_json_object(live_gate)["EVIDENCE"], (name,))
    with pytest.raises(ExecutionStateError, match="stale"):
        require_action(live_gate, "SUBMIT_VASP")


def test_upstream_manifest_mutation_is_stale(live_gate):
    analysis = load_json_object(_source(live_gate, "analysis"))
    Path(analysis["source_files"][0]["path"]).write_text("changed raw output", encoding="utf-8")
    with pytest.raises(ExecutionStateError, match="source file manifest changed"):
        require_action(live_gate, "SUBMIT_VASP")


def test_live_sources_use_shared_loader_once_per_source(live_gate, monkeypatch):
    calls = []
    original = execution_evidence.load_evidence_source
    def load(path, name):
        calls.append(name)
        return original(path, name)
    monkeypatch.setattr(execution_evidence, "load_evidence_source", load)
    require_action(live_gate, "SUBMIT_VASP")
    assert sorted(calls) == sorted(MUTABLE_EVIDENCE)


def test_snapshot_validation_does_not_mistake_itself_for_live_authority(live_gate):
    decision = load_json_object(live_gate)
    _source(live_gate, "analysis").unlink()
    validate_decision(decision)
    with pytest.raises(ExecutionStateError, match="stale"):
        require_action(live_gate, "SUBMIT_VASP")


@pytest.mark.parametrize("bindings", [None, [], {"unexpected_source": {}}])
def test_source_bindings_must_be_a_known_mapping(live_gate, bindings):
    decision = load_json_object(live_gate)
    decision["EVIDENCE"]["source_bindings"] = bindings
    decision["state_sha256"] = sha256_json(decision["EVIDENCE"])
    write_json(live_gate, decision)
    with pytest.raises(ValueError):
        require_action(live_gate, "SUBMIT_VASP")


def test_stored_scheduler_raw_output_validation_remains_required(live_gate):
    source = _source(live_gate, "scheduler")
    payload = load_json_object(source)
    payload["query"]["stdout_sha256"] = "b" * 64
    write_json(source, payload)
    decision = load_json_object(live_gate)
    decision["EVIDENCE"]["scheduler"] = payload
    write_json(live_gate, decision)
    _rebind_hash(live_gate, "scheduler")
    with pytest.raises(ExecutionStateError, match="stored LSF stdout hash mismatch"):
        require_action(live_gate, "SUBMIT_VASP")
