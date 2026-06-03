"""Window preset and theme normalization tests."""

from ui.theme import normalize_appearance
from ui.window_presets import (
    format_window_geometry,
    get_window_preset,
    normalize_window_preset,
    parse_window_geometry,
)


def test_normalize_window_preset_defaults():
    assert normalize_window_preset(None) == "standard"
    assert normalize_window_preset("large") == "large"
    assert normalize_window_preset("unknown") == "standard"


def test_window_preset_dimensions():
    p = get_window_preset("compact")
    assert p.width == 960
    assert p.min_width <= p.width


def test_normalize_appearance():
    assert normalize_appearance("dark") == "dark"
    assert normalize_appearance("light") == "light"
    assert normalize_appearance("1") == "dark"


def test_parse_window_geometry():
    assert parse_window_geometry("1120x740+100+50") == (1120, 740, 100, 50)
    assert parse_window_geometry("900x600") == (900, 600, None, None)


def test_format_window_geometry_keeps_position():
    preset = get_window_preset("standard")
    geo = format_window_geometry(
        preset,
        screen_width=1920,
        screen_height=1080,
        current=(1000, 700, 120, 80),
        center=False,
        force_resize=False,
    )
    assert geo == "1000x700+120+80"


def test_format_window_geometry_resizes_preset():
    preset = get_window_preset("large")
    geo = format_window_geometry(
        preset,
        screen_width=1920,
        screen_height=1080,
        current=(800, 600, 120, 80),
        center=False,
        force_resize=True,
    )
    assert geo.startswith("1320x860+")
