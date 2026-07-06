"""Tests for pre-run input validation."""

from pathlib import Path

from ingestion.validate_inputs import (
    validate_account_inputs,
    validate_1279_dates,
    validate_ledger_date_coverage,
)


def test_validate_1279_dates_invalid_range():
    rep = validate_1279_dates("2026-05-01", "2026-04-30")
    assert rep.errors
    assert "fecha_desde" in rep.errors[0]


def test_validate_1279_warns_when_sql_narrower_than_range(tmp_path: Path):
    sql = tmp_path / "sql.csv"
    sql.write_text(
        "Fecha_Cont,Nro. de Documento,Nombre,Num_Factura,Imponible ML sin IVA,IVA ML\n"
        "29/04/2026,1,A,FA-1,1000,100\n"
        "30/04/2026,2,B,FA-2,2000,200\n",
        encoding="utf-8",
    )
    rep = validate_1279_dates(
        "2026-04-01",
        "2026-04-30",
        sql_path=sql,
    )
    assert not rep.errors
    assert any("mas estrecho" in w for w in rep.warnings)


def test_validate_1279_no_narrow_warning_when_sql_covers_range(tmp_path: Path):
    sql = tmp_path / "sql.csv"
    sql.write_text(
        "Fecha_Cont,Nro. de Documento,Nombre,Num_Factura,Imponible ML sin IVA,IVA ML\n"
        "01/04/2026,1,A,FA-1,1000,100\n"
        "30/04/2026,2,B,FA-2,2000,200\n",
        encoding="utf-8",
    )
    rep = validate_1279_dates(
        "2026-04-01",
        "2026-04-30",
        sql_path=sql,
    )
    assert not rep.errors
    assert not any("mas estrecho" in w for w in rep.warnings)


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


def test_validate_ledger_date_coverage_1279_warns_outside_window(tmp_path: Path):
    ledger = tmp_path / "mayorpc_1279.txt"
    ledger.write_text(
        " CUENTA:   1279  Test\n"
        "  1/04/26 09      71 ROW A    218186 X -                100,00                          GS.\n"
        " 30/04/26 09      72 ROW B    218186 X -                200,00                          GS.\n",
        encoding="latin-1",
    )
    warnings = validate_ledger_date_coverage(
        "1279",
        ledger,
        fecha_desde="2026-04-30",
        fecha_hasta="2026-04-30",
    )
    assert any("mas amplio" in w for w in warnings)


def test_validate_ledger_date_coverage_469_no_overlap(tmp_path: Path):
    ledger = tmp_path / "mayorpc_469.txt"
    ledger.write_text(
        " CUENTA:   469  Test\n"
        "  1/03/26 09      71 ROW A    218186 X -                100,00                          GS.\n",
        encoding="latin-1",
    )
    famafa = tmp_path / "FAMAFA COMPRAS 469.csv"
    famafa.write_text(
        "Tipo Comprobante,IVA 10,Fecha Emision\n109,100,01/04/2026\n",
        encoding="utf-8",
    )
    warnings = validate_ledger_date_coverage(
        "469",
        ledger,
        system_path=famafa,
    )
    assert any("no solapan" in w for w in warnings)
