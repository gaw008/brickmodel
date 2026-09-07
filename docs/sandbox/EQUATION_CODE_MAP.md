# 方程—代码—验证映射 v0.1

仅列实际存在的实现，不将架构接口作为代码。来源类别和运行资格另见 `EVIDENCE_POLICY.md`。

| 关系/约束 | 实现 | 实际测试/来源 |
|---|---|---|
| 单位维数、干湿基与数值有限 | `units.convert`；`materials.FeedPortion` | `test_units.py`、`test_materials.py`；质量基准的代数转换，无材料默认值 |
| 证据分类、来源依赖与域匹配 | `evidence.EvidenceRegistry` | `test_evidence.py`；只检查声明元数据 |
| 自带水 `m_w=m_d*x_w/(1−x_w)` | `materials.prepare_green_batch` | 人工质量账目测试；额外加水显式独立输入 |
| `J=λ_n λ_parallel²` 及共享面积 | `geometry.ReferenceSlab.deform` | `test_geometry.py`；运动学推导见世界定义 |
| 开放气孔=总体−固相−闭孔−液水 | `geometry.pore_geometry` | 域耗尽/无clip反例；未包含真实闭孔转换 |
| Shomate cp、积分h含生成焓、气体u=h−RT | `thermochemistry.ShomateSegment` | NIST原表/原系数/导数/参考能测试，来源表在 `data/sandbox/thermochemistry/` |
| 分段混合能量及温度反解 | `thermochemistry.Thermochemistry` | 原接缝、多解/缺口、次正规数分辨率与溢出反例 |
| 理想气体EOS与全species组成 | `gas_transport.GasState` | `test_gas_transport.py`；孔体积/载气显式 |
| 质量平均扩散、Darcy压力流 | `gas_transport.face_exchange` | `GAS_TRANSPORT.md`；中心修正改为漂移上风，空物种格方向及一阶误差已复验 |
| 半格串联Fourier热率 | `exchanges.conduction_rate_w` | `test_exchanges.py`；`HEAT_EXCHANGES.md` |
| 对流+灰表面/黑体环境辐射 | `exchanges.boundary_heat` | 相反方向热输入、独立气温/辐射温度与非法值测试 |
| 扩散/对流分项的物质焓率 | `exchanges.gas_enthalpy_exchange` | 实际热化学/气体模块接口测试；EOS与热化学R一致 |
| B2被动暴露积分误差步长界 | B2 `solver.exposure_step_limits` | 原容差、独立oracle、提交绑定22情景；仅历史synthetic域 |
| 元素计量矩阵、归一化Arrhenius质量作用源 | `reactions.ReactionNetwork` | `test_reactions.py`；49项及独立审查，仅显式候选/制造算子，不是原污泥机制包 |
| SSPRK2接受子步的共同库存/能量账本 | `integration.integrate` | `test_integration.py`；实际stage时间、局部/累计舍入和拒步，不代替物理守恒验证 |
| 当前n/U解码、EOS、共享扩散/Darcy/导热/物质焓 | `gas_heat_model.GasHeatModel` | `test_gas_heat_model.py`；刚性气相验证域，无固液储能/蒸发/收缩 |
| 独立质量、元素和储存U分步/前缀账本 | `conservation.audit_conservation` | `test_conservation.py`；使用显式基准，不调用求解器导数作为真值，仍须多相热物性重建 |
| IAPWS Helmholtz水物性、h−pv、Cp/Cv导数与统一参考偏移 | `water_properties.WaterProperties` | 78测试、33官方数值核验；`WATER_ADAPTER.md`；原生R显式，未拼接混合气 |
| 连续分段炉温/壁温/压力/气氛与时间节点 | `boundary_program.BoundaryProgram` | 41测试、实际积分与独立解析热量；不是已完成动态边界耦合 |
| 固定R理想水汽 h保持、u=h−RT、Cv=Cp−R | `ideal_water_vapor.IdealWaterVapor` | 28测试、独立2071温点，水来源与CODATA常数来源分列；无相平衡资格 |
| 动态外气与半格导热/对流/辐射串联 | `programmed_gas_heat.ProgrammedGasHeat` | 15测试、独立80表面根及真实积分；仅刚性气相核 |
| 固定相压力的U/H/V求和与条件温度反演 | `phase_storage.PhaseStorage` | 22测试；量化/相消/导数下溢反例，结果保存实际单调路径声明 |

完整湿砖组装器、材料动力学、水分迁移、烧结、力学和多代实验还没有实际映射，保持未完成。后续任何结果的完整DAG还需绑定实际启用的函数、参数和模型版本，不能用这张人读表替代运行时追溯。

| 新增方程 | 实现 | 验证与范围 |
|---|---|---|
| Vliq(T,P)+NgRT/P=Vavailable | `rigid_water_gas.RigidWaterGas` | 现23测试、独立压力根/体积审核及最终数值括区诊断；平界面固定腔体，非相平衡 |
| h(T)=h(Tanchor)+分段积分Cp，u=h−RT | `continuous_caloric.ContinuousShomateGas` | 22测试、独立Decimal核查及真实GasHeatModel跨接缝；原拟合保留 |
| Cclosed=Cp_total−T A²/B | 推导 `RIGID_STORAGE_DERIVATION.md`；条件反演 `rigid_storage.RigidStorage` | 独立三状态闭合压力中央差分，原始结果 `research/rigid-storage-derivative-identity.json` |

| 后续方程/接口 | 实现 | 验证与范围 |
|---|---|---|
| α、κ、dv/dT、dv/dP、du/dP | `water_properties.WaterProperties.state_tp_response` | 21新测试+78旧水测试；局部导数非区间界 |
| 每温度重新闭合P的U反解及条件误差传播 | `rigid_storage.RigidStorage` | 18测试、真实单格热量反馈；显式数值界尚未独立全域准入 |

| 本轮增量 | 实现 | 验证与范围 |
|---|---|---|
| 连续气体相H/U/体积 | `phase_storage.IdealGasPhase` | 新增3测试，旧规则保留，独立7个NIST跨缝反解；不自动补水桥 |
| 多格流体P/T—面输运—热量 | `rigid_fluid_heat.RigidFluidHeat` | 16测试及真实两格积分，局部/系统账本、供体焓；液水不迁移 |
| 原TGA列与SI转换 | `data/sandbox/research/ghodke2022/extract_tga.py` | 独立11575行/单位核对，单次运行；没有拟合或持出预测 |

| 化学势增量 | 实现 | 验证与范围 |
|---|---|---|
| s_g=s0(T,p0)−Rmix ln(p/p0)，mu=h−Ts | `water_chemical_potential.WaterChemicalPotential` | 36测试、独立导数检查、显式Table1八温点oracle；固定p0、共同native熵与能量参考 |
| peq=p0 exp((mu_l−mu_g0)/(Rmix T)) | 同模块的两个明确液态参考入口 | 理想水汽/真实纯液水近似；500K相对native psat约−11.24%，不等同完整真实流体EOS或泥料活度 |
| r=K(peq−p_H2O)，S_liquid=−r，S_vapor=r，新增U源=0 | `water_phase_transfer.WaterPhaseTransfer` | 真实蒸发/凝结制造积分；K显式声明，不由平衡式推得；无液界面退出、零汽极限、不clip有限库存 |

| 固体与数值增量 | 实现 | 验证与范围 |
|---|---|---|
| 单相Cp及h0原Shomate、全温段正下界 | `incompressible_solid.SolidShomateCaloric` | Fraction区间代数、50组独立驻点/差分；不施加气体Cp>R条件、不跨晶相转变 |
| u=h0−p0v0，h(T,p)=u+pv0，Cv=Cp | `incompressible_solid.IncompressibleSolidPhase` | 29新测试，实际PhaseStorage求和/反解；体积及误差显式声明，后续已接SolidFluidStorage整体固体库存 |
| 成功饱和求解快照缓存，命中仍EOS/Gibbs | `water_properties.WaterProperties.saturation_pair` | 18缓存测试+相关181测试、实际计数/同输入反解计时，原容差和域检查保留 |


| 固液气整体增量 | 实现 | 验证与范围 |
|---|---|---|
| Vavailable=Vbulk−ΣNs vs；Utotal=Ufluid+ΣNs us | `solid_fluid_storage.SolidFluidStorage` | 23测试，独立Decimal解析对照、真实25W/10s积分；每个温度试算重解压力，体积误差传播至压力与液水U |
| 完整库存列的U/P/T反解与共享气体/焓/热通量 | `solid_fluid_heat.SolidFluidHeat` | 新host及相变共13测试；两格积分、固体域退出、来源门禁；固体不跨面迁移 |
| 液/汽等摩尔交换、总U不另加潜热 | `water_phase_transfer.WaterPhaseTransfer` 两种显式host | 两种固体Cp的真实蒸发积分温度误差区间分离；不能推定泥料动力学 |


| 动态固液气边界增量 | 实现 | 验证与范围 |
|---|---|---|
| A*k/(dx/2)*(Ts−Tc)=A*h*(Tg−Ts)+A*epsilon*sigma*(Trad^4−Ts^4) | `programmed_solid_fluid_heat.ProgrammedSolidFluidHeat` | 半格膜串联解析、独立辐射根；真实升温/保温/冷却与动态气体入流mol/h账本 |
| 同一动态面账本叠加等摩尔液/汽源，额外潜热源=0 | `water_phase_transfer.WaterPhaseTransfer`显式第三host | 真实外热+蒸发积分；原program evaluation/inverses保留，breakpoints显式转发 |


| 液相面增量 | 实现 | 验证与范围 |
|---|---|---|
| λ=k*krel_l/mu；Q=AΔP/(dL/λL+dR/λR)；Ndot=Q/vdonor；Edot=Ndot*hdonor | `liquid_transport.liquid_face_exchange` | 20独立测试与正反供体手算、极端Fraction；四档实际pure-water连续流对照；不重复pQ |
| S=Vl/(Vbulk−ΣNs vs)，单次decode后共享液mol/h面 | `solid_fluid_heat.LiquidTransportConfig`及SolidFluidHeat | 6独立测试、真实两格逐前缀水/U账本、完整program/phase诊断链与仅液制造门禁 |


| 固相反应增量 | 实现 | 实际证据与范围 |
|---|---|---|
| 网络物种→实际相provider→完整库存列，bulk浓度速率 | `solid_reactions.SolidReactionConfig` | 13项绑定测试；独立二阶速率/列置换手算；相、质量、能量参考与制造门禁，不是材料准入 |
| 同一计量源推进Ns/Ng，总U包含生成能、重解Vs/Vg/P/T | `solid_fluid_heat.SolidFluidHeat.solid_reactions` | 8项host测试，有限O2实际积分、无氧通道、正Ea温敏比、元素/质量/U、完整wrapper诊断链；独立审核 `research/CODE_REVIEW_SOLID_REACTIONS.md` |
