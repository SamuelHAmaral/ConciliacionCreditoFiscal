"""Smoke test for Excel writer."""

import pandas as pd
import pytest

openpyxl = pytest.importorskip("openpyxl")

from reporting.excel_writer import write_reconciliation_workbook


def test_write_workbook(tmp_path):
    out = tmp_path / "t.xlsx"
    d = pd.Timestamp("2026-04-01")
    matched = pd.DataFrame(
        {
            "Ledger__match_amount": [1.0],
            "Ledger_Fecha": [d],
            "System__match_amount": [1.0],
            "System_Fecha_Cont": [d],
            "Difference": [0.0],
        }
    )
    ul = pd.DataFrame({"L": [2.0]})
    us = pd.DataFrame({"S": [3.0]})
    write_reconciliation_workbook(out, matched, ul, us, account_label="469")
    assert out.exists()
    assert out.stat().st_size > 500

    wb = openpyxl.load_workbook(out, data_only=False)
    assert "Partidas Conciliadas" in wb.sheetnames
    assert "Pendientes en Mayor" in wb.sheetnames
    assert "Pendientes en Sistema" in wb.sheetnames
    ws = wb["Partidas Conciliadas"]
    headers = [ws.cell(1, j).value for j in range(1, ws.max_column + 1)]
    assert "Diferencia" in headers
    last_col = ws.max_column
    diff_cell = ws.cell(2, last_col).value
    assert isinstance(diff_cell, str) and diff_cell.startswith("=")
