"""Regression: 469 matches by amount only (CRUCE 469 — invoice date != booking date)."""

from pathlib import Path

import pandas as pd

from config.account_config import match_mode_for
from pipeline.run_reconciliation import run_account
from qa.uat_compare import _count_cuadre_sections, _load_cuadre_sheet


def test_469_match_mode_is_amount_only():
    assert match_mode_for("469") == "amount_only"
    assert match_mode_for("1280") == "amount_and_date"
    assert match_mode_for("2874") == "amount_and_date"
    assert match_mode_for("1279") == "amount_and_date"


def test_469_pairs_same_amount_on_different_dates(tmp_path: Path):
    ledger_path = tmp_path / "mayorpc_469.txt"
    ledger_path.write_text(
        " CUENTA:    469  Operaciones Gravadas y Exentas\n"
        "  6/04/26 09     17 CM 5474 - ANEXO SERV    218179 CAPITAL H          T          180.554,00                          GS.\n"
        "  6/04/26 00  433247 Transferencia de saldo                   T             180.554,00                          GS.\n",
        encoding="latin-1",
    )
    famafa = tmp_path / "FAMAFA COMPRAS 469.csv"
    famafa.write_text(
        "Tipo Comprobante,Nro. Timbrado,IVA 10,Fecha Emision,Razon Social,Nro. Comprobante\n"
        "109,80011111,180554,01/04/2026,CAPITAL HUMANO S.R.L.,001-001-0004289\n"
        "109,12345678,180554,01/04/2026,RETENCION EXCLUIDA,001-001-0000001\n"
        "109,80011111,0,01/04/2026,IVA CERO,001-001-0000002\n",
        encoding="utf-8",
    )
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    path = run_account(
        "469",
        ledger_path,
        famafa_compras=famafa,
        match_469_amount_only=False,
        output=out,
    )
    assert path == out
    sections = _count_cuadre_sections(_load_cuadre_sheet(out, "469"), "469")
    assert sections["matched"] == 1
    assert sections["pend_ledger"] == 0
    assert sections["pend_system"] == 0

    df = _load_cuadre_sheet(out, "469")
    fecha_mayor = pd.to_datetime(df["Fecha Mayor"], errors="coerce", dayfirst=True)
    fecha_sys = pd.to_datetime(df["Fecha Sistema"], errors="coerce", dayfirst=True)
    assert fecha_mayor.iloc[0].day == 6
    assert fecha_sys.iloc[0].day == 1
