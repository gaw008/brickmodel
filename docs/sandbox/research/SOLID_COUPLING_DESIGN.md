# 显式固体库存、占积与储能接入设计

状态：只读设计，尚未实现或验证。依据当前 `phase_storage.py`、`rigid_water_gas.py`、`rigid_storage.py`、`rigid_fluid_heat.py`、`water_phase_transfer.py` 的真实接口；不改变现有流体模块的物理资格。本轮目标可以是固定外体积、惰性且不可压/不热膨胀的固体组分，不能称为完整湿砖或烧结收缩模型。

## 当前机械体积的确切含义

`RigidWaterGas.available_pore_volume_m3` 是液水和气体共享的可用腔体，满足 `Nl vl(T,P) + Ng R T/P = Vavailable`。返回的 `gas_volume_m3 = Vavailable − Nl vl` 才是自由气相体积。它没有固体库存，也没有从矿物密度计算孔隙；`RigidFluidHeat` 只检查它不超过几何 bulk 体积 `face_area_m2 * cell_width_m`。二者差额目前没有储能或物种账本，不可倒推为已建模的某种固体。

接入后应以完整的固定控制体 `Vbulk` 为唯一几何输入，显式 `Vs = Σ Ns vs`、`Vavailable = Vbulk − Vs`、`Vgas = Vavailable − Vl`。禁止同时让用户独立给出不一致的 bulk、孔隙率及 available；若需不可访问孔洞或额外骨架，必须增加具有清楚物理意义的独立体积项，而非悄悄把差额填成惰性质量。每次试探库存变化后重算 Vs 和 available，不能只在构造时计算。

## 最小物性合同与来源

现有 `PhaseMetadata` 已接受 phase='solid'，现有 `PhaseProvider.evaluate(T,P)->PhasePoint` 可以复用为固体点值的公共表示；`PhasePoint` 强制 `h−u−Pv` 一致。但该 Protocol 没有热容、体积响应、原始数据版本、全域导数下界或误差资格，不足以直接支持闭合反解。`RigidStorage` 还严格要求当前具体机械和理想气类，因此不能靠 duck typing 把固体塞进 gas_phases。

建议新建 `solid_phase.py`，提供不可变 `IncompressibleSolidPhase`，包含已来源准入的物种/晶相身份、摩尔质量、明确化学式或化学计量基准、温度域、热量模型原始系数及锚、参考压力 P0、恒定摩尔体积 vs、各项来源资产 hash/位置/版本、模型方法版本和原始分类。公开 `evaluate(T,P)`、`cv_j_mol_k(T)`、完整语义 identity。不同晶型不得共用一个含糊的 SiO2 列；有机组分若无明确摩尔基准不得人为赋予分子量。来源不足就保持待定或明确 fixture，不自动制造材料默认值。

首阶段限定 vs 与 T/P 都无关。若来源给的是参考压力的焓 h0(T)，应定义 `u(T)=h0(T)−P0*vs`，`h(T,P)=h0(T)+(P−P0)*vs`；此时 du/dT=Cp0(T)=Cv(T)。若把 h0(T) 当作所有压力下的 h 再做 u=h−Pvs，会引入不正确的压力储能响应。反应使用统一的标准生成能/参考元素基准，不能把任意热容积分零点包装为可反应的真实生成焓。Cp接缝、晶型转变、体积跳变都必须保留合法域，不跨缺口插值；本阶段可拒绝越界，不预设高温连续性。

另建显式 `SolidNumericalEnvelope`：每个 solid 的全域 u 误差、vs 误差、Cv 下界、适用温压域、来源/方法及资格。点值 Cp 正性不是全域下界证明。密度测量误差、化学组成偏差和模型偏差与浮点误差分开，未获严格界时只能作声明条件，不能声称经过严格误差传播的真值保证。制造物性及制造 envelope 的门禁从输入一直传到输出。

## 整体储能和反解

建议新建 `solid_fluid_storage.py`，定义 `SolidFluidStorage`，明确持有流体模板、solid provider 映射、Vbulk 和固体误差合同，接口：

- `evaluate_at_temperature(T, liquid_mol, gas_mol, solid_mol)` 返回完整固/液/气点值、Vs/available/Vgas、来源及误差资格；内部按当前 Ns 构造本次 RigidWaterGas 腔体，再调用原流体 forward。
- `temperature_from_energy(Utarget, liquid_mol, gas_mol, solid_mol, bracket, policy)` 每个温度试探都重新求流体 P(T)，并计算 `Utotal=Ufluid+ΣNs us(T)`。不得调用旧 fluid inverse 处理含固体的 Utarget，也不能用旧温度一次扣除固体能量。
- 新的整体 inverse 返回原流体机械诊断、固体点值与整体误差区间；不得把流体 inverse 的误差标签冒充整体结论。

固定库存、恒定固体体积时，压力路径和旧流体腔体相同：`Cclosed,total=Cclosed,fluid+ΣNs Cvs`。整体下界可为向下取整的 `Cmin,fluid+ΣNs Cvs,min`，前提是各全域下界确实适用；加入固体不会允许删除现有气相正库存要求。最小阶段依旧要求正的完整气相库存，纯固体/纯液体另设路线，不能靠给气体加 epsilon 解锁。

固体体积不确定性会影响压力，不能只把 ΣNs εu 加入旧 energy error：至少将 `ΣNs εvs` 和 bulk/相减表示误差加入机械残差预算，再以已有适用域内的体积残差斜率下界 Bmin 传播到 εP，并向上加入液相 `Nl sup|du/dP| εP`。名义无液体时原纯气解析分支也会因 uncertain available 获得额外 εP；不能复用原无液体零体积误差简化。恒定固体 us 不依赖 P，故此阶段无固体 du/dP 项。所有乘加除及最终温度区间保持有向舍入，整个压力误差区间必须留在有效域内。既有原流体 envelope 结果可作为组成部分，但扩展误差必须重新计算，不能冒称旧模块已经纳入 solid 占积误差。

固定外控制体、无动能/弹性/界面能的当前阶段，气体流入流出仍用同源供体 h，外边界能量账本不额外加一次 Pv；内部水相转移仍保持总 U 不变。固体在格内固定，没有固体面焓通量。未来固体变形/边界收缩若外边界移动，需要一致的边界应力功与几何更新；若含应变能、表面能必须加入总能量定义。仅让密度或孔隙率随迭代次数变化而不记功、库存、来源，不是烧结模型。

## 列映射、传输和水相接口

建议新建 `solid_fluid_heat.py`，保持旧 RigidFluidHeat 完全可用，同时引入显式不可变 `InventoryLayout(liquid_column_id, gas_species_order, solid_phase_order)`，返回各块精确索引。建议物理存储顺序为 `[liquid, complete gases..., solids...]`，使既有状态语义容易比较，但所有组装应使用索引，不能继续 `row[1:]` 就当气体。布局身份作为模型契约保存；单独的 ConservedState 数值数组目前不携带物种名，所以导入/恢复必须同时验证布局 ID/hash，形状相同不表示库存身份相同。

每个 cell 使用完整 storage inverse 的 T/P/Vgas 构造 GasState；复用已验证的 `face_exchange`、半格 conduction helper 和同一 gas_phases 供体焓，固体/液体面通量列置零。导热系数仍是显式有效材料参数，不能从加入固体库存自动获得。source 矩阵保留所有 solid 列，首阶段全零；这为后续按化学计量生成反应源留出真实库存位置。后续反应必须有元素/电荷/质量守恒、共享生成能参考和独立速率来源；已包含生成能时不再重复加标准反应热。

`WaterPhaseTransfer` 当前严格要求 type(base_model) is RigidFluidHeat，并直接检查 row[0]，不能原封不动套新模型。后续应先引入一个精确的 `FluidTransferHost` 协议或显式已支持主机 union，再让两种主机提供统一 `evaluate`、layout、水汽 caloric identity 与机械状态访问；保留旧构造行为和结果字段，同时为新的整体储能结果增加明确类型。水相 wrapper 只在指定液列减 r、H2O气列加 r，固体列不动；K、μ平衡和零液相退出规则保持不变。不要 monkeypatch 旧 decoder 或伪造 FluidHeatEvaluation 来通过类型检查。

## 独立验收建议与实施顺序

先固体 provider 与来源验收，再整体 forward/机械误差扩展及 inverse，之后多库存 Rates 接口，最后适配水相 wrapper。每步先登记容差并独立审核，旧模块零固体回归不删。

1. 常 Cv、恒 vs、单一理想气和无液体的制造解析解：`P=NgRT/(Vbulk−Ns vs)`，`U=Ns(us0+Cvs ΔT)+Ng(ug0+Cvg ΔT)`。验证改变 Ns 的占积与储能同时反馈；恒功积分终温与独立解析结果吻合。
2. 两种不同固相/摩尔质量/生成能/体积的显式列置换，核对每项质量、总体积和 U；相同数组形状但不同 layout 的重启输入必须拒绝。
3. 人工已知体积扰动±δVs的独立压力参考根及能量闭合，验证扩展 εP/εU/温度区间包含参考；包含无液体分支和接近无气孔的数值不可分辨情况，不靠点导数制造全域界。
4. 固体总库存固定的两格导热+气输运真实积分：全域 U 和物种账本守恒，供体 h 使用同一 gas curve；固体无越格移动。
5. 已有液水界面蒸发/凝结真实积分：总水、全部固体和总 U 守恒，增加固体热容改变降温/升温幅度，压力同时满足固液气体积闭合。独立常热容极限或高精度嵌套参考，而非用同一 inverse 当 oracle。
6. 非法身份/未知晶相/错误基准、域退出、manufactured 门禁、固体占积超过 bulk、可表示气孔接近零、缺少气体、数值预算用尽分别验证诚实分类。来源不足与数值失败不以补零热容或忽略固体降级成功。

这些步骤建立有真实库存位置的固液气中间态，尚不包括干燥毛细压力、泥料有效活度、氧化/脱碳反应、晶相转变、烧结动力学、收缩应力或成品强度。高温固体来源与低温水相域的交集必须实际核验；添加一个高温固体 provider 不会自动扩展低温液水的物性有效域。

## Quartz 来源核验对接备注

根代理本轮取得 NIST Quartz Shomate 原 HTML 与 JANAF O-037 表，报告 847 K 两分支 H−Href 分别 34.196/34.924 kJ/mol，标明 I↔II TRANSITION；差约 0.728 kJ/mol，S 差约 0.860 J/(mol K)，标准压力 0.1 MPa。此为根代理正在归档的来源核验事实，本设计未独立读取原资产，最终系数准入必须绑定归档文件和哈希。它明确阻止复用 ContinuousShomateGas 跨缝积分消去真实固相转变。首版只能明确选择一个单相温段，847 K 另一分支与未来相分率另建模型。石英热化学表不证明泥料含量、体积、热膨胀或具体烧结行为。

审核澄清：声明 solid u 误差必须包括原标准焓误差及 P0*vs 的参考能修正误差（常量、体积与乘加舍入），不能把 h0 误差直接改名。参考体积误差既进入储能参考，又进入可用腔体/压力传播，可以保守求和并明确相关性未利用。本轮根代理进一步报告原 Shomate 847K 两支实际差为 Δh≈729.127 J/mol、Δs≈0.857069 J/(mol K)、Δg≈3.18975 J/mol；这与JANAF表打印值差728 J/mol不能视为逐位相同，均保留各自来源和舍入精度。事实已归档 `data/sandbox/solids/quartz/facts.json`，原HTML在 `runs/sandbox/source-cache/quartz-20260907`。
