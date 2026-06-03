"""Window icon path resolution."""

from pathlib import Path

from ui.window_icon import (
    brand_logo_path,
    default_icon_path,
    default_icon_png_path,
    init_windows_app_identity,
)


def test_default_icon_path_exists():
    root = Path(__file__).resolve().parents[1]
    icon = default_icon_path(root)
    assert icon is not None
    assert icon.name == "app_icon.ico"
    assert icon.is_file()


def test_default_icon_png_path_is_sharp_photo():
    root = Path(__file__).resolve().parents[1]
    png = default_icon_png_path(root)
    assert png is not None
    assert png.name == "app_icon_photo.png"
    assert png.is_file()


def test_brand_logo_path_exists():
    root = Path(__file__).resolve().parents[1]
    logo = brand_logo_path(root)
    assert logo is not None
    assert logo.suffix.lower() == ".png"
    assert logo.is_file()


def test_init_windows_app_identity_no_error():
    init_windows_app_identity()
