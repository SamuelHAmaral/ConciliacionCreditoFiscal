"""
UAT helper: discover inputs under Automatización conciliaciones and run full reconciliation.

Environment variables (optional overrides):
  SQL_1279_CSV          - SQL extract for account 1279
  FAMAFA_COMPRAS_CSV    - FAMAFA Compras (469 and 1280 fallback)
  FAMAFA_VENTAS_CSV     - FAMAFA Ventas (2874)
  FECHA_DESDE           - ISO date, default 2026-04-01 (1279 Fecha_Cont filter)
  FECHA_HASTA           - ISO date, default 2026-04-30
  OUTPUT_DIR            - default ./output_uat
  INSUMOS_DIR           - override discovery root folder
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from ingestion.folder_discovery import discover_inputs  # noqa: E402
from ingestion.ledger_parser import parse_ledger  # noqa: E402
from pipeline.run_reconciliation import run_account  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("uat")


def main() -> None:
    insumos = os.environ.get("INSUMOS_DIR")
    if insumos:
        root = Path(insumos)
    else:
        root = _ROOT.parent / "Automatizaci\u00f3n conciliaciones"

    discovered = discover_inputs(root)
    for acc, path in sorted(discovered.ledgers.items()):
        df = parse_ledger(path, acc)
        logger.info("Parsed ledger account=%s file=%s rows=%s", acc, path.name, len(df))

    out_dir = Path(os.environ.get("OUTPUT_DIR", "output_uat"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fd = os.environ.get("FECHA_DESDE", "2026-04-01")
    fh = os.environ.get("FECHA_HASTA", "2026-04-30")

    sql = os.environ.get("SQL_1279_CSV") or (
        str(discovered.sql_1279) if discovered.sql_1279 else None
    )
    if sql and Path(sql).exists() and "1279" in discovered.ledgers:
        run_account(
            "1279",
            discovered.ledgers["1279"],
            sql_csv=Path(sql),
            fecha_desde=fd,
            fecha_hasta=fh,
            output=out_dir / "CUADRE_1279_uat.xlsx",
        )
    else:
        logger.info("Skip 1279 full run (no SQL file)")

    fc_env = os.environ.get("FAMAFA_COMPRAS_CSV")
    for acc in ("469", "1280"):
        if acc not in discovered.ledgers:
            continue
        fc = fc_env or (
            str(discovered.famafa_compras[acc])
            if acc in discovered.famafa_compras
            else None
        )
        if fc and Path(fc).exists():
            run_account(
                acc,
                discovered.ledgers[acc],
                famafa_compras=Path(fc),
                output=out_dir / f"CUADRE_{acc}_uat.xlsx",
            )
        else:
            logger.info("Skip %s full run (no FAMAFA Compras file)", acc)

    fv = os.environ.get("FAMAFA_VENTAS_CSV") or (
        str(discovered.famafa_ventas) if discovered.famafa_ventas else None
    )
    if fv and Path(fv).exists() and "2874" in discovered.ledgers:
        run_account(
            "2874",
            discovered.ledgers["2874"],
            famafa_ventas=Path(fv),
            output=out_dir / "CUADRE_2874_uat.xlsx",
        )
    else:
        logger.info("Skip 2874 full run (no FAMAFA Ventas file)")


if __name__ == "__main__":
    main()
