# Sludge VME MVP

一个可执行的 research-grade 污泥烧结砖 Virtual Materials Engine。它把污泥 composition/mineralogy/thermal properties/particle morphology 当作可设计 fingerprint，在固定 synthetic 页岩/煤矸石基体与固定隧道窑空间边界上运行：

- `L0`：lumped reduced-effective enthalpy ODE + finite-O2-capped multistep Arrhenius + conserved gas inventories + reduced sintering；
- `L1`：21/41-cell half-thickness finite volume + SciPy BDF（失败时 Radau）+ current-pore **molar** concentration Fick transport；
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

# 非空目录默认拒绝；只有明确要求时才保留旧目录为 rollback 后原子替换
.venv/bin/sludge-vme forward examples/tiny_synthetic.json --fidelity L0 --out runs/tiny_L0 --overwrite

# content hash / conservation / bound / Pareto checks
.venv/bin/sludge-vme verify runs/tiny_L0 --strict
.venv/bin/sludge-vme verify runs/tiny_L1 --strict
.venv/bin/sludge-vme verify runs/tiny_inverse --strict

# source/unknown registry and target resource benchmark
.venv/bin/sludge-vme sources
.venv/bin/sludge-vme benchmark examples/tiny_synthetic.json --out runs/benchmark
```

Exit codes：`0` 成功；`2` schema/validation（含 malformed top-level/kiln/profile/inverse container，无 traceback）；`3` solver/conservation/inverse；`4` hard coverage（保留）；`5` resource budget；`10` internal I/O。L0/L1/inverse/benchmark 的 runtime solver exception 都会原子写入 structured-failure artifact；它只含固定 stage/reason 和 allowlisted exception category，绝不序列化 exception message/repr/args/traceback/locals、真实可控 class name、resolved user input、CLI args 或输出路径。若目标目录非空且未给 `--overwrite`，原目录保持不动，失败证据写入隐藏 sibling。

## Forward artifacts

每个 forward 目录至少含：

- `run_manifest.json`：UTC、CLI、seed、case/source/parameter hashes、Python/NumPy/SciPy、platform、fidelity、git commit、solver statistics，以及每个 payload artifact 的 SHA-256/size；manifest 自身因自引用不可能自哈希，显式记为 `not_applicable_self_reference`；
- `resolved_case.json`, `status.json`, `summary.json`, `conservation.json`, `provenance.json`, `flags.json`；
- `state_trajectory.json`, `state_trajectory.csv`, `uncertainty.json`, `report.md`。

`state_trajectory.json` schema 2.0 同时保留 projected/raw reaction extents、species mass 与 molar reference inventories、released-gas extensive states、current-pore `mol/m3`、`phi_open/J`、cumulative boundary/reaction heat 和 state counts；每个 gas species 都显式携带 `kg/mol` 与 mass↔moles↔current-pore conversion。内嵌 semantic contract 3.0 对每个 strict trajectory field 声明 exact species/unit/basis/conversion、resolved shape、finite requirement 与 inclusive/exclusive range；没有未声明的 strict derived field。`conservation.json` 使用 deforming-cell reference-volume extensive inventory ledger，并序列化 initial/final mass、bulk volume、element inventories、O2 与 reduced-enthalpy ledger。默认 tolerances：mass/element `1e-8`，`reduced_effective_enthalpy_ode` `1e-4`。后者只验证 reduced ODE 的数值恒等式，不再冒充含 variable mass/escaped-gas sensible enthalpy 的完整 energy conservation，也不作为完整物理 hard-pass。BDF 的微小 extent overshoot 会显式投影到 `[0,1]`，并记录 `extent_projection_max`；超过 `1e-5` 则运行失败。

正常 synthetic L0/L1 的 `provenance.json.forward_semantic_replay` 固定 resolved-case hash、fidelity、seed、parameter-overrides digest、parameter/source-pack digest、SciPy solver/version/configuration digest 和比较规则。`verify --strict` 在当前 fresh CLI process 内从这些输入重新运行完整 forward ODE/FVM solver，而不是把 artifact 中的温度、extent 或 gas state 当作真值。它先用 `5 × configured solve_ivp rtol/atol`（默认 L0 `rtol=5e-6, atol=5e-8`；L1 `rtol=5e-6, atol=5e-9`）逐点比较 time/x grid、temperature、raw/projected reaction extents、species mass/molar/current-pore inventories、released gas、volume ratio/Jacobian、porosity、cumulative heat states；mapping keys 比较前按字典序 canonicalize，sequence order 保留。10 K 等 material mutation 远超容差，机器舍入级微差被接受。

只有 primary replay 成功后，strict 才把 replay result 作为独立期望值，比较 pressure/liquid/sintering/stress 等 derived trajectories、全部 summary/extrema/conservation、status 和 CSV projection；原有 algebraic cross-artifact recomputation 是额外检查，不能替代 ODE replay。正常 L0/L1 的 replay failure、缺失 provenance 或 case/fidelity/parameter/source/solver digest mismatch 均返回非零。显式 custom/manufactured fixture 可由 writer 标为 `forward_semantic_replay=not_evaluated`；此时 manifest 把完整 ODE trajectory 列为 integrity-only，strict 输出 warning 并返回非零，绝不声称完整 trajectory semantic verified。

## Inverse artifacts

- `all_evaluations.jsonl`：16 个 L0 designs 加全部 L1 refined records；每条保留逐 policy-sample 固定 status code、sample ID、sampler seed/algorithm、parameters、forward case/parameter-pack provenance 和 primary-state semantic SHA-256（finite floats 先量化到 8 位有效数字，以容忍跨进程 solver roundoff，但 material change 会改变 hash；不保留任意 solver message），以及 quality/risk/conservation verification inputs、failure rate、constraint slack 与 active constraints；Pareto 点必须可按 `(design_id,fidelity)` 精确回溯；
- `pareto.json`, `pareto.csv`：仅含 L1 hard-constraint-pass 且 nondominated points；
- `rank_stability.json`, `feasible_windows.json`, `uncertainty.json`, `report.md`；少于 3 个配对点时 rank 为 `insufficient_points`，两点范围只称 `observed_candidate_envelope`，不称连续 feasible window；
- environmental threshold 缺失时始终是 `not_evaluated`，不是 `passed`。

Inverse `verify --strict` 会从 `resolved_case + declared budget + seed + sampler contract` 重新运行确定性 Sobol design、policy samples、全部 L0、L1 shortlist/grid check 和 Pareto pipeline。它精确核对 ordered design IDs/decisions/record counts、decision bounds、speed→residence time、policy IDs/seeds/parameters/forward-state hashes，并从 replay 重算 feasibility、quantiles、constraints/slacks/objectives、shortlist、counts、rank、observed envelope、CSV 与 nondominance。只有 `solver_statistics.wall_time_s` 和 manifest runtime/platform/transaction provenance 被明确列为 integrity-only；tiny strict replay 在单核上有与一次 inverse 求解同阶的 wall time。

## Hash、semantic replay 与 authenticity

- Artifact SHA-256/size 只能证明当前 manifest 与当前 payload 字节一致；攻击者同步重写 payload 与 manifest hash 时，它不提供语义保护。
- Trusted verifier 中的 forward deterministic full-ODE replay、replay-derived artifact comparison 与 inverse deterministic full-solver replay 提供本仓库声明的 semantic checks；endpoint reduced-enthalpy identity 或 artifact 内部自洽不等于 forward ODE replay，被列为 integrity-only 的字段不在 hard semantic claim 中。
- 本仓库没有签名、MAC、透明日志、remote attestation 或可信时间戳，因此不提供 cryptographic authenticity。能同时替换 verifier 程序和全部 primary states 的攻击者不在边界内。

## 科学边界

模型的守恒结构、Fourier/Fick transport、ideal-gas pressure、Arrhenius 形式和 Gibbs minimization criterion 有物理骨架；参数值、pseudo-liquid、SOVS-inspired reduction、open-pore connectivity、pressure/stress/strength/WA/defect closures 不是从第一性原理唯一推出，均带 source kind、validity 和 uncertainty/unknown 标记。

当前 `MinimalGibbsBackend` 可对 pure-phase manufactured cases做 `A n=b, n>=0, min G`。Forward 会真实调用该 backend 并记录 source hash/status，但 bundled source 不含可覆盖当前 composition 的 Gibbs phase data，因此 thermo 始终为 `not_evaluated_*`，不能 hard-pass。数值 liquid 仅是对 oxide network-modifier 敏感的 unresolved screening proxy；缺少完整多元氧化物 liquid/glass CALPHAD 数据库是首要风险。

Inverse 的 12 个坐标全部进入真实 closure：sludge dry fraction、organic/calcite/amorphous partition、PSD、morphology、wet-feed moisture、speed，以及 sludge true density/cp/k/effective gas diffusivity。逐变量 metamorphic tests 保证它们改变可解释中间量或输出；未耦合变量不得进入 Pareto/envelope。

更多细节：

- `docs/MODEL_ARCHITECTURE.md`
- `docs/FORMULA_CODE_MAP.md`
- `docs/PARAMETER_SOURCES.md`
- `docs/LIMITATIONS_AND_UPGRADE_PATH.md`
- `docs/SAFETY_REWORK_B1_B8.md`
- `docs/VERIFIER_THREAT_MODEL.md`
- Planner 原始交付（原文保留）：`docs/planner/`

## 安全与人工 gate

任何真实工厂数据导入、真实窑 map、真实 speed/recipe trial、产品/排放合规声明、外部发布、付费服务、PLC/robot/kiln connection 都不在本 MVP 中，且必须另行人工审批、现场验证和 rollback 方案。本程序不会自动执行上述行为。
