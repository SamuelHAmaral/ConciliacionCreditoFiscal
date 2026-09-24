"""i18n completeness and output-locale helpers."""

from ui.i18n import (
    OUTPUT_LANGUAGE,
    _ACCOUNT_LABELS,
    _MESSAGES,
    account_label,
    account_label_output,
    missing_message_keys,
    t,
)


def test_all_validation_messages_have_english_and_spanish():
    assert not missing_message_keys("en")
    assert not missing_message_keys("es")


def test_account_labels_have_both_languages():
    for acc, entry in _ACCOUNT_LABELS.items():
        assert "es" in entry, acc
        assert "en" in entry, acc


def test_output_account_labels_always_spanish():
    assert OUTPUT_LANGUAGE == "es"
    assert account_label_output("469") == account_label("469", "es")
    assert "IVA" in account_label_output("469")


def test_t_fallback_to_spanish():
    assert t("val_sql_required", "es")
    assert t("nonexistent_key_xyz", "en") == "nonexistent_key_xyz"


def test_validation_message_keys_present():
    for key in (
        "val_no_jobs",
        "val_ledger_missing",
        "val_sql_required",
        "val_fecha_desde",
        "val_fecha_hasta",
        "val_fc_required",
        "val_fv_required",
        "val_precheck_error",
        "val_precheck_warn",
    ):
        assert key in _MESSAGES
