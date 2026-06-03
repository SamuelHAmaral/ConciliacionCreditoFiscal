"""CLI: rebuild app icons and Concilation Logo.png from the vector brand mark."""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ui.brand_icon import BRAND_LOGO_NAMES, build_app_icons

_ASSETS = _ROOT / "desktop" / "assets"


def main() -> None:
    ico, png, photo = build_app_icons(_ASSETS)
    print(f"Wrote {ico}")
    print(f"Wrote {png}")
    print(f"Wrote {photo}")
    print(f"Wrote {_ASSETS / BRAND_LOGO_NAMES[0]}")


if __name__ == "__main__":
    main()
