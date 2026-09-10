# 方程—代码—验证映射 v0.1

## 当前新增映射

以下条目反映最新实现；后续历史阶段条目保留各自当时的验证范围。

| 关系或数值合同 | 实现与验证入口 | 已证实范围 |
|---|---|---|
| Rosheim解吸Xeq=k[aw/(1−aw)]^n及代数逆；仅30/50°C、图示支持aw0.1..0.8 | `amadou_desorption.AmadouDesorption`；[实际安装/独立复核](research/amadou2006-desorption-v1/REPORT.md) | 原作者表1拟合关系，16实验符号重建；源/安装28项、独立3负控，不提供连续T/吸附热或动态材料资格 |
| Wang D1：u_t=D u_xx，底部无通量、顶部Robin；μ tanμ=Bi的模态平均MR | `research/wang2021-drying-holdout-v1/reproduce/wang_d1.py`；独立高精度、有限体积与实际温度留出；[结果](research/wang2021-drying-holdout-v1/REPORT.md) | 研究脚本未进入生产内核；实际点数学差小于6e-13 MR，但117校准/57留出对照未满足图示一致性，不能授予真实材料参数资格 |
| 混合单位记录的精确数值编码、原初上下文/模型身份、全路径账本与投影一致性 | `mass_wet_exact_record.capture_binding`、`encode_mixed_run`、`audit_mixed_record` | 新schema保留kg/mol/U区别；离线部分一致性审计，明确不授予完整根/六差值重算、物理认证或续算许可；[证据](research/mass-wet-exact-record-v1/README.md) |
| kg/mol分离的两次耗尽、模式切换与原子提交；逐事件及共同终点六门槛、两连续细化与独立approach | `mass_wet_exact_controller.integrate_mixed_exact`、`audit_prefix`；`test_mass_wet_exact_controller.py`与独立DOP853辅助实现 | 明确制造解析液体的完整两格湿湿→干湿→干干数值闭环；[实际证据](research/mass-wet-exact-controller-v1/README.md)，不授予真实原料或原生水准入 |
| 固体kg/流体mol共同总U反解、有限O2反应及无重复化学热 | `mass_storage_bridge.MixedStorage`、`MixedCell`、`integrate_closed` | [混合桥证据](research/mass-storage-bridge-v1/README.md)：68源码/68安装相关测试，86模块一致；制造单格干态，非全周期材料准入 |
| 同研究干固体产率×干固体LHV | `data/sandbox/research/gnest-char-energy-v1/evidence_registry.json`；`units.convert` | [来源及独立复算](research/gnest-char-energy-v1/README.md)：4节点实际安装追溯；燃料能量库存，不是反应热 |
| 质量基准 `Bᵀh₀=q`、逐反应质量/元素配平、循环一致性和可辨识输出 | `reaction_reference.ReactionReferenceNetwork.solve`；`test_reaction_reference.py` | [质量参考证据](research/mass-reaction-reference-v1/README.md)：16源码/16安装及独立18测试；保留完整network和未知量，仅名义代数，不授予材料资格 |
| 精确时间的有序耗尽与全状态仿射交换 | `exact_depletion_integration.integrate_exact_depletion`；`test_exact_depletion_integration.py` | 真实水物性＋制造固体的2/4/8单元短时事件运行；[八格证据](research/exact-eight-cell-v1/README.md)，不是空间收敛或真实原泥材料验证 |
| 原始初态的累计N/E、共享面、分项功与精确机械增量账本；选定事件写回 | `exact_record_audit.audit_exact_run`；`test_exact_record_audit.py` | [原记录实审](research/exact-record-audit-v1/README.md)；不重置原预算，仍不包含全部续算验收条件 |
| 已提交终端的全根排序/完整求积/累计写回 | `exact_terminal_proof_audit.audit_committed_terminal_proofs` | [真实宿主保存记录复核](research/exact-record-gates-v1/README.md)；不重新求解全部RHS |
| 原粗网格锚/六项比较/连续与独立细化 | `exact_record_comparison_audit.audit_exact_comparisons` | 同上；实际函数返回已核，外围错误断言失败另行保留 |
| 原累计资源及已保留计算的去重计费 | `exact_resource_audit.audit_exact_resources` | 同上；原79已用/433剩余，权威历史遥测不能单从状态重建 |
| `ARLABOSSE2005_DRY_CP_EQ2`: 干基Cp=1434+3.29T_C | `arlabosse_caloric.ArlabosseDryCaloric.cp`；`test_arlabosse_caloric.py` | 同来源样品35–105°C的公开拟合计算；源元数据`data/sandbox/research/arlabosse2005/source.json`及原Eq2/单位图均核读 |
| `ARLABOSSE2005_DRY_SENSIBLE_ENTHALPY_DIFF`: 对上述Cp解析积分 | `arlabosse_caloric.ArlabosseDryCaloric.delta_h`、`registry_payload` | [两节点追溯与实际安装例子](research/arlabosse-caloric-v1/README.md)；无绝对形成焓、Cv或摩尔材料准入 |

`exact_continuation_admission` 与 `integrate_exact_depletion(..., continuation=...)` 组合四fresh审计、同版本原始输入和累计预算恢复；[实际取消续算](research/exact-continuation-v1/README.md)达到原终点30步/2事件包。原800秒/512面板预算保持，未接入旧CLI/UI生命周期。

`exact_projection_restore.restore_exact_projection` 按固定数值白名单恢复记录及已提交账本同对象关联；[实际无损恢复](research/exact-projection-restore-v1/README.md)检查30步、2事件包与全字节重编码。历史观察仍是数值证据，不构建实时逆解，不授予续算许可。

`exact_record`提供严格版本化数值记录、输入/来源绑定和状态—账本—事件关联；它本身不是物理方程，也不自动授权续算。见[实际原生记录验证](research/exact-record-native-v1/README.md)。

## 历史阶段映射

`exact_terminal_executor.execute_exact_terminal`：实际三观测、精确Euler中点、全root/panel/原writeback及仅选定mode变化；保存未提交阶段与成本。final58源码/58安装；修复前e324原四格失败初态fresh3EOS终端通过，两个版本均75模块且身份分开。非完整packet。见[证据](research/exact-terminal-native-v1/README.md)。

`exact_terminal_panel` 与 `exact_root_order`：同一共享仿射采样的全状态积分、区间最小值及全wet根排序；完整保存四格失败panel回放并真实water mixed端点通过。68源码/36安装，74模块。原多pass事件接受及全物理验证未完成。见[证据](research/exact-full-panel-replay-v1/README.md)。

`exact_free_host.ExactFreeWaterTransfer`：自主direct FreeSolidSlab/WPT共享state-only物性计算，exact时间无投影；全部water backend type/implementation纳入实际来源绑定。38源码/38安装及原四格初态真实water点对照通过，72模块一致；非完整事件或材料验证。见[证据](research/exact-native-host-v1/README.md)。

`exact_affine_depletion`：对同一三项signed速率的仿射积分建立有界dyadic根区间，逐项绑定一次舍入积分和向下舍入的蒸发正部；复用原修正/累计预算。93源码、54安装测试通过，仅数值原语，未准入实际事件。见[证据](research/exact-affine-depletion-v1/README.md)。

## 联合耗尽库存写回

`depletion_group_roundoff.writeback_exact_group` 将首个精确同根组、每格三项仿射液体积分与同一个已提供面板绑定，复用原逐格修正及累计预算；任一失败不提交部分结果，exactzero 保持 None。新模块20项、相关源码116项及安装52项通过。真实四格短推进仍未分离原候选门槛；完整模式切换/事件记录未接入。见 [联合核算研究](research/depletion-group-roundoff-v1/README.md)。

## 显式仿射多单元根区间

`depletion_group_clock` 对显式 `N(h)=N0+r0*h+a*h²/2` 用有理数隔离首个零点、检查整段最小库存、重验完整单元集合并按区间并集分组。`positive_panel` 包含内部极值；`group_roots` 区分同根与未分离区间；`outward_absolute_times` 仅作外向浮点时间转换。16 项新测试及相关 80 项源码回归通过，安装版 16 项通过。详见 [研究记录](research/depletion-group-clock-v1/README.md)。未接入真实湿态模式切换，不将采样速率视为严格仿射定律。

## 条件成对压力比较与显式事件策略

`paired_pressure.certify_paired_pressure`：B根区间残差差/正顺应性下界与独立根距离界；`paired_pressure_host.prepare_paired_pressure`：实际两状态及端点来源绑定。详细假设、19纯核+12主机检查和四实际保存证书见 [PAIRED_PRESSURE.md](PAIRED_PRESSURE.md)。只准入显式制造共享常数假设、固定报告温度，不含完整温度反解误差tube，默认不替代原事件接受或材料验证。显式v2策略现经 `pressure_comparison.compare_pressure_pair` 接入 `depletion_integration`；`event_record.audit_paired_refinement` 绑定事件/共同终点全部单元与保存观察和提交状态。来源与实际验证范围见 [PAIRED_EVENT_COMPARISON.md](PAIRED_EVENT_COMPARISON.md)。

## 自由形变耗尽事件映射

显式事件案例使用 `catalogs/free-wet-event-slab-equations-v1.json`，22项方程声明、7个输出入口；普通自由案例和原规定形变目录继续分别保留。`depletion_integration.integrate_depletion`推进完整状态及累计历史，`affine_depletion_clock.locate_affine_depletion_clock`定位仿射末端，`depletion_roundoff.depletion_writeback`量化必要的浮点库存修正，`event_record.audit_depletion_record`复核保存的步骤、事件、比较诊断和原始预算。`run_service`将案例/来源/实际算子与续算绑定，最终快照采用实际耗尽模式。

验证见 `test_event_record.py`、`test_depletion_continuation.py`、`test_event_run_service.py` 及 [FREE_EVENT_APPLICATION.md](FREE_EVENT_APPLICATION.md)。安装106项与原生2步湿前缀不等于真实耗尽事件、空间收敛或原污泥实验验证；各后续运行以实际独立审计为准。

## 运行时方程目录与来源图

当前制造湿态模型使用 `src/sludge_sandbox/catalogs/wet-slab-equations-v1.json`：19项公式声明、38项参数元数据、4个输出入口。`run_provenance.build_graph` 将目录绑定到实际运行的案例值、代码AST行号及来源资产；`query_graph` 返回指定输出的上游节点。方程文字不执行，真实计算仍在相应物理模块。来源位置若为JSON指针会实际解析，其他页码/公式号保留核读声明。`run_service` 在EOS前保存图，`trace` 同时检查案例、目录、代码和来源资产的原运行绑定；不会为旧运行补造新图。

实际安装测试与运行/重放记录见 `research/run-provenance-v1`；操作见 `CLI.md`。这是本制造模型的声明依赖图，不是原污泥全周期方程齐备、材料适用性获证或实验通过的证明。

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


| 水汽跨域与事件数值部件 | 实现 | 验证及边界 |
|---|---|---|
| 低温h锚+高温逐段原Cp积分，u=h−RT与Cv>0 | `joined_water_vapor.JoinedWaterVapor` | 低分支保持、500/1700接缝、独立积分/正Cv界/来源/数值误差测试；不扩展液相chemical域 |
| Joined相身份/来源及活动气体数值预算 | `phase_storage.IdealGasPhase`、`solid_reactions`、`rigid_storage`、`water_phase_transfer` | 实际SolidFluidHeat跨500/1700升降温及预算不足拒绝；低分支phase匹配 |
| 精确±δ与binary64写回残差分账、不可取消累计预算 | `depletion_roundoff.depletion_writeback` | 16项数值反例/恢复测试，独立组件审核通过；非事件定位器或全湿干积分 |
| 精确液净率与向下最近事件时间；独立clock残量=abs(netNl)*(root−end) | `depletion_roundoff.DepletionClockEvidence` | 原4ULP默认不变，4项clock证据/伪造拒绝；仍受真实正蒸发比例与累计预算 |
| 完整Rates终端Euler与真实干态共同时间续算，全段Fraction账本 | `depletion_integration.integrate_depletion` | 常/线性根、真细化回归、程序节点、资源/失败隔离；实际host attempt03水/元素/M/U与升温通过；非全轨迹ODE误差证书 |
| existing_liquid→depleted_no_nucleation，假想平界面筛查独立于实际液态μ | `water_phase_transfer.WaterPhaseTransfer` | 11项模式测试；strict域外/凝结退出，显式metastable研究模式，K和来源保留 |
| 多格第二事件重选共同时间并重启比较；普通步局部库存时间比例；全显式dry保持普通自适应积分 | `depletion_integration.integrate_depletion`、`DepletionPolicy.safe_inventory_fraction` | 独立55项事件/clock/写回/多格/比例/干段测试；真实水两格液迁移+反应耗尽attempt02通过；局部预测不构成全轨迹误差界 |
| 实际NL精确0时选择显式dry温度反解括号；正NL保留wet括号与原EOS域 | `solid_fluid_heat.SolidFluidHeat.temperature_brackets_for` | 独立9项括号测试；真实湿态到530.7349451K连续轨迹及独立条件干段参照通过；不是液chemical高温扩域 |
| C1规定法/切向伸长；A=A0*lambda_t²；Vdot=A*width_dot+A_dot*width | `deformation_program.PrescribedSlabMotion` | 独立29项运动学/输入域/不可变性/16–64格坐标检查；非材料收缩律 |
| 相同当前V/A/d与同次气体解码；显式压力匹配气腔功−p*Vdot | `gas_heat_model.GasHeatModel.evaluate`、`deforming_gas_heat.DeformingGasHeat` | 旧版四Rates黄金对照；三档绝热压缩膨胀约4倍温度误差下降，双格/流焓/当前bulk反应与完整prefix检查；非湿固体骨架功 |

## 骨架与分项功接口增量

| 关系/合同 | 实现 | 验证 | 限定 |
|---|---|---|---|
| E_el=V0(K theta²/2+G sum dev²)，E_int=gamma Aint0 t²；同势Piola与E率 | src/sludge_sandbox/skeleton_energy.py | tests/sandbox/test_skeleton_energy.py；research/CODE_REVIEW_SKELETON_ENERGY.md | 制造参数；独立有理对数级数检查75个输出界 |
| D=eta V0 sum(log-rate²)，Rayleigh势=D/2 | 同上 | 同上 | T独立对角规定变形，不是自由烧结模型 |
| 目标能量区间到温度包络 | src/sludge_sandbox/solid_fluid_storage.py | tests/sandbox/test_solid_target_uncertainty.py | 上游误差显式给定；原物理域不变 |
| 接受RK分项功及total-minus-components精确残差 | src/sludge_sandbox/integration.py | tests/sandbox/test_component_work_ledger.py；research/CODE_REVIEW_COMPONENT_WORK_LEDGER.md | 普通integrate；非单项截断误差证书，尚未覆盖耗尽panel |

| 新接口 | 实现 | 独立证据 |
|---|---|---|
| 不透明能量模型身份，普通RK/writeback保留、旧host拒混用 | integration.py/depletion_roundoff.py及三个旧heat host | test_energy_state_identity.py；CODE_REVIEW_ENERGY_STATE_IDENTITY.md，73测试与旧41e5911三轨迹逐字段相同 |
| 当前bulk+固定Ns+Etotal点反解及数值界 | deforming_solid_storage.py | test_deforming_solid_storage.py；CODE_REVIEW_DEFORMING_SOLID_STORAGE.md，11测试与独立target区间 |

上表尚不包含真实湿机械时间积分、自由烧结或材料准入。

| 规定形变增量 | 实现 | 验证与边界 |
|---|---|---|
| 同次current_storage/thermal_inverse面装配 | solid_fluid_heat.py私有_assemble_decoded、deforming_solid_storage.py尾追加current_storage | 旧evaluate AST实际非零热/气/固相反应黄金比对一致；旧positional兼容与single-inverse通过 |
| 固定Ns总E推进，五分项功 | deforming_solid_heat.py | test_deforming_solid_heat.py；CODE_REVIEW_DEFORMING_SOLID_HEAT.md |
| η0闭式T=T0(Vp0/Vp)^(NgR/Ctotal)，elastic/interface势差、pore=CtotalΔT | 同上独立常Cp制造oracle | 实际512/1024/2048均匀0拒步；fine原T和各功门槛通过；非湿/自由烧结验证 |

## 普通积分器时钟（numerical_policy）

`NUM-TIME-CLOCK-EXACT-BINARY-1` → `integration.integrate`：名义二进制步长用 Fraction 精确累加，断点同步、两种拒绝重锚；保留原 min(ulp(target),32ulp(step)) 局部端点界。实际 RK/通量/功始终积分真实端点差。`tests/sandbox/test_integration_clock.py` 有12项新回归，含完整边界通量和3W功；完整安装1124测试通过，三尺度短湿活动相变制造案例通过。历史失败、数值理由、安装身份与独立审查见 `research/integration-clock-correction/README.md`。这不是材料方程或全周期验证。

HEOS共存数值政策 `NUM-HEOS-COEXISTENCE-BACKTRACK-1`：固定T的F=(Δp,Δg)，对logρ的Jacobian保持原式；最大原门槛归一化残差下降回溯见 `src/sludge_sandbox/_heos_kernel.py::_saturation_pair_locked`。数值控制回归 `tests/sandbox/test_heos_backtracking.py`，原生公式与原组合耗尽实际证据 `research/heos-coexistence-backtracking/`。回溯仅为数值政策，不是新增物理本构。

## 反应与规定变形的组成储能

| 关系/合同 | 实现 | 实际检查 |
|---|---|---|
| q(N) 及机械内能、组成偏导、固定组成应力/耗散缩放 | reacting_skeleton_energy.py | test_reacting_skeleton_energy.py；独立同时改变 F/N 的链式法则差分 |
| 当前库存占积与总储能一次反解 | deforming_solid_storage.py | test_reacting_deforming_solid_heat.py；固定总能量组成变化 |
| 当前反应储能重绑、固定组成外功、−p Vbulk_dot | deforming_solid_heat.py | 非一阶速率当前体积与反解对象一致性；实际干态反应/压缩轨迹 |
| 不混合两套分项功字段 | integration.py | test_reacting_deforming_solid_heat.py 与原 component/depletion 回归 |

上述 q 与 A→B 参数均为 manufactured_test_fixture，不属于材料证据注册或实验验证。实际细化、旧失败和审查见 research/reacting-deformation-v1/README.md。

`NUM-SOLID-VOLUME-PRESSURE-LOCAL-1` → `solid_fluid_storage.py`：保留原全局压力包络拒绝，再用已证实上端收紧同一体积误差的导数界，原流体误差不变；`test_solid_pressure_bound.py` 的独立双向有理气体根验证。实际边界与原湿态失败见 `research/solid-pressure-bound-v1/README.md`；这是数值传播政策，不能据此称湿态事件已收敛。

`NUM-DEPLETION-NESTED-APPROACH-1` → `depletion_integration.py` 的 `NestedApproachPolicy`、普通湿态前缀与独立实际网格比较：`test_depletion_spine.py` 独立根/反应/能量参照、缓存等价、共同偏差拒绝、多事件和成本回滚；`test_depletion_spine_source_guards.py` 最后两次试算来源变化与新终端故障拒绝。原 `depletion_roundoff.py` 线性最近向下时钟证据未改。来源注册类别为数值策略，不是材料本构。

`NUM-HEOS-TP-BACKTRACK-1` → `_heos_kernel.py:HEOSCandidate.state_tp`：原动态压力门槛、最多8接受状态/6候选/43实际评估；`test_heos_tp_backtracking.py` 控制反例、精确停滞、失败尝试、来源/快照终止与下溢门槛；`test_heos_tp_native.py` 原失败295K/53692.54782795906Pa及固定八邻点。`water_heos.py`、HEOS manifest 与 source 注册仅同步实现身份，不改物理常数或水数据。

- `NUM-AFFINE-TERMINAL-1`：`affine_depletion_clock.py` 的不可变二次根证书；`depletion_integration.py` 的 affine_midpoint 预测、统一场积分、全区间库存与正向相变积分；`depletion_roundoff.py` 验证证书后沿用原预算。对应 `test_affine_depletion_clock.py`、`test_affine_depletion_integration.py`、`test_affine_depletion_guards.py`；制造解与数值政策，不是污泥材料参数。

## 自由机械状态与液相耗尽

| 关系/数值操作 | 实现 | 实际验证与边界 |
|---|---|---|
| 终端伸长 λ(s)=λ0+a s+b s²；整区间正性，精确有理求积与表示误差 | `depletion_integration._mechanical_panel` | `test_mechanical_depletion.py`：Euler/affine、内部非正反例、独立 exp(t) 轨迹；制造验证 |
| 事件态及公共时刻伸长比较，原初态累计伸长账本 | `depletion_integration.integrate_depletion` | 同上机械独立拒绝/跨段预算/取消测试，见 `MECHANICAL_DEPLETION.md`；实际水组合结果以 `research/mechanical-depletion-v1` 原始运行证据为准 |

| 多格自由形变关系 | 实现 | 验证 |
|---|---|---|
| 全部n_i与共同t生成当前几何；E减恢复能后逐格反解T/P | `current_solid_storage.CurrentSolidStorage` | 非首格、完整几何、独立热容/势能、保守体积误差、单格数值兼容 |
| n_i逐格法向平衡，t_dot由sum(V0_i eta_i)加权虚功平衡 | `free_slab_rates.solve_free_slab_rates` | Decimal160、局部非零R、分割/重编号、零tdot反例 |
| 局部约束功C_i与当前面传热共同推进E | `free_solid_slab.FreeSolidSlab` | 独立DOP853干态两格，漏C_i仍全局守恒的负对照；真实水两档固定相态短轨迹 |

`NUM-ORDERED-AFFINE-PACKET-1` → `depletion_integration.py`：共同采样的逐湿格仿射库存根区间严格排序、实际 mixed-mode 重算、完整逐事件及共同终点细化、整段原子提交。`test_depletion_ordered_packet.py` 的14项制造测试与 `test_ordered_packet_record_boundary.py` 的7项旧记录/服务拒绝测试；源码323项及安装61项回归通过。实际四格实验因 `correction_exceeds_evaporation_fraction` 失败，0事件提交，不能声称原生有序事件通过。详见 `research/ordered-packet-v1/README.md`。该项仅为数值政策，不是材料本构或真实非线性根的严格证书。

其失败证据合同 `ordered_affine_writeback_failure_v1` → `depletion_integration._snapshot_failure_diagnostic` 和两个失败 refinement 入口：`test_depletion_failure_evidence.py` 以真实制造短面板拒绝验证 raw/clock/gross/完整积分重建、不可变性、成功及默认对照、捕获错误不遮蔽原拒绝。相关源码114项、安装65项通过；同条件原生诊断完整数值结果与旧失败相同，原门槛未改。见 `research/ordered-packet-failure-evidence-v1/README.md`；这是未提交试算的诊断，不是通过的比较或检查点。

`NUM-EXACT-TIME-1` → `exact_event_clock.py`：单Fraction语义身份、严格时间/区间编码、独立显示投影；`exact_boundary_program.py`：精确节点/权重和声明的完整程序平移。`test_exact_clock.py` 有23项原语测试，连同原边界程序41项在源码/安装各64通过。

`NUM-EXACT-SSPRK2-1` → `exact_integration.py`：精确回调及实际阶段端点、两半步误差估计、N/E/形变/component账本和原子前缀提交。未来名义步长向下量化是明确数值控制选择，不投影实际时间。`test_exact_integration.py` 16项实际制造测试、`test_exact_time_boundaries.py` 两项旧消费者拒绝；相关源码185/安装132通过，70实际模块匹配。见 `research/exact-integration-v1/README.md`。尚未准入原生耗尽事件、旧记录或完整材料过程。

## 精确事件服务与显示接入

`free-wet-exact-event-slab-equations-v1.json`：27方程、7结果根；18原物理条目保持，新增精确时间/耗尽/记录审计均列为数值策略。`exact_run_service.py` 接入严格记录、四审计、终态快照与完整导出；`run_service.py` 的续算保持原初态、政策和父历史一次。`test_exact_run_service.py` 与真实水取消/续算/重放证据见 research/exact-service-native-v1。

`assets/app.js` 的时间元数据验证与有理时刻排序检查仅用于显示，未知显式schema拒绝，浮点时间不作为续算输入；实际浏览器比较、溯源、导出见 research/exact-ui-v1。不构成新增材料本构或完整周期验证。

## 固体kg与气体mol的共同面传输

`mass_transport_bridge.MixedPair.evaluate` → 当前MixedCell总U反解、`gas_transport.face_exchange`质量修正扩散/Darcy、`exchanges.conduction_rate_w`半格热阻。同一气体参考焓分别在面温度和供体温度评价；`integrate_pair`一次面账本/相反符号更新与失败前缀保留。`test_mass_transport_bridge.py` 独立DOP853全轨迹、元素参考变换、每接受前缀守恒；research/mass-transport-bridge-v1 保存实际源码/安装结果。制造干态验证，不是新增真实污泥本构。

## 同质量基准湿态储能

`mass_wet_storage.WetMixedStorage` → 固体kg参考内能与实际RigidStorage液/气共同储能；真实gas_volume由液占积闭合，固体体积表示误差通过全局/局部压力域与Nl|du/dp|入U。`WetMixedState`在浮点转换时拒绝负原始库存和非零下溢，`WaterElementConvention`绑定CIAAW事实且禁止水化学生成/消耗。制造液响应及独立非零du/dp包络测试见research/mass-wet-storage-v1；实际HEOS一点、原失败与独立Brent数据审计见research/mass-wet-native-v1。仅储能层，不是时间相变/湿干事件或材料准入。

## 同质量基准正液量动态

`mass_wet_transport.WetPair.evaluate` → 同一湿储能反解当前T/P与液气占积，有限O2质量反应、来源绑定水化学势相变、三组分共同面扩散/Darcy焓流与导热。`integrate_wet_pair` → 固定中点、一次共同面账本、kg固体/mol水与气体/总U分量更新及失败前缀保留。相变和反应热通过共同储能体现，不另加热源。制造液响应下独立DOP853与守恒测试见research/mass-wet-transport-v1；真实HEOS两格4/8步短轨迹及逐前缀审计见research/mass-wet-transport-native-v1。固体、动力学及传输系数为明确制造测试值，非真实污泥预测；两档差异不证明收敛阶或空间验证。

`mass_wet_transport.WetPair.interfaces/with_depleted_cells` → 显式已耗尽且禁止成核的计算模式，不是材料定律或耗尽根证书；同湿储能零液分支、实际气压假想液相平衡诊断、严格再凝结DomainExit及不变库存。默认全湿完整parity、混合湿干及失败前缀测试见research/mass-wet-depletion-host-v1。尚无事件写回许可。

`mass_wet_exact_stage.try_step_doubling` → 精确时间局部中点一步/两半步比较、分离kg/mol/U与T/P/time门槛；全二次面板检查和未提交末端尝试证据。`pressure_radius`对dry及显式常数液体制造模型传播完整T/V区间，generic wet缺证据拒绝。独立制造DOP853及原压力/末端失败RED见research/mass-wet-exact-stage-v1；无事件、全局提交或材料验证许可。

`mass_wet_writeback.project_mixed_depletion` → 完整kg/mol/U终态重算、原修正门槛与额外原初本格fraction限制下的等量液→气投影；不更改固体或总U，失败不返回修正状态。research/mass-wet-writeback-v1保存独立单位/累计预算反例和源码/安装结果。实际样本认证、根排序及全事件准入仍由后续控制器负责。

研究候选 `interval_eos.py` / `coupled_rectangle.py`（research/water-pressure-interval-v1证据包）→ IAPWS Eq6区间求导与局部液气压力根包围，显式public/native摩尔质量尺度；原16端点温度误差区间及守界半径独立重算。仅数学研究，未准入实际稳定分支或原生误差合同，不当材料参数事实。

`mass_wet_exact_terminal.prepare_mixed_terminal` → 实际两宿主样本、全部湿格根严格排序/排除、全kg/mol/U仿射终态与原局部writeback连接；保存失败prepared证据与成本。research/mass-wet-exact-terminal-v1验证近根/同根、分量账本及取消，仍不授六门槛比较或事件提交。


## 正式普通水区间原语（2026-09-09）

- IAPWS95残余Helmholtz与有向区间：`water_interval_eos.py`；`test_water_interval_eos.py`。
- 全温体积矩形机械根：`water_coupled_rectangle.py`；同名测试。
- 液汽共存Krawczyk：`water_coexistence.py`；同名测试。
- 全温正密度导数连接管：`water_density_tube.py`；同名测试。
- 固定native查询残差/公开摩尔质量体积界：`water_native_output.py`；同名测试与`test_water_volume_scale.py`。

源码均位于src/sludge_sandbox，测试均位于tests/sandbox。来源、旧新映射、完整独审与源码/安装验证见research/water-packaged-primitives-v1。只是已声明局部数学合同的实现，不自动提供全域物性误差或材料准入。


条件性逐查询连接器：`src/sludge_sandbox/mass_wet_pressure_interval.py`绑定实际WetCellRate与完整原T区间，调用上述五原语，检查同一液体密度管及固定native体积差异，按Fraction返回压力半径。`tests/sandbox/test_mass_wet_pressure_interval.py`验证拒绝/快照/预算逻辑；源码与安装64项通过，独立审查见research/water-pressure-consumer-v1。单次native查询与stage/controller六门槛是不同验证层，后者尚未接线。


累计原生压力接线（2026-09-09）：`mass_wet_pressure_provider_v2.py`复用原数学求证并保结构化失败；`mass_wet_pressure_seed.py`记录有来源系数的未认证初值迭代；`mass_wet_pressure_session.py`在一次构造生命周期内累计所有seed/proof及caller时间限制。`mass_wet_exact_stage.py` optin传实际full/fine samples并保原六gate，新subtype保原输入/门槛字节和全部proof，旧codec拒绝。对应测试test_mass_wet_pressure_session.py、test_mass_wet_native_stage.py及原stage/数学回归；源码/安装各110项通过。ordinary单次实际比较证据正在独审，controller/event仍未接线。


ordinary native实际full/fine已验证：research/water-native-stage-actual-v1包含9回调/4freshproof、原严格逐路径元素/质量/水/能量及六gate独立复算，source252/安装104绑定、全部原失败和运行产物。只是一段0.001s条件性试算；event/controller与完整材料烧成仍未完成。


原生控制器接线（2026-09-09）：mass_wet_controller_pressure.py的显式event/common上下文将实际观测与会话绑定，mass_wet_exact_controller.py同session保拒步/细化/独立路径历史，原全部门槛和原子发布未变；源码14/安装3关键路径实际通过。证据research/water-native-controller-v1。新近事件初态真实水2forward+1pair及独立保存算术见research/water-native-near-event-initial-v1；均不授完整原生controller、材料或全烧成验收。
