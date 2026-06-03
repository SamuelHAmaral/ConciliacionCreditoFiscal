"""Window size presets for the desktop reconciliation app."""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_WINDOW_PRESET = "standard"


@dataclass(frozen=True)
class WindowPreset:
    preset_id: str
    width: int
    height: int
    min_width: int
    min_height: int


WINDOW_PRESETS: dict[str, WindowPreset] = {
    "compact": WindowPreset("compact", 960, 620, 860, 540),
    "standard": WindowPreset("standard", 1120, 740, 900, 600),
    "large": WindowPreset("large", 1320, 860, 1000, 700),
    "wide": WindowPreset("wide", 1440, 780, 1100, 650),
}


def normalize_window_preset(value: str | None) -> str:
    key = (value or "").strip().lower()
    if key in WINDOW_PRESETS:
        return key
    return DEFAULT_WINDOW_PRESET


def get_window_preset(preset_id: str | None) -> WindowPreset:
    return WINDOW_PRESETS[normalize_window_preset(preset_id)]


_GEO_RE = re.compile(r"^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$")


def parse_window_geometry(geometry: str) -> tuple[int, int, int | None, int | None] | None:
    """Parse Tk geometry string ``WxH+X+Y`` (position optional)."""
    m = _GEO_RE.match(geometry.strip())
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    x = int(m.group(3)) if m.group(3) is not None else None
    y = int(m.group(4)) if m.group(4) is not None else None
    return w, h, x, y


def format_window_geometry(
    preset: WindowPreset,
    *,
    screen_width: int,
    screen_height: int,
    current: tuple[int, int, int | None, int | None] | None = None,
    center: bool = False,
    force_resize: bool = True,
) -> str:
    """
    Build a geometry string for a preset.

    When ``force_resize`` is false, keep current width/height if they meet minsize.
    When ``center`` is false and current position is known, keep the top-left corner.
    """
    w = max(preset.width, preset.min_width)
    h = max(preset.height, preset.min_height)
    if current is not None:
        cur_w, cur_h, cur_x, cur_y = current
        if not force_resize:
            w = max(cur_w, preset.min_width)
            h = max(cur_h, preset.min_height)
        if center or cur_x is None or cur_y is None:
            x = max(0, (screen_width - w) // 2)
            y = max(0, (screen_height - h) // 2)
        else:
            x = min(max(0, cur_x), max(0, screen_width - w))
            y = min(max(0, cur_y), max(0, screen_height - h))
    else:
        x = max(0, (screen_width - w) // 2)
        y = max(0, (screen_height - h) // 2)
    return f"{w}x{h}+{x}+{y}"
