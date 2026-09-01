from __future__ import annotations

from pathlib import Path

from sludge_vme.config import load_case
from sludge_vme.uq.propagation import propagate
from sludge_vme.uq.sampling import sample_parameters


ROOT = Path(__file__).resolve().parents[1]
CASE = load_case(ROOT / "examples" / "tiny_synthetic.json")


def test_sobol_parameter_samples_are_power_of_two_bounded_and_reproducible() -> None:
    first = sample_parameters(n_power=2, seed=17)
    second = sample_parameters(n_power=2, seed=17)
    assert first == second
    assert len(first) == 4
    assert all(0.85 <= sample["cp_scale"] <= 1.15 for sample in first)
    assert all(0.5 <= sample["kinetics_scale"] <= 2.0 for sample in first)


def test_uncertainty_propagation_orders_quantiles_and_counts_failures() -> None:
    samples = sample_parameters(n_power=1, seed=23)
    result = propagate(CASE, "L0", samples)
    assert result.failure_rate == 0.0
    stats = result.statistics["bulk_density_kg_m3"]
    assert stats["min"] <= stats["q05"] <= stats["q50"] <= stats["q95"] <= stats["max"]
    assert result.model_discrepancy["status"] == "reported_separately"
