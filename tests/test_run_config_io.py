"""Round-trip tests for GUI run config serialization."""

from pathlib import Path

from ui.run_config_io import run_config_from_dict, run_config_to_dict
from ui.services import AccountJob, RunConfig


def test_run_config_round_trip(tmp_path: Path):
    ledger = tmp_path / "mayor.txt"
    ledger.write_text("x", encoding="utf-8")
    cfg = RunConfig(
        salida=tmp_path / "out",
        jobs=[AccountJob(account="469", ledger_path=ledger)],
        famafa_compras=tmp_path / "fc.csv",
        fecha_desde="2026-04-01",
        fecha_hasta="2026-04-30",
        amount_tolerance_1279=0.01,
    )
    data = run_config_to_dict(cfg, verbose=True, uat_verify=True, models_root=tmp_path)
    restored = run_config_from_dict(data)
    assert restored.salida == cfg.salida.resolve()
    assert restored.jobs[0].account == "469"
    assert restored.famafa_compras == cfg.famafa_compras
