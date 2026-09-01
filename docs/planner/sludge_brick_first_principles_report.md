# 污泥烧结砖第一性原理 Virtual Materials Engine 与 Inverse Feedstock Design 架构报告

版本：0.1（Engineer-ready 设计稿）  
定位：research / design proposal，不是生产控制指令，也不声称已校准到本厂。

## 0. 结论先行

1. **可以在不先做本厂现实试验的前提下启动。** 建议实现一个双层模型：`L0` 为 lumped、守恒约束的快速 world model，用于 10²–10³ 个 synthetic sludge fingerprints 的筛选；`L1` 为砖坯半厚度方向的一维 finite-volume 反应-传热-传质模型，用于候选复算。初始参数来自公开热化学数据、论文区间、理论 bounds 和显式标记的 synthetic policy bounds。现实试验只作为以后缩小不确定性的可选升级，而不是启动门槛。
2. **真正由定律决定的是约束结构，不是所有材料常数。** 元素/质量守恒、能量守恒、化学势极小条件、Fourier/Fick/Darcy 形式、动量平衡和量纲关系可直接写出；反应 `A,E_a,f(α)`、氧化物液相 Gibbs 模型、黏度、表面能、孔隙连通性、强度-孔隙关系以及窑壁换热系数需要公开常数、模型闭合或不确定区间。绝不能把这些闭合关系伪装为“从宇宙定律唯一推出”。
3. **目标应是稳健 specification window，而不是唯一污泥配方。** 反问题天然 many-to-one：不同矿相、粒径、污泥占比、预处理和窑车速度可产生相近的最终孔隙/相组成。输出应是 Pareto set、feasible window、约束裕量和 uncertainty bands，而不是一个“保证高质量”的点。
4. **本厂主要工艺决策变量是窑车速度。** 模型不把窑温曲线当作可任意控制变量，而把已有隧道窑的空间气氛/温度边界 `T_g(s), y_O2(s), h(s)` 视为固定地图，并通过 `s=s₀+v_car t` 将速度映射为砖坯经历的时间历程。
5. **本 MVP 可替代研发早期的大量盲试，但不等价于现实宇宙。** 它适合排除明显不守恒、液相过多、排气受阻、热应力过大或反应不充分的区域，并给出下一步优先级；在没有本厂 phase/property/BC 校准时，不得把预测强度、排放或速度窗口直接用于合规声明或生产控制。

## 1. Objective、non-goals 与使用场景

### 1.1 Objective

给定：

- 可设计的虚拟污泥 fingerprint（元素库存、矿物相、organic pseudo-components、含水率、PSD、sphericity/aspect ratio）；
- 固定页岩/煤矸石基体；
- 干基配比、成型条件；
- 隧道窑固定空间边界及可调窑车速度；

计算：局部温度、反应程度、气体释放、平衡/受限相组成、液相、孔隙、收缩、热/烧结应力、缺陷风险及质量 proxies；反向搜索污泥 specification、掺量、预处理和速度窗口。

### 1.2 Non-goals

- 不做逐批来料预测，也不假设逐批污泥一致。
- 不在本任务中实现 3D 窑炉 CFD、原子级 DFT 或全砖相场。
- 不声称 water absorption proxy 等于标准试验值，不声称 strength proxy 是合格证据。
- 不自动写入 PLC、变频器、窑车控制或生产 recipe。
- 不创建 OCI 资源、不调用收费 API、不依赖商业 CALPHAD 数据库。

### 1.3 User stories

- 材料研发者定义一个 synthetic sludge design space，筛出在多目标约束下稳健的 composition/morphology windows。
- 工艺工程师固定现有窑的空间边界，只比较候选污泥在不同 `speed_ratio` 下的反应完成度、排气压力 proxy、收缩梯度和风险。
- 决策者查看 Pareto frontier：污泥利用率、质量裕量、能耗/停留时间 proxy、气体风险和 epistemic uncertainty 之间的权衡。
- 后续如获得公开新参数或本厂自愿采集的数据，只替换 parameter pack，不重写方程和 API。

## 2. 已验证事实、合理推断、待验证假设

### 2.1 已验证事实

- 原始污泥制砖研究观察到，污泥比例会影响收缩、吸水率和抗压强度，烧失量主要与污泥有机质燃烧有关；该研究给出的具体 10%/880–960 °C 结论仅属于其材料与试验域，不能移植成本厂常数。[1]
- 含污泥陶瓷烧成会产生需要显式建模和控制的 VOC；已有研究用 bench-scale furnace 与 GC/MS 监测烧成排放，因此把气体释放仅当作“消失的质量”是不充分的。[2]
- 两种污水厂污泥的 TGA 研究显示主要热解失重位于约 230–500 °C，并用 conversion-dependent apparent kinetic parameters 重建过程；这支持使用多步/分布参数 kinetics，而不是一个通用单步常数。[3]
- 高岭石脱羟的公开研究用 modified Arrhenius kinetics，并显示样品、结构无序、升温率和水蒸气分压都会影响结果；其两样本得到 F3 mechanism 和 35–60 kcal/mol 的区间，说明单一 `E_a` 需要作为不确定参数，而非定律常数。[4]
- NIST-JANAF 提供标准生成焓、Gibbs 生成能、热容、熵等随温度变化的数据；NASA CEA 使用超过 2,000 个物种的数据库计算化学平衡及热力学/输运性质。[5][6]
- SOVS continuum constitutive relation 已用于陶瓷烧结的收缩和相对密度演化；独立研究还表明温度场非均匀性可能成为不可忽略的烧结预测误差源。[11][22]
- 相场可表达界面能、扩散、刚体颗粒运动并与应力、温度等场耦合，但属于 mesoscopic high-fidelity 路径，不适合当前 1 OCPU/6 GB 的 screening 内环。[12]

### 2.2 合理推断（模型选择）

- 砖坯横截面相对于隧道长度很小，若窑边界只提供空间 profile，则用 brick half-thickness 的 1D L1 捕获内部热/气体梯度，比全窑 3D 更符合当前资源和 inverse-search 需要。
- 有机质 burnout、碳酸盐分解和黏土脱羟时间尺度相差大，且与热扩散耦合，方程通常 stiff；因此 L1 采用 method-of-lines + BDF/Radau 比显式固定步长更稳妥。SciPy 官方将 BDF/Radau列为 stiff IVP 方法，并允许 sparse Jacobian。[16]
- 相平衡只能给“在给定 T/P/元素库存下允许的低 Gibbs 状态”，不能给有限时间内实际到达程度；故需 `equilibrium target + kinetic relaxation/independent reactions` 的混合框架。

### 2.3 待验证假设（默认可运行，但必须在输出中暴露）

- 单砖半厚度 1D 对筛选足够；孔洞、码放接触和边角效应由 model-discrepancy interval 包络。
- 窑在筛选周期内可视为 stationary spatial map；速度变化不反向改变全窑燃烧流场。
- 孔隙气体近似 ideal gas，外表面近大气压；高 overpressure 候选会被风险约束剔除。
- 元素候选集和 condensed-phase candidate list 足以覆盖设计域；数据库缺失相会触发 coverage flag，而不是静默归入“其他”。
- 固定页岩/煤矸石输入本身可由一个公开或 synthetic parameter pack 表示；其真实值未知时输出是设计空间研究，不是本厂预测。

## 3. 第一性原理层级：哪些能推导，哪些必须闭合

| 层级 | 数学骨架 | 可由定律确定 | 仍需数据/近似 | MVP 处理 |
|---|---|---|---|---|
| 元素/质量守恒 | `A n + b_gas = b₀` | 守恒、化学计量矩阵 | 初始元素库存、pseudo-species 组成 | 每步投影/残差检查 |
| 能量守恒 | enthalpy balance | 能量收支与单位 | `c_p(T), k(T,φ), ΔH_r, h, emissivity` | 公开数据+interval |
| 热力学 | `min G(T,P,n)` s.t. `A n=b` | equilibrium criterion | species Gibbs、solution/liquid model、candidate phases | pure-phase/ideal-solution screening；coverage flag |
| kinetics | `dα/dt=A exp(-E/RT)f(α)g(p)` | Arrhenius 形式不是参数值 | `A,E,f,g` 与 mechanism | source ensemble / log-bounds |
| 传热/传质 | Fourier/Fick/Darcy | conservation + flux form | effective properties、tortuosity、permeability | closure ensemble |
| 颗粒堆积 | 几何不可穿透、体积分数 | 几何约束 | 实际压实、形貌、摩擦 | Yu–Standish 类 packing closure + interval；该文建立 PSD→porosity 模型。[14] |
| 烧结致密化 | surface-energy-driven viscous flow | driving-force/平衡形式 | viscosity、surface energy、pore shape | reduced SOVS-inspired law |
| 相场/孔隙 | free-energy gradient flow | variational form | free-energy functional/mobility/interface energy | 仅 L2，不进 MVP 内环 |
| 热应力 | `∇·σ=0`、compatibility | 力平衡 | `E,ν,α_T,strength,damage` | L1 gradient proxy；L2 FEM |
| 最终性能 | density from mass/volume | density identity | open/closed connectivity、strength law、absorption | 明确标为 proxy + interval |

关键诚实边界：NIST-JANAF/NASA CEA 可支撑 pure species 标准态和气相；COD 是开放 crystal-structure 数据源而不是热化学数据库。[5][6][10] pycalphad、Thermochimica 和 Cantera 都有可用的开源 equilibrium 能力，但求解器并不会自动提供适用于页岩-煤矸石-污泥的完整 multicomponent oxide liquid database。[7][8][9] 因而 MVP 的 liquid fraction 是**受数据库覆盖限制的筛选量**，必须同时输出 `thermo_coverage_score`。

## 4. 输入 fingerprint 与规范化

### 4.1 唯一 canonical basis

所有配比先转为 `kg dry solids` basis：

`m_i,dry = m_i,wet (1-w_i)`；`x_i,dry = m_i,dry / Σ_j m_j,dry`。

污泥使用一个不重复计量的 canonical representation：

1. `crystalline_phases`：相的 mol 或 dry-mass fraction；
2. `amorphous_oxide_pool`：用 oxide-equivalent fractions 表示，但在进入守恒矩阵前拆为 elements；
3. `organic_pseudocomponents`：经验式 `C_aH_bO_cN_dS_e`、含量、可选 LHV/ΔH interval；
4. `free_moisture`：独立于 dry solids；
5. trace elements：elemental mol inventory，不与 oxide pool 重复。

校验器必须拒绝：负分数、simplex 不闭合、相与元素重复计量、`d10≥d50`、`d50≥d90`、非法 sphericity、未声明 basis。

### 4.2 可设计变量

`z = {x_sludge,dry, sludge phase/element simplex, organic pseudo-mixture, moisture, d10,d50,d90, sphericity, aspect_ratio, pretreatment_dry_target, grind_d50_target, optional mineral blending, speed_ratio}`。

固定变量：页岩/煤矸石 parameter pack、砖型/半厚度、成型压力范围、窑空间 boundary map。若实际成型压力也可调，可在以后从 context 变量提升为 decision variable。

### 4.3 颗粒到 green body

MVP 不声称仅由 PSD 唯一推出压实孔隙。先由公开 particle-mixture packing closure 计算 `φ_pack(PSD,sphericity)`，再用成型压实系数 `χ_press∈[0,1]` 将其映射为 `φ₀`；二者都保留 model-form interval。Yu–Standish 工作明确研究了 PSD 与混合颗粒 porosity 的数学关联，可作为 closure 候选而非普适真理。[14]

初始 specific surface 以 Sauter diameter `d32` 近似；permeability 使用带可变 `C_KC` 的 Kozeny–Carman 形状：

`K(φ)=d32² φ³/[C_KC (1-φ)²]`，单位 `m²`。[23]

这里 `C_KC` 是 semi-empirical uncertainty，不固定为“宇宙常数”；公开研究也明确指出 Kozeny–Carman constant 并非对所有 porous media 恒定。[23]

## 5. Forward world model

### 5.1 坐标与状态

L1 在 `x∈[0,L]` 上求解，`x=0` 是对称中面，`x=L` 是暴露表面。状态：

- `T(x,t)` [K]；
- `c_g,k(x,t)` [mol m⁻³ pore gas]：`H2O, CO2, CO, O2, N2, VOC_pseudo, SO2, NOx_pseudo`；bulk inventory 为 `φ c_g,k`；
- `α_r(x,t)` [-]：free-water removal、organic devolatilization/oxidation、dehydroxylation、carbonate decomposition、Fe redox、mullitization/solid-state reaction；
- `n_p(x,t)` [mol m⁻³ current bulk]：候选 condensed phases；离散主存储为每个 deforming cell 的 extensive moles `N_p,cell`；
- `ρ_rel(x,t)` [-] 或等价 volumetric sintering strain；
- `V(x,t)/V₀` [-]、`φ_total(x,t)`、`φ_open(x,t)` [-]；
- 可选 `P_g(x,t)` [Pa]；MVP 默认由 quasi-steady Darcy closure 求得；
- cumulative escaped species [mol m⁻²]，用于元素闭合。

Derived fields：liquid fraction、temperature gradient、eigenstrain、stress proxy、gas overpressure proxy、reaction heat、bulk density、open-porosity water-absorption proxy、strength proxy、defect risks。

### 5.2 元素守恒

设 `A_ej` 为 species/phase `j` 中元素 `e` 的原子数；solid phase concentration `n_p` 以 current bulk volume 为基准，pore-gas concentration `c_k` 以 pore volume 为基准：

`b_e(x,t)=Σ_p A_ep n_p(x,t)+φ(x,t)Σ_k A_ek c_k(x,t)` [mol m⁻³ current bulk]。

令 `X` 为 reference coordinate、`F` 为 deformation gradient、`J_def=det(F)=V/V₀`；MVP 的 reduced isotropic closure 取 `F=J_def^(1/3) I`，各向异性变形留给 L2。含气体输运的 deforming-domain 守恒式为：

`∂(J_def b_e)/∂t + Div_X[J_def F⁻¹ (Σ_k A_ek J_k)]=0`。

当 `F=I,J_def=1` 时退化为熟悉的 current-coordinate 形式 `∂b_e/∂t+∇·(...) = 0`；离散实现以 cell extensive inventory 为准。

离散验收：每元素的

`R_e = [inventory(t)+cumulative_outflow-inventory(0)] / max(inventory(0),ε)`

必须小于配置 tolerance；热化学 equilibrium 每次都受 `A n=b_available` 约束。

### 5.3 反应 kinetics 与 equilibrium coupling

每个独立反应：

`r_r = c_r,0 A_r exp[-E_r/(R T)] f_r(α_r) g_r(p_O2,p_H2O,p_CO2)` [mol m⁻³ s⁻¹]，

`∂α_r/∂t = r_r/c_r,0`。

默认 `f_r=(1-α_r)^n`；可逆分解使用 `g_r=max(0,1-Q_r/K_eq,r)`；复杂有机质用 2–4 个 pseudo-components 或 distributed-activation quadrature。污泥 TGA 文献支持 conversion-dependent kinetics 和主要 230–500 °C decomposition window，但参数必须随 source pack 改变。[3]

平衡 target：

`n_eq = argmin_{n≥0} G(T,P,n)=Σ_j n_j μ_j(T,P,n)`，subject to `A n=b_available`。

实际 condensed phase 不瞬时跳到平衡，而用：

`dn_p/dt = (n_eq,p-n_p)/τ_p(T,PSD)`, 并限制其不违反元素库存。

这样明确区分 equilibrium feasibility 与 finite-rate accessibility。Cantera 官方提供 multiphase `vcs/gibbs` equilibrium 接口；Thermochimica 针对给定 composition/T/P 求相与组成；pycalphad 是 CALPHAD Python 库。[7][8][9]

### 5.4 气体传质与 pressure

对 pore-gas species `k`：

`∂(J_def φ c_k)/∂t + Div_X{J_def F⁻¹[c_k u_g - φ D_eff,k ∇c_k]}=J_def Σ_r ν_kr r_r`。

`D_eff,k = D_k φ^m/τ`；`u_g=-(K/μ_g)∇P_g`。

理想气体闭合 `P_g=R T Σ_k c_k`；为避免高成本，MVP 可每个 time step 解一个 quasi-steady pressure correction。若关闭 Darcy，只允许在 `max ΔP` 很小的候选上使用 diffusion-only，并打 flag。

### 5.5 能量守恒

采用 bulk enthalpy 形式：

`∂(J_def H)/∂t = Div_X[J_def F⁻¹(k_eff∇T-Σ_k h_k J_k)] - J_def Σ_r ΔH_r r_r`。

若 shrinkage 对几何/浓度影响可忽略、`J_def≈1`，才可改写为显热近似：

`(ρ c_p)_eff ∂T/∂t = ∇·(k_eff∇T) - Σ_r ΔH_r r_r - Σ_k h_k ∇·J_k`。

符号约定：`ΔH_r>0` 为吸热，故 source 为负。latent heat 应放在 `H` 或 reaction term 之一，不能双计。`k_eff` 可用 Maxwell–Eucken 与另一 closure 构成 model ensemble；ORNL 比较研究指出不同 pore morphology 可使 effective-medium 预测显著变化，因此 morphology discrepancy 必须传播到输出。[15]

### 5.6 边界与初值

中面 `x=0`：

- `∂T/∂x=0`；
- `∂c_k/∂x=0`；
- `∂P_g/∂x=0`。

表面 `x=L`，外法向 `n`：

`n·(-k_eff∇T)=h(s)[T_s-T_g(s)] + ε_rad σ_SB[T_s⁴-T_wall(s)⁴] + Σ_k h_k n·J_k`；

`n·J_k=k_m,k(s)[c_k,s-c_k,∞(s)]`；`P_g=P_ambient`（pressure solve）。

隧道窑 mapping：

`s(t)=s_entry+v_ref·speed_ratio·t`；

`T_g(t)=interp(T_g_map,s(t))`，O₂、壁温、`h,k_m` 同理。若 map 只给 O₂，synthetic MVP 以 `N₂=1-O₂`、其他 ambient species 为零闭合；真实含湿/燃烧气氛必须显式提供。速度是主要操纵量；空间 map 默认固定，禁止 optimizer 任意改每个温区温度。

初值：`T=T_entry`，气相与入口气氛平衡或指定，`α_r=0`，`n_p` 为输入矿相，`φ=φ₀`，`P=P_ambient`。

公开 clay-drying 研究同时讨论 lumped 和 distributed 模型，并明确 distributed model 才能解析内部温湿梯度；这支持 L0/L1 分层，而不支持把 L0 当最终 stress solver。[13]

### 5.7 致密化、孔隙与收缩

MVP 使用 SOVS-inspired isotropic reduction：

`dot ε_v,s = -P_s(ρ_rel,γ,d32,f_liq) / K_v(T,ρ_rel,f_liq)` [s⁻¹]；

`K_v = η_ref exp(Q_η/(R T)) ψ(ρ_rel,f_liq)` [Pa·s]；`P_s≈γ/d_eff · p(ρ_rel)` [Pa]。

`dV/dt=V dot ε_v,s`；`linear_shrinkage=1-(V/V₀)^(1/3)`。

以当前 bulk volume 为基准的相体积分数 `v_s=Σ_p n_p M_p/ρ_p`（`n_p` 必须随 current cell volume 重算，而非把 reference concentration 固定不变），总孔隙：

`φ_total = clip(1-v_s,0,1)`。

`φ_open = φ_total C_open(φ, gas_generation, sintering_state)`，其中 connectivity 是 closure。该构造保证 phase mass/volume 与 shrinkage 一致；不得同时另加一个独立经验“孔隙损失”而双计。SOVS 用于陶瓷收缩/相对密度已有公开实现研究，但材料黏度仍需 source pack。[11]

### 5.8 热应力与 defect risk

完整力学为：

`∇·σ=0`；`σ=C(T,φ):(ε-ε_th-ε_sinter-ε_phase)`。

L1 自由半板不能还原孔洞、边角和码放约束，因此 MVP 输出 engineering proxy：

`σ_proxy(x)=E_eff/(1-ν_eff) · [(ε_th+ε_sinter)-(其截面平均)]`。

风险均为无量纲，并保留阈值来源：

- `R_crack=max(tensile(σ_proxy))/strength_proxy`；
- `R_warp=max(eigenstrain)-min(eigenstrain)` 再除以允许差；
- `R_bloat=max(P_g-P_ambient)/P_allow` 与 `gas_Damkohler`；
- `R_underfire=1-min(required α_r)`；
- `R_overfire=max(f_liq/f_liq_allow, η_allow/η_liq)`；
- `R_efflorescence=mobile_salt_inventory/limit`，若 hydration/solubility data 缺失则输出 `unknown`，不得输出“低风险”。

完整 2D/3D stress 可在本地 PC 使用 FEniCS/DOLFINx；官方示例支持 variational nonlinear elasticity 与自动 Jacobian。[21]

### 5.9 性能 proxies

- `ρ_bulk = final_dry_mass/final_volume` [kg m⁻³]，为守恒派生量；
- `WA_proxy = 100 ρ_water φ_open/ρ_bulk` [mass %]，只是假设可达开孔全部充水的上界/近似；
- `strength_proxy = σ_dense exp(-b φ_open)·(1-D_crack)` [Pa]，`σ_dense,b` 是 empirical uncertain parameters；
- `k_brick` 来自 morphology-aware effective-medium ensemble；
- phase/liquid/porosity/shrinkage/gradient/pressure 输出为 fields + summary quantiles。

若 strength 或 absorption closure 未有可接受 source pack，inverse design 仍可对 phase/porosity/shrinkage/stress-ratio 做筛选，但强度/吸水约束状态必须为 `unresolved`。

## 6. 建模精度路线比较与选型

| 路线 | 方程/空间 | 作用 | 优点 | 主要损失 | 当前机器 |
|---|---|---|---|---|---|
| L0 Screening | lumped enthalpy + multi-step ODE + equilibrium lookup + algebraic packing/sintering | 10²–10³ fingerprints | 快、守恒、适合 UQ/inverse search | 无内部梯度；stress 仅 Biot/gradient bound | 必须实现 |
| L1 Refinement | 1D half-thickness finite volume，heat/mass/kinetics/pressure + reduced sintering | shortlist robust ranking | 捕获中心-表面 lag、排气与 shrinkage gradient | 忽略孔洞/边角/码放三维效应 | 必须实现，串行小网格 |
| L2 Research | 2D/3D CFD/FEM + SOVS/phase-field + kiln flow | 局部机理/最终设计复核 | shape、contact、warpage、pore evolution 更真实 | 参数与计算量巨大，不适合 inverse inner loop | 后续本地 PC |

选择：MVP 同时交付 L0+L1，不在 current OCI 实例安装/运行 OpenFOAM 或 DOLFINx。OpenFOAM 是 GPL 开源、可处理流动、热、热力学和化学的 Linux CFD 平台，适合作为 L2 候选；phase-field review 显示其可与温度和应力耦合，但不应伪装成低成本筛选器。[12][20]

## 7. 数值求解顺序

### 7.1 Parameter-pack preprocessing（一次性）

1. 读取 species/phase schema，构建 element matrix `A`，检查 rank 与重复计量。
2. 将 NIST-JANAF/NASA polynomial 或表格转为统一 `G,H,Cp(T)` evaluators；记录 license、URL、temperature validity。
3. 对 synthetic design bounds 建 Sobol points；SciPy 的 scrambled Sobol 提供 `2^m` low-discrepancy points，并警告非 2 的幂会破坏 balance property。[18]
4. 预计算 `{T, composition reduced-coordinates}` equilibrium cache；数据库缺相时保留 flag。

### 7.2 单次 L1 forward

每一自适应时间步：

1. 由 `s(t)` 更新固定 kiln boundary。
2. 用上一步 `T,c,φ` 计算 properties 与 reaction rates。
3. 求 quasi-steady gas pressure/Darcy velocity。
4. 联立 finite-volume heat + gas species + reaction extents，用 method-of-lines BDF/Radau；提供 block-sparse Jacobian。守恒主变量使用 deforming cell 的 extensive moles/enthalpy，通量除以更新后的 cell volume 形成导数，避免 shrinkage 时仅因基准体积变化产生伪 source。
5. 对每 cell 做 equilibrium target，更新 kinetically limited phases。
6. 更新 sintering strain、bulk volume、phase volume、total/open porosity 和 properties；必要时 Picard 迭代至相对变化 tolerance。
7. 做 element、energy、positivity、simplex residual checks；失败则缩步，仍失败返回 structured failure，不得用 NaN 参与优化。
8. 后处理 stress/defect/performance proxies 和 coverage flags。

SciPy `solve_ivp` 支持 BDF/Radau、event、Jacobian sparsity；这足以支撑 MVP，不需要收费 solver。[16]

### 7.3 时间/空间收敛

- 默认 half-slab `N=21`；复算 `N=41`。
- 默认 solver tolerance 复算时收紧 10 倍。
- 关键输出（max center-surface ΔT、max ΔP、final porosity、shrinkage、reaction completion）相对/绝对差需落入 spec tolerance。
- L0 必须在 Biot 和 gas-generation low-gradient case 收敛到 L1 spatial average；高梯度时应主动产生 fidelity-warning，而非强行一致。

## 8. Inverse design

### 8.1 问题定义

给定目标 fingerprint `y*` 与 constraints：

`min_z [f_quality(z), f_gas(z), f_residence(z), f_uncertainty(z), -x_sludge]`

subject to：

- dry fractions 非负且和为 1；
- element/phase representation 一致；
- `d10<d50<d90`，形貌/含水/预处理可实现；
- `speed_ratio` 在设备已批准 bounds 内；
- robust quality constraints：`q05(quality_margin)≥0`；
- robust risk constraints：`q95(R_i)≤1`；
- environmental limits 缺失时状态为 `not_evaluated`，不能当作通过。

### 8.2 多解性

forward map `F:z→y` 往往不单射。输出必须保留：

- nondominated solutions；
- 每个 solution 的邻域 feasible radius；
- sensitivity / active constraints；
- 等效 fingerprints 的 cluster；
- 由 parameter/model uncertainty 导致的 rank instability。

不要用任意正则化把一个解包装成“唯一最优”。如果需要一个候选用于沟通，只能按已声明 preference（例如最大稳健裕量、最少预处理）从 Pareto set 选 knee point。

### 8.3 搜索策略

1. `Sobol 2^m` 生成 constrained design library，先做 simplex transform 和 feasibility repair。
2. L0 全量筛选，删除守恒失败、coverage 过低、hard constraint 失败点。
3. nondominated sorting 得 Pareto candidates。
4. 用 SciPy `differential_evolution` 做若干 ε-constraint/scalarization 局部扩展，`workers=1`；官方接口支持 bounds、linear/nonlinear constraints 和 integrality，但它是 stochastic global optimizer、函数评估较多。[17]
5. 选 16–32 个 diversity/uncertainty 候选做 L1。
6. 合并 L1 robust metrics，再做 Pareto filter；若 L0/L1 ranking 不稳，报告 fidelity disagreement。

未来可切换 NSGA-II，其原始论文为 Deb 等 2002 年提出的 fast elitist multi-objective GA。[19] MVP 不引入额外包，避免 ARM 安装负担。

### 8.4 Pareto 输出

每行必须包括 `decision_vector`、median/quantiles、constraint margins、model flags、source-pack hash、fidelity、runtime、failure reason。图形至少包括：

- sludge utilization vs quality-margin；
- residence-time proxy vs gas-risk；
- uncertainty width vs quality-margin；
- composition ternary/barycentric slice；
- speed_ratio × sludge_fraction feasible map。

## 9. Uncertainty propagation

### 9.1 类型

- **Parametric epistemic**：`A,E,ΔH,k,c_p,h,k_m,η,γ,E_modulus,strength parameters`；
- **Database**：phase/species 缺失、Gibbs model、liquid solution model；
- **Boundary**：固定 kiln spatial map 的温度/O₂/换热区间；
- **Geometry/closure**：packing、open-pore connectivity、permeability、1D discrepancy；
- **Model form**：instant equilibrium vs kinetic limit、SOVS reduction、strength/WA proxy。

### 9.2 表示

- 有公开 ensemble 时使用 empirical discrete ensemble；
- 只有 bounds 时用 interval 或 log-uniform/triangular **policy distribution**，并明确其不是已知概率；
- `log A` 与 `E` 可按同一 source-set 联合抽样，避免拆散 compensation；
- model discrepancy 单独报告，不能与 parameter CI 混成一个“95%可信区间”。

### 9.3 传播

- L0：scrambled Sobol `2^m` samples，多个 scramble replicate 给 sampling error；
- L1：对 shortlist 用 corners + 小型 Sobol，至少覆盖 thermodynamic/kinetic/BC/closure 四组；
- 输出 `q05,q50,q95,min,max,coverage_score`；
- robust feasibility 以最差 interval 或 q05/q95 决定，由配置选择，不得混用；
- sensitivity MVP 用 rank correlation / standardized effects；后续才加 Sobol indices。

## 10. 开源/免费软件与数据库选型

| 组件 | 用途 | 许可/事实 | ARM/6GB 决策 |
|---|---|---|---|
| Python 3 + NumPy/SciPy | FVM、stiff ODE、QMC、global search | SciPy 官方提供 BDF/Radau、Sobol、DE。[16][17][18] | MVP 主栈；`workers=1` |
| NIST-JANAF SRD 13 | pure-species thermochemistry | 公开推荐温变 thermochemical tables。[5] | 缓存必要 subset |
| NASA CEA data/code | gas/pure condensed species，equilibrium cross-check | 官方说明 >2,000 species 与 equilibrium/transport。[6] | 数据解析/离线 cross-check；非主 runtime |
| Cantera | gas reaction/equilibrium cross-check | multiphase VCS/Gibbs solvers。[8] | optional；先检查 aarch64 wheel/build |
| Thermochimica / Equilipy | CALPHAD equilibrium adapter | BSD-3，composition/T/P→phases；需数据库和 Fortran/LAPACK。[7] | optional adapter；不是 MVP hard dependency |
| pycalphad | TDB/CALPHAD research | Python CALPHAD 库。[9] | optional；数据 coverage 先行 |
| COD | CIF/crystal density/phase identity | public-domain open crystal structures。[10] | 下载必要 CIF，不镜像全库 |
| OpenFOAM | 3D CFD/heat/chemistry | GPL 开源 Linux CFD。[20] | 后续本地 PC L2 |
| DOLFINx | 2D/3D stress/sintering FEM | 官方 variational hyperelasticity demo。[21] | 后续本地 PC L2 |

禁止项：不建议创建任何 OCI 资源、升配、商业 FactSage/Thermo-Calc、收费 API。MVP dependency lock 应只含可在目标 aarch64 安装的版本；安装可行性需 Engineer 在该机上实际验证，不能从 x86 文档推断。

## 11. 可执行 MVP 规格

### 11.1 资源预算

- one process，`workers=1`；
- L0 peak RSS target `<1 GB`，L1 `<3 GB`；
- equilibrium cache 按 temperature/composition quantization，磁盘持久化；
- 默认 screening `2^8=256` designs；每 design 的 parameter UQ 先 `2^4=16`；
- L1 shortlist 默认 16 designs，每个 8–16 uncertainty scenarios；
- 超预算时减少 candidate/UQ 数量并记录 `budget_truncated=true`，不偷偷降 physics。

以上是工程预算，不是性能承诺；实现后须在目标机 benchmark。

### 11.2 端到端 synthetic example（无需手算结果）

`model_spec.json` 的 `synthetic_example` 定义：

- synthetic dry blend：shale 0.72、coal_gangue 0.20、sludge 0.08；
- sludge phases/pseudo-components、PSD 与 morphology 均显式给出；
- half-thickness、forming moisture、green porosity 使用 synthetic policy values；
- 100 m synthetic tunnel profile 与 `speed_ratio=1`，温度/O₂ 都是空间地图；
- 目标为 synthetic porosity/density/shrinkage/risk windows，不引用产品标准；
- 先 `validate`，再 `forward --fidelity L0`，再 `forward --fidelity L1`，最后 `inverse --budget tiny`。

合格运行必须生成：state trajectory、mass/element/energy residual、phase/liquid/porosity/shrinkage、gas release/pressure、risk/performance proxies、flags、UQ quantiles 和 Pareto JSON/CSV。

### 11.3 启动不依赖现实试验

Startup parameter priority：

1. public pure-species thermochemistry；
2. public mineral/kinetic paper ensembles；
3. theoretical positivity/phase-rule/geometric bounds；
4. explicit synthetic policy bounds；
5. optional later plant calibration。

如果 1–3 缺失，模块不能伪造单点值：要么输出 interval/unknown，要么从 hard objective 中降级。该降级不会阻止其他守恒模块运行。

## 12. Verification plan

1. **Schema/property tests**：units、basis、simplex、PSD order、phase-element double-count。
2. **Dimensional tests**：每个 residual term 的 SI dimension 相同；spec 中定义 expected dimension vector。
3. **Conservation manufactured cases**：无反应绝热、单一蒸发、单反应封闭、仅表面 outflow。
4. **Analytic limits**：lumped Newton cooling、1D slab conduction、Fick diffusion、first-order Arrhenius isothermal。
5. **Thermo tests**：`A n=b`、`G_final≤G_initial`、nonnegative phases、candidate-list perturbation coverage。
6. **Positivity/bounds**：`0≤α,φ,ρ_rel,f_liq≤1`，`T>0`，`P>0`。
7. **Grid/time convergence**：21→41 cells、tolerance tightening；关键输出差异合格。
8. **Metamorphic tests**：减慢速度应增加 residence time；关闭 reactions 时 gas source=0；PSD 等比例缩小应改变 surface/permeability 方向但不破坏元素守恒。
9. **L0/L1 consistency**：低 Biot/低 gas-source manufactured case 的均值一致；高梯度 case 触发 warning。
10. **Inverse tests**：返回点全部满足 hard constraints；Pareto set 中不存在被严格支配点；固定 seed 可复现。
11. **Failure tests**：database phase missing、solver nonconvergence、预算截断、environmental threshold missing 都返回 structured status。
12. **Resource benchmark**：在目标 Linux aarch64、1 OCPU/6 GB 实测 tiny example 的 RSS、wall time 和 artifacts。

## 13. Human approval gates、rollback 与残余风险

### 必须人工审批

- 将任何 speed window、配方或预处理结果转为现场试验/生产 recipe；
- 把边界数据从真实窑系统导入，或把输出接到 PLC/robot/控制系统；
- 对外发布、产品合规/环保声明；
- 安装需要额外系统权限的软件；
- 任何收费服务或资源（本计划不要求）。

### Rollback

模型运行本身只读输入、写本地 artifacts。parameter packs、schema 和 solver config 必须 versioned；新 pack 如 conservation/grid/regression tests 失败，回滚到前一 hash。任何未来现场使用必须保留原窑车速度/recipe、一键恢复与人工 stop 条件。

### 最大残余风险

1. 开放数据库对多元氧化物液相/玻璃的覆盖不足；这是 liquid fraction 和过烧判断的首要 epistemic risk。
2. 污泥 organic pseudo-components 只能覆盖 classes，不能预测所有 VOC/toxic species；缺 species 不等于零排放。
3. 1D 无法表达孔洞、码放、边角、火道和全窑 feedback。
4. strength/WA/efflorescence 是 closure-dependent proxies；没有后续独立验证时不能用于认证。
5. synthetic kiln map 与真实窑不等价；速度优化结果只在所给 boundary map validity domain 内成立。

## 14. Acceptance criteria

- 三份交付物字段一致：本报告、`model_spec.json`、`ENGINEER_HANDOFF.md`。
- 所有方程项有单位，Engineer 可用 dimension registry 自动检查。
- forward outputs 覆盖任务要求的温度、反应、气体、相、液相、孔隙、收缩、应力、缺陷风险与性能。
- inverse outputs 是 constrained robust Pareto set，而非单点承诺。
- 参数逐项标记 `source_kind`、URL/DOI、validity 与 uncertainty；synthetic bounds 不伪装为测量。
- L0/L1 均能在目标机运行 tiny synthetic example；L2 明确留给本地 PC。
- 模型可在无本厂试验数据时启动；后续实验仅是 optional credibility upgrade。
- 未给环境/质量阈值时输出 `not_evaluated`，不输出“合格/安全”。
- 不执行外部发布、生产控制、删除或收费操作。

## Sources

[1] Weng, Lin & Chiang (2003), “Utilization of sludge as brick materials.” https://scholars.lib.ntu.edu.tw/bitstreams/4d2777ec-a7bb-4afc-89c3-e37a70e593e8/download  
[2] Cusidó et al. (2003), “Gaseous emissions from ceramics manufactured with urban sewage sludge during firing processes.” https://pubmed.ncbi.nlm.nih.gov/12737969/  
[3] Gašparovič et al. (2011), “Kinetic study of pyrolysis of waste water treatment plant sludge.” https://chemicalpapers.com/?id=7&paper=874  
[4] Polcowñuk Iriarte et al. (2025), “Dehydroxylation of Kaolinite…” https://www.mdpi.com/2075-163X/15/6/607  
[5] NIST-JANAF Thermochemical Tables, SRD 13. https://data.nist.gov/od/id/mds00xmwqs  
[6] NASA Glenn, Chemical Equilibrium with Applications. https://www.nasa.gov/glenn/research/chemical-equilibrium-with-applications  
[7] ORNL-CEES Thermochimica. https://github.com/ORNL-CEES/thermochimica  
[8] Cantera Chemical Equilibrium documentation. https://cantera.org/stable/cxx/d3/d3d/group__equilGroup.html  
[9] pycalphad documentation. https://pycalphad.org/docs  
[10] Crystallography Open Database. https://qiserver.ugr.es/cod/  
[11] Shi et al. (2023), “Efficient modelling of ceramic sintering processes…” https://doi.org/10.1016/j.jeurceramsoc.2023.03.053  
[12] Xue & Yi (2024), “Phase-Field Simulation of Sintering Process: A Review.” https://doi.org/10.32604/cmes.2024.049367  
[13] Lima et al. (2021), “Drying and Heating Processes in Arbitrarily Shaped Clay Materials…” https://doi.org/10.3390/en14144294  
[14] Yu & Standish (1991), “Estimation of the porosity of particle mixtures…” https://doi.org/10.1021/ie00054a045  
[15] Rai et al., “Conduction Heat Transfer through Solid in Porous Materials…” https://www.osti.gov/servlets/purl/1813261  
[16] SciPy `solve_ivp` documentation. https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html  
[17] SciPy `differential_evolution` documentation. https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html  
[18] SciPy `qmc.Sobol` documentation. https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html  
[19] Deb et al. (2002), NSGA-II. https://doi.org/10.1109/4235.996017  
[20] OpenFOAM Foundation. https://openfoam.org/  
[21] DOLFINx hyperelasticity documentation. https://docs.fenicsproject.org/dolfinx/v0.10.0.post5/cpp/demos/demo_hyperelasticity.html  
[22] Petrović, Buljak & Cornaggia (2021), “SOVS Model Sensitivity to Temperature Distribution…” https://omega.mas.bg.ac.rs/_media/istrazivanje/fme/vol49/3/20_v._buljak_et_al.pdf  
[23] Xu & Yu (2008), “Developing a new form of permeability and Kozeny–Carman constant…” https://doi.org/10.1016/j.advwatres.2007.06.003
