"""
Run reconciliation batch in an isolated process (GUI worker).

Usage (from reconciliation_engine):
  py -3 scripts/gui_batch_worker.py --request path/to/request.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ui.batch_worker import run_from_request  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="GUI batch reconciliation worker")
    ap.add_argument("--request", type=Path, required=True, help="Path to request JSON")
    args = ap.parse_args()
    return run_from_request(args.request)


if __name__ == "__main__":
    raise SystemExit(main())
