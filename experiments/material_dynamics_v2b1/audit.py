"""Independent export audit: no solver, diagnostics, or reported residual imports.

Checks integral budgets, schema/coverage and inventory-based diagnostic events.
Does NOT replay the differential equation or certify jointly rewritten artifacts.
"""
import argparse
from collections import defaultdict
import csv
import json
import math
from pathlib import Path

from model import Config, SCOPE, strict_json

TOLERANCE = 1e-6  # Auditor-owned, never loaded from artifacts.
SERIES_FIELDS = "scenario_id tau u_core u_surface carbon_mean carbon_max co2_body co2_generated co2_net_out u_res v_res".split()
PROFILE_FIELDS = "scenario_id tau xi u v f".split()
FLUX_FIELDS = "scenario_id tau_start tau_end o2_net_out_increment co2_net_out_increment".split()


class AuditError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AuditError(reason)


def read_csv(path, fields):
    require(path.stat().st_size <= 64*1024*1024, "export exceeds bounded audit size")
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == fields, "CSV columns differ from schema")
        rows = []
        for row in reader:
            require(set(row) == set(fields), "malformed CSV row")
            converted = {"scenario_id": row["scenario_id"]}
            for key in fields[1:]:
                value = row[key]
                if key in ("u_res", "v_res") and value == "":
                    converted[key] = None
                else:
                    number = float(value)
                    require(math.isfinite(number), "nonfinite CSV value")
                    converted[key] = number
            rows.append(converted)
    return rows


def audit_directory(directory):
    try:
        return _audit(Path(directory))
    except AuditError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OSError, OverflowError, ZeroDivisionError) as error:
        raise AuditError("invalid or missing export structure") from error


def _audit(out):
    doc = strict_json((out/"summary.json").read_text(encoding="utf-8"))
    require(set(doc) == {"schema_version", "scope", "run_status", "scenarios", "audit_scope"}, "summary fields differ from schema")
    require(doc["schema_version"] == 1 and doc["scope"] == SCOPE and doc["run_status"] == "complete", "incomplete or unknown result scope")
    series = read_csv(out/"timeseries.csv", SERIES_FIELDS)
    profiles = read_csv(out/"profiles.csv", PROFILE_FIELDS)
    fluxes = read_csv(out/"boundary_flux.csv", FLUX_FIELDS)
    require(bool(doc["scenarios"]), "empty scenario list")
    configs = {s["scenario_id"]: Config.from_dict(s["config"]) for s in doc["scenarios"]}
    require(len(configs) == len(doc["scenarios"]), "duplicate scenario")
    for table in (series, profiles, fluxes):
        require({r["scenario_id"] for r in table} == set(configs), "scenario coverage mismatch")
    sg, pg, fg = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in series:
        sg[row["scenario_id"]].append(row)
    for row in profiles:
        pg[(row["scenario_id"], row["tau"])].append(row)
    for row in fluxes:
        fg[row["scenario_id"]].append(row)
    max_error, checks = 0.0, 0

    def equal(actual, expected, scale=1.0):
        nonlocal max_error, checks
        require(type(actual) in (int, float) and math.isfinite(actual), "nonfinite/non-numeric audited value")
        error = abs(actual-expected)/max(1.0, scale)
        max_error = max(max_error, error)
        checks += 1
        require(error <= TOLERANCE, "inventory/flux/diagnostic mismatch")

    profile_count = 0
    for summary in doc["scenarios"]:
        sid = summary["scenario_id"]
        cfg = configs[sid]
        require(cfg.scenario_id == sid and summary["scope"] == SCOPE, "scenario config mismatch")
        n, gamma, rho = cfg.n_cells, cfg.Gamma, cfg.reservoir_ratio
        rows, ledger = sg[sid], fg[sid]
        require(len(rows) >= 2 and len(ledger) == len(rows)-1, "missing time/flux record")
        equal(rows[0]["tau"], 0)
        equal(rows[-1]["tau"], cfg.tau_end)
        available = None if cfg.boundary_mode == "infinite" else 1+(rho or 0)
        upper = 1 if available is None else min(1, available/gamma)
        equal(summary["budget"]["max_conversion_upper_bound"], upper)
        equal(summary["budget"]["initial_body_oxygen"], 1)
        equal(summary["budget"]["initial_solid_carbon"], gamma, gamma)
        require(summary["budget"]["total_available_oxygen"] == available, "oxygen budget mismatch")
        require(summary["budget"]["initial_reservoir_oxygen"] == rho, "reservoir budget mismatch")
        require(all(value == "not_modelled" for value in summary["not_modelled"].values()), "unmodelled quantity presented as prediction")
        for key in ("t_close", "pressure", "temperature_field", "energy_conservation", "strength", "kiln_speed"):
            require(summary["not_modelled"].get(key) == "not_modelled", "missing unmodelled declaration")
        net_u, net_v = 0.0, 0.0
        previous_f = [1.0]*n
        for index, row in enumerate(rows):
            tau = row["tau"]
            cells = pg[(sid, tau)]
            require(len(cells) == n, "missing/duplicate profile cell")
            profile_count += n
            if index:
                prior = rows[index-1]
                require(tau > prior["tau"], "nonincreasing sample time")
                entry = ledger[index-1]
                require(entry["tau_start"] == prior["tau"] and entry["tau_end"] == tau, "flux interval gap or reorder")
                net_u += entry["o2_net_out_increment"]
                net_v += entry["co2_net_out_increment"]
                if cfg.boundary_mode == "finite":
                    assert rho is not None  # Config already enforces positive finite rho.
                    equal(rho*(row["u_res"]-prior["u_res"]), entry["o2_net_out_increment"], 1+rho)
                    equal(rho*(row["v_res"]-prior["v_res"]), entry["co2_net_out_increment"], 1+rho)
                if cfg.boundary_mode == "sealed" or cfg.Bi == 0:
                    equal(entry["o2_net_out_increment"], 0)
                    equal(entry["co2_net_out_increment"], 0)
            u, v, f = [], [], []
            for i, cell in enumerate(cells):
                equal(cell["xi"], (i+.5)/n)
                for name in ("u", "v", "f"):
                    require(0 <= cell[name] <= 1+TOLERANCE, "inventory outside invariant domain")
                equal(cell["u"]+cell["v"], 1)
                require(cell["f"] <= previous_f[i]+TOLERANCE, "solid carbon increased")
                if index == 0:
                    equal(cell["u"], 1)
                    equal(cell["v"], 0)
                    equal(cell["f"], 1)
                u.append(cell["u"])
                v.append(cell["v"])
                f.append(cell["f"])
            previous_f = f
            oxygen, co2, carbon = sum(u)/n, sum(v)/n, gamma*sum(f)/n
            generated = gamma-carbon
            equal(row["u_core"], u[0])
            if cfg.boundary_mode == "sealed":
                surface = u[-1]
            else:
                ext = row["u_res"] if cfg.boundary_mode == "finite" else 1.0
                half = .5/n
                # Independent algebraic Robin face reconstruction.
                surface = (u[-1] + cfg.Bi*half*ext)/(1+cfg.Bi*half)
            equal(row["u_surface"], surface)
            equal(row["carbon_mean"], carbon/gamma)
            equal(row["carbon_max"], max(f))
            equal(row["co2_body"], co2)
            equal(row["co2_generated"], generated, gamma)
            equal(row["co2_net_out"], net_v, gamma)
            # Separate O2 consumption, CO2 source and C/O elemental budgets.
            equal(oxygen+generated+net_u, 1, gamma)
            equal(co2+net_v, generated, gamma)
            equal(carbon+co2+net_v, gamma, gamma)
            equal(oxygen+co2+net_u+net_v, 1)
            equal(12*(gamma-carbon)+32*(1-oxygen-net_u), 44*(co2+net_v), 44*gamma)
            require(1-carbon/gamma <= upper+TOLERANCE, "stoichiometric conversion ceiling exceeded")
            if cfg.boundary_mode == "finite":
                assert rho is not None
                require(row["u_res"] is not None and row["v_res"] is not None, "missing finite reservoir")
                require(0 <= row["u_res"] <= 1+TOLERANCE and 0 <= row["v_res"] <= 1+TOLERANCE, "invalid reservoir inventory")
                equal(row["u_res"]+row["v_res"], 1)
                equal(rho*(row["u_res"]-1), net_u, 1+rho)
                equal(rho*row["v_res"], net_v, gamma)
                equal(carbon+co2+rho*row["v_res"], gamma, gamma)
                equal(oxygen+co2+rho*(row["u_res"]+row["v_res"]), 1+rho, 1+rho)
            else:
                require(row["u_res"] is None and row["v_res"] is None, "fabricated exterior state")
            if cfg.K == 0:
                equal(carbon, gamma, gamma)
                equal(row["co2_generated"], 0)
        for percent in (95, 99):
            for key, metric in ((f"t_burn{percent}", "carbon_mean"), (f"t_local_burn{percent}", "carbon_max")):
                crossing = None
                for a, b in zip(rows, rows[1:]):
                    if b[metric] <= 1-percent/100:
                        crossing = a["tau"]+(b["tau"]-a["tau"])*(a[metric]-(1-percent/100))/(a[metric]-b[metric])
                        break
                expected_status = ("reached_diagnostic_threshold" if crossing is not None else
                                   "oxygen_budget_limited" if upper < percent/100 else "not_reached_by_horizon")
                require(summary[key+"_status"] == expected_status, "false threshold status")
                if crossing is None:
                    require(summary[key] is None, "absent event must be null")
                else:
                    equal(summary[key], crossing, cfg.tau_end)
            require(summary["t_gen"][f"t{percent}"] == summary[f"t_burn{percent}"], "CO2 source event mismatch")
        require(summary["status"] == summary["t_burn99_status"], "overall status mismatch")
        require(summary["t_gen"]["species"] == "CO2_only", "gas source scope mismatch")
        final = summary["final"]
        for percent, threshold in ((95, .05), (99, .01)):
            require(final[f"max_local_meets_{percent}"] is (rows[-1]["carbon_max"] <= threshold),
                    "false local completion flag")
        for key, value in rows[-1].items():
            if key == "scenario_id" or value is None:
                require(final[key] == value, "summary final identity/absence mismatch")
            else:
                equal(final[key], value, gamma if key.startswith("co2_") else 1)
        last_cells = pg[(sid, rows[-1]["tau"])]
        u = [c["u"] for c in last_cells]
        v = [c["v"] for c in last_cells]
        f = [c["f"] for c in last_cells]
        oxygen, co2, carbon = sum(u)/n, sum(v)/n, gamma*sum(f)/n
        equal(final["solid_carbon_body"], carbon, gamma)
        equal(final["oxygen_body"], oxygen)
        equal(final["carbon_element_body"], carbon+co2, gamma)
        equal(final["oxygen_equivalents_body"], oxygen+co2)
        equal(final["co2_source_rate"], gamma*cfg.K*sum(a*b for a,b in zip(f,u))/n, gamma)
        if rho is None:
            require(final["co2_reservoir"] is None and final["oxygen_reservoir"] is None, "fabricated reservoir inventory")
        else:
            equal(final["co2_reservoir"], rho*rows[-1]["v_res"], gamma)
            equal(final["oxygen_reservoir"], rho*rows[-1]["u_res"], 1+rho)
    require(profile_count == len(profiles), "unmatched profile records")
    return dict(status="passed", tolerance=TOLERANCE, max_scaled_error=max_error,
                scalar_checks=checks, scenarios_checked=len(configs), timeseries_records=len(series),
                profile_records=len(profiles), boundary_intervals=len(fluxes),
                scope="inventory_and_flux_audit_not_material_validation_or_full_ODE_replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(audit_directory(args.directory), indent=2))
        return 0
    except AuditError:
        print(json.dumps(dict(status="failed", reason="export_audit_rejected", tolerance=TOLERANCE)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
