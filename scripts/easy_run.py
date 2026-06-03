"""
Ejecucion sencilla: lee CONCILIACION.ini y genera los Excel sin escribir comandos largos.

Uso:
  py -3 scripts/easy_run.py
  py -3 scripts/easy_run.py --config "C:\\ruta\\mi.ini"
"""

from __future__ import annotations

import argparse
import configparser
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from datetime import datetime, timezone  # noqa: E402

from ingestion.folder_discovery import discover_inputs  # noqa: E402
from ingestion.validate_inputs import validate_account_inputs  # noqa: E402
from pipeline.errors import audit_error_fields, error_from_exception, format_user_message  # noqa: E402
from pipeline.logging_audit import setup_run_logging  # noqa: E402
from pipeline.run_manifest import build_run_manifest, write_run_manifest  # noqa: E402
from pipeline.run_reconciliation import run_account  # noqa: E402

from ui.services import AccountRunResult  # noqa: E402


def _strip_val(s: str | None) -> str:
    if s is None:
        return ""
    return s.strip().strip('"')


def _resolve_path(base: Path, raw: str) -> Path | None:
    raw = _strip_val(raw)
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = (base / p).resolve()
    return p


def _parse_non_negative_float(raw: str | None, *, default: float = 0.0, key: str = "") -> float:
    s = _strip_val(raw)
    if not s:
        return default
    try:
        v = float(s)
    except ValueError as e:
        raise ValueError(f"Valor invalido para {key or 'float'}: {raw!r}") from e
    if v < 0:
        raise ValueError(f"Valor invalido para {key or 'float'}: debe ser >= 0")
    return v


def _load_config(path: Path) -> configparser.ConfigParser:
    if not path.is_file():
        print()
        print("  No se encontro el archivo de configuracion:")
        print(f"    {path}")
        print()
        print("  Pasos:")
        print("    1. Copie CONCILIACION.ini.example y renombrelo a CONCILIACION.ini")
        print("    2. Abra CONCILIACION.ini con el Bloc de notas y complete las rutas")
        print()
        sys.exit(1)
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    return cp


def main() -> None:
    ap = argparse.ArgumentParser(description="Conciliacion desde CONCILIACION.ini")
    ap.add_argument(
        "--config",
        type=Path,
        default=_ROOT / "CONCILIACION.ini",
        help="Ruta al archivo INI (por defecto: CONCILIACION.ini junto a Conciliar.bat)",
    )
    ap.add_argument("-v", "--verbose", action="store_true", help="Mas detalle en el log")
    args = ap.parse_args()
    ini_path = args.config.resolve()
    base = ini_path.parent

    cp = _load_config(ini_path)
    gen = cp["general"] if cp.has_section("general") else {}

    salida = _resolve_path(base, gen.get("salida", "salidas"))
    if salida is None:
        salida = base / "salidas"
    salida.mkdir(parents=True, exist_ok=True)

    fecha_desde = _strip_val(gen.get("fecha_desde"))
    fecha_hasta = _strip_val(gen.get("fecha_hasta"))
    try:
        amount_tolerance_1279 = _parse_non_negative_float(
            gen.get("amount_tolerance_1279"),
            default=0.0,
            key="amount_tolerance_1279",
        )
    except ValueError as e:
        print()
        print(f"  Error en CONCILIACION.ini: {e}")
        print("  Corrija [general] amount_tolerance_1279 y vuelva a intentar.")
        print()
        sys.exit(1)
    sql_1279 = _resolve_path(base, gen.get("sql_1279"))
    famafa_compras = _resolve_path(base, gen.get("famafa_compras"))
    famafa_ventas = _resolve_path(base, gen.get("famafa_ventas"))
    famafa_by_acc: dict[str, Path] = {}

    carpeta = _resolve_path(base, gen.get("carpeta_insumos", ""))
    if carpeta is None:
        sibling = base.parent / "Automatizaci\u00f3n conciliaciones"
        if sibling.is_dir():
            carpeta = sibling
    discovered = discover_inputs(carpeta) if carpeta and carpeta.is_dir() else None

    jobs: list[tuple[str, Path, dict]] = []

    def ledger(acc: str) -> Path | None:
        led = None
        if cp.has_section(acc):
            led = _resolve_path(base, cp[acc].get("mayorpc"))
        if (led is None or not led.is_file()) and discovered and acc in discovered.ledgers:
            led = discovered.ledgers[acc]
        return led

    if discovered:
        if sql_1279 is None or not sql_1279.is_file():
            sql_1279 = discovered.sql_1279
        if famafa_compras is None or not famafa_compras.is_file():
            if discovered.famafa_compras:
                famafa_compras = next(iter(discovered.famafa_compras.values()))
        famafa_by_acc = dict(discovered.famafa_compras)
        if famafa_ventas is None or not famafa_ventas.is_file():
            famafa_ventas = discovered.famafa_ventas
        if not fecha_desde and discovered.fecha_desde:
            fecha_desde = discovered.fecha_desde
        if not fecha_hasta and discovered.fecha_hasta:
            fecha_hasta = discovered.fecha_hasta

    for acc in ("1279", "469", "1280", "2874"):
        led = ledger(acc)
        if led is None or not led.is_file():
            continue
        extra: dict = {}
        if acc == "1279":
            if sql_1279 is None or not sql_1279.is_file():
                print(f"  [1279] Se omite: falta 'sql_1279' en [general] o el archivo no existe.")
                continue
            extra["sql_csv"] = sql_1279
            extra["fecha_desde"] = fecha_desde or None
            extra["fecha_hasta"] = fecha_hasta or None
            extra["amount_tolerance_1279"] = amount_tolerance_1279
        elif acc in ("469", "1280"):
            fc_acc = famafa_by_acc.get(acc) or famafa_compras
            if fc_acc is None or not fc_acc.is_file():
                print(f"  [{acc}] Se omite: falta 'famafa_compras' en [general] o el archivo no existe.")
                continue
            extra["famafa_compras"] = fc_acc
        else:
            if famafa_ventas is None or not famafa_ventas.is_file():
                print(f"  [2874] Se omite: falta 'famafa_ventas' en [general] o el archivo no existe.")
                continue
            extra["famafa_ventas"] = famafa_ventas

        out = salida / f"CUADRE_{acc}_reconciliacion.xlsx"
        jobs.append((acc, led, {**extra, "output": out}))

    if not jobs:
        print()
        print("  No hay cuentas listas para procesar.")
        print("  Revise CONCILIACION.ini:")
        print("    - En [1279]..[2874]: 'mayorpc' = ruta al archivo mayor (txt)")
        print("    - En [general]: sql_1279, famafa_compras y/o famafa_ventas segun corresponda")
        print()
        sys.exit(1)

    pre_errors: list[str] = []
    pre_warnings: list[str] = []
    for acc, led, kw in jobs:
        rep = validate_account_inputs(
            acc,
            ledger_path=led,
            sql_csv=kw.get("sql_csv"),
            famafa_compras=kw.get("famafa_compras"),
            famafa_ventas=kw.get("famafa_ventas"),
            fecha_desde=kw.get("fecha_desde"),
            fecha_hasta=kw.get("fecha_hasta"),
        )
        pre_errors.extend(rep.errors)
        pre_warnings.extend(rep.warnings)
    if pre_errors:
        print()
        print("  Validacion previa fallida:")
        for err in pre_errors:
            print(f"    - {err}")
        print()
        sys.exit(1)
    if pre_warnings:
        print("  Advertencias de validacion previa:")
        for warn in pre_warnings:
            print(f"    - {warn}")
        print()

    run_id, log_path, audit_path, audit = setup_run_logging(
        salida,
        console=True,
        verbose=args.verbose,
    )
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    log = logging.getLogger("conciliation")
    batch_results: list[AccountRunResult] = []

    print()
    print("  Conciliacion en curso...")
    print(f"  Salida: {salida}")
    print(f"  Registro (log): {log_path}")
    print(f"  Auditoria (JSON): {audit_path}")
    print(f"  Ejecucion run_id: {run_id}")
    print()

    audit.record(
        "easy_run_start",
        "ok",
        config_path=str(ini_path),
        jobs_planned=len(jobs),
        accounts=[j[0] for j in jobs],
    )
    log.info("Easy run start config=%s jobs=%s", ini_path, len(jobs))

    ok: list[Path] = []
    errors = 0
    try:
        for acc, led, kw in jobs:
            print(f"  -> Cuenta {acc} ...")
            log.info("Easy run job start account=%s ledger=%s", acc, led)
            try:
                path = run_account(acc, led, audit=audit, **kw)
                ok.append(path)
                print(f"     Listo: {path.name}")
                audit.record("easy_run_job_ok", "ok", account=acc, output=str(path))
                batch_results.append(AccountRunResult(account=acc, ok=True, output=path))
            except Exception as e:
                errors += 1
                code, msg = error_from_exception(e)
                err = format_user_message(code, msg)
                print(f"     ERROR en cuenta {acc}: {err}")
                batch_results.append(
                    AccountRunResult(account=acc, ok=False, error=err, error_code=code.value)
                )
                audit.record("easy_run_job_failed", "failed", account=acc, **audit_error_fields(e))
                logging.getLogger("conciliation").exception("Easy run job failed account=%s", acc)

        ended_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        manifest = build_run_manifest(
            run_id=run_id,
            source="easy_run",
            salida=salida,
            accounts=[j[0] for j in jobs],
            results=batch_results,
            log_path=log_path,
            audit_path=audit_path,
            started_at=started_at,
            ended_at=ended_at,
            inputs={"config_path": str(ini_path)},
        )
        manifest_path = write_run_manifest(salida / "logs" / f"run_manifest_{run_id}.json", manifest)

        if errors:
            audit.record(
                "easy_run_complete",
                "failed",
                outputs=[str(p) for p in ok],
                error_count=errors,
            )
        else:
            audit.record(
                "easy_run_complete",
                "ok",
                outputs=[str(p) for p in ok],
                error_count=0,
            )
    finally:
        audit.close()

    print()
    if ok:
        print(f"  Terminado. {len(ok)} archivo(s) generado(s).")
        for p in ok:
            print(f"    - {p}")
    if errors:
        print(f"  Hubo {errors} error(es). Revise el log y la auditoria JSON.")
    print(f"  Log: {log_path}")
    print(f"  Auditoria: {audit_path}")
    if "manifest_path" in locals():
        print(f"  Manifiesto: {manifest_path}")
    print()

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
