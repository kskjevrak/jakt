"""Re-fetch Artskart observations any time: `python scripts/refresh_artskart.py`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_artskart  # noqa: E402

if __name__ == "__main__":
    rep = fetch_artskart.main(force=True)
    print(f"{'OK' if rep.ok else 'FEIL'}: {rep.notes[-1] if rep.notes else ''}")
