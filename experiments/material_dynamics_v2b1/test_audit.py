import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from model import Config
from solver import simulate
from test_model import config

HERE = Path(__file__).resolve().parent


class ExportTests(unittest.TestCase):
    def test_export_contains_profiles_and_signed_integrated_boundary_flux(self):
        self.assertIsNotNone(importlib.util.find_spec("export"), "export not implemented")
        from export import write_results
        results = [simulate(Config.from_dict(config(scenario_id="test_"+mode, n_cells=7, tau_end=.2,
                    boundary_mode=mode, reservoir_ratio=.25 if mode == "finite" else None)))
                   for mode in ("finite", "infinite", "sealed")]
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            write_results(results, Path(tmp))
            for name in ("summary.json", "timeseries.csv", "profiles.csv", "boundary_flux.csv"):
                self.assertTrue((Path(tmp)/name).is_file())
            summary = json.loads((Path(tmp)/"summary.json").read_text())
            self.assertEqual(len(summary["scenarios"]), 3)
            with (Path(tmp)/"timeseries.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 9)
            self.assertTrue(all(row["u_res"] == "" for row in rows if row["scenario_id"] != "test_finite"))
            with (Path(tmp)/"boundary_flux.csv").open() as stream:
                fluxes = list(csv.DictReader(stream))
            self.assertEqual(len(fluxes), 6)
            self.assertLess(float(fluxes[0]["o2_net_out_increment"]), 0)
            self.assertGreater(float(fluxes[0]["co2_net_out_increment"]), 0)


class AuditTests(unittest.TestCase):
    def test_independent_audit_rejects_inventory_and_flux_mutations(self):
        self.assertIsNotNone(importlib.util.find_spec("audit"), "independent audit not implemented")
        from audit import AuditError, audit_directory
        from export import write_results
        results = [simulate(Config.from_dict(config(scenario_id="case_"+mode, n_cells=7, tau_end=.3,
                    boundary_mode=mode, reservoir_ratio=.25 if mode == "finite" else None)))
                   for mode in ("finite", "infinite", "sealed")]
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            out = Path(tmp)
            write_results(results, out)
            good = audit_directory(out)
            self.assertEqual(good["status"], "passed")
            self.assertEqual(good["tolerance"], 1e-6)
            self.assertEqual(good["scenarios_checked"], 3)
            self.assertLess(good["max_scaled_error"], 1e-10)
            for name, field in (("profiles.csv", "f"), ("timeseries.csv", "co2_body"),
                                ("boundary_flux.csv", "o2_net_out_increment")):
                original = (out/name).read_text()
                with (out/name).open() as stream:
                    reader = csv.DictReader(stream)
                    fields, rows = reader.fieldnames, list(reader)
                assert fields is not None
                rows[1][field] = str(float(rows[1][field])+.02)
                with (out/name).open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fields)
                    writer.writeheader()
                    writer.writerows(rows)
                with self.subTest(file=name), self.assertRaises(AuditError):
                    audit_directory(out)
                (out/name).write_text(original)
            flux = out/"boundary_flux.csv"
            original = flux.read_text()
            flux.write_text("\n".join(original.splitlines()[:-1])+"\n")
            with self.assertRaises(AuditError):
                audit_directory(out)
            flux.write_text(original)
            summary = out/"summary.json"
            doc = json.loads(summary.read_text())
            doc["tolerance"] = 1.0
            summary.write_text(json.dumps(doc))
            with self.assertRaises(AuditError):
                audit_directory(out)


    def test_absent_events_nonfinite_inventory_and_false_local_claim_are_rejected(self):
        from audit import AuditError, audit_directory
        from export import write_results
        result = simulate(Config.from_dict(config(n_cells=7, tau_end=.2)))
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            out = Path(tmp)
            write_results([result], out)
            summary = out/"summary.json"
            original = summary.read_text()
            for field, value in (("t_burn95", 0), ("pressure", 0), ("max_local_meets_95", True), ("max_local_meets_99", True)):
                doc = json.loads(original)
                s = doc["scenarios"][0]
                if field == "pressure":
                    s["not_modelled"][field] = value
                elif field.startswith("max_local_meets_"):
                    s["final"][field] = value
                else:
                    s[field] = value
                summary.write_text(json.dumps(doc))
                with self.subTest(field=field), self.assertRaises(AuditError):
                    audit_directory(out)
            summary.write_text(original)
            path = out/"profiles.csv"
            rows = path.read_text().splitlines()
            fields = rows[1].split(",")
            fields[-1] = "NaN"
            rows[1] = ",".join(fields)
            path.write_text("\n".join(rows)+"\n")
            with self.assertRaises(AuditError):
                audit_directory(out)


if __name__ == "__main__":
    unittest.main()
