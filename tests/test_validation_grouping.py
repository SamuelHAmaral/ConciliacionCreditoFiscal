"""Tests for grouped validation results."""

from pathlib import Path

from ui.services import AccountJob, RunConfig, RunValidationResult, validate_run_config


def test_validate_run_config_groups_by_account(tmp_path: Path):
    led = tmp_path / "mayor.txt"
    led.write_text("x", encoding="utf-8")
    cfg = RunConfig(
        salida=tmp_path,
        jobs=[AccountJob("469", led)],
        famafa_compras=None,
    )
    result = validate_run_config(cfg, include_precheck=False)
    assert isinstance(result, RunValidationResult)
    assert result.has_errors
    assert "469" in result.account_errors or result.global_errors
