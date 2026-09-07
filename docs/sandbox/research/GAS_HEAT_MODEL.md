# 刚性气体—热量多格耦合验证模型 v1

日期：2026-09-07 UTC。实现：`src/sludge_sandbox/gas_heat_model.py`；验证：`tests/sandbox/test_gas_heat_model.py`。

模型实际连接现有热化学、气体输运、焓交换、反应矩阵和守恒时间积分。状态不是独立手写的测试 ODE：每次试探状态都重新经过这些模块。它仍是**固定几何、仅有气相储能的算子耦合验证**，不表示已经建立含固相热容、液水、干燥、收缩或力学的湿砖模型。

## 对象、参数与身份

对象是同面积、可有不同格宽的刚性一维平板。必须显式提供：

- 物种固定次序、每种摩尔质量 kg/mol、相容的 `Thermochemistry`；
- 共享面积 m²、每格宽度 m、每格气孔体积 m³；
- 每格导热率 W/(m K)、每种气体的每格有效扩散系数 m²/s；
- 每格 K（m²）、kr（无量纲）、μ（Pa s）；
- 整套系数的 ID、版本、分类及来源 ID。

气孔体积必须正且不超过面积×格宽，没有补孔体积或小正数裁剪。导热、扩散、渗透率可以显式为零。kr 限制在 [0,1]，μ 必须正。系数按初始输入复制并冻结，热化学包装对象另外复制；若其参数在构造后被改写，在下一步前拒绝。可调用温程本身是外部输入函数，调用者需保存其版本及输入，不宣称 Python 函数已经被自动序列化。

制造系数、制造热化学或制造反应都要求显式 `allow_manufactured=True`。即使系数标为 literature_candidate，`scientific_status` 仍仅为 `operator_integration_validation_not_material_qualified`，`material_qualified=False`。source IDs 是供证据解析的链接，不是资格证明。

测试使用 `manufactured:gas-heat-integration-v1`。A/B 为人为规定的同元素气相测试物种，M=0.012 kg/mol、cp=30 J/(mol K)、R=8 J/(mol K)、生成焓差 1000 J/mol 等均为制造数值。它们不是对任何现实气体、污泥或砖坯的物性声明。真实 NIST 接缝测试只使用其实际气体热化学；该测试的几何和输运仍属于显式制造输入。

## 每次试探的计算链

`GasHeatModel(state, time_s)` 实现积分器的 operator 接口。输入 `ConservedState` 保存每格各物种实际 mol 与每格总 U（J）。一次调用依次执行：

1. 对每格用其当前 n/U 调用 `temperature_from_internal_energy_j`。包含生成能的 u 不换基准，也不另加反应热。
2. 用当前实际气体库存、该格显式气孔体积和反解 T，调用 `ideal_gas_state` 得到组成与压力。没有额外惰性载气补齐。
3. 每个内部面仅调用一次 `face_exchange`，得到扩散、Darcy、合计物种 mol/s。
4. 对该面调用 `conduction_rate_w` 与 `gas_enthalpy_exchange`。扩散使用共同面温度的 h；Darcy 使用实际供体温度的 h。
5. 将同一面的物种和能量放入同一个 `Rates`；时间积分器对左右单元使用相反号，并用同样的时间权重更新库存与能量账本。

矩阵形状为 `face_species[NC+1,NS]`、`face_energy[NC+1]`、`reaction_species[NC,NS]`、`cell_power[NC]`。所有面正方向从左到右。该刚性模型没有另设的体积功或外部体热源，因此 `cell_power` 为零；边界热仍通过面能量进入同一账本。

反应是可选的实际 `ReactionNetwork`，其 species_order、显式摩尔质量与 R 必须匹配，而且每个物种都必须是当前热化学已支持的气相。固体或液体反应不能绕过缺失的凝聚相 u。其表观动力学浓度基准是**当前单元总体积**，而 EOS/气体输运浓度基准是**气孔体积**，二者在代码中分别传入。反应只填物种源，不填热源。

## 半格阻力与面状态

内部面距离 `dl=dx_left/2`、`dr=dx_right/2`，中心间距为 dl+dr。现有气体模型的线性面状态权重为：

```text
left_weight = dr / (dl + dr)
```

给定逐格 D 后，面 D 由两半格串联得到：

```text
D_face = (dl+dr) / (dl/D_left + dr/D_right)
```

这是在现有气体模块的共同面 EOS 近似下装配 D，不宣称对任意半格内连续变化的密度/组成已做精确积分。任一侧 D=0 时该物种这一扩散系数为零；质量平均扩散修正仍由现有气体模块计算。

Darcy 串联的是 `b=K*kr/mu`：

```text
b_face = (dl+dr) / (dl/b_left + dr/b_right)
```

不是分别平均 K、kr、μ 后相乘。调用已有 `face_exchange` 时，取线性 μ_face，再代数分解为 `K_argument=b_face*mu_face`、`kr_argument=1`。原始每格 kr 已经包含在 b 中；这个 1 不是把物理相对渗透率改为 1。组装后因子化不能表示时明确退出，不把非零流动变成零。

导热直接使用原函数的阻力 `dl/k_left+dr/k_right`，得到 `A*(T_left-T_right)/resistance`。上述装配对应固定逐格系数，不声称已存在真实材料随温度、反应和孔结构变化的本构。

## 边界

左侧始终是中心对称面：气体与能量通量均为零。右侧默认密闭、绝热。

可选 `outer_reservoir` 必须是显式 `GasState` 并带边界来源 ID。该状态**定义在外表面**，不是远处炉气：从最后格中心到外表面的距离只有 dx/2，面状态权重为 0，输运系数采用该半格输入。没有引入或猜测气膜厚度、膜扩散系数或传质系数。若要表达远场炉气，需另建有依据的表面传质边界。

可选 `outer_surface_temperature_k` 是正有限常数或 time_s→K 的显式表面温程，另带来源 ID；它是 Dirichlet 表面温度，不是直接把炉温施加到砖芯。外侧导热仅使用最后一个半格阻力。为了复用两段阻力函数，代码将这一个半格拆成同 k 的两个四分之一格，其总阻力仍为 dx/(2k)，不存在额外膜。连续温程的斜率节点可以交给 integrate 的 breakpoints；真正温度跳变必须使用跳变两侧各自的 operator 分段积分，并从前段末态重启，不能让同一步平均跨越跳变。对流和辐射边界尚未在本模型中实现。

外侧气体焓与传导热都累加在同一个最右面能量率中，方向由各自实际梯度/供体决定，不额外调整净边界热以凑守恒。

## 域、失败与调用方式

NIST 原分段的能量缺口、多根和温区边界保留。对于明确列举的温区越界、无公共温域、能量域/接缝缺口、多根、空热库存，以及明确动力学温域越界，返回 `DomainExit`，积分结果保存 `domain_exit` 和最后已接受状态。

模块异常类本身不是“物理退出”标签。反解不收敛、能量表示精度不足、浮点范围错误、物种/能量面通量不一致等内部契约错误，均转换为 `GasHeatModelError`，积分器记录 `numerical_failure`，保留原异常链。未预期的 KeyError、RuntimeError 等代码错误原样传播。状态形状或参数配置错误也属于 `GasHeatModelError`。

模型没有内置材料默认值，也没有完整模拟 CLI。调用者先构造上述明确参数的 model：

```python
initial = model.state_from_temperatures(amount_mol, temperatures_k)
result = integrate(initial, model, start_s=0.0, end_s=end_s,
                   policy=explicit_numerical_policy, breakpoints_s=known_schedule_slope_knots)
temperatures = model.temperatures_k(result.states[-1])
```

这里 n 是实际 mol，U 是实际 J。若外层使用参考体积密度，必须先按一致参考单元体积转换，不把 mol/m³ 直接交给这一接口。

## TDD 与实际验证

测试先于模块：首次命令实际因 `sludge_sandbox.gas_heat_model` 尚不存在而 collection error。实现后又新增极端 K/kr/μ 因子化下溢反例，先得到 DID NOT RAISE，再修复为 `mobility_factorization_outside_float_range`。独立审查进一步指出内部面通量契约错误被误报为物理域退出；三个新增测试（面契约、温度反解不收敛、能量分辨率不足）实际先得到 3 failed，再将其区分为数值失败。

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_gas_heat_model.py -q
```

实际结果：Python 3.12.13 / macOS arm64，**26 passed in 0.35 s**，退出码 0。包括真正 integrate 的以下案例：

- 双格温差＋压力差＋组成梯度，同时检查逐物种总量、C 元素、显式质量和 U。
- 相同初态关闭气体输运，或关闭导热，结果确实改变而总 U 继续闭合。
- 关闭输运的两格导热独立指数解：每格 Cv=22 J/K、面导热系数 1 W/K。
- 同 cp/生成焓/摩尔质量的二元扩散独立指数解，并检查温度保持不变。
- 非等格宽的半格阻力、Darcy 移动率与面温度；独立 D_face=0.4 m²/s、反向 ±0.08 mol/s 扩散及其 80 W 生成焓交换；显式表面气体/温程边界的流量与累计能量。
- 实际制造气相 A→B 配平反应：数值浓度对照一阶指数解，温度对照生成能独立公式，不新增热源。
- 真实 N₂ Shomate 500 K 接缝的不可反解能量，明确 domain_exit，不产生伪轨迹。
- 非法几何、缺项、来源、制造开关、固相误接、参数冻结，以及代码错误原样传播。

追加的实际运行结果如下；不是预期值或手写演示输出：

| 双格 0.3 s 工况 | T_left / K | T_right / K | 总 U 变化 / J |
|---|---:|---:|---:|
| 全部耦合 | 617.423649875 | 892.479762739 | 0 |
| 气体输运关闭 | 604.044769759 | 897.303486827 | −3.64e−12 |
| 导热关闭 | 613.707110666 | 895.075478381 | −3.64e−12 |

初温为 600/900 K，初始 n 为 [[0.8,0.2],[0.3,1.2]] mol。全耦合 8 个接受步、57 次 operator 调用；最终 n=[[0.782300600506,0.240034093023],[0.317699399494,1.159965906977]] mol，各物种全域总量残差为 0。

封闭气相反应 1 s 后，n_A=0.818731396797、n_B=0.181268603203 mol，T=608.239481964 K，独立解析温度为 608.239511224 K，总 U 变化为 0。此处反应特意保持总 mol；一般反应只保证其计量规定的元素/质量守恒，不能通用要求总 mol 不变。

这些结果证明现有算子已经进入同一试探步与能量账本。它们不替代真实材料机制对照，尚不能验证全周期污泥砖、蒸发凝结、烧结孔结构、形变功、强度或工厂控制。
