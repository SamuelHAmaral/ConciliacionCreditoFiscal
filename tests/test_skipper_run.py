"""Tests for Skipper CLI runner wiring."""

from __future__ import annotations

from pathlib import Path

from ingestion.folder_discovery import discover_inputs
from ui.services import AccountJob, RunConfig


def test_skipper_run_config_from_discovery(tmp_path: Path) -> None:
    insumos = tmp_path / "insumos"
    acc = insumos / "Cuenta 469 IVA CF 10%"
    acc.mkdir(parents=True)
    (acc / "mayorpc 469.txt").write_text("CUENTA: 469\n", encoding="latin-1")
    (acc / "FAMAFA COMPRAS 469.csv").write_text(
        "Tipo Comprobante,IVA 10,Fecha Emision\n109,10,01/04/2026\n",
        encoding="utf-8",
    )
    discovered = discover_inputs(insumos)
    jobs = [AccountJob(account="469", ledger_path=discovered.ledgers["469"])]
    cfg = RunConfig(
        salida=tmp_path / "out",
        jobs=jobs,
        famafa_compras=discovered.famafa_compras.get("469"),
        famafa_compras_by_account=discovered.famafa_compras or None,
        match_469_amount_only=True,
    )
    assert cfg.match_469_amount_only is True
    assert len(cfg.jobs) == 1
    assert cfg.famafa_compras is not None
