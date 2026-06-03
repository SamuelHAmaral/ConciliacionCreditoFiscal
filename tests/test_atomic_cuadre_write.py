"""Tests for atomic CUADRE workbook publish."""

from pathlib import Path

import pandas as pd
import pytest

from reporting.cuadre_writer import write_cuadre_workbook


def test_atomic_write_leaves_no_part_files(tmp_path: Path, monkeypatch):
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    d = pd.Timestamp("2026-04-01")
    matched = pd.DataFrame(
        {
            "Ledger_Debito": [1.0],
            "Ledger_Cuenta": ["469"],
            "Ledger_Fecha": [d],
            "Ledger_Ag": [9],
            "Ledger_Asiento": [1],
            "Ledger_Descripcion": ["x"],
            "Ledger_Credito": [None],
            "System_IVA 10": [1.0],
            "System_Fecha Comprobante": [d],
        }
    )
    write_cuadre_workbook(out, "469", matched, pd.DataFrame(), pd.DataFrame(), ledger_side="Debito")
    assert out.is_file()
    parts = list(tmp_path.glob(".*.part"))
    assert parts == []


def test_atomic_publish_permission_error_propagates(tmp_path: Path, monkeypatch):
    import reporting.cuadre_writer as cw

    out = tmp_path / "CUADRE_1279_reconciliacion.xlsx"
    calls = {"n": 0}

    real_replace = cw.os.replace

    def fake_replace(temp_path: Path, final_path: Path) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("locked")
        real_replace(temp_path, final_path)

    monkeypatch.setattr(cw.os, "replace", fake_replace)

    d = pd.Timestamp("2026-04-01")
    matched = pd.DataFrame(
        {
            "Ledger_Debito": [1.0],
            "Ledger_Cuenta": ["1279"],
            "Ledger_Fecha": [d],
            "Ledger_Ag": [9],
            "Ledger_Asiento": [1],
            "Ledger_Descripcion": ["x"],
            "Ledger_Credito": [None],
            "System_IVA ML": [1.0],
            "System_Fecha_Cont": [d],
        }
    )
    with pytest.raises(PermissionError):
        write_cuadre_workbook(out, "1279", matched, pd.DataFrame(), pd.DataFrame(), ledger_side="Debito")
