from __future__ import annotations

from pathlib import Path

from sludge_vme.config import load_case
from sludge_vme.inverse.search import run_inverse
from sludge_vme.io.artifacts import verify_run, write_inverse_run


ROOT = Path(__file__).resolve().parents[1]
CASE = load_case(ROOT / "examples" / "tiny_synthetic.json")


def test_inverse_artifacts_preserve_all_evaluations_and_pareto(tmp_path: Path) -> None:
    result = run_inverse(CASE, budget="tiny", seed=20260831)
    out = tmp_path / "inverse"
    write_inverse_run(out, CASE, result, cli_args=["inverse"], seed=20260831)
    required = {"all_evaluations.jsonl", "pareto.json", "pareto.csv", "rank_stability.json", "feasible_windows.json", "report.md"}
    assert required <= {path.name for path in out.iterdir()}
    assert len((out / "all_evaluations.jsonl").read_text().splitlines()) == 16
    verification = verify_run(out, strict=True)
    assert verification.valid, verification.errors
