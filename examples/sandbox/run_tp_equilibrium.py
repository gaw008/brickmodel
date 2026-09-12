"""中文示例：指定元素池的受限 TP 平衡；不计算真实污泥产气率。"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
import sys


def json_value(value: object) -> object:
    """Only the solver's small value records; no provider objects or imports."""
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    if isinstance(value, Mapping):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_computed_float": str(value)}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported_output_value:{type(value).__name__}")


def amount(text: str) -> Fraction:
    try:
        value = Fraction(text)
        if value < 0 or not math.isfinite(float(value)):
            raise ValueError("finite nonnegative amount required")
        return value
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        raise argparse.ArgumentTypeError("元素量必须是有限非负 mol 原子数") from exc


def temperature(text: str) -> float:
    try:
        value = float(text)
        if not 800 <= value <= 1200:
            raise ValueError("outside 800–1200 K")
        return value
    except ValueError as exc:
        raise argparse.ArgumentTypeError("温度必须在 800–1200 K") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="18 种理想气体和纯石墨的 1 bar TP 平衡；研究示例，材料适用性未知。")
    parser.add_argument("--source-root", required=True, type=Path, help="含 data/sandbox/research/tp-equilibrium-v1 的项目目录")
    parser.add_argument("--output", required=True, type=Path, help="新建 JSON，拒绝覆盖已有文件")
    parser.add_argument("--temperature-k", required=True, type=temperature)
    for element in ("carbon", "hydrogen", "oxygen", "nitrogen", "sulfur"):
        parser.add_argument(f"--{element}-mol", required=True, type=amount, help="mol 原子数；未知量不能当成零")
    parser.add_argument("--basis-id", required=True, help="此虚拟元素池的明确尺度说明；不能冒称 1 kg 真实污泥")
    parser.add_argument("--seed", choices=("element_basis", "methane_shift"), default="element_basis")
    parser.add_argument("--solver", choices=("vcs", "gibbs"), default="vcs", help="明确数值算法；不自动回退")
    args = parser.parse_args(argv)
    elements = tuple(getattr(args, f"{e}_mol") for e in ("carbon", "hydrogen", "oxygen", "nitrogen", "sulfur"))
    if not any(elements) or not args.basis_id.strip():
        parser.error("元素池不能全零，且必须明确尺度说明")
    record = {"status": "inputs_saved", "request": {"temperature_k": args.temperature_k,
              "pressure_pa": 100000., "element_order": ("C", "H", "O", "N", "S"),
              "element_mol": elements, "basis_id": args.basis_id, "seed_variant": args.seed, "solver": args.solver,
              "classification": "virtual_design_choice", "source_root": str(args.source_root)},
              "qualification": {"material_qualified": False, "training_eligible": False,
                  "scope": "固定 T/P 的闭合元素池；候选相及输入库存是虚拟设计，省略相和材料误差未知",
                  "not_inferred": "真实热解速率、初态能量、升温热耗及开放系统累计排气"}}
    try:
        output = args.output.open("x", encoding="utf-8")
    except OSError as exc:
        print(f"无法新建结果文件，未执行求解：{exc}", file=sys.stderr)
        return 2
    with output:
        def save() -> None:
            # Serialize before writing; an I/O failure can still leave a partial file.
            text = json.dumps(json_value(record), ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            output.seek(0)
            output.write(text)
            output.truncate()
            output.flush()
        try:
            save()
            from sludge_sandbox.tp_equilibrium import TPPool, TPPolicy, solve_tp
            pool = TPPool(args.temperature_k, 100000., elements, args.basis_id,
                          "virtual_design_choice", ("user_declared:virtual_CHONS_pool",))
            result = solve_tp(pool, args.source_root, policy=TPPolicy(solver=args.solver), seed_variant=args.seed)
            record.update(status=result.status, result=result)
            save()
            print("限定 TP 平衡检查通过；材料适用性仍未知。" if result.status == "completed"
                  else f"计算未通过：{result.status} / {result.reason}。已保存返回数据。")
            return 0 if result.status == "completed" else 1
        except OSError as exc:
            print(f"结果未完整保存，输出文件可能不完整：{exc}", file=sys.stderr)
            return 2
        except Exception as exc:
            record.update(status="entry_failed", failure={"error_type": type(exc).__name__, "reason": str(exc)})
            try:
                save()
            except OSError as save_error:
                print(f"结果未完整保存，输出文件可能不完整：{save_error}", file=sys.stderr)
                return 2
            print(f"入口失败，已保存输入与错误：{exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
