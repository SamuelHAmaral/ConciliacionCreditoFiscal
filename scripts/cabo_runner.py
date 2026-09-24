#!/usr/bin/env python3
"""
Cabo / Kowalski entry for Skipper production runs.

This is what Kowalski launches via run_cabo.sh (Linux) or run_cabo.bat
(Windows). It is not skipper_run.py (that CLI never talks to Skipper).

Flow:
  1. GET  {SKIPPER_API_BASE_URL}/api/execution/{EXECUTION_ID}
     (Bearer SKIPPER_API_TOKEN; form fields + file_original_names)
  2. PUT  same URL  {"status": "En Ejecución"}
  3. Rename Cabo files from upload name -> original name, reconcile, write
     salidas/<execution_id>/CUADRE_*_reconciliacion.xlsx
  4. Email those CUADRE files to Skipper data.user.email (plus form correo)
  5. PUT  {"status": "Finalizado"} if every cuenta succeeded. Email is required
     on live API only when SMTP or Outlook is configured. Excel is not uploaded.

Offline: --details-json skips GET/PUT. See docs/COMO_FUNCIONA.md and docs/SKIPPER.md.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from reporting.email_export import (  # noqa: E402
    EmailSettings,
    deliver_cuadre_email,
    has_email_transport,
    load_email_settings,
)
from ui.services import AccountRunResult, run_batch, validate_run_config  # noqa: E402
from ui.skipper_execution import (  # noqa: E402
    prepare_insumos_dir,
    params_from_execution,
    run_config_from_insumos,
)

_DEFAULT_CONFIG = _ROOT / "config" / "cabo_config.ini"
_EXAMPLE_CONFIG = _ROOT / "config" / "cabo_config.ini.example"


def _emit(payload: dict[str, Any], code: int) -> int:
    print(json.dumps(payload, ensure_ascii=False, default=str))
    return code


def _load_ini(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    if path.is_file():
        cp.read(path, encoding="utf-8")
    elif _EXAMPLE_CONFIG.is_file():
        cp.read(_EXAMPLE_CONFIG, encoding="utf-8")
    return cp


def load_cabo_settings(config_path: Path | None = None) -> dict[str, Any]:
    ini = _load_ini(config_path or _DEFAULT_CONFIG)
    api = ini["api"] if ini.has_section("api") else {}
    paths = ini["paths"] if ini.has_section("paths") else {}
    token_env = (api.get("token_env") if api else None) or "SKIPPER_API_TOKEN"
    timeout_raw = (api.get("timeout_seconds") if api else None) or "20"
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 20.0
    salida_root = Path((paths.get("salida_root") if paths else None) or "salidas")
    if not salida_root.is_absolute():
        salida_root = _ROOT / salida_root
    base_url = os.environ.get("SKIPPER_API_BASE_URL") or (api.get("base_url") if api else "") or ""
    token = os.environ.get(token_env) or os.environ.get("SKIPPER_API_TOKEN") or (api.get("token") if api else "") or ""
    status_method = str((api.get("status_method") if api else None) or "PUT").strip().upper() or "PUT"
    return {
        "base_url": str(base_url).rstrip("/"),
        "token": str(token).strip(),
        "timeout": timeout,
        "salida_root": salida_root,
        "token_env": token_env,
        "status_method": status_method,
        "email": load_email_settings(ini),
    }


def resolve_execution_id(args: argparse.Namespace) -> str | None:
    if args.execution_id:
        return str(args.execution_id).strip()
    env_id = os.environ.get("EXECUTION_ID", "").strip()
    if env_id:
        return env_id
    json_path = args.execution_json or os.environ.get("CABO_EXECUTION_JSON", "").strip()
    if json_path:
        path = Path(json_path)
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in ("execution_id", "id"):
                value = data.get(key)
                if value:
                    return str(value).strip()
    return None


STATUS_RUNNING = "En Ejecuci\u00f3n"
STATUS_DONE = "Finalizado"


def execution_url(base_url: str, execution_id: str) -> str:
    return f"{str(base_url).rstrip('/')}/api/execution/{execution_id}"


def fetch_execution(
    *,
    base_url: str,
    token: str,
    execution_id: str,
    timeout: float,
) -> dict[str, Any]:
    if not base_url:
        raise RuntimeError("SKIPPER_API_BASE_URL is not set")
    if not token:
        raise RuntimeError("SKIPPER_API_TOKEN is not set")
    url = execution_url(base_url, execution_id)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise RuntimeError(f"Skipper API HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo consultar la ejecucion en Skipper: {exc.reason}") from exc
    data = json.loads(body)
    if not isinstance(data, dict):
        raise RuntimeError("Skipper API returned a non-object JSON payload")
    inner = data.get("data")
    if isinstance(inner, dict) and (
        inner.get("id") is not None
        or inner.get("execution_id") is not None
        or "attachments" in inner
        or "file_original_names" in inner
        or "other" in inner
    ):
        return inner
    return data


def update_execution_status(
    *,
    base_url: str,
    token: str,
    execution_id: str,
    status: str,
    timeout: float,
    method: str = "PUT",
) -> None:
    """PUT/POST ``{"status": ...}`` to Skipper ``/api/execution/{id}``."""
    if not base_url:
        raise RuntimeError("SKIPPER_API_BASE_URL is not set")
    if not token:
        raise RuntimeError("SKIPPER_API_TOKEN is not set")
    url = execution_url(base_url, execution_id)
    body = json.dumps({"status": status}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=(method or "PUT").upper(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise RuntimeError(f"Skipper status HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo actualizar el estado en Skipper: {exc.reason}") from exc


def _try_update_status(
    settings: dict[str, Any],
    execution_id: str,
    status: str,
    warnings: list[str],
) -> None:
    try:
        update_execution_status(
            base_url=settings["base_url"],
            token=settings["token"],
            execution_id=execution_id,
            status=status,
            timeout=settings["timeout"],
            method=str(settings.get("status_method") or "PUT"),
        )
    except RuntimeError as exc:
        warnings.append(str(exc))


def _read_details_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("details JSON must be an object")
    return data


def _result_base(execution_id: str) -> dict[str, Any]:
    return {
        "execution_id": execution_id,
        "status": "error",
        "outputs": [],
        "log": None,
        "audit": None,
        "error": None,
        "email": None,
        "failed_accounts": [],
    }


def _ok_outputs(results: list[AccountRunResult]) -> list[str]:
    return [str(r.output) for r in results if r.ok and r.output]


def run_from_payload(
    *,
    execution_id: str,
    payload: dict[str, Any],
    attachment_dir: Path,
    salida: Path,
    verbose: bool = False,
) -> tuple[dict[str, Any], int]:
    result = _result_base(execution_id)
    try:
        insumos = prepare_insumos_dir(attachment_dir, payload=payload)
    except FileNotFoundError as exc:
        result["error"] = str(exc)
        return result, 2

    params = params_from_execution(payload)
    cfg = run_config_from_insumos(insumos, salida, params)
    if cfg is None:
        result["error"] = "No se encontraron archivos mayorpc para las cuentas solicitadas"
        return result, 2

    validation = validate_run_config(cfg)
    if validation.has_errors:
        result["error"] = "; ".join(validation.flat_errors())
        return result, 2

    run_id, log_path, audit_path, results = run_batch(
        cfg,
        verbose=verbose,
        console_log=True,
        ui_source="skipper_cabo",
        skip_input_validation=False,
        run_id=execution_id,
    )
    result["log"] = str(log_path)
    result["audit"] = str(audit_path)
    result["outputs"] = _ok_outputs(results)
    result["run_id"] = run_id
    result["failed_accounts"] = [r.account for r in results if not r.ok]
    ok_n = sum(1 for r in results if r.ok)
    failed = [r for r in results if not r.ok]
    if ok_n == len(results) and results:
        result["status"] = "ok"
        result["error"] = None
        return result, 0
    result["error"] = "; ".join(f"{r.account}: {r.error}" for r in failed) or "La conciliacion no completo todas las cuentas"
    return result, 1


def attach_email_delivery(
    result: dict[str, Any],
    *,
    payload: dict[str, Any],
    settings: EmailSettings,
    failed_accounts: list[str] | None = None,
    required: bool = False,
) -> int | None:
    """Send CUADRE files. Returns a new exit code when delivery is required and fails."""
    delivery = deliver_cuadre_email(
        attachments=result.get("outputs") or [],
        payload=payload,
        settings=settings,
        execution_id=str(result.get("execution_id") or ""),
        failed_accounts=failed_accounts,
    )
    result["email"] = delivery.as_dict()
    if not required or delivery.status == "ok":
        return None
    if delivery.status == "skipped" and not (result.get("outputs") or []):
        return None
    if delivery.status == "skipped" and not has_email_transport(settings):
        return None
    result["status"] = "error"
    if not result.get("error"):
        result["error"] = delivery.error or "No se pudo enviar el correo con los CUADRE"
    return 1


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cabo runner for fiscal credit reconciliation")
    p.add_argument("--execution-id", default=None)
    p.add_argument("--execution-json", default=None, help="JSON file with execution_id")
    p.add_argument("--details-json", default=None, help="Skip live API; use this execution payload")
    p.add_argument("--cabo-config", type=Path, default=None)
    p.add_argument("--attachment-dir", type=Path, default=None)
    p.add_argument("--salida", type=Path, default=None)
    p.add_argument("--verbose", action="store_true")
    p.add_argument(
        "--no-email",
        action="store_true",
        help="Do not email CUADRE files (local debug only)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = load_cabo_settings(args.cabo_config)
    execution_id = resolve_execution_id(args)
    result = _result_base(execution_id or "")
    if not execution_id:
        result["error"] = "Falta EXECUTION_ID (o --execution-id / CABO_EXECUTION_JSON)"
        return _emit(result, 2)

    result["execution_id"] = execution_id
    if args.attachment_dir is not None:
        attachment = args.attachment_dir
    else:
        env_att = os.environ.get("CABO_ATTACHMENT_DIR", "").strip()
        if not env_att:
            result["error"] = "No se definio carpeta de adjuntos (CABO_ATTACHMENT_DIR)"
            return _emit(result, 2)
        attachment = Path(env_att)

    if args.details_json:
        try:
            payload = _read_details_json(Path(args.details_json))
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            result["error"] = f"No se pudo leer details JSON: {exc}"
            return _emit(result, 1)
        live_api = False
    else:
        try:
            payload = fetch_execution(
                base_url=settings["base_url"],
                token=settings["token"],
                execution_id=execution_id,
                timeout=settings["timeout"],
            )
        except RuntimeError as exc:
            result["error"] = str(exc)
            return _emit(result, 1)
        live_api = True

    if not payload.get("execution_id") and not payload.get("id"):
        payload = dict(payload)
        payload["execution_id"] = execution_id

    status_warnings: list[str] = []
    if live_api:
        _try_update_status(settings, execution_id, STATUS_RUNNING, status_warnings)

    salida = args.salida or (settings["salida_root"] / execution_id)
    payload_out, code = run_from_payload(
        execution_id=execution_id,
        payload=payload,
        attachment_dir=Path(attachment),
        salida=Path(salida),
        verbose=args.verbose,
    )
    email_settings = settings.get("email") or EmailSettings()
    if args.no_email:
        email_settings = EmailSettings(enabled=False)
        payload_out["email"] = {
            "status": "skipped",
            "to": [],
            "cc": [],
            "attachments": [],
            "transport": None,
            "error": "envio de correo deshabilitado",
        }
    else:
        email_code = attach_email_delivery(
            payload_out,
            payload=payload,
            settings=email_settings,
            failed_accounts=list(payload_out.get("failed_accounts") or []),
            required=live_api and has_email_transport(email_settings),
        )
        if email_code is not None:
            code = email_code
    if live_api and code == 0:
        _try_update_status(settings, execution_id, STATUS_DONE, status_warnings)
    if status_warnings:
        payload_out["status_warnings"] = status_warnings
    return _emit(payload_out, code)


if __name__ == "__main__":
    raise SystemExit(main())
