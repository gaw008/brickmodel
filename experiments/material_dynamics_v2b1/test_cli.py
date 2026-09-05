import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from model import Config

HERE = Path(__file__).resolve().parent
IDS = ["base", "reaction_slow", "reaction_fast", "carbon_low", "carbon_high", "film_weak",
       "film_strong", "sealed", "finite_small", "finite_medium", "finite_large", "no_reaction"]


class CLITests(unittest.TestCase):
    def test_all_twelve_cli_exports_are_real_audited_and_plotted(self):
        self.assertTrue((HERE/"run.py").is_file(), "CLI not implemented")
        from audit import audit_directory
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            out = Path(tmp)/"demo"
            completed = subprocess.run([sys.executable, str(HERE/"run.py"), "--out", str(out)],
                                       capture_output=True, text=True, timeout=180)
            self.assertEqual(completed.returncode, 0, completed.stdout+completed.stderr)
            doc = json.loads((out/"summary.json").read_text())
            self.assertEqual([s["scenario_id"] for s in doc["scenarios"]], IDS)
            self.assertEqual(audit_directory(out)["status"], "passed")
            verification = json.loads((out/"verification.json").read_text())
            self.assertEqual(verification["status"], "passed")
            self.assertEqual(verification["resources"]["threads"], 1)
            self.assertLess(verification["resources"]["peak_rss_mib"], 512)
            self.assertLess(verification["resources"]["wall_seconds"], 180)
            with (out/"timeseries.csv").open() as stream:
                series = list(csv.DictReader(stream))
            for name in ("oxygen_carbon_trajectories.svg", "scenario_diagnostics.svg"):
                tree = ET.parse(out/name)
                text = (out/name).read_text()
                self.assertIn("无量纲机制情景，非工厂配方/烧成时长预测", text)
                self.assertNotIn("<script", text)
                self.assertIsNotNone(tree.getroot())
            tree = ET.parse(out/"oxygen_carbon_trajectories.svg")
            curves = tree.findall(".//{http://www.w3.org/2000/svg}polyline")
            self.assertEqual(len(curves), 16)
            for curve in curves:
                sid, metric = curve.attrib["data-scenario"], curve.attrib["data-metric"]
                points = [tuple(map(float, point.split(","))) for point in curve.attrib["points"].split()]
                rows = [r for r in series if r["scenario_id"] == sid]
                self.assertEqual(len(points), len(rows))
                x0, y0 = float(curve.attrib["data-x0"]), float(curve.attrib["data-y0"])
                width, height = float(curve.attrib["data-width"]), float(curve.attrib["data-height"])
                for (x,y), row in zip(points, rows):
                    self.assertAlmostEqual(x, x0+width*float(row["tau"])/20, places=3)
                    self.assertAlmostEqual(y, y0+height*(1-float(row[metric])), places=3)
            report = (out/"DIAGNOSTIC_REPORT.md").read_text()
            self.assertIn("未验证真实污泥材料规律", report)
            self.assertIn("finite_small", report)
            self.assertIn("0.625", report)
            self.assertIn("Safety", report)

    def test_frozen_input_coverage_and_parameters(self):
        changes = [{}, {"K":.1}, {"K":10}, {"Gamma":.25}, {"Gamma":8}, {"Bi":.1}, {"Bi":10},
                   {"boundary_mode":"sealed"}, {"boundary_mode":"finite","reservoir_ratio":.25},
                   {"boundary_mode":"finite","reservoir_ratio":1},
                   {"boundary_mode":"finite","reservoir_ratio":10}, {"K":0}]
        from test_model import config
        self.assertEqual({p.stem for p in (HERE/"inputs").glob("*.json")}, set(IDS))
        for sid, delta in zip(IDS, changes):
            actual = Config.from_json((HERE/"inputs"/(sid+".json")).read_text()).to_dict()
            self.assertEqual(actual, config(scenario_id=sid, **delta))

    def test_timeout_is_partial_and_invalid_configuration_fails_closed(self):
        self.assertTrue((HERE/"run.py").is_file(), "CLI not implemented")
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root = Path(tmp)
            out = root/"timeout"
            command = [sys.executable, str(HERE/"run.py"), "--out", str(out), "--budget-seconds", "0.000001"]
            done = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(done.returncode, 0)
            doc = json.loads((out/"verification.json").read_text())
            self.assertEqual(doc["status"], "partial")
            self.assertEqual(doc["reason"], "timeout")
            invalid = root/"invalid.json"
            invalid.write_text('{"K":NaN}')
            done = subprocess.run([sys.executable, str(HERE/"run.py"), "--out", str(root/"bad"),
                                   "--config", str(invalid)], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(done.returncode, 0)
            self.assertNotIn("Traceback", done.stderr)
            self.assertIn("invalid_configuration", done.stdout)


if __name__ == "__main__":
    unittest.main()
