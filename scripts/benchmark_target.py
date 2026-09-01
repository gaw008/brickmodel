"""Convenience wrapper for the documented target benchmark."""

from __future__ import annotations

import sys

from sludge_vme.cli import main


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if not arguments:
        arguments = ["examples/tiny_synthetic.json", "--out", "runs/benchmark"]
    raise SystemExit(main(["benchmark", *arguments]))
