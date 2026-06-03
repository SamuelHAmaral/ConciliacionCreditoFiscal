"""i18n completeness and output-locale helpers."""

from ui.i18n import (
    LANG_DISPLAY_CHOICES,
    OUTPUT_LANGUAGE,
    _ACCOUNT_LABELS,
    _MESSAGES,
    account_label,
    account_label_output,
    language_code_from_display,
    language_display_for,
    missing_message_keys,
    t,
)


def test_all_ui_messages_have_english_and_spanish():
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
    assert t("app_title", "es") == t("header_title", "es")
    assert t("app_title", "en") == t("header_title", "en")
    assert t("nonexistent_key_xyz", "en") == "nonexistent_key_xyz"


def test_message_count_stable():
    assert len(_MESSAGES) >= 80


def test_language_display_round_trip():
    label = language_display_for("es")
    assert label in LANG_DISPLAY_CHOICES
    assert language_code_from_display(label) == "es"
    assert language_code_from_display("English") == "en"
