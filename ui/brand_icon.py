"""Build window icons from a crisp vector-style AMARAL brand mark."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

BRAND_LOGO_NAMES = (
    "Concilation Logo.png",
    "Conciliation Logo.png",
    "conciliation_logo.png",
)

ICO_NAME = "app_icon.ico"
PNG_NAME = "app_icon.png"
PHOTO_NAME = "app_icon_photo.png"
VERSION_NAME = ".brand_icon_version"
# Bump when render_brand_mark() changes so icons auto-rebuild on startup.
ICON_MARK_VERSION = 2
SOURCE_SIZE = 1080
# Windows title bar / taskbar + Tk iconphoto (sharp at common DPI scales).
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
PHOTO_SIZE = 128

# Match ui/theme.py LIGHT_THEME primary.
_PRIMARY = "#0f4ba5"
_PRIMARY_DARK = "#0b3f8c"
_WHITE = "#ffffff"


def find_brand_logo(*search_dirs: Path) -> Path | None:
    for base in search_dirs:
        for name in BRAND_LOGO_NAMES:
            path = base / name
            if path.is_file():
                return path.resolve()
    return None


def render_brand_mark(size: int) -> Image.Image:
    """Draw the AMARAL mark: blue squircle, white triangle, symmetric inner notch."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(1, round(size * 0.06))
    radius = max(2, round(size * 0.18))
    outer = (pad, pad, size - pad - 1, size - pad - 1)
    draw.rounded_rectangle(outer, radius=radius, fill=_PRIMARY)

    cx = size // 2
    if size >= 48:
        halo_r = round(size * 0.27)
        draw.ellipse(
            (cx - halo_r, cx - halo_r, cx + halo_r, cx + halo_r),
            fill=_PRIMARY_DARK,
        )

    apex_y = round(size * 0.28)
    base_y = round(size * 0.78)
    half_w = round(size * 0.22)
    draw.polygon(
        [(cx, apex_y), (cx - half_w, base_y), (cx + half_w, base_y)],
        fill=_WHITE,
    )

    if size >= 32:
        notch_top = round(size * 0.50)
        notch_bottom = round(size * 0.70)
        notch_half = round(size * 0.085)
        chamfer = max(1, round(size * 0.025))
        draw.polygon(
            [
                (cx - notch_half, notch_bottom),
                (cx + notch_half, notch_bottom),
                (cx + notch_half - chamfer, notch_top + chamfer),
                (cx + notch_half * 0.35, notch_top),
                (cx - notch_half * 0.35, notch_top),
                (cx - notch_half + chamfer, notch_top + chamfer),
            ],
            fill=_PRIMARY,
        )

    return img


def build_app_icons(out_dir: Path) -> tuple[Path, Path, Path]:
    """Write .ico (multi-size), preview .png, Tk photo .png, and source PNG."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_size = {s: render_brand_mark(s) for s in ICON_SIZES}
    ordered = [by_size[s] for s in sorted(ICON_SIZES, reverse=True)]
    ico_path = out_dir / ICO_NAME
    ordered[0].save(
        ico_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in ordered],
        append_images=ordered[1:],
    )
    png_path = out_dir / PNG_NAME
    by_size[256].save(png_path, format="PNG")
    photo_path = out_dir / PHOTO_NAME
    by_size[PHOTO_SIZE].save(photo_path, format="PNG")
    brand_path = out_dir / BRAND_LOGO_NAMES[0]
    render_brand_mark(SOURCE_SIZE).save(brand_path, format="PNG")
    (out_dir / VERSION_NAME).write_text(str(ICON_MARK_VERSION), encoding="utf-8")
    return ico_path.resolve(), png_path.resolve(), photo_path.resolve()


@dataclass(frozen=True)
class ResolvedIcons:
    """Paths used at runtime for the window / taskbar."""

    brand_png: Path
    ico: Path
    photo_png: Path


def _needs_rebuild(out_dir: Path, ico: Path, photo: Path) -> bool:
    for path in (ico, photo):
        if not path.is_file():
            return True
    version_file = out_dir / VERSION_NAME
    if not version_file.is_file():
        return True
    try:
        return int(version_file.read_text(encoding="utf-8").strip()) < ICON_MARK_VERSION
    except (OSError, ValueError):
        return True


def resolve_icons(assets_dir: Path) -> ResolvedIcons | None:
    brand = find_brand_logo(assets_dir)
    if brand is None:
        return None
    ico = assets_dir / ICO_NAME
    photo = assets_dir / PHOTO_NAME
    if _needs_rebuild(assets_dir, ico, photo):
        build_app_icons(assets_dir)
        brand = find_brand_logo(assets_dir)
        if brand is None:
            return None
    return ResolvedIcons(
        brand_png=brand,
        ico=ico.resolve(),
        photo_png=photo.resolve(),
    )
