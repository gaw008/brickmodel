"""中文离线入口：同一未知原料状态下的条件等压供热差。"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys
import time

MAX_RESULT_BYTES = 4 * 1024 * 1024


def json_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: json_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Mapping):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite_output_value")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError("unsupported_output_value")


def save(path: Path, record: object, *, new: bool = True) -> None:
    text = json.dumps(json_value(record), ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    with path.open("x" if new else "w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只读两份保存结果，计算800 K预热O₂/N₂条件下的相对供热差；不求平衡，不计算绝对热耗。")
    parser.add_argument("--source-root", required=True, type=Path, help="公开来源数据所在项目目录")
    parser.add_argument("--baseline-result", required=True, type=Path, help="λ=0的原始TPResult JSON")
    parser.add_argument("--candidate-result", required=True, type=Path, help="所选λ的原始TPResult JSON")
    parser.add_argument("--lambda", dest="lambda_text", required=True, choices=("0", "1/4", "1"))
    parser.add_argument("--output-dir", required=True, type=Path, help="新目录，拒绝覆盖")
    args = parser.parse_args(argv)
    folder = args.output_dir.absolute()
    try:
        folder.mkdir()
    except OSError as exc:
        print(f"无法新建输出目录，未执行比较：{exc}", file=sys.stderr)
        return 2
    started = time.monotonic()
    request = {"source_root": str(args.source_root.resolve()), "baseline_result": str(args.baseline_result.resolve()),
               "candidate_result": str(args.candidate_result.resolve()), "baseline_lambda": 0,
               "candidate_lambda": Fraction(args.lambda_text), "inputs": {}}
    status = {"status": "reading_inputs", "stage": "request_saved", "equilibrium_calls": 0, "EOS_calls": 0}

    def guard() -> None:
        if time.monotonic() - started > 30.:
            raise TimeoutError("offline_boundary_budget_30s")

    try:
        save(folder / "INPUT.json", request)
        save(folder / "STATUS.json", status)
        documents = {}
        for label, path in (("baseline", args.baseline_result), ("candidate", args.candidate_result)):
            guard()
            with path.open("rb") as stream:
                raw = stream.read(MAX_RESULT_BYTES + 1)
            if len(raw) > MAX_RESULT_BYTES:
                raise ValueError("saved_result_exceeds_4MiB:" + label)
            request["inputs"][label] = {"path": str(path.resolve()), "bytes": len(raw),
                                        "sha256": hashlib.sha256(raw).hexdigest()}
            save(folder / "INPUT.json", request, new=False)
            guard()
            documents[label] = json.loads(raw)
        from sludge_sandbox import cedrone_heat
        code_path = Path(cedrone_heat.__file__).resolve()
        code_bytes = code_path.read_bytes()
        request["comparison_module"] = {"path": str(code_path), "bytes": len(code_bytes),
                                        "sha256": hashlib.sha256(code_bytes).hexdigest()}
        save(folder / "INPUT.json", request, new=False)
        guard()
        status.update(status="comparing", stage="offline_comparison")
        save(folder / "STATUS.json", status, new=False)
        result = cedrone_heat.compare_cedrone_heat(documents["baseline"], documents["candidate"],
                    source_root=args.source_root, candidate_lambda=Fraction(args.lambda_text))
        status["stage"] = "comparison_returned"
        save(folder / "RESULT.json", result)
        status.update(status="completed", stage="saved_comparison")
        guard()
    except Exception as exc:
        status.update(status="resource_limit" if isinstance(exc, TimeoutError) else "failed",
                      failure={"error_type": type(exc).__name__, "reason": str(exc)})
    elapsed = time.monotonic() - started
    status["elapsed_seconds"] = elapsed
    if elapsed > 30.:
        status.update(status="resource_limit", resource_reason="offline_budget_at_return")
    try:
        save(folder / "STATUS.json", status, new=False)
        finished = time.monotonic() - started
        if finished > 30.:
            status.update(status="resource_limit", resource_reason="offline_budget_after_save", elapsed_seconds=finished)
            save(folder / "STATUS.json", status, new=False)
    except OSError as exc:
        print(f"状态未完整保存，输出文件可能不完整：{exc}", file=sys.stderr)
        return 2
    if status["status"] == "completed":
        value = float(result["conditional_delta_q_mj_per_kg_reported_sample"])
        print(f"条件相对供热差：{value:.9g} MJ/原1 kg报告样本。绝对热耗与自热条件仍未知。")
    else:
        print(f"比较未通过：{status['status']}；请查看已保存输入身份与STATUS。", file=sys.stderr)
    return 0 if status["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

