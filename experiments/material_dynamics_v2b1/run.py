#!/usr/bin/env python3
"""Offline B1 diagnostic runner. Existing output directories are never overwritten."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import resource
import time

from audit import AuditError, audit_directory
from export import write_json, write_results
from model import Config, SCOPE
from plots import draw
from reporting import write_report
from solver import simulate
from verification import verify_numerics

HERE = Path(__file__).resolve().parent
SCENARIOS = ("base", "reaction_slow", "reaction_fast", "carbon_low", "carbon_high", "film_weak",
             "film_strong", "sealed", "finite_small", "finite_medium", "finite_large", "no_reaction")
MAX_WALL_SECONDS = 180.0
MAX_MEMORY_BYTES = 512*1024*1024


def resources(start):
    return dict(wall_seconds=time.monotonic()-start,
                peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                threads=len(tuple(Path("/proc/self/task").iterdir())), workers=1,
                wall_budget_seconds=MAX_WALL_SECONDS, memory_budget_mib=512)


def owned_path(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(HERE) or resolved == HERE:
        raise ValueError("path outside standalone experiment")
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE/"artifacts")
    parser.add_argument("--config", type=Path, help="one strict JSON inside this experiment; defaults run all 12")
    parser.add_argument("--budget-seconds", type=float, default=MAX_WALL_SECONDS, help="only tighten the 180s budget")
    args = parser.parse_args()
    start = time.monotonic()
    out = None
    results = []
    stage = "configuration"
    try:
        if not math.isfinite(args.budget_seconds) or not 0 < args.budget_seconds <= MAX_WALL_SECONDS:
            raise ValueError("invalid budget")
        out = owned_path(args.out)
        # Prevent accidental writes to source, inputs, or a prior completed run.
        if out.exists():
            out = None
            raise ValueError("output already exists")
        configs = []
        paths = [owned_path(args.config)] if args.config else [HERE/"inputs"/(sid+".json") for sid in SCENARIOS]
        for path in paths:
            if path.stat().st_size > 16384:
                raise ValueError("configuration too large")
            configs.append(Config.from_json(path.read_text(encoding="utf-8")))
        if not args.config and [c.scenario_id for c in configs] != list(SCENARIOS):
            raise ValueError("frozen scenario coverage mismatch")
        out.mkdir(parents=True, exist_ok=False)
        # Process-local hard resource limit; no shared environment changes.
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        cap = min([MAX_MEMORY_BYTES] + [v for v in (soft,hard) if v != resource.RLIM_INFINITY])
        resource.setrlimit(resource.RLIMIT_AS, (cap,cap))
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ[name] = "1"
        deadline = start+args.budget_seconds

        def within_budget():
            if time.monotonic() > deadline:
                raise TimeoutError("wall-time budget exceeded")

        stage = "simulation"
        for cfg in configs:
            within_budget()
            result = simulate(cfg, deadline=deadline)
            results.append(result)
            print(json.dumps(dict(scenario_id=cfg.scenario_id, status="integrated", steps=result.steps)), flush=True)
        within_budget()
        stage = "export"
        write_results(results, out)
        stage = "audit"
        audited = audit_directory(out)
        write_json(out/"audit.json", audited)
        within_budget()
        stage = "numerical_verification"
        if args.config:
            numeric = dict(status="not_run_custom_configuration", reason="prescribed_refinement_applies_to_default_suite")
        else:
            numeric = verify_numerics({r.config.scenario_id:r for r in results}, deadline=deadline)
        verification = dict(schema_version=1, scope=SCOPE,
                            status="passed" if numeric["status"] in ("passed","not_run_custom_configuration") else "failed",
                            created_at_utc=datetime.now(timezone.utc).isoformat(),
                            audit=audited, numerics=numeric, scenarios_completed=[c.scenario_id for c in configs],
                            verification_scope="audit_only" if args.config else "audit_and_prescribed_numerical_references",
                            safety_review="pending_independent_child", resources=resources(start))
        write_json(out/"verification.json", verification)
        stage = "plots_and_report"
        within_budget()
        draw(out)
        write_report(out, verification)
        within_budget()
        verification["resources"] = resources(start)
        verification["resources"]["wall_budget_seconds"] = args.budget_seconds
        write_json(out/"verification.json", verification)
        print(json.dumps(dict(status=verification["status"], scenarios=len(results),
                              resources=verification["resources"], audit_max_scaled_error=audited["max_scaled_error"])))
        return 0 if verification["status"] == "passed" else 1
    except (TimeoutError, MemoryError) as error:
        failure = dict(status="partial", reason="timeout" if isinstance(error,TimeoutError) else "memory_limit",
                       stage=stage, scenarios_completed=[r.config.scenario_id for r in results], resources=resources(start))
        code = 3
    except (ValueError, OSError, ArithmeticError, AuditError):
        failure = dict(status="numerical_failure" if stage != "configuration" else "invalid_configuration",
                       reason="rejected", stage=stage, scenarios_completed=[r.config.scenario_id for r in results])
        code = 2
    if out is not None and out.is_dir():
        # Never claim complete on timeout/failure; preserve any prior successful CSVs.
        if (out/"summary.json").is_file():
            doc = json.loads((out/"summary.json").read_text(encoding="utf-8"))
            doc["run_status"] = failure["status"]
            write_json(out/"summary.json", doc)
        write_json(out/"verification.json", failure)
    print(json.dumps(failure))  # Allowlisted messages only; no raw exception/path dump.
    return code


if __name__ == "__main__":
    raise SystemExit(main())
