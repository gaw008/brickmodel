from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

from .config import load_case
from .inverse.search import run_inverse
from .io.artifacts import _begin_atomic_output, _exception_category, _finish_atomic_output, _write_json, verify_run, write_forward_run, write_inverse_run, write_structured_failure
from .models import simulate
from .uq.propagation import propagate
from .uq.sampling import sample_parameters
from .validation import validate_case

EXIT_VALIDATION = 2
EXIT_SOLVER = 3
EXIT_COVERAGE = 4
EXIT_RESOURCE = 5
EXIT_INTERNAL = 10


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sludge-vme", description="Research-only synthetic sludge fired-brick forward/inverse virtual materials engine")
    sub = parser.add_subparsers(dest="command", required=True)

    cycle = sub.add_parser("full-cycle", help="run the traceable ventilated full-cycle approximation")
    cycle.add_argument("parameters", type=Path)
    cycle.add_argument("--out", type=Path, required=True)
    cycle.add_argument("--acceptance", action="store_true")

    validate = sub.add_parser("validate", help="validate and normalize a JSON case")
    validate.add_argument("case", type=Path)
    validate.add_argument("--json", action="store_true")

    forward = sub.add_parser("forward", help="run L0 lumped or L1 half-slab forward model")
    forward.add_argument("case", type=Path)
    forward.add_argument("--fidelity", choices=("L0", "L1"), required=True)
    forward.add_argument("--out", type=Path, required=True)
    forward.add_argument("--uq-power", type=int)
    forward.add_argument("--seed", type=int, default=20260831)
    forward.add_argument("--overwrite", action="store_true")

    inverse = sub.add_parser("inverse", help="run constrained Sobol/UQ/L1/Pareto inverse search")
    inverse.add_argument("case", type=Path)
    inverse.add_argument("--budget", choices=("tiny", "default"), default="tiny")
    inverse.add_argument("--out", type=Path, required=True)
    inverse.add_argument("--seed", type=int, default=20260831)
    inverse.add_argument("--overwrite", action="store_true")

    verify = sub.add_parser("verify", help="verify hashes, conservation, status and Pareto artifacts")
    verify.add_argument("run_dir", type=Path)
    verify.add_argument("--strict", action="store_true")

    sources = sub.add_parser("sources", help="show parameter/source registry and known unknowns")
    sources.add_argument("--json", action="store_true")

    benchmark = sub.add_parser("benchmark", help="run target-machine L0/L1 benchmark")
    benchmark.add_argument("case", type=Path)
    benchmark.add_argument("--out", type=Path, required=True)
    benchmark.add_argument("--seed", type=int, default=20260831)
    benchmark.add_argument("--overwrite", action="store_true")
    return parser


def _load_valid(path: Path):
    case = load_case(path)
    report = validate_case(case)
    return case, report


def _record_solver_exception(
    args: argparse.Namespace,
    case,
    exc: Exception,
    *,
    stage: str,
    fidelity: str | None = None,
    budget: str | None = None,
) -> int:
    directory = write_structured_failure(
        args.out,
        case,
        exc,
        stage=stage,
        cli_args=sys.argv[1:],
        seed=args.seed,
        overwrite=args.overwrite,
        fidelity=fidelity,
        budget=budget,
    )
    print(f"ERROR: structured solver failure stage={stage} reason=solver_runtime_exception", file=sys.stderr)
    return EXIT_SOLVER


def command_validate(args: argparse.Namespace) -> int:
    case, report = _load_valid(args.case)
    payload = report.as_dict()
    payload["case_hash"] = case.content_hash
    payload["spec_version"] = case.raw.get("spec_version") if isinstance(case.raw, dict) else None
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"valid={report.valid} errors={len(report.errors)} warnings={len(report.warnings)} source_coverage={report.source_coverage:.3f}")
        for item in [*report.errors, *report.warnings]:
            print(f"{item.code}: {item.path}: {item.message}")
    return 0 if report.valid else EXIT_VALIDATION


def command_forward(args: argparse.Namespace) -> int:
    case, report = _load_valid(args.case)
    if not report.valid:
        print(json.dumps(report.as_dict(), indent=2), file=sys.stderr)
        return EXIT_VALIDATION
    try:
        result = simulate(case, args.fidelity)
        uncertainty = None
        if args.uq_power is not None and result.status.success:
            uncertainty = propagate(case, args.fidelity, sample_parameters(args.uq_power, args.seed))
    except Exception as exc:
        return _record_solver_exception(args, case, exc, stage=f"forward_{args.fidelity}", fidelity=args.fidelity)
    directory = write_forward_run(args.out, case, result, cli_args=sys.argv[1:], seed=args.seed, uncertainty=uncertainty, overwrite=args.overwrite)
    print(f"RESEARCH-ONLY synthetic forward {args.fidelity}: status={result.status.code} out={directory}")
    print(f"mass_residual={result.conservation.get('mass_relative_residual')} element_residual={result.conservation.get('max_element_relative_residual')} reduced_effective_enthalpy_ode_residual={result.conservation.get('reduced_effective_enthalpy_ode_relative_residual')}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 0 if result.status.success else EXIT_SOLVER


def command_inverse(args: argparse.Namespace) -> int:
    case, report = _load_valid(args.case)
    if not report.valid:
        print(json.dumps(report.as_dict(), indent=2), file=sys.stderr)
        return EXIT_VALIDATION
    try:
        result = run_inverse(case, budget=args.budget, seed=args.seed)
    except Exception as exc:
        return _record_solver_exception(args, case, exc, stage="inverse", budget=args.budget)
    directory = write_inverse_run(args.out, case, result, cli_args=sys.argv[1:], seed=args.seed, overwrite=args.overwrite)
    l0_design_count = sum(item.get("fidelity") == "L0" for item in result.all_evaluations)
    print(f"RESEARCH-ONLY synthetic inverse: status={result.status} evaluated={l0_design_count} records={len(result.all_evaluations)} L0_feasible={len(result.feasible_set)} L1_ranked={len(result.ranked_candidates)} pareto={len(result.pareto_set)} out={directory}")
    print("environmental_status=not_evaluated; no plant recipe, certification, deployment or control action was produced")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 0 if result.status == "success" else EXIT_SOLVER


def command_verify(args: argparse.Namespace) -> int:
    result = verify_run(args.run_dir, strict=args.strict)
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0 if result.valid else EXIT_SOLVER


def command_sources(args: argparse.Namespace) -> int:
    path = Path(__file__).resolve().parents[2] / "data" / "sources.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f"source_pack={payload['pack_id']} sources={len(payload['sources'])}")
        for item in payload["sources"]:
            print(f"- {item['id']}: {item.get('url', item.get('path'))} [{item['kind']}] — {item['validity']}")
        print("Known unknowns:")
        for item in payload["known_unknowns"]:
            print(f"- {item}")
    return 0


def command_benchmark(args: argparse.Namespace) -> int:
    case, report = _load_valid(args.case)
    if not report.valid:
        print(json.dumps(report.as_dict(), indent=2), file=sys.stderr)
        return EXIT_VALIDATION
    records = []
    results = {}
    for fidelity in ("L0", "L1"):
        started = time.perf_counter()
        try:
            result = simulate(case, fidelity)
        except Exception as exc:
            return _record_solver_exception(args, case, exc, stage=f"benchmark_{fidelity}", fidelity=fidelity)
        wall = time.perf_counter() - started
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        results[fidelity] = result
        records.append({"fidelity": fidelity, "status": result.status.code, "wall_time_s": wall, "peak_rss_bytes_process_high_water": peak_rss, "solver_statistics": result.solver_statistics})
    target, out, transaction = _begin_atomic_output(args.out, args.overwrite)
    for fidelity in ("L0", "L1"):
        result = results[fidelity]
        write_forward_run(out / fidelity, case, result, cli_args=sys.argv[1:], seed=args.seed)
    payload = {
        "target": "Linux aarch64 1 OCPU / 6 GB",
        "workers": 1,
        "records": records,
        "limits": {"L0_peak_RSS_bytes": 1_000_000_000, "L1_peak_RSS_bytes": 3_000_000_000, "overall_memory_bytes": 6_000_000_000},
        "within_budget": all(record["status"] == "success" for record in records) and records[-1]["peak_rss_bytes_process_high_water"] < 3_000_000_000,
        "notice": "ru_maxrss is the process high-water mark; L1 includes the 21/41-cell convergence run.",
        "output_transaction": transaction,
    }
    _write_json(out / "benchmark.json", payload)
    (out / "report.md").write_text("# Target benchmark\n\n```json\n" + json.dumps(payload, indent=2) + "\n```\n", encoding="utf-8")
    _finish_atomic_output(target, out, transaction)
    print(json.dumps(payload, indent=2))
    return 0 if payload["within_budget"] else EXIT_RESOURCE


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "full-cycle":
        from .models.full_cycle import read_parameters, run_acceptance, run_cycle, write_json
        config = read_parameters(args.parameters)
        if args.acceptance:
            result = run_acceptance(config, args.out)
            print(json.dumps({"passed":result["passed"], "relative_differences":result["relative_differences"]}))
            return 0 if result["passed"] else EXIT_SOLVER
        report, fields = run_cycle(config)
        write_json(args.out / "summary.json", report)
        write_json(args.out / "fields.json", fields)
        print(json.dumps({"summary":report["summary"], "conservation_passed":report["conservation_passed"], "elapsed_s":report["elapsed_s"]}))
        return 0 if report["conservation_passed"] else EXIT_SOLVER
    try:
        if args.command == "validate":
            return command_validate(args)
        if args.command == "forward":
            return command_forward(args)
        if args.command == "inverse":
            return command_inverse(args)
        if args.command == "verify":
            return command_verify(args)
        if args.command == "sources":
            return command_sources(args)
        if args.command == "benchmark":
            return command_benchmark(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        validation_error = isinstance(exc, (FileExistsError, ValueError, KeyError, json.JSONDecodeError))
        reason = "validation_error" if validation_error else "internal_io_error"
        print(f"ERROR: reason={reason} category={_exception_category(exc)}", file=sys.stderr)
        return EXIT_VALIDATION if validation_error else EXIT_INTERNAL
    return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
