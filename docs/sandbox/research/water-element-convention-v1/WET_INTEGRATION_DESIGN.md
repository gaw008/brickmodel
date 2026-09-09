# 同一 kg 固体参考下的两格湿坯→干态接入设计

只读依据：当前 mass_storage_bridge.py、mass_transport_bridge.py、rigid_storage.py、rigid_water_gas.py、water_phase_transfer.py，以及 exact_free_host.py / exact_terminal_executor.py。未运行 EOS、未修改仓库；现有 mass_transport 文件仍由 root 管理。以下是可落实到当前系统的接入顺序，不是新材料准入。

## 1. 最小目标与状态契约

下一实际目标：同一两格固定刚性坯体，在有限 O2 反应、导热、H2O/O2/N2 气体扩散与 Darcy 输运下，从两格有液水推进到一个耗尽、另一个仍湿，再到两个耗尽后的干态共同终点。保留每格总 U、kg 固体反应参考和逐面守恒。先不加液水跨面输运、收缩、毛细压力、吸附束缚水、成核或烧结；这些缺项必须出现在模型声明。

新增明确类型，例如 WetMixedState：solid_mass_kg[ncell,nsolid]；liquid_water_mol[ncell]；gas_amounts_mol[ncell,ngas]；total_internal_energy_j[ncell]；完整模型/参考身份。gas_order 固定为显式声明的 O2/N2/H2O，不能继续依赖现有两项 tuple 的长度和下标。液水与气相水为同一物质的两个库存；固体质量不能塞进 ConservedState.amounts_mol，不能用虚构固体 M 或缩放“伪物种”绕过旧求解器。

对应 WetMixedRates / WetMixedLedger 显式区分 solid_kg_s、liquid_mol_s、gas_mol_s、face_species_mol_s、face_energy_w 和 total-U 分项。固体不跨面、液水面流本轮严格为零，但相变源的液/气分项必须分别保存。初始每格全部质量、摩尔数非负且有限；湿模式必须有正液量，干模式必须精确零液量。模式是算子状态，不用微小正数维持假湿模式。

## 2. 湿态总 U / 孔隙 / 参考闭合

可复用 RigidStorage.evaluate_at_temperature(T,Nl,Ng)，它已经调用真实 RigidWaterGas 共同压力闭合及液水响应。给它的 available_pore_volume 必须是

V_available = V_bulk − Σ m_s v_s(T,p,composition)。

本轮 MassSolid 仍为明确制造常比容，所以只依赖实际当前 m_s。由流体闭合自己扣除液体：V_g = V_available − Nl v_l(T,p)。绝不能把已扣水的 V_g 再作为 available_pore_volume 传入，也不能仍用干态 MixedPoint.pore_volume 作为 gas_transport 的气体体积。后者必须读取实际流体 mechanical.gas_volume_m3。

总能量保持单一参考：
U_total = Σ m_s[h_s,ref + ∫Cp_s dT − p_ref v_s] + U_fluid(T,Nl,Ng,V_available)。

现有常比容固体的 −p_ref*v 正是 u_ref=h_ref−p_ref*v；不能改成任意零基准或在每次当前压力变化时多加 −p*v。流体返回的 U 已含液水/气相形成参考及温压贡献。固定外体积、无外部机械功时，相变并不另加 L*dN 或反应 q*dξ 到总 U；温度变化来自同一 U 的重新反解。对账可用 h_total−U_total=p*V_bulk 检查，但不是第二条演化方程。

当前 dry MixedStorage.evaluate 把 Nl 写死为0，且 pressure_error 增项采用干态 p*δV/V 形式。这两处不能简单放开零液量就称湿态支持。湿态需把固体体积转换/求和误差 εVs 传到压力残差：在稳定液体单调域，可用现有流体方法的 bmin = Ng_total*R*T/p_max² 作为保守正下界，增量 εp_solid≤εVs/bmin；将整个 p±εp 保持在原压力误差域中，并传播 Nl*|du_l/dp|max*εp_solid 到 U 误差。此处必须保留原 RigidStorage 已算的源误差、体积根误差和液体响应项，不能覆盖它们或重复计同一项。固体若将来不是常比容，此简单推导失效，必须重新求导闭合。

温度逆解继续使用实际湿态 forward 的完整 U 和 Cmin。现有 RigidStorage.closed_heat_capacity_j_k 含压力/液体占积响应；不可用 Nl*Cp_l+ΣNg*Cv_g 简单替换。其下界加固体 ΣmCp，保持原正性/域/符号未分辨拒绝；所有能量接受判据仍用 Fraction residual+误差与原界比较。若真实湿态 envelope 给不出分辨率，返回明确 numerical/domain failure，不调宽原科学门槛。

## 3. 水物质身份与 kg 反应参考

当前 MixedStorage 构造器仅准 O2/N2，并要求 reference.component_ids == solid_ids+gas_ids；MixedCell 仅认 A/B+O2/N2 和反应行(-1,2,-1,0)。因此 H2O 不能通过仅给 gas_phases 多加一个 key 接入。

最小完整扩展：新湿域参考网络显式加入 H2O(g) 组分及 H 元素列。A/B/O2/N2 原元素分数和反应热不变；旧反应的 H2O 化学计量系数为零。气相 H2O 的 kg 参考锚用实际来源绑定 vapor.h(Tref,pref)/Mwater；水的分子身份、元素组成、M 和液/气参考必须一致。元素质量分数必须有显式来源与与同一 M 的归一化约定，不能凭名字通用解析或套用另一个数据库的原子量后假称精确相等。该网络的化学反应不产生/消耗水；相变另以同一 mol 水跨相守恒实现，不需要伪造一个固体→水反应热。

使用现有 IdealWaterVapor 的实际来源桥（或被既有策略允许的 JoinedWaterVapor 低分支），不能用干态制造 O2 Shomate 示例复制成“真实水”。检查 reference、source_asset_sha256、caloric_method_id、R、M 及所有实际 thermal/chemical 水 provider 的具体类型和 implementation 内容。只相同字符串 source_id 不足以证明同一后端；每次 callback 前后检查完整 binding，延续已有 exact/paired host 的教训。

一般元素 gauge 改动必须同时变换每个固体、水液相、水蒸气及所携焓。下一湿实现先固定现有水形成参考，不开放任意水 gauge。可继续验证不涉及 H/O 水参考的合法碳元素 gauge；任意 H/O gauge 若没有能同步变换液水 provider 的明确接口就应拒绝，不能只改蒸气锚造成潜热改变。

## 4. 复用相变物理，不能直接复用现有 host 类型

WaterChemicalPotential.equilibrium_at_liquid_tp(T,p_liquid) 可直接复用，输入来自当前 wet inverse 的同一液体压力。水蒸气实际分压用 N_H2O*R*T/V_g 精确组合，避免先除总摩尔数丢失痕量水。沿用当前已声明 J=k*(p_eq−p_H2O) mol/s；J>0蒸发，J<0在已有液界面凝结。液体源−J，气水源+J，其他化学源独立叠加；JΔμ/T非负检查和零蒸气极限保持。k 仍为显式制造系数，不能从污泥热容论文推出来。

现有 WaterPhaseTransfer 不可直接套在 MixedPair：__post_init__ 有严格 host 白名单，species_order/liquid_index 从统一 mol layout 取值，_assemble_transfer 返回 Rates，with_depleted_cells 要求旧 ConservedState，evaluate_autonomous 只认直接 FreeSolidSlab。给新类加一个 isinstance 绕过会让固体 kg 在积分、原始 audit 或事件比较中被静默遗漏。

可选最小工程落点是新 MixedWaterPhaseTransfer/湿 MixedPair，复用化学 provider 的公式并返回新的单位明确诊断；若抽取旧 _assemble_transfer 的逐格纯相变计算 helper，必须让旧行为逐字段/回调数回归一致。保留 full actual chemical endpoint observation，不只保存一个 J 数字。已有 dry_policy 的 strict/metastable_no_nucleation 两个分支不能变成默认静默凝结或剪裁。

## 5. 共享面与两格动态

从新的湿 forward 实际 T、V_g、Ng 构造 gas_transport.ideal_gas_state，三种气体完整参与同一 face_exchange。复用 Fourier half-resistance及 Darcy/修正扩散；共享面只算一次，逐气体 mol integral 和能量 integral 应用到左右格的−/+各一次。扩散用 face T 的同一来源气体焓，Darcy 用供体 T 的同一来源焓；不额外添加“蒸发潜热面流”。热传导、物质携能和化学参考诊断分开保存。

当前 mass_transport_bridge 的 SharedFace.diffusivities 长度2、gas loop固定两个组分、反应 row及初态测试均是干域契约。新湿类必须明确扩展到3种实际气体，而不是把 H2O 默认D=0或从别种气体复制系数。相变改变液量→液占积变化→Vg/p变化→扩散/Darcy与化学分压变化→总U反解T变化，这条闭环必须在每个实际 stage 重建。液体跨面为零是一项显式初始限制，不等于多孔湿坯液体运动普遍可忽略。

## 6. 真实湿→干的必要事件桥

先做正液量短轨迹可以验证耦合，不能因此宣布完成湿→干。耗尽必须保留原 exact-clock/root-order/fullpanel/writeback/两连续pass+独立双减半 approach 的实质门槛。

不可直接调用 ExactFreeWaterTransfer / execute_exact_terminal：它们严格绑定 FreeSolidSlab、ConservedState/Rates 和全mol积分账本。最小完整改法是增加一个明确 mixed-state exact executor/integration route，或在原内核中抽取被验证的单位分离 stage/ledger 操作后分别绑定 old/mol 与 new/mixed schema。两条路线都要包括 kg 量：stage predictor、误差估计、拒步、整个仿射面板各固体非负、逐事件及共同终点比较、全初始前缀累计 kg/source/元素审计。原 fluid mol/E/T/P/time gates保持；kg比较必须新增显式有单位的 caller mass tolerance/scale，不能拿 mol tolerance 冒充 kg。制造验证可沿用现干桥测试数值尺度，但不能称材料不确定度。

现有纯 exact affine liquid root enclosure、严格全wet-cell root ordering及局部 DepletionRoundoffPolicy/Totals 可复用其数学；输入样本须绑定到实际 mixed start/mid state与所有分量源，不能只绑定水数组而忽略同期固体变化。写回只允许原局部液→气水的舍入修正，保留每格 U与全部固体 kg；每格自己的 gross evaporation与累计质量/元素/绝对/分数预算，不能借别格蒸发量。精确零液以后才切换该格模式，重算实际 mixed dry RHS，继续到共同终点；strict 干界面要求再凝结/液体再出现时明确域外，不假造再成核。

旧 exact_record 及4auditor未含这套 mixed kg schema，暂必须明确拒收。新可恢复版本需要 canonical kg/liquid/gas/U ledger、reference/源/参数完整身份和新mass gates，重构后4类审计涵盖新增字段才可授权续算。不要先接 UI/save“成功”而缺失 kg 守恒证明。

## 7. 具体交付顺序与验收

A. 同一候选中完成新湿 state/storage + source-bound H2O/三气体参考网络 +实际 wet point inverse测试。独立给定T/库存构造U及机械体积根，测试液体占积不重复扣除、p_ref*v、h−U=pV、固体体积误差传播、液/气参考不一致拒绝；原干bridge默认不变。需要真实 EOS 时由root冻结后一次有界运行。

B. 在该状态上完成两格 stage 级相变+热/三气体共享面动态，两个不同初温/水分压形成真实蒸发/凝结或不同蒸发率。测试逐prefix总水（Nl+NgH2O）、固体反应元素、O2有限消耗、全系统U/局部携焓，及全零传输/相平衡极限。保存至少两实际步长档和所有失败；不从纯fixture自动复制真实水数值误差界。

C. 将同一 host 接上mixed exact terminal+packet bridge，运行湿湿→干湿→干干后有限正时长；每个事件、共同时间、独立 approach、全初始质量/元素/U账本均过原门槛及显式kg门槛。模式切换不更换材料、参考或初始总U。达到这一项才可交付“制造参数下、同一质量基准的两格湿坯到干态动态模型”。

D. 再扩版本化服务/record恢复与来源图；前3项形成的实际记录不是自动可恢复旧record。自由变形、高温真实污泥热解/烧结与全周期材料闭合仍是后续工作：本轮保留已有真实 Cp/燃料能量来源记录，但它们不足以给此制造反应网络和湿输运系数材料准入。

## 8. 下一轮可直接分配的文件所有权

建议一个实现者独占新 mass_wet_storage.py + tests/sandbox/test_mass_wet_storage.py，负责显式state/三气体参考绑定/实际孔隙和完整U误差；另一个实现者在冻结该API后独占 mass_wet_transport.py + test_mass_wet_transport.py，负责复用共享面和化学provider形成同一host的湿态动态。不要两人同时改旧 mass_storage_bridge.py；默认旧干域接口保持。必要相变纯helper抽取若启动，明确单独所有者拥有 water_phase_transfer.py 并要求原路回归。

事件阶段由单一实现者拥有 mass_wet_exact_integration.py +对应tests，依赖已冻结新state/host；数值/来源审查者只读，避免同时更改上游RHS和事件gate。若决定抽取原exact公共操作，则先单独审核那一组精确文件差异，禁止随手放宽所有旧类型白名单。上述文件名是建议的新目标，尚未创建或应用；A/B的实际交付后必须继续C，不能把正液短轨迹当最终任务完成。

补核现有可直接借鉴实现：solid_fluid_storage.py:127–178 已有完整体积不确定度→全局压力界→局部压力界→液体U增误差链。湿质量storage应复制其数学契约而非摩尔固体布局：error_v汇总bulk误差、available舍入及m_s*比容误差，先要求error_v<available；全局bmin先证明双根压力区间在域内，再用certified_upper=min(envelope_max,p+global_pressure_error)收紧局部bmin，不能未经全局证明直接用当前p作局部界。最终仅额外extra_p对应项加入Nl*liquid_abs_du_dp_bound*extra_p，保留原fluid.energy_error不重复加已包含的压力项。该例程适合本轮直接复用/抽取压力证书helper，固体kg能量累加仍走新质量参考。
