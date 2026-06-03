"""Tests for CUADRE-style Excel output."""

import pandas as pd
import pytest

openpyxl = pytest.importorskip("openpyxl")

from reporting.cuadre_writer import build_cuadre_dataframe, write_cuadre_workbook


def test_build_cuadre_dataframe_order():
    d = pd.Timestamp("2026-04-01")
    matched = pd.DataFrame(
        {
            "Ledger_Cuenta": ["469"],
            "Ledger_Fecha": [d],
            "Ledger_Ag": [9],
            "Ledger_Asiento": [1],
            "Ledger_Descripcion": ["test"],
            "Ledger_Debito": [100.0],
            "Ledger_Credito": [None],
            "System_IVA 10": [100.0],
            "System_Nro. Identific.": ["80000001"],
            "System_Razon Social": ["ACME"],
            "System_Fecha Comprobante": [d],
            "System_Nro. Comprobante": ["001"],
            "System_Imponible 10": [1000.0],
        }
    )
    main_df, hoja1 = build_cuadre_dataframe(
        "469", matched, pd.DataFrame(), pd.DataFrame(), ledger_side="Debito"
    )
    assert hoja1 is None
    assert "CRUCE" in main_df.columns
    debit_cols = [c for c in main_df.columns if "bito" in str(c) and "Cr" not in str(c)[:3]]
    assert main_df.iloc[0][debit_cols[0]] == 100.0


def test_write_cuadre_workbook(tmp_path):
    out = tmp_path / "cuadre_469.xlsx"
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
    assert out.exists()
    wb = openpyxl.load_workbook(out, data_only=False)
    assert "469" in wb.sheetnames
    ws = wb["469"]
    assert ws["A1"].value == "CUADRE CUENTA 469"
    assert ws["A2"].value == "Total registros conciliados"
    assert ws["A3"].value == "Monto total conciliado"
    assert ws.freeze_panes == "A6"
    headers = [ws.cell(5, c).value for c in range(1, ws.max_column + 1)]
    assert "Fecha Mayor" in headers
    assert "Fecha Sistema" in headers
    assert headers.count("Fecha") == 0
    assert "CRUCE" in headers
    cruce_idx = headers.index("CRUCE") + 1
    val = ws.cell(6, cruce_idx).value
    assert isinstance(val, str) and val.startswith("=")


def test_write_cuadre_workbook_nullable_numeric_columns(tmp_path):
    """Regression: pandas 3 leaves float NaN after astype(str); column sizing must not use map(len)."""
    out = tmp_path / "cuadre_1280.xlsx"
    d = pd.Timestamp("2026-04-01")
    matched = pd.DataFrame(
        {
            "Ledger_Debito": [10.0, None],
            "Ledger_Cuenta": ["1280", "1280"],
            "Ledger_Fecha": [d, d],
            "Ledger_Ag": [1, 2],
            "Ledger_Asiento": [1, 2],
            "Ledger_Descripcion": ["a", None],
            "Ledger_Credito": [None, None],
            "System_IVA 10": [10.0, None],
            "System_Nro. Identific.": ["1", None],
            "System_Razon Social": ["X", None],
            "System_Fecha Comprobante": [d, None],
            "System_Nro. Comprobante": ["1", None],
            "System_Imponible 10": [100.0, None],
        }
    )
    write_cuadre_workbook(out, "1280", matched, pd.DataFrame(), pd.DataFrame(), ledger_side="Debito")
    assert out.stat().st_size > 0
