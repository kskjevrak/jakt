"""Build everything from raw/ : jaktfelt -> 10 m rasters + N50 vectors -> scores, PNG, COG, 50 m grid.

  python scripts/build.py            # assumes scripts/download.py has been run
  python scripts/build.py --download # run download.py first (cached)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import log  # noqa: E402


def main(argv: list[str]) -> int:
    if "--download" in argv:
        import download
        rc = download.main([a for a in argv if a != "--download"])
        if rc:
            log("download.py rapporterte feil – fortsetter med det som finnes")
    import build_jaktfelt, build_grid, build_scores  # noqa: E401

    build_jaktfelt.main()
    build_grid.main()
    build_scores.main()
    log("build ferdig")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
