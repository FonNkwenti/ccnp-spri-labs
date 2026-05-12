#!/usr/bin/env python3
"""PNG diagram export has been dropped from this project.

Topology diagrams ship as `.drawio` source only. Open them in the draw.io
desktop app or app.diagrams.net to view; no rendered image is committed.

This file is kept as a no-op stub so any lingering scripts or CI steps that
still invoke it exit cleanly with this message instead of failing obscurely.
"""

import sys


def main() -> int:
    sys.stderr.write(
        "export_diagrams.py: PNG export has been removed. "
        "Diagrams are .drawio-only now — nothing to do.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
