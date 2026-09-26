"""Offline source-checkout entry for the VME full-cycle CLI."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sludge_vme.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["full-cycle", *sys.argv[1:]]))
