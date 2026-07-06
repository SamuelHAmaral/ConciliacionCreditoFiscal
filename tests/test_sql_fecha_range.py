"""Tests for SQL Fecha_Cont range helpers."""

from pathlib import Path

from ingestion.sql_fecha_range import (
    infer_fecha_range_from_sql,
    infer_fecha_range_from_sql_filename,
    infer_last_sql_day,
    sql_fecha_coverage,
)


def test_infer_fecha_from_sql_filename_only():
    p = Path("SQL - Cuenta1279_2026-04-30.xlsx")
    assert infer_fecha_range_from_sql_filename(p) == ("2026-04-30", "2026-04-30")
    assert infer_fecha_range_from_sql(p) == ("2026-04-30", "2026-04-30")


def test_infer_fecha_from_sql_content(tmp_path: Path):
    sql = tmp_path / "sql.csv"
    sql.write_text(
        "Fecha_Cont,Nro. de Documento,Nombre,Num_Factura,Imponible ML sin IVA,IVA ML\n"
        "29/04/2026,1,A,FA-1,1000,100\n"
        "30/04/2026,2,B,FA-2,2000,200\n",
        encoding="utf-8",
    )
    assert infer_fecha_range_from_sql(sql) == ("2026-04-29", "2026-04-30")
    coverage = sql_fecha_coverage(sql)
    assert coverage is not None
    assert coverage.fecha_desde == "2026-04-29"
    assert coverage.fecha_hasta == "2026-04-30"
    assert coverage.distinct_days == 2
    assert coverage.row_count == 2


def test_infer_last_sql_day_from_content(tmp_path: Path):
    sql = tmp_path / "sql.csv"
    sql.write_text(
        "Fecha_Cont,Nro. de Documento,Nombre,Num_Factura,Imponible ML sin IVA,IVA ML\n"
        "29/04/2026,1,A,FA-1,1000,100\n"
        "30/04/2026,2,B,FA-2,2000,200\n",
        encoding="utf-8",
    )
    assert infer_last_sql_day(sql) == "2026-04-30"


def test_infer_last_sql_day_from_filename():
    p = Path("SQL - Cuenta1279_2026-04-30.xlsx")
    assert infer_last_sql_day(p) == "2026-04-30"
