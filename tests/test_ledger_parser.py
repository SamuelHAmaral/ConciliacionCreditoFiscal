"""Tests for ledger parsing."""

from pathlib import Path

import pytest

from ingestion.ledger_parser import parse_ledger


_RECON = Path(__file__).resolve().parents[1]
_WS = _RECON.parent


def _find_mayorpc(account: str) -> Path | None:
    base = _WS / "Automatizaci\u00f3n conciliaciones"
    if not base.is_dir():
        return None
    for p in base.rglob(f"mayorpc*{account}*.txt"):
        return p
    for p in base.rglob("mayorpc*.txt"):
        if account in p.read_text(encoding="latin-1", errors="ignore")[:5000]:
            return p
    return None


MAYORPC_469 = _find_mayorpc("469")
MAYORPC_2874 = _find_mayorpc("2874")


@pytest.mark.skipif(MAYORPC_469 is None, reason="Sample mayorpc 469 not found under workspace")
def test_parse_ledger_469_smoke():
    assert MAYORPC_469 is not None
    df = parse_ledger(MAYORPC_469, 469)
    assert len(df) > 100
    assert "Descripcion" in df.columns
    assert "Debito" in df.columns
    assert "Credito" in df.columns
    xfer = df["Descripcion"].str.contains("Transferencia de saldo", case=False, na=False)
    assert not xfer.any()
    assert df["Debito"].notna().sum() + df["Credito"].notna().sum() > 0


@pytest.mark.skipif(MAYORPC_2874 is None, reason="Sample mayorpc 2874 not found under workspace")
def test_parse_ledger_2874_credito_rows():
    assert MAYORPC_2874 is not None
    df = parse_ledger(MAYORPC_2874, 2874)
    cred = df["Credito"].dropna()
    deb = df["Debito"].dropna()
    assert len(cred) > 0 or len(deb) > 0


def test_parse_ledger_filters_transfer(tmp_path: Path):
    p = tmp_path / "m.txt"
    p.write_text(
        " CUENTA:   469  Test\n"
        "  1/04/26 09      71 SOME TX    218186 X -                100,00                          GS.\n"
        "  1/04/26 00  391007 Transferencia de saldo                   T            36.874.191,00                          GS.\n",
        encoding="latin-1",
    )
    df = parse_ledger(p, 469)
    assert len(df) == 1
    assert df.iloc[0]["Debito"] == 100.0


def test_parse_ledger_filters_transfer_variants(tmp_path: Path):
    p = tmp_path / "m_variants.txt"
    p.write_text(
        " CUENTA:   1279  Test\n"
        "  2/04/26 09      72 TRASPASO DE SALDOS                  T            10.000,00                          GS.\n"
        "  2/04/26 09      73 SALDO TRANSFERENCIA INTERNA         T            15.000,00                          GS.\n"
        "  2/04/26 09      74 NC CLIENTE X                        T               250,00                          GS.\n",
        encoding="latin-1",
    )
    df = parse_ledger(p, 1279)
    assert len(df) == 1
    assert "NC CLIENTE X" in str(df.iloc[0]["Descripcion"])
