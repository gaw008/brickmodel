# Arlabosse 湿态共同热力学：有限设计审查

日期：2026-09-12。范围是固定液相机械压力1 bar、35–95°C、W=0.15–0.8 kg水/kg干物的声明研究模型。温压/含水范围是本次研究选择，不能称为湿样实测有效域。本轮只读实际API、既有原件阅读记录与候选公式；没有构造水对象、运行EOS/积分/测试、新搜索或生产修改。

**结论：支持这个有界近似的实施。未发现候选过量势的热力学代数错误；应交付给定W的定压H→T反解、实际供热/蒸气携焓账与95°C源q复现。** 接入后仍是条件探索模型，不能称已验证的湿料状态方程、干燥时钟或全周期材料。实测误差未知不构成实施阻塞。以下单位、参考、源值与模型值分离及反解约束应在实现中明确。

## 1. 已核实际API，不另造水参考

构造一个 `WaterChemicalPotential(source_directory, backend=..., backend_manifest=...)`，复用其 `vapor` 和 `reference`：

| 实际接口/字段 | 本方案的用途 |
|---|---|
| `chemical.equilibrium_at_liquid_tp(T, 100000)` | 返回 `WaterPhaseEquilibrium`；采用其 `liquid`、`vapor`、`equilibrium_partial_pressure_pa`、`phase_enthalpy_difference_j_mol`。液相机械压为1 bar，不能换成水汽分压。 |
| `chemical.liquid_tp(T, 100000)` | 得液体摩尔h/s/μ及底层 `state`；若该次计算不需要平衡压，可直接用此公开入口。底层按稳定液体TP做域检查，异常应传播。 |
| `chemical.vapor.enthalpy_j_mol(T)` | `IdealWaterVapor` 的已对齐理想水汽h；不需要用真实水汽 `state_tp(T,1bar)`，后者在研究温区可能请求不稳定汽相。 |
| `chemical.ideal_vapor(T, pv)` | 在明确正水汽分压下返回摩尔h/s/μ，用于模型平衡回代；pv不是液体机械压。 |
| `chemical.reference.molar_mass_kg_mol` | 同一M供全部 mol↔kg 转换；不要另取另一版水分子量。 |
| `chemical.gas_constant_j_mol_k` | 固定 CODATA R=8.31446261815324；本模型使用 `R_s=R/M`。不是原生IAPWS的质量R。 |

建议采用同一返回字段转换：`h_l=liquid.enthalpy_j_mol/M`、`g_l=liquid.chemical_potential_j_mol/M`、`s_l=liquid.entropy_j_mol_k/M`、`cp_l=liquid.state.cp_j_kg_k`；`h_v=vapor.enthalpy_j_mol/M`。因此 `L=phase_enthalpy_difference_j_mol/M=h_v-h_l`，单位J/kg水。

焓已经含所有水相共用的NIST能量偏移，不能重加。熵仍是原生IAPWS参考，不能称NIST绝对熵。现有化学模型固定标准压力 `reference_pressure_pa=100000`，其标准熵取原生理想项，而压强对数项用登记R；API明确不允许任意改该标准压力。本候选保持这一完整派生模型，不改原水EOS常数、Cp或系数。

液相1 bar是当前研究条件；蒸气是理想组分标准/分压状态，不需要在1 bar存在稳定纯蒸气。无载气库存/流量模型时，不将这段热力学计算冒充一个已构造的真实干燥器。

## 2. 候选势的代数检查

以下 `H,G,S` 均为每kg干物的湿体系量，`m0,b0,mu_ex` 为每kg水的偏比量。令 `T0=368.15 K`：

```text
m0(W) = R_s T0 ln aw0(W)
b0(W) = L(T0,1bar) - q0(W)
Gex0(W) = integral[W*=0.8 -> W] m0(w) dw
Hex0(W) = integral[W*=0.8 -> W] b0(w) dw
Sex0(W) = [Hex0(W)-Gex0(W)]/T0
Gex(T,W) = Hex0(W)-T Sex0(W)
mu_ex(T,W) = dGex/dW = (T/T0)m0(W)+(1-T/T0)b0(W)
H_ex = Gex-T*dGex/dT = Hex0(W)
Cp_ex = dH_ex/dT = 0
```

于是 `H=h_d+W h_l+Hex0`、`G=g_d+W g_l+Gex` 相容，且：

```text
Cp_dry_basis(T,W) = cp_d(T)+W cp_l(T,1bar)
Cp_wet_basis = Cp_dry_basis/(1+W)
h_water_partial = (dH/dW)_T = h_l+b0(W)
q_model(T,W) = h_v-h_water_partial = L(T,1bar)-b0(W)
q_model(T0,W) = q0_interpolant(W)
dq_model/dT = cp_v-cp_l                  [fixed P,W]
dmu_ex/dT = (m0-b0)/T0
mu_ex-T*dmu_ex/dT = b0
```

这落实作者湿Cp加和式所采用的零过量热容近似，且没有把解吸热重复放到一个额外外热源中。零过量Cp/温度不变的偏比过量焓是模型假设，不能叫同湿样实测导数。q95复现属于用于构造模型的数据约束复现，不是独立现实验证。

W*=0.8只选积分参考，令该点积分值为零；**不意味着该点aw=1、b0=0或水已经不受束缚**。固定干质量下，与W无关的相容H/S参考常数不改变水偏比性质或去水热量；无需新原泥绝对生成焓。

`ArlabosseDryCaloric` 只有 `cp(...)` 和 `delta_h(...)`，没有干物G/S API。若必须输出总G，可用该原式的解析熵差：若 `cp_d(T)=A+B T`，其中 `A=1434-3.29*273.15`、`B=3.29`，则 `s_d(T)-s_d(Tref)=A ln(T/Tref)+B(T-Tref)`；干物h/s参考可明确选零，再令 `g_d=h_d-Ts_d`。这是同一Cp积分和参考选择，不是新的实测熵/形成自由能。若只交付H反解与水化学势，无需增加总G getter，但内部过量势定义仍应保存。

## 3. aw与平衡压桥接的来源含义

用现有模型得到 `p_eq,pure(T,1bar)`，定义：

```text
a_model(T,W) = exp[mu_ex/(R_s T)]
p_eq,sludge_model = p_eq,pure * a_model
mu_v,mol(T,p_eq,sludge_model)
    = mu_l,mol(T,1bar) + M*mu_ex(T,W)
```

这是现有理想水汽对数压强关系的直接结果。**μ_ex是J/kg水；现有chemical结果是J/mol水，两者不可直接相加。** 必须乘同一M，或全程统一为质量基。

保持 `a_model(T0,W_i)=aw_source(W_i)` 是将源活动度数值赋给本派生标准态的建模约定。源方法的样品平均温度/湿度、理想蒸气解释、真实纯水标准与当前纯液体1bar/理想汽平衡压的差异，属于未量化模型/适用性误差。不能声称原论文实测了当前模型的平衡压，也不能把 `p_eq,pure` 命名为原生精确psat。

没有必要再混入原生饱和压、额外Poynting系数或原生R来“纠正”这个已声明桥接；那会引入另一个模型并需要重新核对G/H/熵。当前方案在使用既有API的前提下假设较少。更少假设的交付边界是只报告相对化学势/H/q；若输出压力，保留模型平衡分压的明确名称与上述unknown，不能称实测压力。

## 4. 节点、连续性与允许的检查

本域内aw有8个已读节点（0.15/0.20/0.30/0.40/0.50/0.60/0.70/0.80），q有6个（缺0.50/0.60）；原0.10在本域外。**m0用aw自己的节点，b0用q自己的节点即可，不必丢弃可读aw。** m0必须按预定方案线性插值已经取对数的量，不能悄悄改成先线性插值aw再取对数。b0线性等价于q线性，因为L0与W无关。积分和分段处理使用两套节点的并集。

Gex0/Hex0分段二次且一阶连续，mu_ex/b0连续；节点处二阶W导数可跳，不应用跨节点中央差分声称不存在的光滑性。0.50/0.60处的q是明确模型插值，原事实的unknown仍不变。0.10处连模型值都不得外推。

35–95°C是声明试算温区，尚未由本轮数值检查确认全域性质。执行时至少核对 `Cp>0`、有限正a、目标模型是否满足 `a<=1` 及组成稳定性 `dmu_water/dW>=0`。因为mu_ex在T上线性、在各联合W段的斜率为常数，名义组成稳定性可检查各段在温区端点的斜率；节点用两侧斜率。若失败，应报告失稳/域限制或重新审查模型，不clip、不隐藏平滑。原始读图误差不能冒充温度延拓误差。

## 5. 定压H→T与蒸气携焓：必须交付的闭合

H→T的输入须有**已知W、固定正干质量（或明确每kg干物归一化）和目标H**。一个H不能同时识别未知T与W。对固定W，`dH/dT=cp_d+W cp_l>0`，可在 `[308.15,368.15] K` 做受控单调反解；目标超出端点焓范围即拒绝，不夹回端点。若使用大负值的水形成焓参考，残差宜在相同W下作锚定焓差以减少相消，但物流焓必须保留同一参考。可利用干物正Cp给反解条件下界；数值残差/温度括号不等于物性或模型不确定度。

设 `m_d` 固定，只有水汽流出，`dm_out=-m_d dW`，无其他功和物流。恒定外压下若采用通常焓开放系统账（边界pV功由H处理），第一定律为：

```text
dQ = m_d dH + h_v dm_out
   = m_d[(cp_d+W cp_l)dT - q_model(T,W)dW]
Q_ab = m_d[H(Tb,Wb)-H(Ta,Wa)]
       - m_d integral[Wa -> Wb] h_v(T(W)) dW
```

这里不是H=U，也没有忽略一个待补的体积功；本方案仅限上述定压焓系统。去水Wb<Wa时，恒温段所需Q为 `m_d integral[Wb -> Wa]q_model(T,W)dW`。已在H中包含Hex0，故不能再加一次q或latent到第一行右侧。

建议一次交付三段受控路径：固定高W升温到95°C→95°C去水跨越至少一个q分段→固定低W冷却。升/降温段无出水；95°C去水段hv常数、q分段积分可解析，独立账应同时核对水量、ΔH、蒸气携焓与Q。这能实际检查非等温储能反馈和变含水能量账，不需要假定干燥速度、孔容或扩散系数。每段末态以输入Q/已知W反解T，不能只前向造H再写固定温度结果。

需保留的负控/区分：去掉b0或重复加latent会破坏q95/能量账；kg/mol混用应被识别；W/T/P域外及目标H越界拒绝；改变W*但保持同一参考转换后可观测热量不变；q源unknown与模型插值分别报告。独立反解/热账oracle应从上述解析关系组织，不能直接用被测求解器输出为真值。95°C只要求在6个源q节点复现名义值与明确的读图传播，跨节点值不是新增测量。

## 6. 不确定性与审查版本

误差至少分数值误差、源读图传播、插值/零过量Cp/标准态映射等模型误差。后者与源实验误差目前unknown，允许实施但不授予预测精度；不设主观统计置信区间。原图共享轴校准导致节点相关，原aw/q实验关系也不等于独立高斯样本。若用逐节点盒传播，可声明保守包络，不能称独立随机实验误差或自动认为覆盖模型偏差。

实际核读版本SHA256：

| 文件 | SHA256 |
|---|---|
| `src/sludge_sandbox/water_chemical_potential.py` | `2683bb786ad5e5b6648c02a3d5e9b9671f595820ab4a781e29808c3a95f80767` |
| `src/sludge_sandbox/ideal_water_vapor.py` | `e30b7470e50942f56fffe3fec79dde61e347fc1ac40dd62f3fd2bb66425e86b5` |
| `src/sludge_sandbox/water_properties.py` | `b374ea87873815a4d8959823a3323d29ce70d6c5ce0b706ba1a81f2b9437d8b6` |
| `src/sludge_sandbox/arlabosse_caloric.py` | `42e828e640bdc10d69dd7195cba7440e5851096e23a9a933e080e98211ab6ca3` |
| `data/sandbox/water/reference_alignment.json` | `fc817045502f2158543e930eed1e3b911a295ee799597636133302ddc5f019c1` |

辅助核读 `docs/sandbox/WATER_CHEMICAL_POTENTIAL.md`、`IDEAL_WATER_VAPOR.md`、`docs/sandbox/research/arlabosse95/SOURCE_AND_CODE_REVIEW.md`、冻结facts、前轮FEASIBILITY/BLOCKER_AUDIT。Ferrasse2004来源解释沿用此前实际读过的作者上传全文文本（printed1366、1368–1369与§3.2）；本轮未重新访问该正文、未看其PDF页图。Arlabosse Eq1/2沿用前轮原图实际查看结果。没有把既往测试记录写成本轮新跑结果。

最终建议：**按上述边界进入实现与数值验收，不再等待新实测误差条；固定P的H/μ共同闭合可以研究，实际干燥时间、U动态、孔容/压力反馈、反应与全周期仍不在本项结论内。**
