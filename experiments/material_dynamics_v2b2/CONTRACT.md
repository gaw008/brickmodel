# B2 非等温反应—输运与条件化原料筛选研究合同

合同版本：`B2-1.0.1`。模块：`material_dynamics_v2b2`。
状态：`frozen_candidate_pending_manager_review`；本文件冻结 Planner 的建议，不表示 Manager 已批准实施。
任务：`t_c6385001`；原规划：`t_d7507b62`。仅规划补正；未实现或运行 B2。`implementation_authorized=false`，`production_approved=false`。

> For Hermes / Engineer：仅在 Manager 读回本合同并明确派发隔离实施后，按 B2_HANDOFF.md 分步实施。不得由本计划自动派发、部署或生产控制。

Goal：把“寻找什么样的污泥”收窄为给定基料代理、壁厚、供氧边界、温度程序及假设包络下的可氧化负荷—反应时序—输运能力约束。
Architecture：沿用 B1 的 1D 对称半板、固定几何和固定孔隙、单一 C+O2→CO2 守恒骨架；外部给定空间均匀 T(τ)，只改变明确假设的反应/扩散系数。输出离散条件筛选，不求热场、不拟合材料常数。
Tech stack：未来仅离线 Python3 标准库；JSON 输入，CSV 原始数值，JSON 诊断/验收，中文 Markdown 报告及浅色静态 SVG；单 worker/thread。

补正范围：仅统一§5.2/§7.2/JSON的验证状态契约，并补充§9.1及handoff§5.1的证据绑定建议。字段枚举与未绑定不得通过是Manager已决定项；具体CLI/文件绑定方案为`pending_manager_decision`，不是G0批准。数值、公式、22情景、24验收ID、容差及预算不变。以下原规划的“本轮读取/已验证事实”是t_d7507b62的历史证据记录，不冒充本补正重新查文献或复跑；本补正仅完整读回指定三附件及Manager三份结构检查文件，详见B2_G0_CHANGELOG.md。

## 1. 结论、依据与授权边界

### 1.1 建议冻结的最小可执行域

采用 `synthetic_prescribed_temperature_equimolar`：温度是外部指定的材料温度标签，不是窑温求解结果；所有运行参数为 synthetic_assumption，不自动加载文献 CSV。该版本在声明的物种库存域内有封闭的质量方程，但不是完整热力学/力学闭合模型。

已验证事实（本轮读取的证据）：
- B1 Safety 报告与 safety-review.json 一致，审核提交 `d051c0982835dbe54fc4f509f1819661b85de055`，批准仅 `research_diagnostic_scope`，production_approved=false、required_changes=[]。本轮未重跑 B1。
- Stage2A 的持久机制报告、候选 CSV、来源 registry 与候选草案均已实际读取；102 条/9 unknown 是父报告声明，本轮不声称重新统计/执行其提取测试。
- S02 的 O2 模型拟合限环境温度至500°C；A600 的拟合与其余数据不一致；O2 与 CO2 在原试验并非同一个等摩尔 Fick 系数。[1]
- S09 方法明确：准等温系列先在 N2 中以50 K/min加热到873/973/1073/1173/1273 K，再切 O2/CO2；动态 TG 是另一系列。§3.1 用40–60%转化段，80%和100%O2的点因自热被排除。[2]

合理推断：S02 的砖用黏土输运拟合与 S09 的预热污泥颗粒表观动力学，材料、温区、气氛和反应基准不匹配；不能拼成已标定空气砖坯。温度依赖的结构可用于有界假设实验，不能继承这些论文的参数真实性。[1][2]

待验证假设：均匀给温、固定孔隙、等摩尔共同扩散、单一可氧化碳负荷、所选参数包络足以揭示某些条件方向。若方向在声明包络中翻转，必须报告 unresolved，而非换参数挑结论。

### 1.2 用户故事

- 研究者先固定一种基料代理和壁厚，对比相同可氧化负荷在早升温/晚升温下的芯部氧和局部残碳，决定公开资料中优先寻找哪些条件化特征。
- 研究者发现平均99%已达而局部99%未达，拒绝把“均值达标”解释为砖体全局燃尽。
- 研究者发现有限氧下反应近停但尚有碳，优先检查氧预算而非宣称材料已燃尽。
- Manager/Safety 从原始状态、通量、输入与独立参考重建结论；无实际求解结果、超时或缺映射时，报告 unknown，而不是供应商排名。

### 1.3 Non-goals

不建孔关闭/收缩/开闭孔转移、压力/渗流/气体热膨胀流、完整多组分挥发、吸附库存、热解/脱水/碳酸盐、热传导/反应热/能量闭合、自热、窑炉温度场、强度/裂纹/黑心/排放或生产控制模型。不输出真实秒数、最佳配方、供应商总分、实际污泥通过/淘汰名单。公开 SSA 不替代 raw sludge；TG 残渣、LOI 不替代可氧化碳。现场数据仅为可选后续校准，不是开展本轮研究的前置要求。

不安装依赖、不创建 OCI/收费资源、不升配、不改 Hermes/服务/隧道、不外发/公开发布/push/merge/部署/删除。不重新认证，不读取凭据；仅现有 openai-codex/gpt-6-astra 订阅。保持旧 B1 文件及历史 pending 标签不变。

## 2. 物理基准、状态、单位

### 2.1 固定的跨情景参照

两面对称供气代表壁的半板，ξ=x/L∈[0,1]；芯部ξ=0，外表面ξ=1。固定截面 A、固定均匀开孔率 ε；不模拟烧失引起的孔隙改变。

参照尺度定义（只作代数，不赋真实材料数值）：
- L_ref：参考半厚，物理单位 m；L=ell·L_ref，ell=`length_ratio`。
- D_star：按总截面积定义的参考有效扩散系数，物理单位 m²/s。
- t_star=ε L_ref²/D_star；τ=t/t_star，所有 B2 情景共用同一个未标定 t_star。不得随 ell 或 d_ref 重新置零/重算时间基准。
- c_star：常数参考孔内 O2 浓度，物理单位 mol/m³(pore)；本合同不提供数值，不令它随 T 改变。
- C_s0：初始可氧化固体碳 mol/m³(bulk)；Γ=C_s0/(ε c_star)。不同 Γ 情景改变负荷而不改 ε、c_star、L_ref。
- K_ref=k_ref·t_star；k_ref 是假设一阶库存速率 s^-1，并非文献 K0。theta 是无量纲温度敏感度，若未来有材料校准才可解释为 E/(R T_ref)。B2 不输出 E、k_ref 或 t_star 的物理值。
- d_ref=D_eff(T_ref)/D_star；Bi_ref=h_ref L_ref/D_star，h_ref 按总外表面积 m/s。Bi_ref 不是当前温度/当前长度下的 Bi。
- 有限库 rho=V_res/(ε A L)，按本情景实际 L 定义；密闭外库无补气/排气。若跨长度保持 rho，就是改变 V_res；不得宣称同时固定 V_res。默认长度对照只用 infinite，避免这一混淆。

场状态均无量纲（unit=`1`）：u=c_O2/c_star、v=c_CO2/c_star、f=C_s/C_s0。有限库状态 u_res,v_res 按同一 c_star；非 finite 取 null，不伪造0。全部默认 u=1、v=0、f=1，finite 初始 u_res=1、v_res=0。

### 2.2 非等温但不偷偷加入恒压气体模型

保持常数参考浓度、固定控制体积、共同等摩尔交换；T 只驱动明确系数，不把 u 按每步 p/(RT) 重归一化。infinite 代表人为维持固定摩尔浓度的源库，不代表恒定压力和氧体积分数的真实窑气。

这是 `thermal_expansion_flow=not_modelled`、`equation_of_state=not_modelled` 的浓度库存诊断。真实气体受热可能改变压力或产生流动；本合同既不强制压力恒定，也不预测压力。不得同时声称固定总浓度、固定压力、变温理想气体已闭合。若要恒压空气边界、p/T 状态或热膨胀流，需另改合同并审核，不能静默增加稀释项或删除分子。

## 3. 材料关系与来源分层

下列关系采用统一来源分类：`conservation_identity`、`synthetic_assumption`、`candidate_not_executable`、`unknown_mapping`。公式的结构有文献背景不等于参数获得标定。

| id | 关系/量 | 分类、来源与采用理由 | B2 迁移限制 |
|---|---|---|---|
| REL-C | C+O2→CO2，单一摩尔计量 | conservation_identity；B1合同§3–4；仅C/O物种域 | 不是原污泥全部质量/全部气体 |
| REL-K | K(T)=K_ref exp[theta(1−T_ref/T)]；q=ΓKfu | synthetic_assumption；Arrhenius温度比结构见S09§2 Eq6–10；一阶f、一阶u和全部数值由本合同定义[2] | 不用S09颗粒表面积K0，不叫本征动力学 |
| REL-D | d(T)=d_ref(T/T_ref)^m；a_D=d/ell² | synthetic_assumption；S02§4.4讨论气相温度幂律，但本式m=0或1只是机制对照[1] | 不是S02 MTPM/Bosanquet拟合，不推断高温孔喉 |
| REL-B | b=Bi_ref/ell，J=b(c_s−c_ext) | synthetic_assumption；B1 Robin膜关系；h_ref恒定 | O2/CO2共用，不是多组分传质/真实恒压边界 |
| REL-G | Γ、ell、rho 的尺度/库存定义 | conservation_identity；本合同§2，延续B1归一化 | 无实际kg/kg_dry、mm或秒数映射 |
| REL-P | 固定均匀ε、固定几何与共同D | synthetic_assumption；数值研究约束 | 不声称从SSA或S02总孔隙率测得 |
| CAND-S09 | quasi_d1mm/quasi_d2mm 成组E/n/K0 | candidate_not_executable；S09§2、§3.1、Fig5–6[2] | 两组分别45.57/31.92 kJ/mol，n=0.82/0.86，K0=0.0127/0.033 mg/(m² s Pa)；非整数分压幂与报告单位/归一化未解决，不转成K_ref/theta |
| CAND-S02 | ψ、r、D_s0、Ea,s成组候选 | candidate_not_executable；S02 Table4、§4.2–4.4[1] | O2拟合至500°C；A600异常；不拼列；不把CO2表面项用于O2 |
| MAP-RAW | 原泥/基料/预处理→Γ、K_ref、theta、d_ref、m、Bi_ref | unknown_mapping；Stage2A报告§4.2 | 干基组成/PSD/TG并不能唯一识别此联合映射 |
| MAP-QUALITY | 局部残碳/时序→强度、裂纹、合规 | unknown_mapping；本轮不建 | 不把诊断阈值称质量标准 |

S09 动态 Table5 的 O2/CO2 升温特征与准等温颗粒拟合不能互换；WR 是总残余固体质量比例，不是残碳。S11 制片/烧成方法属于焚烧灰小圆片，峰温保温3 h不等于总停留时间，也未补全本模型的供氧边界。[2][3]

## 4. 冻结方程与离散边界

令 a_D(τ)=d(T(τ))/ell²，b=Bi_ref/ell，局部 q=Γ K(T) f u：

    ∂τu = a_D ∂ξξu − q
    ∂τv = a_D ∂ξξv + q
    ∂τf = −K(T) f u

芯部 ∂ξu=∂ξv=0。向外为正：J_u=−a_D∂ξu=b(u_s−u_ext)，J_v同理。

- infinite：u_ext=1，v_ext=0；不声明有限总氧。
- finite：du_res/dτ=J_u/rho，dv_res/dτ=J_v/rho；外库只初始化一次，反向通量也要等量更新。
- sealed：J_u=J_v=0；Bi_ref=0，rho=null。

均匀 cell-centered FV，Δξ=1/N；内部面 J_i=−a_D(c_right−c_left)/Δξ。表面半格/膜串联：

    g(τ)=1/[1/b + Δξ/(2a_D)]
    J=g(c_last−c_ext)
    c_s=c_ext+J/b

b=0 时显式 g=0、J=0，不算1/0；sealed 表面值可取末单元值但必须标边界重建约定。finite 外库增量 +J/rho 与末单元 −J/Δξ 同步。芯部输出为第一个单元平均，不冒充 ξ=0 精确点值。测试专用 Dirichlet 极限 g=2a_D/Δξ 另命名，不接受数值Infinity当Bi。

采用 B1 风格保正 SSPRK2 或等价保守二阶方法；基线固定建议 SSPRK2，若替换须 Manager 同意。非自治两阶段分别在 τ_n 与 τ_n+Δτ 求 T/K/d/g，通量和反应账本用同阶段权重；不能全步只用起点温度。步长碰到温度 knot/输出时刻须截断。CFL safety=0.8，约束内部/表面扩散对角损失、ΓKf、Ku、finite外库g/rho；对本步系数的端点极值与每阶段状态复核。必要时拒绝该步并减半，计数受资源上限约束。禁止库存 clip、负数补零、事后重新定义状态以通过守恒。

本节为冻结的数学规范，未声称本轮已执行代数脚本或数值对照；Engineer/Safety 必须分别推导并验证。

## 5. T(τ)、参数域与 JSON 输入

### 5.1 温度规定

`temperature.interpolation="piecewise_linear"`；knots 为严格递增 τ，包含0及τ_end。相邻同温允许hold，温度非单调允许升/降循环；重复τ、跳变、范围外外推均拒绝。每个 knot 固定字段 `tau`（unit1）、`T_K`（Kelvin）。只接受Kelvin，不自动猜测°C。显示°C可另转换，不改变求解单位。

温度并非文献测量：T_ref_K=600；B2 synthetic范围450–750 K。此范围只是有界计算选择，不是S02/S09联合材料适用域。默认 τ_end=20，sample_dtau=0.1，max_dtau=0.02；τ是无量纲，报告中计算机运行墙钟秒与物理过程时间必须分栏。

固定程序（全部 synthetic_assumption）：
- P_ISO：[(0,600),(20,600)]。
- P_EARLY：[(0,450),(2,750),(20,750)]。
- P_LATE：[(0,450),(10,750),(20,750)]。
- P_CYCLE：[(0,450),(5,750),(10,450),(20,450)]。

### 5.2 输入安全域不等于数值验证域

输入允许域：Γ∈[0.25,8]；K_ref∈[0,10]；theta∈[0,6]；d_ref∈[0.5,2]；m∈{0,1}；ell∈[1,2]；Bi_ref∈[0.1,10]（sealed为0）；finite rho∈[0.25,10]。温度450–750 K、T_ref_K固定600；正 τ_end≤20；N∈{7,15,31}；0<max_dtau≤0.02；dt_scale∈{1,0.5,0.25}；sample_dtau固定0.1且终点另输出。Knots不超过8个。预检所有分段端点，K(T)≤20、0<d(T)≤4；不能以溢出后截断指数实现。

只有 B2_ACCEPTANCE_MATRIX.json 的实际默认 manifest、指名解析/收敛域可获得对应验证标签。结构合法但自定义的连续参数点只允许 `verification_scope="audit_only"`、`numerical_validation="not_verified_for_custom_case"`；不得继承默认情景的数值通过或进入正式筛选。

`verification_scope`只表示拟适用检查范围，不是通过结果；默认/指名冻结域为`frozen_suite`，合法自定义为`audit_only`。默认在同一源码、完整展开输入内容与实际验证覆盖尚未绑定前，`numerical_validation="not_run"`，即使积分完成或库存audit通过也不升级。合法custom保持上述标签；实际失败/未运行另按execution_status及逐门结果如实保存，不能伪装通过。§7.2给出唯一枚举与通过前置条件。

### 5.3 完整单情景格式示例（输入，非模拟输出）

```json
{
  "schema_version": "B2-1.0.1",
  "scope": "synthetic_prescribed_temperature_equimolar",
  "scenario_id": "W03",
  "provenance": "synthetic_assumption",
  "base_context_id": "synthetic_fixed_matrix_v1",
  "mapping_status": "unknown_real_material",
  "temperature": {
    "T_ref_K": 600,
    "interpolation": "piecewise_linear",
    "knots": [{"tau": 0, "T_K": 450}, {"tau": 2, "T_K": 750}, {"tau": 20, "T_K": 750}]
  },
  "reaction": {"K_ref": 1, "theta": 6, "Gamma": 2},
  "transport": {"d_ref": 1, "m": 1, "Bi_ref": 1},
  "geometry": {"kind": "symmetric_half_slab", "length_ratio": 1, "porosity_mode": "fixed"},
  "boundary": {"mode": "infinite", "reservoir_ratio": null},
  "initial": {"u": 1, "v": 0, "f": 1},
  "numerics": {"n_cells": 15, "tau_end": 20, "sample_dtau": 0.1, "max_dtau": 0.02, "dt_scale": 1},
  "diagnostic_thresholds": [0.95, 0.99]
}
```

全部字段必填，禁止缺失/未知/重复JSON key；数字拒绝bool、字符串、NaN、Inf；标识只允许 `[A-Za-z0-9_-]{1,64}`。输入不得含执行表达式、网络URL、来源全文、路径/凭据字段；嵌套深度≤8、单输入≤64 KiB。默认批次由已冻结配置展开，不在运行时合并任意用户patch。只给文献参数、真实供应商ID、物理秒数、不同热场/气体模式等请求时 fail closed 或明确unsupported，不自行补猜数据。

## 6. 冻结的小规模情景与不确定性

机器权威：`B2_ACCEPTANCE_MATRIX.json` 的 `scenario_manifest`。由 defaults、programs、bundles、runs 严格展开为逐情景完整JSON；展开文件必须持久化。Markdown与JSON冲突即阻断，不由实现者任选。

- R01/R02/R03/R04：B1退化回归，分别 base、reaction_fast、finite_small、film_weak。P_ISO，theta=0,m=0,d_ref=1,ell=1，保留 B1 的 K/Γ/Bi/rho。仅回归这些指名哨兵，不重做旧全套研究。
- W01–W06：Γ=0.5、2、8，每个负荷分别P_EARLY/P_LATE，联合包U0（K_ref1,theta6,d_ref1,m1）。
- W07–W12：同样负荷/程序，联合包U1（K_ref0.5,theta6,d_ref0.5,m0）。U1为“较慢反应/较弱输运”的联合替代，不代表概率最坏界或实测相关性。
- L01/L02：Γ2、U0、ell2，分别P_EARLY/P_LATE；与W03/W04成对，时间基准不变、h_ref不变。
- C01：P_EARLY、K_ref0，其余U0，验证变温无反应均匀不变。
- C02：P_EARLY、U0、Γ2、sealed。
- C03：P_EARLY、U0、Γ2、finite rho0.25。
- C04：P_CYCLE、U0、Γ2、infinite，验证降温与分段边界，无预设完成结果。

情景必须串行，不做连续优化、随机Monte Carlo或自动扩大参数网格。U0/U1不是置信区间，未证明覆盖真实材料或所有不确定性。

## 7. 守恒、时序与条件筛选

### 7.1 必须成立的独立库存审计

气体积分按孔内参考库存归一化；碳元素 C_body=∫(Γf+v)dξ，氧分子当量 O_body=∫(u+v)dξ。finite 另加rho·v_res与rho·(u_res+v_res)。氧原子为上述氧分子当量的两倍；名义质量为∫(12Γf+32u+44v)dξ，加对应finite库。不是原污泥所有元素的总质量。

infinite/体内审计：C_body(τ)−C_body(0)+∫J_v dτ=0；O_body(τ)−O_body(0)+∫(J_u+J_v)dτ=0；名义质量用32J_u+44J_v。finite整体/ sealed恒定。局部u+v=1、finite库u_res+v_res=1；固体C消耗、O2反应消耗、CO2产生共用反应进度但分别从状态/通量重建。

finite最大平均转化≤min(1,(1+rho)/Γ)，sealed≤min(1,1/Γ)。时序不能改变氧元素预算。infinite不是总氧有限，但在指定时窗仍有有限膜导通约束。

固定审计容差 `B2-AUDIT-1`：对于库存/预算，|lhs−rhs|/max(1,|initial_reference_inventory|)≤1e-6；正负库存与非有限另单独检查，不用守恒容差授权负库存。表格字段/状态重建使用同一固定1e-6规范化尺度。容差来自 reviewer/受审源码中的合同常量，不读取artifact自报tolerance。任何输入层、summary层、嵌套verification层的容差覆盖均拒绝或忽略且不能改变判定。

守恒审计只是导出库存/积分通量的一致性检查，不是完整 ODE 轨迹真实性认证；不能承诺识别协同重写所有状态和通量。独立解析、数值重跑、不可变输入/源码定位构成不同证据层，不互相冒充。

### 7.2 事件与状态分离

记录平均f和最大cell-average f；阈值以剩余量≤0.05/0.01定义平均/局部95/99%，不以q接近0触发。最大cell平均仍不是连续场严格最大值，需网格误差说明。

每事件为 `{tau, bracket_tau, status}`：由相邻输出首次越阈线性插值并保留包围区间；未发生tau=null、bracket_tau=null，不以0或τ_end代替。默认包围宽≤0.1τ，插值不是额外精度。初始已达可为tau=0且status=initially_reached。

不同维度的状态不得混成一个feasible字段：
- execution_status：integrated / partial_timeout / rejected_input / numerical_failure / resource_limit。
- budget_status：sufficient_upper_bound / oxygen_budget_limited / not_applicable_infinite。
- threshold_status（每个平均/局部阈值）：reached_diagnostic_threshold / not_reached_by_horizon / excluded_by_oxygen_budget / not_evaluated。
- verification_scope：frozen_suite / audit_only。
- numerical_validation：passed_frozen_suite / not_verified_for_custom_case / failed / not_run。
- material_mapping：unknown_real_material（本轮恒定）。
- screening_status：见§7.3。失败/缺映射不允许写material_infeasible。

Manager已决定的字段规则（同JSON `validation_status_contract`及handoff§5.1）：
- `audit_only`不是numerical_validation值；`frozen_suite`也不表示已通过。scope与result必须分别导出。
- 默认/指名冻结域：尚未运行、缺证据、覆盖不全、源码/完整展开输入身份不匹配时为`not_run`；已实际发现适用数值/审计门失败时为`failed`，不能由旧PASS覆盖。partial_timeout/resource_limit不是通过，其execution_status照实记录；没有实际数值失败证据时numerical_validation为not_run。
- 仅当当前运行integrated、当前原始数据审计通过、指名参考/回归/收敛等适用数值门实际完成并通过、同一源码/本版合同/完整展开输入内容和覆盖关系均已核验绑定，才可为`passed_frozen_suite`。未执行/跳过/失配不能当通过。通过仅限声明覆盖，不是全连续域认证，也不等于G0、Safety或生产批准。
- 合法custom恒为`verification_scope=audit_only`、`numerical_validation=not_verified_for_custom_case`，即使沿用W03等ID、audit通过或提供旧默认PASS也不继承；其实际失败或未执行由execution_status和逐门结果保存，不因标签而隐藏。material_mapping及输入/筛选mapping_status均恒为`unknown_real_material`。
- 默认W配对缺绑定覆盖时，不得输出正式`sampled_candidate_under_assumptions`或`not_reached_in_sampled_domain`，按§7.3保留unresolved；实际失败为unknown_numerical。预算排除仅是模型必要条件，不代表数值通过或真实材料淘汰。R/L/C仍仅diagnostic_only。
- `B2_VALIDATION_STATUS_FIXTURES.json`仅为schema examples，含条件性expected状态；它不是执行证据，不提供实测PASS、数值或哈希，不得被证据加载器接受。

t_gen只涉及本模型CO2，不代表全部污泥气体；本轮不输出全部产气完成时间或t_escape完成时间。输出CO2累计生成、体内库存、finite库库存、净向外积分即可；净通量可反向，净排出不等于累计生成。`tau_source_peak`是采样源率首次最大值的τ，恒零则null，必须标 sampled_peak；不是燃尽时刻。t_close、压力、能量、收缩、强度、排放均not_modelled且数值null。

### 7.3 筛选的可执行定义

被筛的是模型的离散负荷/程序/联合参数情景，不是真实供应商。固定评价时点τ=20，主阈值“最大局部剩余≤0.01”，并同时报告0.05和平均阈值敏感性。

`condition_key`冻结为matrix中uncertainty_pairs每对的首个scenario_id（如W03/W09共用W03）；完整条件参数由该key引用的展开输入给出，bundle_id另列。不在配对中的R/L/C保留自身scenario_id作为key，screening_status=`diagnostic_only`，仅报告预算/时序/长度对照，不凭单包结果给包络候选资格。正式sampled筛选仅适用于W组配对；所有情景仍独立输出budget_status和threshold_status。

必须逐情景导出：
- 氧预算允许转化上界；有限/密闭给出Γ与供氧库存的必要不等式，不能当充分条件。
- 反应暴露 H(τ)=∫K(T)dτ；在本初边值u≤1下，f≥exp(−H)是本模型的理想供氧下界。用它作“即使理想供氧也来不及”的必要筛选，不当空间解。
- 扩散暴露 S_D(τ)=∫d(T)/ell² dτ；膜暴露 S_B(τ)=∫Bi_ref/ell dτ；瞬时反应/扩散比 Da_O2=ΓK ell²/d。它们只作机制坐标，不从单一Da给普适合格线。
- τ=10和τ_end的碳均值/最大局部、芯/表氧、累计CO2；平均/局部事件包围区间。

条件结论：
1. 任一计算/审计失败：`unknown_numerical`，保留原因，不计作失败材料。
2. 定义的库存上界严格排除所需转化：`excluded_by_model_oxygen_budget`，仅限此边界/库存域。
3. U0/U1均完成且各自远离阈值、具有指名数值验证覆盖时：可以报告 `sampled_candidate_under_assumptions` 或 `not_reached_in_sampled_domain`。
4. U0/U1跨阈、方向翻转、接近阈值、验证覆盖不足：`unresolved_in_assumption_envelope`。任一结果均保持material_mapping=unknown_real_material。

冻结防过度精确的筛选余量 `screening_guard_f=0.005`：候选要求f_max+guard≤0.01；明确未达要求f_max−guard>0.01；其间unresolved。这是研究报告的保守决策缓冲，不是经证明的全域离散误差上界，也不代替收敛测试。没有证明连续区间插值/单调性，SVG只画被计算离散点，不填充“连续可行窗”。若需边界精化，另经Manager批准，不自动加网格。

### 7.4 面向寻找/混配/预处理的条件方向与反例

允许说“在这个基料代理、壁厚、给温和供氧窗口下，优先寻找较低可氧化需氧负荷，或同等负荷下更早在供氧可达窗口消耗的原料特征，且需联合检查输运”。这不是已经计算出的方向；最终语句必须引用真实W/L/C输出。

必须检查以下反例，不允许预写成功：
- 提高温度/提前反应不能突破finite总氧上界；C03与R03对照。
- 早升温未必使局部诊断更好：在快耗氧/弱输运包络中检查芯部缺氧和局部残碳；若不翻转，应如实报告本域未观察到，不能造反例。
- 降低负荷在所有供氧窗口都“够用”是强假设；比较不同程序/长度，如果低负荷仍未达则否定。
- 减小原料颗粒不等于减小壁半厚ell，也不能由PSD唯一推d_ref；本轮只计算壁尺度，禁止将L对照解释成磨细工艺量化收益。
- 脱水改变湿质量与热负荷，不自动减少干基可氧化碳Γ；预氧化/掺混可能同时改变孔隙、塑性、气体物种和排放，这些联动本轮未识别。

真实基料配对、干基需氧量/碳特异性数据、同条件多速率残碳/供氧曲线、壁/肋厚与热态输运是优先寻找的公开特征；缺失时给unknown及最有信息量的后续公开证据需求，不强制用户先积累长期现场记录。

## 8. 数值验收门（未来必须实际执行）

各门稳定ID见JSON，以下阈值也是冻结规范。实现者不能为通过而扩大容差；达不到就修算法或请求修订。

### 8.1 B1退化与守恒

R01–R04与审核B1 fresh重跑/保存原始产物比较，相同N/输出τ：u/v/f、库存和积分通量最大规范化差≤1e-4；平均/局部事件τ差≤0.1且null语义一致。两者步长不同则比较误差门，不要求字节相同。B1运行只在安全临时副本，不恢复旧worktree、不修改旧分支。

C01变温、K=0、均匀初边值：u=1,v=0,f=1，最大误差≤1e-10。C02/C03逐时刻守恒、正性和转化上界通过；缺氧停止与燃尽不同，必须有真实数值输出。另以非均匀手工状态测试finite边界双向通量：增量符号/总转移误差≤1e-12；这是单步构造测试，不伪装真实材料结果。

### 8.2 独立非等温参考

A-SEALED：无空间梯度、sealed，Γ取0.25/1/2；K_ref=1,theta=6,P_CYCLE，余默认。在温度分段独立积分H=∫K dτ；令a=1−Γ，闭式候选：

    Γ != 1: f = a / [exp(a H) − Γ]
    Γ == 1: f = 1/(1+H)
    u = 1−Γ+Γ f, v=1−u

Reviewer 从ODE自行推导或采用另一独立参考实现；用稳定expm1等避免抵消，不能导入生产求解器/温度插值/诊断函数。H用独立分段复合Simpson，从64子区间逐次倍增至4096；相邻积分差≤1e-9方可作为参考，否则reference_not_converged。比较完整采样轨迹的u/v/f绝对误差≤2e-5，并验充分氧/等计量/缺氧极限。闭式及求积在本规划未运行，不预填通过值。

A-DIFF：非反应，初u=0,v=1，芯部Neumann、表面测试专用Dirichlet u=1/v=0；P_EARLY，m=1,d_ref=1,ell=1，τ_end20。独立构造 S_D（分段线性T的积分可精确按梯形段面积），在扩散时间S_D中使用标准半板级数：

    λ_n=(n+1/2)π
    u(ξ,τ)=1−Σ [2(−1)^n/λ_n] cos(λ_n ξ) exp(−λ_n² S_D)

比较cell平均的解析积分，不把点值与FV均值混比；τ≥0.5。级数128/256项差≤1e-9；N31时u最大绝对误差≤5e-4，N7/15/31误差应改善。另用P_ISO验证参照退化。Dirichlet只在专用测试，不冒充默认Robin正确性；Robin由R回归、单步串联阻力和非等温收敛共同覆盖。

A-TEMP：独立检查每个knot、段中点、hold、降温、恰好终点的T/K/d/g，误差≤1e-12·max(1,|reference|)；温度外推/重复τ拒绝；theta=0和m=0退化；length_ratio变化同时影响a_D、b但不影响K_ref和共同τ。

### 8.3 收敛与事件

代表情景W03、L02、C03：
- 空间：N7/15/31，dt_scale固定0.25。
- 时间：N31，dt_scale1/0.5/0.25；max_dtau随倍率一起缩放，CFL也缩放。记录真实接受步数，不能三次用同一步长却声称时间收敛。
- 输出共同τ上的f_mean、f_max、u_core（对应cell平均粒度差明确标出）。空间15→31差≤0.005(f)、≤0.01(u_core)；时间0.5→0.25差≤0.001(f)、≤0.002(u_core)。细化差不大于粗化差的1.1倍，除非两者均低于1e-6误差地板。
- 两个事件均出现时，差≤0.1τ且报告采样区间；只有一个出现则event_convergence_unresolved，不得按τ_end补值通过。双null只证明该采样窗未观察到事件，event_time_error=null，另审连续残碳指标；不得计为0时间误差。
- 平均/局部差别用R04实际回归证据验证，不通过手工造最终结果。所有默认情景仍逐例进行守恒、输入和状态核验；代表收敛不等于每个连续参数均获验证。

### 8.4 审计与失败路径

独立审计拒绝：库存修改、finite库重置、通量符号反转、删通量区间、重复/缺profile行、NaN/负数、null事件改0、平均当局部、伪造能量/压力通过、顶层/嵌套容差扩大并伴库存修改。删除预写audit/verification仍应能从raw数据进行库存核对；没有源码/输入身份链则不能宣布完整真实性。

路径与输入：既有输出拒覆盖且哈希不变；拒绝绝对/..越界、符号链接父目录或输入链接、非普通文件；仅受控本地CLI，非并发不可信上传服务。错误只显示固定错误码与安全字段名，不回显原始不可信内容或堆栈中的敏感值。

## 9. 未来输出/API 固定命名

未来仅新增 `experiments/material_dynamics_v2b2/`；不得编辑B1/Stage1/core。入口 `run.py`，审核入口 `audit.py`，focused入口 `run_tests.py`。CLI具体命令与文件拆分见handoff。

- `manifest.json`：合同/输入schema、源码提交、每个展开输入路径与真实SHA256、命令、所用基线、units、provenance、验证scope；不得将输入自报hash当已经核验。
- `inputs/*.json`：完整展开参数与T knots，不只存patch或defaults引用。
- `timeseries.csv`：scenario_id,tau,T_K,K_tau,d_tau,a_D,b,g,H,S_D,S_B,Da_O2,u_core,u_surface,f_mean,f_max,co2_body,co2_generated,co2_net_out,u_res,v_res,source_rate。
- `profiles.csv`：scenario_id,tau,cell_index,xi_left,xi_right,u,v,f。固定cell边界可复原平均库存。
- `flux_intervals.csv`：scenario_id,tau_left,tau_right,integral_J_u,integral_J_v,integral_q_body。按真实RK阶段累积，每个输出间隔完整覆盖，不以稀疏端点梯形强称同阶精确账本。
- `summary.json`：每情景全部输入、assumptions、units、全部状态维度、各事件{tau,bracket_tau,status}、氧预算、scope与not_modelled；provenance=synthetic_assumption。physical_time_seconds=null，physical_time_status=uncalibrated。
- `screening.csv`：负荷/程序/联合包/长度、原始指标、两阈值、guard、数值覆盖（verification_scope与numerical_validation分别输出）、配对方向、condition_key、screening_status、mapping_status；完整列清单由JSON矩阵要求，不加入供应商分数。
- `audit.json`、`verification.json`、`test_results.json`：实测通过/失败及固定容差，实际命令退出码、验证域、跳过原因；不预填PASS。
- `resources.json`：active_budget_seconds,ceiling_budget_seconds,elapsed_wall_seconds,peak_rss_mib,workers,threads,phase,completed_scenario_ids,pending_scenario_ids,status。
- `THERMAL_DIAGNOSTIC_REPORT.md`：中文、三层事实标识、条件方向/反例、U0/U1包络及未覆盖域、数值失败与材料失败分开。
- `thermal_profiles.svg`、`conditional_screening.svg`：浅色、静态、数据坐标来自CSV，标“无量纲假设研究，非工厂配方或烧成时长预测”；不含脚本、事件属性、foreignObject、外链或外部字体。缺失事件标未发生，不画0时间柱。

CSV数字均使用足够精度（建议17位有效数字），不存在值留空，JSON用null并配status；NaN/Infinity不得序列化。所有u/v/f/Γ/K/d/ell/rho/积分/Da/τ单位为1，T_K为K；source_rate为参考库存/无量纲τ。wall_seconds只是计算资源遥测。

### 9.1 跨阶段证据绑定补正建议（pending_manager_decision）

已核缺口：旧§9有源码/输入hash、原始数据及验证文件，旧handoff§5将180s demo与300s tests拆开，却未定义run.py如何读取后者证据或何时重算报告；仅凭这些文件名不足以断言闭环。

唯一建议方案`B2-BIND-001`：先在300s内运行既有focused/reference/convergence，再在180s demo命令增加可选`--verification validation/tests001/verification.json`。不加求解case、不加预算、不增加报告重跑阶段；证据读取、当前数据audit、状态合并、筛选、报告仍计入原180s。缺省不提供该参数的demo只能生成未验证诊断报告。完整CLI、文件字段、身份计算与拒绝规则见handoff§5.1、矩阵`evidence_binding_proposal`；此方案尚需Manager明确决定，不由Engineer临时设计API。

最终报告必须把当前raw结果、当前受审源码/测试/合同快照、本版完整展开输入内容与真正执行的验证覆盖绑定在一起，并可追溯到实际命令、退出码、误差/原始参考和证据文件实算hash；不能仅按scenario_id、旧artifact的pass、自报hash或audit成功升为passed_frozen_suite。不同源码/合同版本的旧证据不继承，即使数值参数未变。代表收敛覆盖与逐例审计仍是不同证据层，Safety独立批准仍另行执行。绑定建议未获决定期间，默认维持not_run、不输出正式sampled候选。

## 10. 资源、审批、回滚

资源为合同上限而非性能承诺；任务提供主机约束1核6GB，本轮未运行系统命令核验主机。B1 Safety记录演示34.947s、41.285MiB，focused约65s，是参考而非B2测量。

未来全流程串行、worker=1/thread=1、仅stdlib；每次演示含导出/审计/报告active预算180s，ceiling180s；focused+指名解析/收敛总预算300s；Safety独立流程总预算600s；任何角色单次本地验证累计墙钟预算900s，不自动重试全套。默认演示情景上限24；指名额外求解调用上限40；N≤31、每情景接受/拒绝步总数≤1000000、峰值RSS≤512MiB、复现包≤20MiB（不含已有B1包和原文）。原始记录可压缩但不可删必要数据。实际超预算partial/exit3，内存/步数资源限额为resource_limit/exit3；若不足只能Manager修订，不升配或并行。

必须沿用并改正 B1 LOW 注意项：若复用CLI，active_budget_seconds和ceiling_budget_seconds在成功、解析失败、数值失败、timeout路径都分别记录；`--budget-seconds 0.000001`必须真实触发partial/timeout/exit3且active为实际输入，ceiling仍180。不得沿用失败遥测仅显示180.0的歧义；不得在本卡改B1。

预算参数本身无法解析时active_budget_seconds=null、reason=budget_parse_rejected，ceiling=180；不回显非法原值、不默认180为active。安全输出路径尚未成立时只向stdout/stderr写结构化安全失败遥测，由测试harness在自己的安全目录留存；不能为了记录失败而创建越界目录。

审批顺序：
G0：Manager读回三个冻结文件，确认版本、假设域/浓度边界/无真实秒数/预算，另行派Engineer；本任务不创建后续卡。
G1：Engineer隔离实施与自验完成不等于通过；源码/测试/数据/复现包闭合后交独立Safety。
G2：独立Safety真实重跑指名域、审查科学和权限边界，给明确approved/approval_scope/production_approved=false；Manager再决定后续研究。
G3：任何生产实验/控制、外发/公开发布、部署、费用、删除或模型范围扩展均需另行人工审批，当前均未授权。

回滚：当前只是scratch文档，无部署需要回滚。未来隔离模块失败则停止使用并保留证据；要撤回提交由Manager批准revert，不reset历史、不删除B1、不移动旧分支。

## 11. 待 Manager 确认与完成定义

建议G0接受本唯一默认方案，不把未解决材料参数变成实施前必须获取的现场数据。仍需Manager明确接受：
- synthetic给温/固定浓度边界，而非恒压空气或能量闭合。
- U0/U1和离散筛选是机制包络，不是概率覆盖或实际供应商筛选。
- 基线严格为已审d051c0982835dbe54fc4f509f1819661b85de055；未来独立branch/worktree路径由Manager派卡确认，本Planner不创建。
- 计算预算若实际不足，停止、汇报，重新冻结而非扩算。
- `B2-BIND-001`的tests先行、run.py可选--verification及文件身份/覆盖绑定方案：`pending_manager_decision`；本补正不自行批准G0。

本规划完成=三个文件真实保存且相互引用、来源读回与限制完整、JSON语法通过文件工具检查、全部验收项有稳定ID/证据/方法/阻断性/scope，并交Manager review。不是B2已经通过数值验证。未来研究实现完成=JSON所有适用blocking门有真实证据，复现包完整，独立Safety明确批准对应研究scope；产品/生产始终未批准。

## Sources 与定位

编号沿用已读Manager台账 stage2a-manager/citations.json；本轮按同一文献标识保留，不创造新编号。本轮无terminal执行接口，未运行sources.py引用校验/数学脚本；来源定位通过read_file/web_extract实际核读，不能把它写成自动引用门PASS。

[1] https://www.mdpi.com/1996-1944/14/17/4942
- S02；原文缓存S02-primary.txt:121–150（§4.2–4.4、Table4）；短证据：“was limited to a temperature range from ambient to 500 °C”。
[2] https://www.mdpi.com/1996-1073/17/21/5382/htm
- S09；本轮该/htm请求失败，canonical页面 https://www.mdpi.com/1996-1073/17/21/5382 成功取得正文；§2、§3.1、Eq6–15、Table5。短证据：“Heating to the target temperature was carried out in a nitrogen atmosphere at a heating rate of 50 K/min”。
[3] https://orbit.dtu.dk/files/418782101/1-s2.0-S2214509525011854-main.pdf
- S11；仅核读Manager保存方法摘录S11-method-excerpt.md:4–18；短证据：“the maximum firing holding time was 3 h.”；本轮未重抓全文或检查SEM图像。
