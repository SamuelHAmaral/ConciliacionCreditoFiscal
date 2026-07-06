"""Tests for folder discovery."""

from pathlib import Path

import pytest

from ingestion.folder_discovery import discover_inputs, infer_fecha_range_from_sql

_WS = Path(__file__).resolve().parents[2].parent
_INSUMOS = _WS / "Automatizaci\u00f3n conciliaciones"


@pytest.mark.skipif(not _INSUMOS.is_dir(), reason="Sample insumos folder missing")
def test_discover_sample_folder():
    d = discover_inputs(_INSUMOS)
    assert "1279" in d.ledgers or "469" in d.ledgers
    if d.sql_1279:
        fd, fh = infer_fecha_range_from_sql(d.sql_1279)
        assert fd is not None and fh is not None
        assert fd <= fh
        assert d.fecha_desde == fd
        assert d.fecha_hasta == fh


def test_discover_sets_fecha_from_sql_content(tmp_path: Path):
    root = tmp_path / "insumos"
    acc_dir = root / "Cuenta 1279 IVA CF 10%"
    acc_dir.mkdir(parents=True)
    (acc_dir / "mayorpc 1279.txt").write_text("CUENTA: 1279\n", encoding="latin-1")
    (acc_dir / "SQL - Cuenta1279_2026-04-30.csv").write_text(
        "Fecha_Cont,Nro. de Documento,Nombre,Num_Factura,Imponible ML sin IVA,IVA ML\n"
        "29/04/2026,1,A,FA-1,1000,100\n"
        "30/04/2026,2,B,FA-2,2000,200\n",
        encoding="utf-8",
    )
    d = discover_inputs(root)
    assert d.fecha_desde == "2026-04-29"
    assert d.fecha_hasta == "2026-04-30"
