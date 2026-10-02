"""Write a humid-gas inlet candidate from an explicit root parameter contract.

Usage in the installed project environment:
    python scripts/build_humid_gas_boundary.py ROOT_PARAMETERS --out CANDIDATE_JSON

All physical input values, units and sources are read from ROOT_PARAMETERS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sludge_vme.models.gas_boundary_inputs import build_humid_gas_boundary
from sludge_vme.models.full_cycle import read_parameters


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parameters", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = read_parameters(args.parameters)
    try:
        candidate = build_humid_gas_boundary(root)
    except ValueError as exc:
        parser.error(str(exc))
    candidate["input_parameter_path"] = str(args.parameters.resolve())
    payload = json.dumps(candidate, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        handle.write(payload)
    print(f"humid gas inlet candidate written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
