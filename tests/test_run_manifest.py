"""Tests for run_manifest.json generation."""

import json
from pathlib import Path

from pipeline.run_manifest import build_run_manifest, write_run_manifest
from ui.services import AccountRunResult


def test_write_run_manifest(tmp_path: Path):
    log_path = tmp_path / "logs" / "conciliacion_test.log"
    audit_path = tmp_path / "logs" / "audit_test.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("log", encoding="utf-8")
    audit_path.write_text("{}", encoding="utf-8")

    results = [
        AccountRunResult(account="469", ok=True, output=tmp_path / "CUADRE_469_reconciliacion.xlsx"),
        AccountRunResult(account="1279", ok=False, error="[E_VALIDATION] bad", error_code="E_VALIDATION"),
    ]
    manifest = build_run_manifest(
        run_id="test123",
        source="unit_test",
        salida=tmp_path,
        accounts=["469", "1279"],
        results=results,
        log_path=log_path,
        audit_path=audit_path,
        started_at="2026-06-01T00:00:00+00:00",
        ended_at="2026-06-01T00:01:00+00:00",
        inputs={"fecha_desde": "2026-04-01"},
    )
    out = write_run_manifest(tmp_path / "logs" / "run_manifest_test123.json", manifest)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["run_id"] == "test123"
    assert data["summary"]["ok_count"] == 1
    assert data["summary"]["error_count"] == 1
    assert len(data["accounts"]) == 2
