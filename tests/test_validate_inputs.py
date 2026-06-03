"""Tests for pre-run input validation."""

from pathlib import Path

from ingestion.validate_inputs import validate_account_inputs, validate_1279_dates


def test_validate_1279_dates_invalid_range():
    rep = validate_1279_dates("2026-05-01", "2026-04-30")
    assert rep.errors
    assert "fecha_desde" in rep.errors[0]


def test_validate_1279_schema_missing_columns(tmp_path: Path):
    ledger = tmp_path / "mayorpc_1279.txt"
    ledger.write_text("CUENTA: 1279\n", encoding="latin-1")
    sql = tmp_path / "SQL_1279_2026-04-30.csv"
    sql.write_text("Fecha_Cont,Nombre\n2026-04-30,ACME\n", encoding="utf-8")

    rep = validate_account_inputs(
        "1279",
        ledger_path=ledger,
        sql_csv=sql,
        fecha_desde="2026-04-01",
        fecha_hasta="2026-04-30",
    )
    assert rep.errors
    assert "IVA ML" in rep.errors[0]


def test_validate_469_schema_missing_tipo(tmp_path: Path):
    ledger = tmp_path / "mayorpc_469.txt"
    ledger.write_text("CUENTA: 469\n", encoding="latin-1")
    famafa = tmp_path / "FAMAFA COMPRAS 469.csv"
    famafa.write_text("IVA 10,Fecha Emision\n10,01/04/2026\n", encoding="utf-8")

    rep = validate_account_inputs("469", ledger_path=ledger, famafa_compras=famafa)
    assert rep.errors
    assert "Tipo Comprobante" in rep.errors[0]
