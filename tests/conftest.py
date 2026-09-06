from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts.artifact_io import sha256_file, sha256_text, write_json
from scripts.ts_strategy_engine.execution_evidence import TRUSTED_ARTIFACTS
from scripts.ts_strategy_engine.execution_gate_cli import build_decision


ROOT = Path(__file__).resolve().parents[1]
for path in (
    ROOT / "scripts" / "neb_agent",
    ROOT / "scripts" / "convergence",
    ROOT / "scripts" / "adsorption",
    ROOT / "scripts" / "adsmind_lite",
    ROOT / "skills" / "catalysis-data-retrieval" / "scripts",
):
    sys.path.insert(0, str(path))


# Synthetic, file-bound gate inputs shared by execution integration tests.


@pytest.fixture
def bound_gate(tmp_path):
    def create(evidence, *, directory=None):
        folder = directory or tmp_path / "bound_gate"
        folder.mkdir(parents=True, exist_ok=True)
        request = {"climb": evidence.get("climb", False), "path_reviewed": evidence.get("path_reviewed", True)}
        for name in ("geometry", "analysis", "thresholds", "path_quality", "preflight", "validation", "scheduler", "authorization"):
            payload = dict(evidence.get(name, {}))
            if payload and name in TRUSTED_ARTIFACTS:
                raw = folder / f"{name}.raw"
                raw.write_text(f"synthetic {name} test evidence", encoding="utf-8")
                kind, producer = TRUSTED_ARTIFACTS[name]
                payload.setdefault("document_kind", kind)
                payload.setdefault("producer", producer)
                payload.setdefault("source_files", [{"path": str(raw), "sha256": sha256_file(raw)}])
            path = write_json(folder / f"{name}.json", payload)
            request[f"{name}_file"] = str(path)
        request_path = write_json(folder / "request.json", request)
        output = folder / "decision.json"
        build_decision(request_path, output)
        return output
    return create


@pytest.fixture
def scheduler_snapshot():
    def create(status="RUN"):
        stdout = f"JOBID USER STAT QUEUE FROM_HOST EXEC_HOST JOB_NAME SUBMIT_TIME\n123 user {status} queue host exec neb Jul 24 00:00\n"
        return {
            "schema_version": 1, "document_kind": "scheduler_job_evidence", "stage": "neb_pilot",
            "scheduler": "LSF", "server_alias": "sunboquan-codex", "job_id": "123", "status": status,
            "checked_at": "2026-07-24T00:00:00Z", "source_command": "ssh sunboquan-codex bjobs -a 123",
            "query": {"argv": ["ssh", "sunboquan-codex", "bjobs", "-a", "123"], "returncode": 0,
                      "stdout": stdout, "stderr": "", "stdout_sha256": sha256_text(stdout)},
        }
    return create
