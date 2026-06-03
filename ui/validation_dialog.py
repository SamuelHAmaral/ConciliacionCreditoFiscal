"""Pre-run validation summary modal for the desktop GUI."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

from ui.i18n import account_label, t
from ui.services import RunValidationResult

if TYPE_CHECKING:
    from desktop.conciliation_gui import ConciliationApp


def show_validation_dialog(
    parent: ctk.CTk,
    app: "ConciliationApp",
    result: RunValidationResult,
    *,
    lang: str,
) -> bool:
    """
    Show grouped validation summary.

    Returns True when the user may start the run (no errors; warnings accepted).
    """
    if result.has_errors:
        _show_blocking_dialog(parent, app, result, lang=lang)
        return False
    if result.warnings:
        return _show_warning_dialog(parent, app, result, lang=lang)
    return True


def _format_body(result: RunValidationResult, *, lang: str) -> str:
    lines: list[str] = []
    if result.global_errors:
        lines.append(t("validation_section_general", lang))
        lines.extend(f"- {e}" for e in result.global_errors)
    for acc in sorted(result.account_errors):
        items = result.account_errors[acc]
        if not items:
            continue
        label = account_label(acc, lang)
        lines.append(t("validation_section_account", lang, label=label))
        lines.extend(f"- {e}" for e in items)
    if result.warnings:
        lines.append(t("validation_section_warnings", lang))
        lines.extend(f"- {w}" for w in result.warnings)
    return "\n".join(lines)


def _show_blocking_dialog(
    parent: ctk.CTk,
    app: "ConciliationApp",
    result: RunValidationResult,
    *,
    lang: str,
) -> None:
    dlg = ctk.CTkToplevel(parent)
    dlg.title(t("err_validation_title", lang))
    dlg.geometry("640x420")
    dlg.transient(parent)
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text=t("validation_errors_intro", lang),
        font=ctk.CTkFont("Segoe UI", 13, "bold"),
        anchor="w",
    ).pack(fill="x", padx=12, pady=(12, 6))

    txt = ctk.CTkTextbox(dlg, font=ctk.CTkFont("Consolas", 11))
    txt.pack(fill="both", expand=True, padx=12, pady=6)
    txt.insert("1.0", _format_body(result, lang=lang))
    txt.configure(state="disabled")

    ctk.CTkButton(dlg, text=t("validation_ok", lang), command=dlg.destroy).pack(pady=12)
    dlg.wait_window()


def _show_warning_dialog(
    parent: ctk.CTk,
    app: "ConciliationApp",
    result: RunValidationResult,
    *,
    lang: str,
) -> bool:
    choice = {"proceed": False}

    dlg = ctk.CTkToplevel(parent)
    dlg.title(t("warn_validation_title", lang))
    dlg.geometry("640x420")
    dlg.transient(parent)
    dlg.grab_set()

    ctk.CTkLabel(
        dlg,
        text=t("validation_warnings_intro", lang),
        font=ctk.CTkFont("Segoe UI", 13, "bold"),
        anchor="w",
    ).pack(fill="x", padx=12, pady=(12, 6))

    txt = ctk.CTkTextbox(dlg, font=ctk.CTkFont("Consolas", 11))
    txt.pack(fill="both", expand=True, padx=12, pady=6)
    txt.insert("1.0", _format_body(result, lang=lang))
    txt.configure(state="disabled")

    btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_row.pack(fill="x", padx=12, pady=12)

    def on_cancel() -> None:
        choice["proceed"] = False
        dlg.destroy()

    def on_continue() -> None:
        choice["proceed"] = True
        dlg.destroy()

    ctk.CTkButton(btn_row, text=t("validation_cancel", lang), command=on_cancel).pack(
        side="left", padx=(0, 8)
    )
    ctk.CTkButton(btn_row, text=t("validation_continue", lang), command=on_continue).pack(
        side="left"
    )
    dlg.wait_window()
    return choice["proceed"]
