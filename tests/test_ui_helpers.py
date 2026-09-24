"""Tests for headless validation helpers."""

from pathlib import Path

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
