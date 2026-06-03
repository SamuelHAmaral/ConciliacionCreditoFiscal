"""Tests for audit trail and logging setup."""

import json
import logging
from pathlib import Path

from pipeline.logging_audit import AuditTrail, setup_run_logging


def test_audit_trail_jsonl(tmp_path: Path):
    p = tmp_path / "a.jsonl"
    a = AuditTrail(p, "test_run")
    try:
        a.record("stage_a", "ok", account="469", rows=3)
        a.record("stage_b", "failed", error="boom")
    finally:
        a.close()
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    r0 = json.loads(lines[0])
    assert r0["stage"] == "stage_a" and r0["run_id"] == "test_run" and r0["account"] == "469"
    r1 = json.loads(lines[1])
    assert r1["status"] == "failed" and r1["error"] == "boom"


def test_setup_run_logging_creates_files(tmp_path: Path):
    root = logging.getLogger()
    before_handlers = list(root.handlers)
    rid, log_p, audit_p, audit = setup_run_logging(tmp_path, console=False, run_id="fixed_id")
    try:
        assert rid == "fixed_id"
        assert log_p.name == "conciliacion_fixed_id.log"
        assert audit_p.name == "audit_fixed_id.jsonl"
        logging.getLogger("conciliation").info("hello file")
    finally:
        audit.close()
        for h in list(root.handlers):
            if h not in before_handlers:
                root.removeHandler(h)
    assert log_p.is_file()
    assert "hello file" in log_p.read_text(encoding="utf-8")
