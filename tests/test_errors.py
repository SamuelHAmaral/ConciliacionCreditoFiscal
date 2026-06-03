"""Tests for structured reconciliation error codes."""

from pipeline.errors import ErrorCode, ReconciliationError, audit_error_fields, error_from_exception, format_user_message


def test_error_from_reconciliation_error():
    exc = ReconciliationError(ErrorCode.E_SCHEMA, "missing column")
    code, msg = error_from_exception(exc)
    assert code == ErrorCode.E_SCHEMA
    assert msg == "missing column"


def test_error_from_permission_error():
    code, _ = error_from_exception(PermissionError("locked"))
    assert code == ErrorCode.E_FILE_LOCK


def test_audit_error_fields_includes_code():
    exc = ReconciliationError(ErrorCode.E_VALIDATION, "bad dates")
    fields = audit_error_fields(exc)
    assert fields["error_code"] == "E_VALIDATION"
    assert fields["error"] == "bad dates"


def test_format_user_message_prefixes_code():
    text = format_user_message(ErrorCode.E_FILE_READ, "cannot read file")
    assert text.startswith("[E_FILE_READ]")
