"""Regression test for Account 2874 structural filtering and matching."""

from pathlib import Path

import pandas as pd

from ingestion.ledger_parser import parse_ledger
from reconcile.matcher import match_exact_one_to_one
from rules.account_rules import add_ledger_match_amount, filter_famafa_2874


def test_2874_structural_regression_end_to_end(tmp_path: Path):
    """Lock 2874 rules: Tipo 110 + IVA10 != 0 + strict same-day credit match."""
    ledger_path = tmp_path / "mayorpc_2874.txt"
    ledger_path.write_text(
        " CUENTA:   2874  RETENCIONES A COBRAR\n"
        " 08/04/2026 09 700111 CLIENTE ALPHA RETENCION                         T                0,00             45.500,00   GS.\n"
        " 17/04/2026 09 700222 CLIENTE BETA RETENCION                          T                0,00             12.340,00   GS.\n"
        " 29/04/2026 09 700333 CLIENTE GAMMA RETENCION                         T                0,00             98.765,00   GS.\n"
        " 20/04/2026 00 700999 Transferencia de saldo                          T                0,00        365.952.544,00   GS.\n",
        encoding="latin-1",
    )

    ledger_df = parse_ledger(ledger_path, 2874)
    assert set(ledger_df["Asiento"].astype(str)) == {"700111", "700222", "700333"}

    system_raw = pd.DataFrame(
        {
            "Tipo Comprobante": [110, 110, 110, 110, 109],
            "Nro. Timbrado": ["A1", "A2", "A3", "A4", "A5"],
            "IVA 10": [45500.0, 12340.0, 98765.0, 0.0, 45500.0],
            "Fecha Emision": [
                "08/04/2026",
                "17/04/2026",
                "29/04/2026",
                "22/04/2026",
                "08/04/2026",
            ],
            "Cliente": [
                "Cliente Alpha",
                "Cliente Beta",
                "Cliente Gamma",
                "Should Be Removed By IVA Zero",
                "Should Be Removed By Tipo",
            ],
        }
    )

    system_df = filter_famafa_2874(system_raw)
    assert len(system_df) == 3
    assert set(system_df["Cliente"]) == {"Cliente Alpha", "Cliente Beta", "Cliente Gamma"}

    ledger_match = add_ledger_match_amount(ledger_df, "Credito")
    ledger_match = ledger_match.copy()
    ledger_match["_match_date"] = pd.to_datetime(ledger_match["Fecha"], errors="coerce").dt.normalize()

    matched, unmatched_ledger, unmatched_system = match_exact_one_to_one(ledger_match, system_df)

    assert len(matched) == 3
    assert unmatched_ledger.empty
    assert unmatched_system.empty
    assert set(matched["Ledger_Asiento"].astype(str)) == {"700111", "700222", "700333"}
    assert set(matched["System_Cliente"]) == {"Cliente Alpha", "Cliente Beta", "Cliente Gamma"}
    assert (matched["Difference"].abs() <= 1e-9).all()
