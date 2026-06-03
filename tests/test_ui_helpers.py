"""Tests for Streamlit UI helpers (no Streamlit runtime)."""

from pathlib import Path

import pandas as pd

from ui.history import summarize_audit_file
from ui.preview import preview_workbook
from ui.services import AccountJob, RunConfig, validate_run_config


def test_validate_run_config_requires_inputs(tmp_path: Path):
    cfg = RunConfig(salida=tmp_path, jobs=[], sql_csv=None)
    result = validate_run_config(cfg)
    assert result.has_errors
    assert any("tipo" in e.lower() for e in result.flat_errors())

    led = tmp_path / "m.txt"
    led.write_text("x", encoding="utf-8")
    cfg2 = RunConfig(
        salida=tmp_path,
        jobs=[AccountJob("1279", led)],
        sql_csv=None,
        fecha_desde="2026-01-01",
        fecha_hasta="2026-01-31",
    )
    result2 = validate_run_config(cfg2)
    assert result2.has_errors
    assert any("SQL" in e for e in result2.flat_errors())


def test_summarize_audit_ui_run(tmp_path: Path):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    audit = logs / "audit_test123.jsonl"
    audit.write_text(
        '{"ts":"2026-01-01T00:00:00+00:00","run_id":"test123","stage":"ui_run_start","status":"ok","source":"desktop_tk","accounts":["469"]}\n'
        '{"ts":"2026-01-01T00:01:00+00:00","run_id":"test123","stage":"ui_run_complete","status":"ok","outputs":["C:/out.xlsx"],"error_count":0,"jobs":1,"ok_count":1}\n',
        encoding="utf-8",
    )
    s = summarize_audit_file(audit)
    assert s is not None
    assert s.run_id == "test123"
    assert "469" in s.accounts


def test_preview_empty_workbook(tmp_path: Path):
    p = tmp_path / "empty.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(p, index=False)
    prev = preview_workbook(p, nrows=5)
    assert isinstance(prev, dict)
