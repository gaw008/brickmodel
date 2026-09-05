"""Read committed demo evidence and check both SVGs against its actual exports."""
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from audit import audit_directory

HERE = Path(__file__).resolve().parent


def main():
    out = HERE/"artifacts"
    audited = audit_directory(out)
    summary = json.loads((out/"summary.json").read_text())["scenarios"]
    lookup = {s["scenario_id"]: s for s in summary}
    verification = json.loads((out/"verification.json").read_text())
    tests = json.loads((HERE/"validation/test_results.json").read_text())
    with (out/"timeseries.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    ns = "{http://www.w3.org/2000/svg}"
    curves = ET.parse(out/"oxygen_carbon_trajectories.svg").findall(".//"+ns+"polyline")
    points_checked = 0
    for curve in curves:
        a = curve.attrib
        source = [r for r in rows if r["scenario_id"] == a["data-scenario"]]
        points = [tuple(map(float,p.split(","))) for p in a["points"].split()]
        assert len(source) == len(points)
        horizon = lookup[a["data-scenario"]]["config"]["tau_end"]
        for row,(x,y) in zip(source,points):
            assert abs(x-float(a["data-x0"])-float(a["data-width"])*float(row["tau"])/horizon) < 1e-4
            assert abs(y-float(a["data-y0"])-float(a["data-height"])*(1-float(row[a["data-metric"]]))) < 1e-4
            points_checked += 1
    bars = [r for r in ET.parse(out/"scenario_diagnostics.svg").findall(".//"+ns+"rect") if "data-scenario" in r.attrib]
    assert len(bars) == len(summary)*2
    for bar in bars:
        a = bar.attrib
        expected = lookup[a["data-scenario"]]["final"][a["data-metric"]]
        assert float(a["data-value"]) == expected
        assert abs(float(a["width"])-420*expected) <= 1e-5
    brief = dict(audit=audited, resources=verification["resources"],
                 focused_tests=dict(status=tests["status"],count=tests["tests_run"],failures=tests["failures"],errors=tests["errors"]),
                 svg_checks=dict(curves=len(curves),coordinate_pairs=points_checked,bars=len(bars),status="passed"),
                 scenario_evidence=[dict(scenario_id=s["scenario_id"],
                                        carbon_mean_percent=s["final"]["carbon_mean"]*100,
                                        carbon_max_percent=s["final"]["carbon_max"]*100,
                                        source_rate=s["final"]["co2_source_rate"],
                                        t_burn95=s["t_burn95"],t_burn99=s["t_burn99"],
                                        status=s["status"]) for s in summary])
    print(json.dumps(brief,indent=2))


if __name__ == "__main__":
    main()
