"""Regression test for Account 1280 structural segregation and matching."""

from pathlib import Path

import pandas as pd

from ingestion.ledger_parser import parse_ledger
from reconcile.matcher import match_exact_one_to_one
from rules.account_rules import add_ledger_match_amount, filter_famafa_1280


def test_1280_structural_regression_end_to_end(tmp_path: Path):
    """Lock the 1280 business rules with known April mappings."""
    ledger_path = tmp_path / "mayorpc_1280.txt"
    ledger_path.write_text(
        " CUENTA:   1280  RETENCIONES DEL EXTERIOR\n"
        " 30/04/2026 09 126433 AMAZON WEB SERVICES DESARROLLO                 T            12.349,00                          GS.\n"
        " 15/04/2026 09 258915 CLEARSTREAM INVEST                              T            29.558,00                          GS.\n"
        " 24/04/2026 09 214697 APPLE PAY                                       T            86.747,00                          GS.\n"
        " 11/04/2026 00 325674 Transferencia de saldo                          T       365.952.544,00                          GS.\n",
        encoding="latin-1",
    )

    ledger_df = parse_ledger(ledger_path, 1280)
    assert set(ledger_df["Asiento"].astype(str)) == {"126433", "258915", "214697"}

    system_raw = pd.DataFrame(
        {
            "Tipo Comprobante": [109, 109, 109, 109, 109, 110],
            "Nro. Timbrado": [
                "12345678",
                "12345678",
                "12345678",
                "12345678",
                "99999999",
                "12345678",
            ],
            "IVA 10": [12349.0, 29558.0, 86747.0, 0.0, 999.0, 12349.0],
            "Fecha Emision": [
                "30/04/2026",
                "15/04/2026",
                "24/04/2026",
                "10/04/2026",
                "30/04/2026",
                "30/04/2026",
            ],
            "Proveedor": [
                "Amazon Web Services Desarrollo",
                "Clearstream Invest",
                "Apple Pay",
                "Should Be Removed By IVA Zero",
                "Should Be Removed By Timbrado",
                "Should Be Removed By Tipo",
            ],
        }
    )

    system_df = filter_famafa_1280(system_raw)
    assert len(system_df) == 3
    assert set(system_df["Proveedor"]) == {
        "Amazon Web Services Desarrollo",
        "Clearstream Invest",
        "Apple Pay",
    }

    ledger_match = add_ledger_match_amount(ledger_df, "Debito")
    ledger_match = ledger_match.copy()
    ledger_match["_match_date"] = pd.to_datetime(ledger_match["Fecha"], errors="coerce").dt.normalize()

    matched, unmatched_ledger, unmatched_system = match_exact_one_to_one(ledger_match, system_df)

    assert len(matched) == 3
    assert unmatched_ledger.empty
    assert unmatched_system.empty
    assert set(matched["Ledger_Asiento"].astype(str)) == {"126433", "258915", "214697"}
    assert set(matched["System_Proveedor"]) == {
        "Amazon Web Services Desarrollo",
        "Clearstream Invest",
        "Apple Pay",
    }
    assert (matched["Difference"].abs() <= 1e-9).all()
