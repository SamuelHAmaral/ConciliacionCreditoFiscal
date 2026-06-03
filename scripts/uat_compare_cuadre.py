"""
UAT: run reconciliation on sample folder and compare metrics to manual CUADRE models.

Usage (from reconciliation_engine):
  py -3 scripts/uat_compare_cuadre.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from ingestion.folder_discovery import discover_inputs  # noqa: E402
from pipeline.run_reconciliation import run_account  # noqa: E402
from qa.uat_compare import compare_with_golden  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("uat_compare")

FECHA_DESDE = "2026-04-01"
FECHA_HASTA = "2026-04-30"
_INSUMOS = _ROOT.parent / "Automatizaci\u00f3n conciliaciones"

def main() -> None:
    root = _INSUMOS
    if not root.is_dir():
        logger.error("Sample folder not found: %s", root)
        sys.exit(1)

    discovered = discover_inputs(root)
    out_dir = _ROOT / "output_uat_compare"
    out_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("  UAT compare - engine vs manual CUADRE models")
    print(f"  Period 1279: {FECHA_DESDE} .. {FECHA_HASTA}")
    print()

    failures = 0
    outputs_by_account: dict[str, Path] = {}
    for acc in ("1279", "469", "1280", "2874"):
        if acc not in discovered.ledgers:
            logger.warning("[%s] No mayor file - skip", acc)
            failures += 1
            continue

        out_path = out_dir / f"CUADRE_{acc}_uat_compare.xlsx"
        kw: dict = {"output": out_path}
        if acc == "1279":
            if not discovered.sql_1279:
                logger.warning("[%s] No SQL file - skip", acc)
                failures += 1
                continue
            kw["sql_csv"] = discovered.sql_1279
            kw["fecha_desde"] = FECHA_DESDE
            kw["fecha_hasta"] = FECHA_HASTA
        elif acc in ("469", "1280"):
            fc = discovered.famafa_compras.get(acc)
            if not fc:
                logger.warning("[%s] No FAMAFA Compras - skip", acc)
                failures += 1
                continue
            kw["famafa_compras"] = fc
        else:
            if not discovered.famafa_ventas:
                logger.warning("[%s] No FAMAFA Ventas - skip", acc)
                failures += 1
                continue
            kw["famafa_ventas"] = discovered.famafa_ventas

        logger.info("[%s] Running engine...", acc)
        try:
            run_account(acc, discovered.ledgers[acc], **kw)
        except Exception as e:
            logger.error("[%s] Engine failed: %s", acc, e)
            failures += 1
            continue
        outputs_by_account[acc] = out_path

    for row in compare_with_golden(outputs_by_account, models_root=root):
        print(f"  Account {row.account}")
        if row.model_path is None:
            print(f"    Model:  MISSING ({row.detail})")
            print(f"    Engine: {row.output_path.name}")
            failures += 1
        else:
            print(f"    Model:  {row.model_path.name}  rows={row.model_total}")
            print(f"    Engine: {row.output_path.name}  rows={row.output_total}")
            print(
                f"    Side-by-side rows (ledger+system): engine={row.output_matched} "
                f"(model CRUCE=0 rows={row.model_matched})"
            )
        print()

    if failures:
        print(f"  Completed with {failures} skipped account(s).")
    else:
        print("  All accounts processed.")
    print()


if __name__ == "__main__":
    main()
