"""Apply ThemeColors to CustomTkinter widget trees."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from ui.theme import ThemeColors


def apply_widget_theme(root: tk.Misc, colors: ThemeColors) -> None:
    """Recursively align CTk widgets with the active custom palette."""
    for child in root.winfo_children():
        if isinstance(child, ctk.CTkEntry):
            child.configure(
                fg_color=colors.input_bg,
                border_color=colors.border,
                text_color=colors.text,
            )
        elif isinstance(child, ctk.CTkTextbox):
            child.configure(
                fg_color=colors.input_bg,
                border_color=colors.border,
                text_color=colors.text,
            )
        elif isinstance(child, ctk.CTkCheckBox):
            child.configure(
                text_color=colors.text,
                fg_color=colors.input_bg,
                border_color=colors.border,
                hover_color=colors.secondary_hover,
            )
        elif isinstance(child, ctk.CTkSwitch):
            child.configure(
                text_color=colors.text,
                progress_color=colors.primary,
                button_color="#f4f6f8",
                button_hover_color="#ffffff",
                fg_color=colors.border,
            )
        elif isinstance(child, ctk.CTkLabel):
            child.configure(text_color=colors.text)
        elif isinstance(child, ctk.CTkButton):
            # Primary/secondary buttons are configured explicitly in the GUI.
            pass
        elif isinstance(child, ctk.CTkProgressBar):
            child.configure(progress_color=colors.primary, fg_color=colors.border)
        elif isinstance(child, ctk.CTkFrame):
            fg = child.cget("fg_color")
            if fg not in ("transparent", "Transparent"):
                # Inner panels use bg; cards use surface (set in GUI).
                pass
        elif isinstance(child, tk.Canvas):
            child.configure(bg=colors.bg)
        apply_widget_theme(child, colors)
