"""User-friendly activity messages from audit events."""

from ui.activity_log import format_audit_activity


def test_format_audit_activity_account_flow():
    lang = "es"
    start = format_audit_activity({"stage": "account_start", "account": "1279"}, lang=lang)
    assert start is not None
    assert "1279" in start or "NC" in start

    done = format_audit_activity(
        {
            "stage": "match_complete",
            "account": "1279",
            "matched_rows": 100,
            "unmatched_ledger_rows": 5,
            "unmatched_system_rows": 3,
        },
        lang=lang,
    )
    assert done is not None
    assert "100" in done
    assert "8" in done

    ok = format_audit_activity({"stage": "ui_job_ok", "account": "469"}, lang=lang)
    assert ok is None


def test_format_audit_activity_run_level():
    lang = "en"
    start = format_audit_activity({"stage": "ui_run_start", "accounts": ["1279", "469"]}, lang=lang)
    assert start is not None
    assert "2" in start


def test_format_audit_activity_skips_noise():
    assert format_audit_activity({"stage": "ledger_parsed", "account": "1279"}, lang="es") is None
