"""User-friendly activity lines derived from audit events (not raw file logs)."""

from __future__ import annotations

from typing import Any

from ui.i18n import account_label, t


def format_audit_activity(row: dict[str, Any], *, lang: str) -> str | None:
    """Map one audit JSONL row to a short UI message, or None to skip."""
    stage = str(row.get("stage") or "")
    acc = row.get("account")
    label = account_label(str(acc), lang) if acc else ""

    if stage == "ui_run_start":
        accounts = row.get("accounts") or []
        n = len(accounts) if isinstance(accounts, list) else 0
        if n:
            return t("activity_run_start", lang, n=str(n))
        return None

    if stage == "account_start" and acc:
        return t("activity_account_start", lang, label=label)

    if stage == "match_complete" and acc:
        matched = int(row.get("matched_rows") or 0)
        pending = int(row.get("unmatched_ledger_rows") or 0) + int(
            row.get("unmatched_system_rows") or 0
        )
        return t(
            "activity_account_done",
            lang,
            label=label,
            matched=str(matched),
            pending=str(pending),
        )

    if stage == "integrity_check" and acc:
        if row.get("integrity_ok"):
            return t("activity_integrity_ok", lang, label=label)
        return t("activity_integrity_failed", lang, label=label)

    if stage in ("account_failed", "ui_job_failed") and acc:
        err = str(row.get("message") or row.get("error") or t("activity_unknown_error", lang))
        return t("activity_account_err", lang, label=label, err=err)

    return None
