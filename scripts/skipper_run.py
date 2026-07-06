#!/usr/bin/env python3
"""
CLI batch runner for Skipper / Amaral studio automation.

Discovers inputs from an insumos folder, runs reconciliation, optional model compare.

Usage:
  py -3 scripts/skipper_run.py --insumos "D:\\mes\\insumos" --salida "D:\\mes\\salida"
  py -3 scripts/skipper_run.py --insumos ... --salida ... --fecha-desde 2026-04-30 --fecha-hasta 2026-04-30
  py -3 scripts/skipper_run.py --insumos ... --salida ... --469-amount-only --models-root ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from ingestion.folder_discovery import discover_inputs  # noqa: E402
from qa.uat_compare import compare_with_golden, write_variance_csv  # noqa: E402
from ui.services import AccountJob, RunConfig, run_batch  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Skipper batch runner for fiscal credit reconciliation")
    p.add_argument("--insumos", required=True, type=Path, help="Monthly input folder")
    p.add_argument("--salida", required=True, type=Path, help="Output folder for CUADRE and logs")
    p.add_argument("--fecha-desde", default=None, help="1279 Desde (YYYY-MM-DD)")
    p.add_argument("--fecha-hasta", default=None, help="1279 Hasta (YYYY-MM-DD)")
    p.add_argument("--amount-tolerance-1279", type=float, default=0.01)
    p.add_argument("--469-amount-only", dest="match_469_amount_only", action="store_true")
    p.add_argument("--models-root", type=Path, default=None, help="Folder with CUADRE modelo files")
    p.add_argument("--accounts", default="1279,469,1280,2874", help="Comma-separated account codes")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    insumos = args.insumos.expanduser().resolve()
    salida = args.salida.expanduser().resolve()
    if not insumos.is_dir():
        print(f"ERROR: insumos folder not found: {insumos}", file=sys.stderr)
        return 2

    discovered = discover_inputs(insumos)
    wanted = [a.strip() for a in args.accounts.split(",") if a.strip()]
    jobs: list[AccountJob] = []
    for acc in wanted:
        mayor = discovered.ledgers.get(acc)
        if mayor and mayor.is_file():
            jobs.append(AccountJob(account=acc, ledger_path=mayor))

    if not jobs:
        print("ERROR: no mayor files discovered for requested accounts", file=sys.stderr)
        return 2

    cfg = RunConfig(
        salida=salida,
        jobs=jobs,
        sql_csv=discovered.sql_1279,
        famafa_compras=discovered.famafa_compras.get("469") or discovered.famafa_compras.get("1280"),
        famafa_compras_by_account=discovered.famafa_compras or None,
        famafa_ventas=discovered.famafa_ventas,
        fecha_desde=args.fecha_desde or discovered.fecha_desde,
        fecha_hasta=args.fecha_hasta or discovered.fecha_hasta,
        amount_tolerance_1279=args.amount_tolerance_1279,
        match_469_amount_only=args.match_469_amount_only,
    )

    run_id, log_path, audit_path, results = run_batch(
        cfg,
        verbose=args.verbose,
        console_log=True,
        ui_source="skipper_cli",
        skip_input_validation=False,
    )
    ok_n = sum(1 for r in results if r.ok)
    print(f"Run {run_id}: {ok_n}/{len(results)} accounts OK")
    print(f"Log: {log_path}")
    print(f"Audit: {audit_path}")

    outputs = {r.account: r.output for r in results if r.ok and r.output}
    metrics = {r.account: r.metrics for r in results if r.ok}
    models_root = args.models_root or insumos
    if models_root.is_dir() and outputs:
        variances = compare_with_golden(outputs, models_root=models_root, output_metrics=metrics)
        from datetime import datetime

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report = write_variance_csv(variances, salida / "logs" / f"qa_variance_{stamp}.csv")
        print(f"QA variance: {report}")
        for row in variances:
            print(
                f"  {row.account}: engine={row.output_matched} model={row.model_matched} "
                f"status={row.status}"
            )

    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
