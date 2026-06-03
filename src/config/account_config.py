"""Load ``config/accounts.yml`` and expose account metadata helpers."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_CACHE: dict[str, Any] | None = None

_DEFAULT_ACCOUNTS: dict[str, dict[str, Any]] = {
    "1279": {
        "profile_name": "NC emitidas",
        "system_type": "sql",
        "ledger_side": "Debito",
        "match_column": "IVA ML",
        "required_columns": {
            "sql": ["Fecha_Cont", "IVA ML"],
        },
        "filters": {},
    },
    "469": {
        "profile_name": "IVA compras",
        "system_type": "famafa_compras",
        "ledger_side": "Debito",
        "match_column": "IVA 10",
        "required_columns": {
            "famafa": ["Tipo Comprobante", "IVA 10", "Fecha Emision"],
        },
        "filters": {
            "tipo_comprobante": 109,
            "timbrado_rule": "exclude",
            "timbrado_value": "12345678",
        },
    },
    "1280": {
        "profile_name": "Retenciones exterior",
        "system_type": "famafa_compras",
        "ledger_side": "Debito",
        "match_column": "IVA 10",
        "required_columns": {
            "famafa": ["Tipo Comprobante", "Nro. Timbrado", "IVA 10", "Fecha Emision"],
        },
        "filters": {
            "tipo_comprobante": 109,
            "timbrado_rule": "include",
            "timbrado_value": "12345678",
        },
    },
    "2874": {
        "profile_name": "NC recibidas",
        "system_type": "famafa_ventas",
        "ledger_side": "Credito",
        "match_column": "IVA 10",
        "required_columns": {
            "famafa": ["Tipo Comprobante", "IVA 10", "Fecha Emision"],
        },
        "filters": {
            "tipo_comprobante": 110,
        },
    },
}


def _default_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return (base / "config" / "accounts.yml").resolve()
    # src/config/account_config.py -> parents[2] = reconciliation_engine/
    return Path(__file__).resolve().parents[2] / "config" / "accounts.yml"


def load_account_config(path: Path | None = None) -> dict[str, Any]:
    """Return parsed YAML dict, or empty dict if file missing / PyYAML unavailable."""
    global _CONFIG_CACHE
    p = (path or _default_config_path()).resolve()
    if _CONFIG_CACHE is not None and str(_CONFIG_CACHE.get("_path")) == str(p):
        return _CONFIG_CACHE

    if not p.is_file():
        logger.debug("No account config at %s; using built-in defaults", p)
        _CONFIG_CACHE = {"_path": str(p)}
        return _CONFIG_CACHE

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("PyYAML not installed; ignoring %s", p)
        _CONFIG_CACHE = {"_path": str(p)}
        return _CONFIG_CACHE

    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
    data["_path"] = str(p)
    _CONFIG_CACHE = data
    logger.info("Loaded account config from %s", p)
    return data


def account_profile(account: str) -> dict[str, Any]:
    cfg = load_account_config()
    table = cfg.get("accounts")
    if not isinstance(table, dict):
        table = {}
    base = dict(_DEFAULT_ACCOUNTS.get(account, {}))
    custom = table.get(account) if isinstance(table.get(account), dict) else {}
    out = {**base, **custom}
    base_filters = base.get("filters") if isinstance(base.get("filters"), dict) else {}
    custom_filters = custom.get("filters") if isinstance(custom.get("filters"), dict) else {}
    out["filters"] = {**base_filters, **custom_filters}
    base_required = (
        base.get("required_columns") if isinstance(base.get("required_columns"), dict) else {}
    )
    custom_required = (
        custom.get("required_columns") if isinstance(custom.get("required_columns"), dict) else {}
    )
    out["required_columns"] = {**base_required, **custom_required}
    return out


def required_columns_for(account: str, source: str) -> list[str]:
    prof = account_profile(account)
    req = prof.get("required_columns")
    if not isinstance(req, dict):
        return []
    cols = req.get(source)
    if not isinstance(cols, list):
        return []
    return [str(c) for c in cols]


def timbrado_valor_for(account: str, *, default: str = "12345678") -> str:
    prof = account_profile(account)
    filters = prof.get("filters") if isinstance(prof.get("filters"), dict) else {}
    v = filters.get("timbrado_value")
    if v is not None and str(v).strip():
        return str(v).strip()
    cfg = load_account_config()
    top = cfg.get("timbrado_especial")
    if top is not None and str(top).strip():
        return str(top).strip()
    legacy = prof.get("timbrado_valor")
    if legacy is not None and str(legacy).strip():
        return str(legacy).strip()
    return default
