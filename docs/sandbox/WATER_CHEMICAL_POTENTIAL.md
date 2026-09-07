# 固定参考压力下的纯液水/理想水汽化学势

先登记数值检查：pref固定1e5Pa，温区293–500K；气体使用当前Rmix，液水保留原IAPWS。共同使用原生IAPWS熵参考，焓已含共同NIST能量偏移且不得再加一次。局部恒等检查不是非理想混合气或泥水活度验证。

事前验收：ds0/dT=Cp/T，T中央差分步0.01K，绝对误差≤1e-7 J/(mol K²)；dmu_g/dp=Rmix*T/p，p步1e-4*p，相对误差≤2e-7，绝对误差≤1e-9 J/(mol Pa)；dmu_l/dp=v_l，p步max(100Pa,1e-4p)，相对误差≤1e-4，绝对误差≤1e-8 m³/mol；回代mu_l=mu_g绝对残差≤1e-7J/mol。298.15/350/450K覆盖原生公式与稳定液/汽参照，零pv查询拒绝，peq不依赖输入pv。仅对照原psat，不强制两个模型相等。

## 定义、接口与边界

`WaterChemicalPotential(source_directory)` 通过已有 source-gated loader 构造真实水与 `IdealWaterVapor`。只接受登记的共同能量参考、相同水资产与固定混合气 R=8.31446261815324 J/(mol K)。温区仍为293–500 K；稳定液体 TP 的压力/相门禁完全由原水模块执行，没有高温拼接。

设 M 为原水摩尔质量，R95 为原水质量比气体常数，τ=647.096/T，δ=pref/(R95 T·322)。IAPWS 原生理想 Helmholtz 项给出：

- s0(T)=M R95[τ φ0,τ−φ0]，pref=100000 Pa。
- sg(T,pv)=s0(T)−Rmix ln(pv/pref)，hg 直接取已有水汽 caloric bridge。
- μg=hg−Tsg；sl=M·s_native，μl=hl−Tsl。
- peq=pref exp[(μl−hg+T s0)/(Rmix T)]。

这是热力学相容的真实纯液水/理想水汽近似。液水压力是机械压力，pv 是气体水汽分压，二者不能混同。理想标准态不要求在1 bar下实际存在稳定纯水蒸汽。共同焓偏移已经进入两相 h；它在 μ 差和 hg−hl 中相消，不再添加任何相变热偏移。两相熵都使用原生 IAPWS 参考，尚未对齐 NIST 绝对熵。

pref 固定是本派生模型的定义。若改 pref 而仍用原生 R95 的标准熵及 Rmix 压力项，sg 会变化 `(Rmix−M R95) ln(pref_new/pref_old)`；因此本 API 不提供任意参考压力配置。

公开接口：

- `ideal_vapor(T,pv)` 返回气相 h、s、μ 和真实传入分压。pv 必须有限正数；0分压的 μ 是负无穷极限，不返回伪造有限值。正的最小浮点分压通过对数差计算，避免先算 pv/pref 下溢。
- `liquid_tp(T,Pliq)` 和 `saturated_liquid(T)` 返回原 `WaterState`、摩尔 h/s/μ。
- `equilibrium_at_liquid_tp(T,Pliq)` 和 `equilibrium_at_saturation(T)` 返回 `equilibrium_partial_pressure_pa`、`phase_enthalpy_difference_j_mol=hg−hl`、两相化学状态及回代 `chemical_potential_residual_j_mol`。前者无需输入当前 pv，故可用于当前无蒸汽但有液界面的状态；后者只用原生饱和液状态作为参照，peq 不等于声明精确的原生 psat。

模型及返回结果带 `method_id=derived_native_entropy_fixed_pressure_water_equilibrium_v1`、`classification=derived_from_evidence`。`source_ids` 继承原水/bridge来源，包括登记的 `nist-codata-2022` R 来源；模型另暴露 `reference`、`source_asset_sha256`、`gas_constant_j_mol_k` 和 `caloric_method_id`，用于调用者匹配热量曲线。水的五个运行时哈希资产不冒称涵盖 CODATA 原件；R 的登记来源与精确SI乘积沿用 [IDEAL_WATER_VAPOR.md](IDEAL_WATER_VAPOR.md)。原生 φ0 来自已门禁水依赖与核读 IAPWS 表达式，未另造系数。

`WaterChemicalError` 表示派生数值不可表示、零/错误分压、化学结果或参考身份失败；底层 `WaterDomainError`、`WaterNumericalError`、`WaterSourceError` 保留原类别。平衡压溢出、下溢到零或 μ 回代残差超过1e-7 J/mol均拒绝，不夹逼。该残差是数值一致性门槛，不是物性误差界，也不保证近平衡任意小 μ 差的相对精度。

资格始终为 `ideal_water_vapor_real_pure_liquid_not_sludge_activity`：没有真实载气非理想 EOS、泥水活度、毛细界面、成核或传质系数的准入。接口不自动改变相库存，也不证明整个烧结砖的相平衡。

## 实际验证记录

测试文件先运行时因新模块不存在得到 `ModuleNotFoundError`；实现后36项检查通过。除事前门槛外，覆盖固定 pv 的 dμg/dT=−sg、公共能量偏移相消、参考压力不可配置、异常 φ0、温域外和最小正浮点分压。

独立审核者先使用原始 `_phi0` 直接手算公式，再与本模块比较以下五点；这是独立公式接线核验，并非逐系数重新实现 Table 1：

| T (K) | s0 (J/mol/K) | 饱和液输入得到 peq (Pa) | 相对原生 psat 差 |
|---|---:|---:|---:|
|300|125.73719510996519|3530.8482218640897|−0.16847%|
|350|130.93580655498917|41329.66820114837|−0.84464%|
|400|135.48372149678266|239279.93100786887|−2.64045%|
|450|139.54504406348235|875680.8989204273|−6.06334%|
|500|143.22900616155832|2342446.518059965|−11.24393%|

这些差异量化理想水汽近似与真实 EOS 的区别，不能视为载气混合物验证，不能以误差修正系数消除。主代理另以逐项 Table 1 实现核对8个温点，结果见 [oracle记录](research/water_chemical_oracle.json) 与 [独立脚本](research/water_chemical_oracle.py)；主代理实跑报告最大相对差2.59e-13，本模块测试不冒称重新执行该脚本。

复跑命令：`PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_chemical_potential.py -q`。

完稿回归：上述新36项连同原水78项、桥28项，实际合计142 passed in 0.95s。
