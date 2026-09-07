"""Independent Table 1 algebra; run from repository root with PYTHONPATH=src."""
import hashlib
import json
import math
from pathlib import Path

from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[3]
    source = root / "data/sandbox/water"
    facts = json.loads((source / "source_facts.json").read_text())
    alignment = json.loads((source / "reference_alignment.json").read_text())
    constants = facts["iapws_constants"]
    coefficients = facts["ideal_formula_constants"]
    water = load_water_properties(source)
    candidate = WaterChemicalPotential(source)
    mass = water.reference.molar_mass_kg_mol
    r95 = constants["R_specific_j_kg_k"] * mass
    rmix = 8.31446261815324
    p0 = 100000.0
    rows = []
    for t in (293., 298.15, 313.15, 333.15, 373.15, 423.15, 473.15, 500.):
        tau = constants["T_critical_k"] / t
        delta = p0 / (constants["R_specific_j_kg_k"] * t * constants["rho_critical_kg_m3"])
        terms = tuple(zip(coefficients["n4_to_n8"], coefficients["gamma4_to_gamma8"]))
        phi = math.fsum((math.log(delta), coefficients["n1"], coefficients["n2"] * tau,
                        coefficients["n3"] * math.log(tau),
                        *(n * math.log(-math.expm1(-g * tau)) for n, g in terms)))
        derivative = math.fsum((coefficients["n2"], coefficients["n3"] / tau,
                               *(n * g / math.expm1(g * tau) for n, g in terms)))
        h = r95 * t * (1 + tau * derivative) + alignment["common_energy_shift_j_mol"]
        s0 = r95 * (tau * derivative - phi)
        liquid = water.saturation_pair(t).liquid
        mu_l = liquid.enthalpy_j_mol - t * liquid.native_entropy_j_kg_k * mass
        peq = p0 * math.exp((mu_l - h + t * s0) / (rmix * t))
        actual = candidate.equilibrium_at_saturation(t)
        standard = candidate.ideal_vapor(t, p0)
        row = dict(temperature_k=t, native_psat_pa=liquid.pressure_pa,
                   oracle_peq_pa=peq, hybrid_vs_native_relative=peq / liquid.pressure_pa - 1,
                   implementation_relative_error=actual.equilibrium_partial_pressure_pa / peq - 1,
                   h_error_j_mol=standard.enthalpy_j_mol - h,
                   entropy_error_j_mol_k=standard.entropy_j_mol_k - s0,
                   phase_enthalpy_difference_j_mol=h - liquid.enthalpy_j_mol)
        rows.append(row)
    passed = all(abs(r["implementation_relative_error"]) <= 1e-10
                 and abs(r["h_error_j_mol"]) <= 1e-6
                 and abs(r["entropy_error_j_mol_k"]) <= 1e-8 for r in rows)
    paths = [Path(__file__).resolve(), source / "source_facts.json", source / "reference_alignment.json",
             root / "src/sludge_sandbox/water_chemical_potential.py",
             root / "docs/sandbox/research/WATER_CHEMICAL_ORACLE.md"]
    output = dict(scope="independent_ideal_algebra_shared_liquid_eos_not_material_validation",
                  passed=passed, hashes={str(p.relative_to(root)): digest(p) for p in paths}, rows=rows)
    target = Path(__file__).with_suffix(".json")
    target.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(output, indent=2, allow_nan=False))
    if not passed:
        raise SystemExit("registered comparison failed; output preserved")


if __name__ == "__main__":
    main()
