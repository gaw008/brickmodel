# 污泥烧结砖：第一性原理研究与反向原料设计

本仓库从 Hermes 的 `research/material-dynamics-v2b2` 分支导入，保留完整的 10 个原始提交；导入时的模型提交为 `3b501c5`。后续实现与验收以当前分支及下列进度记录为准。

**目前没有砖厂可用的污泥成分窗口，也没有完成完整 virtual world model。所有模型结果只用于研究。**

当前按 [完整 Goal 合同](docs/GOAL_BRICK_PHYSICS_SANDBOX.md) 构建独立的 `sludge_sandbox` 物理沙盒。已实现来源/材料账目、热化学、水物性、守恒输运与反应、规定变形储能、耗尽积分及独立账本检查；[原生冷却能量接口](docs/sandbox/research/cooling-energy-host-v1/REPORT.md)通过限定制造半板验证。真实材料查询包括[原污泥95°C离散解吸物性](docs/sandbox/research/arlabosse95/README.md)、低温干基比热和同来源纯方解石热化学。完整原污泥材料、湿坯至冷却耦合及三机制公开实验验证仍未完成。

[CLI/Python入口](docs/sandbox/CLI.md)支持限定湿态验证案例、保存及重放；[保存来源运行视图](docs/sandbox/research/source-view-v1/IMPLEMENTATION.md)提供`inspect`、`export`及`ui --view-source-run`，可按原观测与空间单元追查来源。当前资格、检查和应用边界见 [Goal进度](docs/sandbox/GOAL_STATUS.md) 与 [验收矩阵](docs/sandbox/ACCEPTANCE_MATRIX.md)。下文`sludge-vme`仍属于早期synthetic原型，不能作为新沙盒全流程入口。

新增[单胞水分平衡示例](docs/sandbox/research/arlabosse-equilibrium-flash-v1/REPORT.md#本地运行入口)：在给定总水、载气、体积和完整内能下，计算低含水区液汽分配及温度，并保存逐次物性与来源记录。已完成实际命令行试验；瞬时平衡是明确的建模假设，材料适用性及达到平衡的时间仍未验证。

[两格排湿命令行示例](docs/sandbox/CLI.md#两格平衡排湿示例)已连接内部传热、迁水、局部相平衡及外排蒸气，提供固定1秒的1/2/4步运行。三档实际计算及新命令行入口均完成；当前结果用于限定短段研究。

[Cedrone 2024 原污泥 TG/DSC 数据](data/sandbox/research/cedrone2024-joint-thermal-v1/README.md)提供有许可的原图、12 个有限锚点及实际复现脚本。11 个点可读、1 个保留未知；读图包围与实验误差分开记录，含水吸热峰不直接作为化学反应焓。

[高温CHONS平衡模块](docs/sandbox/research/tp-equilibrium-v1/REPORT.md)已通过四个虚拟池案例，并实际接入Cedrone论文的条件元素池。采用可追查的NASA7气体/石墨物性和显式VCS求解，保留原Gibbs算法的元素守恒失败；结果限于800–1200 K、1 bar的终态组成，灰分矿物、动力学及完整烧成热耗仍未闭合。

[论文样本有限供氧入口](docs/sandbox/CLI.md#论文样本的有限供氧单点)可直接选择`λ=0、1/4、1`并运行一个条件组成点，保存本次原子量、全部产物、守恒检查及来源。真实入口和同条件结果比较已完成；[三点报告](docs/sandbox/research/finite-oxygen-equilibrium-v1/REPORT.md)中的石墨变化不能作为真实砖坯燃尽证明。

| 模块 | 内容 | 状态 |
| --- | --- | --- |
| [公开材料研究](experiments/material_design_v2/artifacts/DIRECTION_REPORT.md) | DTU 污泥焚烧灰数据重算、基料依赖、吸水与收缩折衷 | 独立审核通过，仅 Stage1 研究 |
| [B1 反应—输运](experiments/material_dynamics_v2b1/README.md) | 一维等温、固定几何、有限氧库存与局部残碳 | 独立审核通过，仅冻结诊断范围 |
| [B2 给定温度程序](experiments/material_dynamics_v2b2/README.md) | prescribed-temperature 扩展 | 历史审计失败已在 `0634e80` 修复并完成[冻结范围复验](docs/sandbox/research/b2-bound-0634e80/summary.json)；不代表湿砖全周期验证 |
| [早期 VME](docs/MODEL_ARCHITECTURE.md) | 正向/反向求解与 synthetic 筛选框架 | 受限研究原型；不能继承 B1 的审核结论 |

后续更新每 15 分钟由 Codex 自动同步：[同步范围、分支位置与运行条件](docs/research-status/GITHUB_SYNC.md)。

完整审核、失败原始数据、上传核验与复跑方法见 [研究状态说明](docs/research-status/README.md)。早期文档和历史产物中的 pending / PASS 均属于各自提交与范围，应结合独立审核阅读。

---

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

正常 synthetic L0/L1 的 `provenance.json.forward_semantic_replay` 固定 resolved-case hash、fidelity、parameter-overrides digest、parameter/source-pack digest、SciPy solver/version/configuration digest 和比较规则。Forward seed 仍记录在 manifest 与 descriptor 中并检查缺失或单边不一致，但 baseline forward ODE 不消费 seed，所以它明确属于 self-declared integrity-only provenance；没有外部真实性锚点时，协同改写两个 seed 副本不可由 deterministic replay 识别。`verify --strict` 在当前 fresh CLI process 内从语义输入重新运行完整 forward ODE/FVM solver，而不是把 artifact 中的温度、extent 或 gas state 当作真值。

求解器数值容差与 semantic acceptance tolerance 是两个独立 contract。受信 verifier 的版本化 solver policy 只支持 finite numeric `solver_rtol ∈ [1e-10, 1e-5]`、`solver_atol ∈ [1e-13, 1e-7]`；NaN、Inf、非正值、字符串或超范围值会在 replay 前 fail closed。Artifact 可在该范围内决定重跑求解器的数值配置，但不能放宽比较门槛。Semantic comparison 使用 verifier-owned 固定 hard caps `rtol=5e-6`、`atol=5e-8`，逐点比较 time/x grid、temperature、raw/projected reaction extents、species mass/molar/current-pore inventories、released gas、volume ratio/Jacobian、porosity和 cumulative heat states；mapping keys 比较前按字典序 canonicalize，sequence order 保留。10 K、1% inventory 等 material mutation 远超门槛，约 `3e-8 K` 的机器舍入级微差被接受。

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
