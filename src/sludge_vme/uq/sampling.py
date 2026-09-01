from __future__ import annotations

import math

from scipy.stats import qmc

PARAMETER_POLICY = {
    "cp_scale": {"bounds": [0.85, 1.15], "kind": "synthetic_policy_interval"},
    "conductivity_scale": {"bounds": [0.70, 1.30], "kind": "closure_ensemble_policy"},
    "kinetics_scale": {"bounds": [0.50, 2.00], "kind": "log_uniform_policy"},
    "h_scale": {"bounds": [0.80, 1.20], "kind": "synthetic_boundary_interval"},
    "diffusivity_scale": {"bounds": [0.50, 2.00], "kind": "log_uniform_policy"},
    "connectivity_scale": {"bounds": [0.80, 1.20], "kind": "model_form_interval"},
    "sintering_scale": {"bounds": [0.50, 2.00], "kind": "log_uniform_policy"},
}


def sample_parameters(n_power: int, seed: int, scramble: bool = True) -> list[dict[str, float]]:
    if not isinstance(n_power, int) or n_power < 0:
        raise ValueError("n_power must be a nonnegative integer so sample count is 2**n_power")
    names = list(PARAMETER_POLICY)
    points = qmc.Sobol(d=len(names), scramble=scramble, seed=int(seed)).random_base2(n_power)
    samples: list[dict[str, float]] = []
    for point in points:
        sample: dict[str, float] = {"grid_check": False}
        for name, unit_value in zip(names, point):
            low, high = PARAMETER_POLICY[name]["bounds"]
            if "log_uniform" in PARAMETER_POLICY[name]["kind"]:
                sample[name] = math.exp(math.log(low) + float(unit_value) * (math.log(high) - math.log(low)))
            else:
                sample[name] = low + float(unit_value) * (high - low)
        samples.append(sample)
    return samples
