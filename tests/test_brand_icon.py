"""Brand logo ? app icon resolution."""

from pathlib import Path

from ui.brand_icon import find_brand_logo, resolve_icons


def test_find_brand_logo():
    root = Path(__file__).resolve().parents[1]
    assets = root / "desktop" / "assets"
    logo = find_brand_logo(assets)
    assert logo is not None
    assert logo.name == "Concilation Logo.png"


def test_resolve_icons_uses_brand():
    root = Path(__file__).resolve().parents[1]
    assets = root / "desktop" / "assets"
    resolved = resolve_icons(assets)
    assert resolved is not None
    assert resolved.brand_png.name == "Concilation Logo.png"
    assert resolved.ico.name == "app_icon.ico"
    assert resolved.ico.is_file()
    assert resolved.photo_png.name == "app_icon_photo.png"
    assert resolved.photo_png.is_file()
