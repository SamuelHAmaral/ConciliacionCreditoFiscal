"""Structured reconciliation error codes for logs, audit, and UI."""

from __future__ import annotations

import traceback
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    E_FILE_LOCK = "E_FILE_LOCK"
    E_FILE_READ = "E_FILE_READ"
    E_VALIDATION = "E_VALIDATION"
    E_MISSING_INPUT = "E_MISSING_INPUT"
    E_SCHEMA = "E_SCHEMA"
    E_UNSUPPORTED_ACCOUNT = "E_UNSUPPORTED_ACCOUNT"
    E_INTERNAL = "E_INTERNAL"


class ReconciliationError(Exception):
    """Application error with a stable machine-readable code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def error_from_exception(exc: BaseException) -> tuple[ErrorCode, str]:
    if isinstance(exc, ReconciliationError):
        return exc.code, exc.message
    if isinstance(exc, PermissionError):
        return ErrorCode.E_FILE_LOCK, str(exc)
    if isinstance(exc, KeyError):
        return ErrorCode.E_SCHEMA, str(exc)
    if isinstance(exc, ValueError):
        msg = str(exc).lower()
        if any(k in msg for k in ("missing", "requires", "not found", "falta")):
            return ErrorCode.E_MISSING_INPUT, str(exc)
        if "unsupported account" in msg:
            return ErrorCode.E_UNSUPPORTED_ACCOUNT, str(exc)
        return ErrorCode.E_VALIDATION, str(exc)
    if isinstance(exc, (UnicodeDecodeError, UnicodeError)):
        return ErrorCode.E_FILE_READ, str(exc)
    if isinstance(exc, RuntimeError) and "could not read" in str(exc).lower():
        return ErrorCode.E_FILE_READ, str(exc)
    return ErrorCode.E_INTERNAL, str(exc)


def format_user_message(code: ErrorCode, message: str) -> str:
    return f"[{code.value}] {message}"


def audit_error_fields(exc: BaseException) -> dict[str, Any]:
    code, msg = error_from_exception(exc)
    return {
        "error_code": code.value,
        "error": msg,
        "error_type": type(exc).__name__,
        "traceback": traceback.format_exc(),
    }
