"""中文单点入口：Cedrone 报告样本的有限 O2/N2 条件 TP 组成。"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time


def json_value(value: object) -> object:
    """Only small value records; no live provider or arbitrary serialization."""
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: json_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Mapping):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_computed_float": str(value)}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError(f"unsupported_output_value:{type(value).__name__}")


def save(path: Path, value: object, *, new: bool = True) -> None:
    """Serialize first; a subsequent I/O error can leave this file incomplete."""
    text = json.dumps(json_value(value), ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with path.open("x" if new else "w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def load_runtime():
    """Import the installed provider only inside the timed worker."""
    import cantera as ct
    from sludge_sandbox import cedrone_oxygen, tp_equilibrium
    return ct, cedrone_oxygen, tp_equilibrium


def run_worker(source_root: Path, folder: Path, lam: Fraction) -> int:
    """One solve with 30 s boundary guards; use main for external native supervision."""
    started = time.monotonic()
    try:
        folder.mkdir()
    except OSError as exc:
        print(f"无法新建计算目录，未执行求解：{exc}", file=sys.stderr)
        return 2
    request = {"source_root": str(source_root), "lambda": lam, "temperature_k": 800.,
               "pressure_pa": 100000., "solver": "vcs", "seed_variant": "element_basis",
               "element_reads": {}, "basis": "原 1 kg Cedrone Table 4 报告样本，未归一化为完整污泥",
               "qualification": {"material_qualified": False, "training_eligible": False,
                                 "material_uncertainty": "unknown", "graphite_is_measured_char": False}}
    status = {"status": "running", "stage": "inputs_saved", "new_solve_attempts": 0,
              "attempt_count_final": False, "runtime_code_unchanged": None,
              "result_saved": False, "atomic_weights_binding_checked": False,
              "worker_budget_s": 30., "module_budget_s": 10., "in_flight_timeout": "requires parent supervisor"}
    runtime_files = {}

    def guard() -> None:
        if time.monotonic() - started > 30.:
            raise TimeoutError("worker_budget_30s")

    try:
        save(folder / "INPUT.json", request)
        save(folder / "STATUS.json", status)
        guard()
        ct, model, tp = load_runtime()
        request["runtime"] = {"cantera_version": ct.__version__,
                              "cantera_module": getattr(ct, "__file__", None),
                              "calculation_module": getattr(model, "__file__", None),
                              "TP_module": getattr(tp, "__file__", None)}
        save(folder / "INPUT.json", request, new=False)
        guard()
        request["runtime"]["code_identity"] = runtime_files
        for name, loaded_module in (("cedrone_oxygen", model), ("tp_equilibrium", tp)):
            path = Path(loaded_module.__file__).resolve(strict=True)
            raw = path.read_bytes()
            runtime_files[name] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            save(folder / "INPUT.json", request, new=False)
            guard()
        if ct.__version__ != "3.2.0":
            raise ValueError("cantera_version_mismatch")
        status["stage"] = "element_reads"
        save(folder / "STATUS.json", status, new=False)
        weights = {}
        for name in model.ELEMENTS:
            guard()
            element = ct.Element(name)
            reading = {"symbol": element.symbol}
            request["element_reads"][name] = reading
            save(folder / "INPUT.json", request, new=False)
            guard()
            weight = element.weight
            reading["weight_kg_kmol"] = weight
            save(folder / "INPUT.json", request, new=False)
            guard()
            if reading["symbol"] != name or not isinstance(weight, float) or not math.isfinite(weight) or weight <= 0:
                raise ValueError("invalid_element_weight_read")
            weights[name] = weight
        inputs = model.derive_cedrone_oxygen_pool(source_root, lam, weights)
        policy = tp.TPPolicy(solver="vcs", rtol=1e-10, max_steps=1000, maximum_elapsed_s=10.)
        request.update(derivation=inputs.definition(), policy=policy.definition())
        save(folder / "INPUT.json", request, new=False)
        status["stage"] = "about_to_call"
        save(folder / "STATUS.json", status, new=False)
        guard()
        status.update(stage="solve_started", new_solve_attempts=1)
        result = tp.solve_tp(inputs.pool, source_root, policy=policy, seed_variant="element_basis")
        status.update(stage="solve_returned", module_status=result.status)
        save(folder / "RESULT.json", result)
        status.update(stage="returned_unchecked", result_saved=True)
        save(folder / "STATUS.json", status, new=False)
        guard()
        if result.status == "resource_limit":
            raise TimeoutError("module_reported_resource_limit")
        observations = model.check_cedrone_oxygen_result(result, inputs)
        save(folder / "OBSERVABLES.json", observations)
        status.update(status="completed", stage="accepted", atomic_weights_binding_checked=True)
    except Exception as exc:
        status.update(status="resource_limit" if isinstance(exc, TimeoutError) else "failed",
                      failure={"error_type": type(exc).__name__, "reason": str(exc)})
        if isinstance(exc, OSError) and not isinstance(exc, TimeoutError):
            status["io_failed"] = True
    if runtime_files:
        try:
            for identity in runtime_files.values():
                raw = Path(identity["path"]).read_bytes()
                if len(raw) != identity["bytes"] or hashlib.sha256(raw).hexdigest() != identity["sha256"]:
                    raise ValueError("runtime_code_changed:" + identity["path"])
            status["runtime_code_unchanged"] = len(runtime_files) == 2
        except Exception as exc:
            status["runtime_code_unchanged"] = False
            status["runtime_code_check_failure"] = {"error_type": type(exc).__name__, "reason": str(exc)}
            if status["status"] == "completed":
                status["status"] = "failed"
    status["attempt_count_final"] = True
    finished = time.monotonic() - started
    status["elapsed_seconds"] = finished
    if finished > 30.:
        status.update(status="resource_limit", resource_reason="worker_budget_at_return")
    try:
        save(folder / "STATUS.json", status, new=False)
        after_save = time.monotonic() - started
        if after_save > 30.:
            status.update(status="resource_limit", resource_reason="worker_budget_after_save", elapsed_seconds=after_save)
            save(folder / "STATUS.json", status, new=False)
    except OSError as exc:
        print(f"状态未完整保存，输出文件可能不完整：{exc}", file=sys.stderr)
        return 2
    print("条件 TP 组成检查通过；材料适用性仍未知。" if status["status"] == "completed"
          else f"计算未通过：{status['status']}；已保留可写入的输入和返回记录。")
    return 0 if status["status"] == "completed" else (2 if status.get("io_failed") else 1)


def supervisor_path() -> Path:
    """Resolve shipped executable code relative to this example, never source_root."""
    return Path(__file__).resolve().parents[2] / "docs/sandbox/research/research-process-supervisor/supervisor.py"


def load_supervisor():
    path = supervisor_path()
    spec = importlib.util.spec_from_file_location("cedrone_process_supervisor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("supervisor_module_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="论文报告样本＋有限虚拟 O₂/N₂ 的单点 800 K、1 bar 平衡；不代表实际排放或焦炭产率。")
    parser.add_argument("--source-root", required=True, type=Path, help="含公开 data/sandbox/research 数据的项目目录")
    parser.add_argument("--output-dir", required=True, type=Path, help="新结果目录；已存在则拒绝")
    parser.add_argument("--lambda", dest="lambda_text", required=True, choices=("0", "1/4", "1"), help="形式计量供氧比例；一次只计算选中一点")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    source_root, output = args.source_root.resolve(), args.output_dir.absolute()
    lam = Fraction(args.lambda_text)
    if args.worker:
        return run_worker(source_root, output, lam)
    try:
        output.mkdir()
    except OSError as exc:
        print(f"无法新建结果目录，未执行求解：{exc}", file=sys.stderr)
        return 2
    status = {"status": "starting_supervision", "source_root": str(source_root), "lambda": lam,
              "worker_budget_s": 30., "module_budget_s": 10., "supervisor_budget_s": 40.,
              "cleanup_grace_s": 5., "material_qualified": False, "training_eligible": False}
    try:
        save(output / "STATUS.json", status)
        supervisor = load_supervisor()
        script = Path(__file__).resolve()
        command = [sys.executable, "-I", str(script), "--worker", "--source-root", str(source_root),
                   "--output-dir", str(output / "calculation"), "--lambda", args.lambda_text]
        current_inputs = [script, supervisor_path(), Path(sys.executable).resolve()]
        source = source_root / "data/sandbox/research/cedrone2024-element-pool-v1/printed-pool.json"
        if source.is_file():
            current_inputs.append(source)
        receipt = supervisor.run_attempt(output / "supervision", command, cwd=str(output),
                                         input_paths=current_inputs, timeout_s=40., cleanup_grace_s=5.)
        passed = (receipt["status"] == "complete" and receipt["returncode"] == 0
                  and receipt["inputs_unchanged"] is True and receipt["cleanup"]["leader_reaped"] is True)
        status.update(status="completed" if passed else "failed", supervision_status=receipt["status"],
                      worker_returncode=receipt["returncode"])
        save(output / "STATUS.json", status, new=False)
    except Exception as exc:
        status.update(status="entry_failed", failure={"error_type": type(exc).__name__, "reason": str(exc)})
        try:
            save(output / "STATUS.json", status, new=False)
        except OSError as error:
            print(f"入口状态未完整保存，输出文件可能不完整：{error}", file=sys.stderr)
            return 2
    print(f"结果：{output}；" + ("条件组成检查通过，材料资格仍为 false。" if status["status"] == "completed"
                             else "计算未完成，请查看 STATUS 与监督日志。"))
    return 0 if status["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
