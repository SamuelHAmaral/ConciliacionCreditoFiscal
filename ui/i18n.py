"""Account labels and validation strings for the headless runner."""

from __future__ import annotations

DEFAULT_LANGUAGE = "es"
OUTPUT_LANGUAGE = "es"
SUPPORTED_LANGUAGES = ("es", "en")

_MESSAGES: dict[str, dict[str, str]] = {
    "val_no_jobs": {
        "es": "Seleccione al menos un tipo con su archivo mayor (mayorpc).",
        "en": "Select at least one reconciliation type with its ledger file (mayorpc).",
    },
    "val_ledger_missing": {
        "es": "{label}: no existe el archivo mayor: {path}",
        "en": "{label}: ledger file not found: {path}",
    },
    "val_sql_required": {
        "es": "NC emitidas (SQL) requiere un archivo SQL valido (CSV o Excel).",
        "en": "Issued credit notes (SQL) requires a valid SQL file (CSV or Excel).",
    },
    "val_fecha_desde": {
        "es": "NC emitidas (SQL) requiere fecha_desde (YYYY-MM-DD).",
        "en": "Issued credit notes (SQL) requires fecha_desde (YYYY-MM-DD).",
    },
    "val_fecha_hasta": {
        "es": "NC emitidas (SQL) requiere fecha_hasta (YYYY-MM-DD).",
        "en": "Issued credit notes (SQL) requires fecha_hasta (YYYY-MM-DD).",
    },
    "val_fc_required": {
        "es": "{label} requiere archivo FAMAFA Compras (CSV o Excel).",
        "en": "{label} requires FAMAFA Purchases file (CSV or Excel).",
    },
    "val_fv_required": {
        "es": "NC recibidas (Ventas) requiere archivo FAMAFA Ventas (CSV o Excel).",
        "en": "Received credit notes (Sales) requires FAMAFA Sales file (CSV or Excel).",
    },
    "val_date_invalid": {"es": "{detail}", "en": "{detail}"},
    "val_date_warn": {"es": "{detail}", "en": "{detail}"},
    "val_precheck_error": {"es": "{detail}", "en": "{detail}"},
    "val_precheck_warn": {"es": "{detail}", "en": "{detail}"},
}

# MANTENIMIENTO — si cambia el numero de cuenta, actualizar tambien:
#   config/accounts.yml, folder_discovery.ACCOUNTS, account_config._DEFAULT_ACCOUNTS,
#   run_reconciliation.py, skipper_job.json, docs/MANTENIMIENTO.md.
_ACCOUNT_LABELS: dict[str, dict[str, str]] = {
    "1279": {
        "es": "NC emitidas (SQL)",
        "en": "Issued credit notes (SQL)",
    },
    "469": {
        "es": "IVA compras (FAMAFA Compras)",
        "en": "Purchase VAT (FAMAFA Purchases)",
    },
    "1280": {
        "es": "Retenciones exterior (FAMAFA Compras)",
        "en": "Foreign withholding (FAMAFA Purchases)",
    },
    "2874": {
        "es": "NC recibidas (FAMAFA Ventas)",
        "en": "Received credit notes (FAMAFA Sales)",
    },
}


def normalize_language(lang: str | None) -> str:
    if not lang or not str(lang).strip():
        return DEFAULT_LANGUAGE
    low = str(lang).strip().lower()
    if low.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: str) -> str:
    lang = normalize_language(lang)
    entry = _MESSAGES.get(key, {})
    text = entry.get(lang) or entry.get("es") or key
    if kwargs:
        return text.format(**kwargs)
    return text


def account_label(account: str, lang: str = DEFAULT_LANGUAGE) -> str:
    lang = normalize_language(lang)
    entry = _ACCOUNT_LABELS.get(account, {})
    return entry.get(lang) or entry.get("es") or account


def account_label_output(account: str) -> str:
    """Account label for Excel, logs, and manifests (always Spanish)."""
    return account_label(account, OUTPUT_LANGUAGE)


def missing_message_keys(lang: str = "en") -> list[str]:
    """Return keys missing a translation for *lang* (for tests)."""
    lang = normalize_language(lang)
    missing: list[str] = []
    for key, entry in _MESSAGES.items():
        if lang not in entry:
            missing.append(key)
    return missing
