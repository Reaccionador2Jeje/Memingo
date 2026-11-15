"""Frozen and source entry point for Memingo Desktop."""
from __future__ import annotations

import sys
from pathlib import Path

# Make the repository/package root discoverable when running from source.
# In PyInstaller builds, --paths and the installed package include the module.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memingo.desktop import main


if __name__ == "__main__":
    main()
