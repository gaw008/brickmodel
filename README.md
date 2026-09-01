# Sludge VME MVP

一个可执行的 research-grade 污泥烧结砖 Virtual Materials Engine。它把污泥 composition/mineralogy/thermal properties/particle morphology 当作可设计 fingerprint，在固定 synthetic 页岩/煤矸石基体与固定隧道窑空间边界上运行：

- `L0`：lumped enthalpy + multistep Arrhenius + conserved gas inventories + reduced sintering；
- `L1`：21/41-cell half-thickness finite volume + SciPy BDF（失败时 Radau）+ heat/mass transfer；
- UQ：power-of-two scrambled Sobol policy samples；
- inverse：physically-realizable Sobol design library → robust constraints → L1 refinement → nondominated Pareto/ranked candidates。

> 重要：本仓库所有示例值和默认阈值都是 synthetic policy/公开公式/显式 unknown interval，不是硕治工厂事实、产品标准、排放标准、合格证据或生产建议。不得把输出直接写入 PLC、窑车、机器人或 recipe；仓库不存在这些接口。

## 运行环境

已针对 Python 3.12、Linux aarch64、1 OCPU/6 GB 设计。Runtime 仅使用 NumPy/SciPy；pytest 只用于开发测试。求解器 `workers=1`，不调用网络、云资源、收费 API 或商业数据库。

## 从干净环境安装

推荐已有 `uv` 的机器：

```bash
uv venv --python /usr/bin/python3.12 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
```

若系统没有 `uv`，请从 Astral 官方 release 安装并核对 checksum；不要写入 PEP 668 system site-packages。依赖版本固定在 `pyproject.toml`/`uv.lock`。

验证安装：

```bash
.venv/bin/sludge-vme --help
.venv/bin/python -m pytest -q
```

## CLI

```bash
# schema/units/source coverage
.venv/bin/sludge-vme validate examples/tiny_synthetic.json

# forward JSON + CSV + Markdown artifacts
.venv/bin/sludge-vme forward examples/tiny_synthetic.json --fidelity L0 --out runs/tiny_L0
.venv/bin/sludge-vme forward examples/tiny_synthetic.json --fidelity L1 --out runs/tiny_L1

# optional forward policy-UQ (2^2 samples)
.venv/bin/sludge-vme forward examples/tiny_synthetic.json --fidelity L0 --uq-power 2 --seed 20260831 --out runs/tiny_L0_uq

# constrained inverse + L1 refinement + Pareto
.venv/bin/sludge-vme inverse examples/tiny_synthetic.json --budget tiny --seed 20260831 --out runs/tiny_inverse

# content hash / conservation / bound / Pareto checks
.venv/bin/sludge-vme verify runs/tiny_L0 --strict
.venv/bin/sludge-vme verify runs/tiny_L1 --strict
.venv/bin/sludge-vme verify runs/tiny_inverse --strict

# source/unknown registry and target resource benchmark
.venv/bin/sludge-vme sources
.venv/bin/sludge-vme benchmark examples/tiny_synthetic.json --out runs/benchmark
```

Exit codes：`0` 成功；`2` schema/validation；`3` solver/conservation/inverse；`4` hard coverage（保留）；`5` resource budget；`10` internal I/O。

## Forward artifacts

每个 forward 目录至少含：

- `run_manifest.json`：UTC、CLI、seed、case/source/parameter hashes、Python/NumPy/SciPy、platform、fidelity、git commit；
- `resolved_case.json`, `status.json`, `summary.json`, `conservation.json`, `flags.json`；
- `state_trajectory.json`, `state_trajectory.csv`, `uncertainty.json`, `report.md`。

`conservation.json` 使用 deforming-cell reference-volume extensive inventory ledger。默认 tolerances：mass/element `1e-8`，energy `1e-4`。BDF 的微小 extent overshoot 会显式投影到 `[0,1]`，并记录 `extent_projection_max`；超过 `1e-5` 则运行失败，不会静默吞掉。

## Inverse artifacts

- `all_evaluations.jsonl`：16 个 L0 designs，包括 infeasible/failed reason；
- `pareto.json`, `pareto.csv`：仅含 L1 hard-constraint-pass 且 nondominated points；
- `rank_stability.json`, `feasible_windows.json`, `uncertainty.json`, `report.md`；
- environmental threshold 缺失时始终是 `not_evaluated`，不是 `passed`。

## 科学边界

模型的守恒结构、Fourier/Fick transport、ideal-gas pressure、Arrhenius 形式和 Gibbs minimization criterion 有物理骨架；参数值、pseudo-liquid、SOVS-inspired reduction、open-pore connectivity、pressure/stress/strength/WA/defect closures 不是从第一性原理唯一推出，均带 source kind、validity 和 uncertainty/unknown 标记。

当前 `MinimalGibbsBackend` 可对 pure-phase manufactured cases做 `A n=b, n>=0, min G`，但 forward 的 oxide liquid 仍是明确标记的 `ideal_pseudo` screening closure，coverage 为有限值；缺少完整多元氧化物 liquid/glass CALPHAD 数据库是首要风险。

更多细节：

- `docs/MODEL_ARCHITECTURE.md`
- `docs/FORMULA_CODE_MAP.md`
- `docs/PARAMETER_SOURCES.md`
- `docs/LIMITATIONS_AND_UPGRADE_PATH.md`
- Planner 原始交付（原文保留）：`docs/planner/`

## 安全与人工 gate

任何真实工厂数据导入、真实窑 map、真实 speed/recipe trial、产品/排放合规声明、外部发布、付费服务、PLC/robot/kiln connection 都不在本 MVP 中，且必须另行人工审批、现场验证和 rollback 方案。本程序不会自动执行上述行为。
