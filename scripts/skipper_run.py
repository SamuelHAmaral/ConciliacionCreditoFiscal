#!/usr/bin/env python3
"""
CLI batch runner for Skipper / Amaral studio automation.

Discovers inputs from an insumos folder (or a ZIP of that folder), runs reconciliation,
optional model compare.

Usage:
  py -3 scripts/skipper_run.py --insumos "D:\\mes\\insumos" --salida "D:\\mes\\salida"
  py -3 scripts/skipper_run.py --insumos ... --salida ... --fecha-desde 2026-04-30 --fecha-hasta 2026-04-30
  py -3 scripts/skipper_run.py --insumos ... --salida ... --solo-ultimo-dia
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

from qa.uat_compare import compare_with_golden, write_variance_csv  # noqa: E402
from ui.services import run_batch  # noqa: E402
from ui.skipper_execution import (  # noqa: E402
    SkipperJobParams,
    prepare_insumos_dir,
    run_config_from_insumos,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Skipper batch runner for fiscal credit reconciliation")
    p.add_argument("--insumos", required=True, type=Path, help="Monthly input folder (or folder containing a ZIP)")
    p.add_argument("--salida", required=True, type=Path, help="Output folder for CUADRE and logs")
    p.add_argument("--fecha-desde", default=None, help="1279 Desde (YYYY-MM-DD)")
    p.add_argument("--fecha-hasta", default=None, help="1279 Hasta (YYYY-MM-DD)")
    p.add_argument("--solo-ultimo-dia", dest="solo_ultimo_dia_sql", action="store_true")
    p.add_argument("--amount-tolerance-1279", type=float, default=0.01)
    p.add_argument(
        "--469-amount-only",
        dest="match_469_amount_only",
        action="store_true",
        help="Legacy. 469 already matches by amount via accounts.yml.",
    )
    p.add_argument("--models-root", type=Path, default=None, help="Folder with CUADRE modelo files")
    p.add_argument("--accounts", default="1279,469,1280,2874", help="Comma-separated account codes")
    p.add_argument("--email-to", default=None, help="Email CUADRE files to this address after the run")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        insumos = prepare_insumos_dir(args.insumos)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    params = SkipperJobParams(
        fecha_desde=args.fecha_desde,
        fecha_hasta=args.fecha_hasta,
        solo_ultimo_dia_sql=args.solo_ultimo_dia_sql,
        match_469_amount_only=args.match_469_amount_only,
        accounts=[a.strip() for a in args.accounts.split(",") if a.strip()],
        amount_tolerance_1279=args.amount_tolerance_1279,
    )
    cfg = run_config_from_insumos(insumos, args.salida.expanduser().resolve(), params)
    if cfg is None:
        print("ERROR: no mayor files discovered for requested accounts", file=sys.stderr)
        return 2

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
        report = write_variance_csv(variances, cfg.salida / "logs" / f"qa_variance_{stamp}.csv")
        print(f"QA variance: {report}")
        for row in variances:
            print(
                f"  {row.account}: engine={row.output_matched} model={row.model_matched} "
                f"status={row.status}"
            )

    if args.email_to:
        from reporting.email_export import deliver_cuadre_email, load_email_settings

        delivery = deliver_cuadre_email(
            attachments=[r.output for r in results if r.output],
            payload={"user": {"email": args.email_to}},
            settings=load_email_settings(),
            execution_id=run_id,
            failed_accounts=[r.account for r in results if not r.ok],
        )
        print(f"Email: {delivery.status} to={', '.join(delivery.to) or '-'} transport={delivery.transport}")
        if delivery.error:
            print(f"Email error: {delivery.error}")
        if delivery.status == "error":
            return 1

    return 0 if ok_n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
