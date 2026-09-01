from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from sludge_vme.config import load_case
from sludge_vme.io.artifacts import verify_run, write_forward_run
from sludge_vme.models import simulate


ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "examples" / "tiny_synthetic.json"


def test_forward_artifacts_include_json_csv_markdown_and_verify(tmp_path: Path) -> None:
    case = load_case(CASE_PATH)
    result = simulate(case, "L0")
    out = tmp_path / "forward"
    write_forward_run(out, case, result, cli_args=["forward", str(CASE_PATH)], seed=7)
    required = {
        "run_manifest.json", "resolved_case.json", "status.json", "summary.json", "conservation.json",
        "flags.json", "state_trajectory.json", "state_trajectory.csv", "uncertainty.json", "report.md",
    }
    assert required <= {path.name for path in out.iterdir()}
    verification = verify_run(out, strict=True)
    assert verification.valid, verification.errors
    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["resolved_case_hash"] == case.content_hash
    assert manifest["platform"]["machine"] == "aarch64"


def test_cli_validate_forward_verify_and_inverse_help(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    validate = subprocess.run([sys.executable, "-m", "sludge_vme.cli", "validate", str(CASE_PATH), "--json"], cwd=ROOT, env=env, text=True, capture_output=True)
    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["valid"] is True
    out = tmp_path / "cli_forward"
    forward = subprocess.run([sys.executable, "-m", "sludge_vme.cli", "forward", str(CASE_PATH), "--fidelity", "L0", "--out", str(out), "--seed", "11"], cwd=ROOT, env=env, text=True, capture_output=True)
    assert forward.returncode == 0, forward.stderr
    verify = subprocess.run([sys.executable, "-m", "sludge_vme.cli", "verify", str(out), "--strict"], cwd=ROOT, env=env, text=True, capture_output=True)
    assert verify.returncode == 0, verify.stdout + verify.stderr
    inverse_help = subprocess.run([sys.executable, "-m", "sludge_vme.cli", "inverse", "--help"], cwd=ROOT, env=env, text=True, capture_output=True)
    assert inverse_help.returncode == 0
