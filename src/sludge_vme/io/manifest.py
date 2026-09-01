from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import scipy


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(root: Path) -> str | None:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def build_manifest(*, root: Path, case_hash: str, parameter_pack_hash: str, cli_args: list[str], seed: int, run_type: str, fidelity: str | None = None, budget: str | None = None) -> dict[str, Any]:
    source_path = root / "data" / "sources.json"
    return {
        "manifest_version": "1.0",
        "utc_timestamp": datetime.now(UTC).isoformat(),
        "run_type": run_type,
        "cli_args": cli_args,
        "seed": int(seed),
        "spec_version": "0.1.0",
        "source_pack_hash": file_sha256(source_path),
        "parameter_pack_hash": parameter_pack_hash,
        "resolved_case_hash": case_hash,
        "software": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__, "sludge_vme": "0.1.0"},
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python_implementation": platform.python_implementation()},
        "fidelity": fidelity,
        "budget": budget,
        "git_commit": git_commit(root),
        "workers": 1,
        "network_used_by_solver": False,
        "paid_services": False,
        "production_control_side_effects": False,
    }
