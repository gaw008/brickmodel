from __future__ import annotations

from pathlib import Path

import numpy as np

from sludge_vme.config import load_case
from sludge_vme.inverse.pareto import nondominated_mask
from sludge_vme.inverse.search import run_inverse


ROOT = Path(__file__).resolve().parents[1]
CASE = load_case(ROOT / "examples" / "tiny_synthetic.json")


def test_nondominated_filter_excludes_infeasible_nan_and_dominated_rows() -> None:
    objectives = np.array([[1.0, 1.0], [2.0, 2.0], [0.5, 3.0], [np.nan, 0.0], [0.0, 0.0]])
    feasible = np.array([True, True, True, True, False])
    assert nondominated_mask(objectives, feasible).tolist() == [True, False, True, False, False]


def test_tiny_inverse_returns_reproducible_multiple_constrained_candidates() -> None:
    first = run_inverse(CASE, budget="tiny", seed=20260831)
    second = run_inverse(CASE, budget="tiny", seed=20260831, refine_l1=False)
    assert first.status == "success"
    assert len(first.all_evaluations) == 16
    assert len(first.feasible_set) >= 2
    assert len(first.ranked_candidates) >= 2
    assert all(item["constraints"]["all_hard_constraints"] for item in first.ranked_candidates)
    assert all(item["fidelity"] == "L1" for item in first.ranked_candidates)
    assert [item["decision"] for item in first.all_evaluations] == [item["decision"] for item in second.all_evaluations]
    pareto_objectives = np.array([item["objectives"] for item in first.pareto_set])
    if len(pareto_objectives):
        assert nondominated_mask(pareto_objectives, np.ones(len(pareto_objectives), dtype=bool)).all()
    assert first.environmental_status == "not_evaluated"
    assert first.rank_stability["status"] in {"stable", "unstable", "insufficient_points"}
