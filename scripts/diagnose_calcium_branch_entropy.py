"""Offline saved-scalar calcium entropy diagnosis; no model import or call.

Missing donor or coefficient records stay incomplete. Known negative entropy
is retained even when its cause cannot be determined. No clipping or floors.
"""
from __future__ import annotations
import math

UNITS = {"temperature_k": "K", "delta_mu_j_mol": "J/mol", "rate_mol_s": "mol/s",
         "entropy_w_k": "W/K", "lime_mol": "mol", "calcite_mol": "mol", "portlandite_mol": "mol",
         "co2_pressure_pa": "Pa", "water_pressure_pa": "Pa", "mobility_per_s": "1/s",
         "reverse_factor": "1", "phase_multiplier": "1"}


def comparison(actual, expected, identity_limit):
    residual = actual - expected
    budget = abs(actual) + abs(expected)
    return {"signed_residual": residual, "component_budget": budget,
            "relative": abs(residual) / budget if budget else None,
            "existing_identity_limit": identity_limit,
            "within_existing_identity_limit": abs(residual) < identity_limit * budget if budget else residual == 0,
            "scope": "Scalar arithmetic diagnostic, not a formal rounding bound or dynamic acceptance"}


def diagnose(record, config):
    # mobility_per_s is the full effective coefficient at this T, not bare A.
    # OH includes factor*A*exp(-E/RT); carbonate reverse/M are separate.
    # Only the direct channel uses independently supplied L.
    p = config["parameters"]
    R = p["reference.R"]["value"]
    Pr = p["reference.pressure"]["value"]
    limit = p["validation.hydroxide.identity_tolerance"]["value"]
    if p["reference.R"]["unit"] != "J/mol/K" or p["reference.pressure"]["unit"] != "Pa":
        raise ValueError("root R/Pr units differ from the existing host contract")
    out = {"id": record["id"], "branch": record["branch"], "raw": dict(record),
           "issues": [], "unavailable": [], "strict_entropy_nonnegative": None,
           "dynamic_qualified": False, "R_Pr_source": "explicit root reference.R/reference.pressure"}
    issues, missing = out["issues"], out["unavailable"]
    def finish():
        out["sample_contract_validation"] = "violated" if issues else "incomplete" if missing else "verified_for_saved_scalar_observations"
        return out
    def value(key):
        if key not in record or record[key] is None:
            missing.append(key)
            return None
        v = record[key]
        if type(v) not in (int, float) or not math.isfinite(v):
            issues.append("nonfinite:" + key)
            return None
        return v
    reported = value("entropy_w_k")
    if reported is not None:
        out["strict_entropy_nonnegative"] = reported >= 0
        if reported < 0:
            issues.append("strict_negative_reported_entropy")
    if "units" not in record:
        missing.append("source_declared_units; no declaration invented from field names")
    else:
        for key, unit in UNITS.items():
            if key in record and key not in record["units"]:
                missing.append("declared_unit:" + key)
            elif key in record["units"] and record["units"][key] != unit:
                issues.append("unit_mismatch:" + key)
    T, dg, rate = (value(k) for k in ("temperature_k", "delta_mu_j_mol", "rate_mol_s"))
    if any(v is None for v in (T, dg, rate)):
        return finish()
    if T <= 0:
        issues.append("nonpositive_temperature")
        return finish()
    computed = -rate * dg / T
    out["computed_entropy_w_k"] = computed
    dissipative = rate == 0 or dg == 0 or (rate > 0) != (dg > 0)
    out["rate_opposes_gibbs_difference"] = dissipative
    if not dissipative:
        issues.append("rate_dissipation_sign_violation")
    if reported is not None:
        out["entropy_identity"] = comparison(reported, computed, limit)
        if not out["entropy_identity"]["within_existing_identity_limit"]:
            issues.append("entropy_identity_mismatch")
    branch = record["branch"]
    forward = dg <= 0
    donor_key = ({"hydroxide": "portlandite_mol", "carbonate": "calcite_mol", "direct": "portlandite_mol"}
                 if forward else {"hydroxide": "lime_mol", "carbonate": "lime_mol", "direct": "calcite_mol"})[branch]
    gas_key = ("co2_pressure_pa" if forward and branch == "direct" else
               "water_pressure_pa" if not forward and branch in ("hydroxide", "direct") else
               "co2_pressure_pa" if not forward and branch == "carbonate" else None)
    donor = value(donor_key)
    pressure = value(gas_key) if gas_key else Pr
    k = value("mobility_per_s")
    reverse = value("reverse_factor") if branch == "carbonate" else 1
    multiplier = value("phase_multiplier") if branch == "carbonate" else 1
    out.update(active_donor_field=donor_key, active_pressure_field=gas_key, active_donor_mol=donor)
    if donor is not None and donor < 0:
        issues.append("negative_active_donor")
    if pressure is not None and pressure < 0:
        issues.append("negative_active_gas_pressure")
    if any(v is None for v in (donor, pressure, k, reverse, multiplier)):
        return finish()
    if k < 0 or reverse < 0 or multiplier <= 0:
        issues.append("coefficient_domain_violation")
    a = dg / (R * T)
    drive = -math.expm1(a if forward else -a)
    expected = k * (donor * pressure / Pr * drive) * (1 if forward else -reverse) * multiplier
    out["rate_identity"] = comparison(rate, expected, limit)
    if not out["rate_identity"]["within_existing_identity_limit"]:
        issues.append("rate_identity_mismatch")
    out["cause_scope"] = "Donor-domain witness only; no attribution to subtraction, Newton, dense output or roundoff"
    return finish()
