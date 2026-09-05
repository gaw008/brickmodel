"""Small transparent exports; integral flux ledger is essential audit evidence."""
import csv
import json
from pathlib import Path

from diagnostics import summarize, timeseries_rows
from model import SCOPE


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_results(results, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    summaries = [summarize(result) for result in results]
    write_json(out/"summary.json", dict(schema_version=1, scope=SCOPE,
               run_status="complete", scenarios=summaries,
               audit_scope="exported_inventory_and_integrated_boundary_flux_not_full_semantic_replay"))
    series = [row for result in results for row in timeseries_rows(result)]
    write_csv(out/"timeseries.csv", ["scenario_id", "tau", "u_core", "u_surface", "carbon_mean", "carbon_max",
              "co2_body", "co2_generated", "co2_net_out", "u_res", "v_res"], series)

    def profiles():
        for result in results:
            for rec in result.records:
                for i, (u,v,f) in enumerate(zip(rec.state.u,rec.state.v,rec.state.f)):
                    yield dict(scenario_id=result.config.scenario_id, tau=rec.tau,
                               xi=(i+.5)/result.config.n_cells, u=u, v=v, f=f)
    write_csv(out/"profiles.csv", ["scenario_id", "tau", "xi", "u", "v", "f"], profiles())

    def fluxes():
        for result in results:
            for a,b in zip(result.records, result.records[1:]):
                yield dict(scenario_id=result.config.scenario_id, tau_start=a.tau, tau_end=b.tau,
                           o2_net_out_increment=b.state.net_u-a.state.net_u,
                           co2_net_out_increment=b.state.net_v-a.state.net_v)
    write_csv(out/"boundary_flux.csv", ["scenario_id", "tau_start", "tau_end", "o2_net_out_increment",
                                       "co2_net_out_increment"], fluxes())
    return summaries
