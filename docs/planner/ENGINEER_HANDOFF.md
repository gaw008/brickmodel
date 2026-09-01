# Sludge Brick VME MVP — Engineer 实现任务说明

> 实现依据：`sludge_brick_first_principles_report.md` 与 `model_spec.json`。两者冲突时先提 issue，不自行改变物理定义。  
> 约束：仅实现本地 research tool；不接 PLC/窑车/生产系统，不创建 OCI 资源，不用收费 API/商业数据库。

## 1. 交付结论

Engineer 需交付一个可在 Linux aarch64、1 OCPU/6 GB 上运行的 Python package + CLI，包含：

1. canonical feedstock/schema validation；
2. 元素/质量/能量守恒基础设施；
3. L0 lumped forward model；
4. L1 half-thickness 1D finite-volume forward model；
5. parameter uncertainty propagation；
6. constrained inverse search 与 Pareto artifacts；
7. tiny synthetic end-to-end case 的真实执行输出、测试和 resource benchmark。

MVP 启动不得依赖本厂试验数据。公开参数缺失时应使用 spec 中的 interval/unknown flag，而非阻塞整个模型或发明单点。

## 2. Scope 与 non-goals

### In scope

- Python 3.12；runtime hard dependencies 仅 NumPy/SciPy（尽量用 stdlib JSON/argparse/dataclasses）。
- 所有内部计算 SI；输入允许 `degC`，进入 solver 前统一转 K。
- deterministic seed、source/config/software hash、structured failure。
- L0/L1、QMC、inverse、JSON/CSV artifacts。
- minimal thermochemical adapter interface；MVP 可用受 provenance 管理的 minimal pure-species tables/polynomials 和 ideal pseudo-liquid。

### Non-goals

- 2D/3D、OpenFOAM/DOLFINx/phase-field 实现。
- 在线抓取数据、任何 paid API。
- 真实产品标准合格判断、排放合规判断。
- GUI、云服务、数据库 server、分布式并行。
- 生产部署、实时控制、自动 recipe 下发。

## 3. Architecture decisions（已定，不下放重复决策）

1. Package 名：`sludge_vme`；CLI 名：`sludge-vme`。
2. 配置格式：JSON；不得引入 YAML parser。
3. Core runtime：NumPy/SciPy + Python stdlib；pytest 仅 dev。
4. L1：cell-centered finite volume + method of lines + `scipy.integrate.solve_ivp(method="BDF")`；BDF 失败才允许配置 fallback `Radau`。
5. Equilibrium：统一 `EquilibriumBackend` protocol；默认 `MinimalGibbsBackend`，Cantera/Thermochimica/pycalphad 只做 optional adapters，不进入 MVP acceptance 的 hard dependency。
6. Inverse：Sobol library + nondominated filter + ε-constraint/scalarized `differential_evolution`；`workers=1`。不引入 pymoo/NSGA-II 包。
7. Result 不返回裸数组字典；使用 dataclasses，序列化时带 units、status、flags、provenance。
8. 所有 solver failure 返回 `RunStatus`；optimizer 对 failed design 做显式 infeasible，不把 NaN 转成任意 penalty 后静默继续。
9. `model_spec.json` 是 normative design spec，不直接当 run case；实现时从其中复制/生成 `examples/tiny_synthetic.json` 和 parameter packs，并保留 `spec_version`。
10. 环境/质量 threshold 缺失时状态为 `not_evaluated`，绝不能默认通过。

## 4. Proposed repository layout

```text
pyproject.toml
README.md
src/sludge_vme/
  __init__.py
  cli.py
  types.py
  config.py
  units.py
  provenance.py
  validation.py
  chemistry/
    __init__.py
    formula.py
    stoichiometry.py
    reactions.py
  thermo/
    __init__.py
    properties.py
    equilibrium.py
    minimal_backend.py
    cache.py
  physics/
    __init__.py
    packing.py
    transport.py
    kinetics.py
    energy.py
    sintering.py
    porosity.py
    mechanics_proxy.py
    performance_proxy.py
  models/
    __init__.py
    common.py
    l0.py
    l1.py
    fvm.py
    postprocess.py
  uq/
    __init__.py
    sampling.py
    propagation.py
    sensitivity.py
  inverse/
    __init__.py
    transforms.py
    constraints.py
    pareto.py
    search.py
  io/
    __init__.py
    artifacts.py
    manifest.py
data/
  minimal_species.json
  minimal_phases.json
  synthetic_matrix_v1.json
  parameter_pack_synthetic_v1.json
  sources.json
examples/
  tiny_synthetic.json
tests/
  unit/
  physics/
  models/
  thermo/
  uq/
  inverse/
  integration/
  regression/
scripts/
  benchmark_target.py
```

若仓库已有 layout，保持现有约定，但上述 module boundaries 和 public APIs 不变。

## 5. Public APIs

### 5.1 Configuration

```python
load_case(path: Path) -> CaseConfig
validate_case(case: CaseConfig) -> ValidationReport
normalize_feedstocks(case: CaseConfig) -> NormalizedFeed
```

`ValidationReport` 至少包括 `errors`, `warnings`, `normalized_simplex_residuals`, `element_double_count_checks`, `source_coverage`。

### 5.2 Chemistry / thermo

```python
parse_formula(formula: Mapping[str, float]) -> ElementVector
build_element_matrix(species: Sequence[Species]) -> ndarray
check_element_balance(reactions, A, tol) -> BalanceReport

class EquilibriumBackend(Protocol):
    def equilibrate(self, T_K, P_Pa, element_inventory, candidate_phases) -> EquilibriumResult: ...

evaluate_species_properties(T_K, species_pack) -> ThermoProperties
```

`EquilibriumResult` 必须有 phase amounts、chemical potentials（若 backend 支持）、Gibbs before/after、element residual、coverage score、missing species/phases 和 status。

### 5.3 Forward

```python
simulate(case: CaseConfig, fidelity: Literal["L0", "L1"],
         parameters: ParameterSample | None = None) -> ForwardResult
```

`ForwardResult`：

- coordinates/time；
- fields；
- released gas；
- phase/liquid/porosity/shrinkage；
- pressure/stress/risk/performance proxies；
- element/mass/energy residuals；
- coverage、warnings、status、provenance；
- solver statistics：nfev/njev/nlu/retries/wall time/peak RSS（RSS 可只在 CLI benchmark 记录）。

### 5.4 UQ / inverse

```python
sample_parameters(pack, n_power, seed, scramble=True) -> list[ParameterSample]
propagate(case, fidelity, samples) -> UncertaintyResult

run_inverse(case, budget: InverseBudget) -> InverseResult
nondominated_mask(objectives, feasible) -> ndarray[bool]
```

`InverseResult` 必须保留全部 evaluated designs（含失败原因）、feasible set、final Pareto set、rank stability、active constraints 和 L0/L1 disagreement。

## 6. CLI contract

```text
sludge-vme validate CASE.json [--json]
sludge-vme forward CASE.json --fidelity {L0,L1} --out DIR [--uq-power M] [--seed N]
sludge-vme inverse CASE.json --budget {tiny,default} --out DIR [--seed N]
sludge-vme verify RUN_DIR [--strict]
sludge-vme sources [--json]
sludge-vme benchmark CASE.json --out DIR
```

Exit codes：

- `0` success；
- `2` schema/validation failure；
- `3` solver/conservation failure；
- `4` missing hard threshold/database coverage failure；
- `5` resource budget exceeded；
- `10` internal error。

CLI 必须把 human-readable summary 写 stdout，把完整 structured result 写 artifacts。不得把 warning 当 success 隐藏。

## 7. Artifact contract

每个 run directory：

```text
run_manifest.json
resolved_case.json
status.json
summary.json
conservation.json
flags.json
state_trajectory.json       # L0/L1；L1 可压缩或只保留配置采样时刻
uncertainty.json            # 有 UQ 时
pareto.json                 # inverse
pareto.csv                  # inverse
all_evaluations.jsonl       # inverse，包括 failed/infeasible
rank_stability.json         # inverse
```

`run_manifest.json` 必须有：UTC timestamp、CLI args、seed、spec version、source pack hash、parameter pack hash、resolved case hash、Python/NumPy/SciPy 版本、platform、fidelity、budget、git commit（若有）。不存 token、credentials、完整本厂敏感连接信息。

## 8. Task breakdown 与 dependencies

### Task 1 — Bootstrap 与 schema（无物理求解）

Files：`pyproject.toml`, `types.py`, `config.py`, `units.py`, `validation.py`, examples/data。

步骤：

1. 写 failing tests：dry basis、simplex、PSD order、sphericity/aspect、temperature conversion、double-count rejection。
2. 实现 dataclasses/validators。
3. 从 `model_spec.json.synthetic_example` 生成 `examples/tiny_synthetic.json`，不要手工产生不同版本。
4. 实现 `validate` CLI 与 exit code。

Acceptance：合法 example exit 0；逐项 mutation（负 fraction、sum 错、PSD 乱序、缺 basis、重复元素）exit 2 且给精确 JSON path。

Dependency：无。后续全部依赖 Task 1。

### Task 2 — Stoichiometry 与 provenance

Files：`chemistry/*`, `provenance.py`, `data/sources.json`。

步骤：

1. 测试 formula→element vector、reaction balance、phase+oxide+organic inventory。
2. 构建固定 element ordering；任何 backend 只能使用该 ordering。
3. 每个 parameter 记录 `source_kind`, URL/DOI, validity, unit, transform, uncertainty。
4. 未知 active reaction enthalpy 不允许以 0 静默运行；返回 flag 或禁用该 reaction。

Acceptance：synthetic feed element inventory 非负；所有启用 reactions CHONS/ash elements 残差在 tolerance 内；source pack 可 hash。

Dependency：Task 1。

### Task 3 — Minimal thermochemistry/equilibrium backend

Files：`thermo/*`, `data/minimal_species.json`, `data/minimal_phases.json`。

步骤：

1. 为纯 species 实现 table/polynomial interpolation interface，严格检查 temperature validity。
2. 实现 constrained Gibbs minimization；变量非负、`A n=b`。可用 SciPy constrained optimizer；失败必须 structured。
3. oxide liquid MVP 只允许显式标为 `ideal_pseudo`; database 缺相降低 coverage。
4. 实现 temperature/composition quantized cache，key 含 source-pack hash。
5. 写 backend contract tests；以后 optional backend 不影响 core。

Acceptance：manufactured two/three-species cases满足 `A n=b`、`G_final≤G_initial+tolerance`、`n≥0`；删掉候选相后 coverage 明显下降并产生 flag。

Dependency：Tasks 1–2。

### Task 4 — Properties、packing、transport closures

Files：`physics/packing.py`, `transport.py`, `energy.py`, properties。

步骤：

1. 实现 PSD moments、`d32`、packing closure interface；Yu–Standish 类算法如无完整参数，先实现 deterministic bounded surrogate，命名不得写成 exact Yu–Standish。
2. 实现 Kozeny–Carman shape、effective diffusivity、ideal-gas pressure、Maxwell–Eucken + second closure ensemble。
3. 所有 closure 返回 value + validity + parameter/source metadata。
4. 实现 limit tests：`φ→0/1` 前截断/失败策略、positive property、units。

Acceptance：permeability dimension `m²`；无 NaN/negative properties；closure ensemble 差异进入 uncertainty，而非被平均后丢弃。

Dependency：Tasks 1–2。

### Task 5 — Kinetics、sintering、porosity、proxies

Files：`kinetics.py`, `sintering.py`, `porosity.py`, `mechanics_proxy.py`, `performance_proxy.py`。

步骤：

1. 实现 generic Arrhenius reaction interface 和 atmosphere multiplier。
2. 实现 multistep organic pseudo-components、dehydroxylation、carbonate decomposition。
3. 实现 equilibrium-target relaxation，与 element projection 一体化。
4. 实现 reduced SOVS-inspired volumetric strain；禁止同时独立扣减 pore volume。
5. cell extensive phase moles / current cell volume → current concentrations → solid volume fraction → total porosity → open-porosity closure；不得把 reference concentration 当作 current concentration。
6. 实现 stress/defect/performance proxies，所有 proxy 带 `proxy=true` 和 resolution status。

Acceptance：isothermal first-order analytic case；关闭 reaction 时 gas source=0；volume/porosity identity 成立；`0≤alpha,phi,f_liq≤1`；缺 strength 参数时 `unresolved` 而非 pass。

Dependency：Tasks 2–4。

### Task 6 — L0 forward

Files：`models/common.py`, `models/l0.py`, `postprocess.py`。

步骤：

1. `speed_ratio` 映射 fixed spatial kiln map，不提供任意 temperature decision API。
2. lumped enthalpy/species/extent ODE + equilibrium target + porosity/sintering。
3. 输出全部 required summaries 与 conservation ledger。
4. 做 synthetic dry run 及 analytic limit tests。

Acceptance：no-reaction adiabatic case守恒；Newton cooling/first-order reaction analytic error在 test tolerance；tiny L0 真实运行成功并产生 artifacts。

Dependency：Tasks 1–5。

### Task 7 — L1 FVM + stiff solver

Files：`models/fvm.py`, `models/l1.py`。

步骤：

1. cell-centered half-slab，center symmetry、surface convection/radiation/mass-transfer/pressure BC。
2. method-of-lines state layout 与 sparse Jacobian pattern；守恒主存储使用每个 deforming cell 的 extensive species moles/enthalpy，current concentrations 仅作为 derived values。
3. 每步 property/reaction/pressure/thermo/sintering Picard coupling。
4. positivity、element projection、step retry、structured failure。
5. 21/41 cells convergence runner。

Acceptance：slab conduction/Fick diffusion manufactured solution；low-gradient L0/L1 spatial mean agreement；high-gradient case产生 fidelity warning；tiny L1 完成且 conservation/grid checks 通过。

Dependency：Tasks 3–6。

### Task 8 — UQ

Files：`uq/*`。

步骤：

1. `qmc.Sobol.random_base2`，sample count 必须 `2^m`；参数 transforms 与 correlation groups。
2. interval 与 probability-like policy distribution 在 schema/report 中分开。
3. propagate 生成 min/q05/q50/q95/max/coverage；model discrepancy 单列。
4. sensitivity 只做 Spearman/standardized effects；常数输入返回 unresolved。

Acceptance：固定 seed bitwise/reasonably deterministic；每组 sample 在 bounds 内；相关 `(logA,E)` 不被拆散；quantile ordering 正确；失败样本计入 failure rate。

Dependency：Tasks 6–7。

### Task 9 — Inverse / Pareto

Files：`inverse/*`。

步骤：

1. decision transform：simplex、ordered PSD、bounded morphology/preprocess/speed。
2. hard constraint evaluator；missing threshold=not_evaluated。
3. Sobol→L0→nondominated→DE expansion→diverse shortlist→L1→final Pareto。
4. objective normalization只用 declared scales；保留 raw objectives。
5. rank instability 与 L0/L1 disagreement。

Acceptance：final Pareto 中无 strict domination；每点 hard constraints pass；infeasible/failed 不混入 Pareto；同 seed 可复现；tiny budget 返回至少 structured result，即使 feasible set 为空也解释原因。

Dependency：Tasks 6–8。

### Task 10 — CLI、verification、benchmark、docs

Files：`cli.py`, `io/*`, `scripts/benchmark_target.py`, README, integration/regression tests。

步骤：

1. 完成 CLI/exit code/artifact contracts。
2. `verify RUN_DIR` 重算 hash、schema、conservation、bounds、Pareto。
3. 在目标 aarch64 实际运行五条 synthetic commands。
4. 记录 wall time、peak RSS；若超 budget，先优化 array layout/cache，不能宣称通过。
5. README 明确 research-only、validity、human gates、optional calibration。

Acceptance：见第 10 节。

Dependency：Tasks 1–9。

## 9. Test matrix

### Unit

- unit conversions（尤其 degC→K；差值 K/°C 不混淆）；
- formula parser、element matrix、reaction balance；
- simplex/PSD/shape constraints；
- kiln `s(t)` interpolation 与 out-of-map event；
- every closure positivity/validity；
- Pareto domination with ties/NaNs/failed status。

### Physics manufactured solutions

- adiabatic no-reaction；
- Newton cooling；
- 1D slab heat conduction；
- Fick diffusion；
- first-order isothermal Arrhenius；
- closed single reaction heat sign；
- Darcy pressure under constant permeability；
- Gibbs constrained minimization；
- uniform eigenstrain gives zero stress proxy。

### Metamorphic

- slower `speed_ratio` increases residence time exactly by mapping convention；不要求质量单调。
- all reaction rates disabled → released reaction gas zero。
- emissivity=0 removes radiation term。
- equal center/surface fields → gradient risk zero。
- phase candidate deletion cannot increase coverage score。
- environmental threshold deletion changes `passed` to `not_evaluated`。

### Numerical

- BDF vs Radau selected cases；
- time tolerance tighten；
- 21 vs 41 cells；
- positivity under aggressive step；
- cache hit returns same result/source hash。

### Inverse

- hard constraints；
- no dominated final points；
- seed reproducibility；
- empty feasible set；
- all solver failures；
- budget truncation。

### Resource

- L0 RSS target <1 GB；L1 <3 GB；overall <6 GB；
- no process pool；
- no network required after repository/data setup；
- tiny commands complete within task-configured timeout（具体秒数由首次 benchmark 冻结，不能预先虚构）。

## 10. Final acceptance criteria

实现完成必须提供真实命令输出，不能只写计划或 stub：

1. `sludge-vme validate examples/tiny_synthetic.json` exit 0。
2. L0/L1 forward exit 0，required artifacts 存在且 `sludge-vme verify` exit 0。
3. inverse tiny budget 生成 `all_evaluations.jsonl`, `pareto.json`, `pareto.csv`, `rank_stability.json`；无 feasible 点也允许，但必须是物理/约束原因，不是未实现。
4. element relative residual、energy residual、state bounds 达到 `model_spec.json` tolerance；若 energy residual 对 operator splitting 使用不同定义，先更新 spec/ADR，不得静默放宽。
5. 21/41 cell convergence 对关键 metrics 达配置 tolerance；未收敛时该 case 输出 warning/failure，不能作为 inverse feasible point。
6. 全测试实际通过，报告 passed/failed/skipped；skipped 必须有原因。
7. 在目标 Linux aarch64 实测 peak RSS；不得用 x86 结果替代。
8. parameter/source/config/software hashes 出现在 manifest。
9. 缺环境标准、液相数据库或 strength closure 时正确输出 `not_evaluated/unresolved/coverage flag`。
10. 无网络、无收费服务、无新 OCI 资源、无生产控制连接。

## 11. Verification commands（实现后执行）

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest -q
.venv/bin/sludge-vme validate examples/tiny_synthetic.json
.venv/bin/sludge-vme forward examples/tiny_synthetic.json --fidelity L0 --out runs/tiny_L0
.venv/bin/sludge-vme forward examples/tiny_synthetic.json --fidelity L1 --out runs/tiny_L1
.venv/bin/sludge-vme inverse examples/tiny_synthetic.json --budget tiny --out runs/tiny_inverse
.venv/bin/sludge-vme verify runs/tiny_L0 --strict
.venv/bin/sludge-vme verify runs/tiny_L1 --strict
.venv/bin/sludge-vme benchmark examples/tiny_synthetic.json --out runs/benchmark
```

若 target 系统 PEP 668，不得写 system site-packages；只使用 venv。安装失败需记录 exact package/platform error，再选择 compatible free version；不得切换收费 API。

## 12. Dependencies、unknowns、risks

### 工程依赖

- Task graph 按第 8 节串行；L0 在 L1 前，chemistry/provenance 在所有 physics 前。
- SciPy aarch64 可安装性必须在 target 实测。
- minimal thermochemical tables 的再分发/许可与字段 provenance 需要逐条确认；若不允许打包，提供 importer + checksum，不复制受限数据。

### 不阻塞 MVP 的 unknowns

- 本厂 shale/gangue fingerprint；
- 真实 kiln spatial map、heat/mass transfer coefficients；
- 设备批准 speed bounds；
- 产品质量/环保 thresholds；
- 本材料 viscosity/strength/open-pore connectivity；
- 完整 oxide-liquid CALPHAD database。

处理：synthetic pack + interval + `unknown/coverage/not_evaluated`。不要以“必须先实验”停止。

### 主要技术风险与 mitigation

- Gibbs optimizer local failure：多初值、KKT/residual check、structured failure、cache 只缓存成功结果。
- Stiff/strong coupling：sparse Jacobian、events、adaptive step、Picard cap、Radau fallback。
- element projection 改变能量：记录 projection correction，超过 tolerance 失败，不默默修正。
- inverse 被 cheap model 欺骗：L1 shortlist、fidelity disagreement、rank stability。
- proxy 被误用：字段级 `proxy`, `validity`, `not_for_compliance`，CLI 顶部 warning。
- resource overrun：array preallocation、float64、stream evaluations to JSONL、bounded cache、no multiprocessing。

## 13. Rollback 与 human gates

- 每个 parameter/source pack content-addressed；新 pack regression 失败时回滚前一 hash。
- solver tolerances、phase list、reaction network 变更必须新增 ADR + regression baseline，不覆盖旧结果。
- 任何真实窑 map 导入、现场 recipe/speed 试验、PLC/robot 连接、合规声明、外部发布或费用操作均需人工审批；本 MVP 不实现这些 write paths。
