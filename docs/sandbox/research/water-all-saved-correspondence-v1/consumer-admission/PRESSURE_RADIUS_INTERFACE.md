# 原生水 pressure_radius：下一步可实现的接入合同

结论：**不需要先证明“所有可能物相和所有 EOS 数学根的全局唯一性”，才能在明确选择的普通液水模型中计算条件性压力区间。** 需要明确选择物理分支，证明本次区间计算确实沿该分支得到局部根，并诚实保留原 U、Cp 和体积误差假设。全局热力学稳定性、模型有效性和区间算法正确性是不同命题。

本方案只针对当前 `mass_wet_exact_stage.pressure_radius` 的普通湿态拒绝路径，不要求先覆盖整个温压域，不改变原六项比较阈值，也不把制造误差包络变成实测或原生通用证书。

## 1. 来源支持的模型选择，不伪装成全局定理

IAPWS-95 官方 2018 发布第 4 节和表 3定义普通水流体 EOS 及液汽共存条件；第 5 节说明从熔化压力曲线起的稳定流体适用范围。这支持将已声明的 295–310 K、10⁴–10⁷ Pa研究域建模为普通流体水，并用与液汽共存相关的高密度液体支解释请求的 `phase='liquid'`。它不提供我们的 Python 数值实现对所有根的自动形式证明。辅助饱和公式与完整 EOS 不完全相同，只能作为初值。[官方发布](https://iapws.org/relguide/IAPWS95-2018.pdf)

当前 `_heos_kernel.state_tp` 已采用显式 phase、饱和压力侧别、原模糊带、原生相标识和密度侧别检查。因此“采用普通液水支”本身是现有物理模型约定，并非为绕过新数学检查而创造的额外物性。模型仍是纯水平面界面与理想混合气；不是含盐孔隙水、毛细液体或任意砖料的相图。

新增不可变 `LiquidBranchModelPolicy` 应记录：`iapws95_ordinary_water_liquid_branch` 模型名称；官方文献资产 SHA/定位；固定 provider/原生实现/系数 JSON身份；原温压域；明确的物理分支解释与未覆盖物理效应；误差包络原分类。其物理分支解释必须写成 **source_supported_model_selection**，不能写 `global_stability_proved=True`。对于这个已选择模型，分支对应关系是明确前提；区间求证器负责验证所选局部共存盒及机械根的联系。

不要求为每次 pressure_radius 调用另证明全部冰相、任意亚稳根或极远密度上的全局 Gibbs 最小值。若以后请求接近熔化边界、临界区、过冷水、盐分或毛细作用，那是模型范围变化，必须另立合同，不能沿用当前标签自动接受。

## 2. 每次实际查询的不可省略检查

建立 `BoundLiquidPressureRequest`，由当前已完成的实际 `WetCellRate` 构造，而非从调用者 JSON 或历史成功列表导入：

1. 固定 pair/storage/cell/interface、原状态 kg/Nl/Ng/U、inverse target、原 reference、provider descriptor/source/实现与实际回调绑定。核对原 minimum Cp>0、能量误差非负、保存 epsilon 不小于精确 `(abs(U(T)-Utarget)+E_U)/Cp_min`，并保留原 inverse policy 检查。原合同是否物理成立仍是条件，不由这一不等式证明。
2. 使用原完整 `[Treturned−epsilon,Treturned+epsilon]`；要求原 storage 温域和原逆解 bracket 包含。不缩小 T、不改 epsilon、不用名义点替代区间。
3. 从原状态重算有效体积 `Vbulk−Σm_s v_s`，保留原 bulk 误差与 `Nl*liquid_v_error`；使用 `scale=Mpublic/Mnative`、`v_public=scale/rho_native`。EOS 用 native R，气体闭合用原 Rg。均用 Fraction 或有向区间运算。
4. 对全 T 的局部液汽共存盒验证严格 Krawczyk 包含、合法加权范数<1、液汽密度顺序与全盒正 D，及两相压力交集。辅助公式/点 Newton只是数值候选。模型 policy 指定其普通液水分支解释；数学记录仅声称这个盒中的局部结论。
5. 对本次 T/V/rho 矩形验证两个密度面的严格残差异号、全矩形正机械导数和正气体体积。证明全参数矩形的局部机械根及压力区间。
6. 用全 T 的正 `dpEOS/drho` 管无缝连接整个共存液体框至整个机械根框。严格检查 `P_lower > psat_upper + ambiguity_upper`，保持现有 `max(.01,2e−8*psat)` 的保守上界。只验两端或抽样导数均不接受。
7. 绑定本次实际 native 液体输出。固定返回 T/P/rho 做区间残差、严格根面和全局部盒正斜率检查，计算密度误差→public体积误差，并显式加入实际 host `(Nl*Mpublic)/rho_mass` 的舍入项。必须不超过本次原声明；失败拒绝，不能自动扩大声明。此检查只证明实际固定查询的数值差异，不证明全 T 域上的所有 native 调用误差。
8. 检查实际返回密度属于本次已证液体管；固定查询的压力/温度与 inverse 内机械输出及当前 equilibrium snapshot完全匹配。若需扩展管到实际密度/固定查询根盒，重新证明完整扩展管，而非取区间并集后继承证明。这样不会仅凭另一个正导数盒，就把另一局部根当作同一液支。
9. 完整压力区间须在原 envelope pressure domain 内。来源与预算前后均核对；未解决、超时、来源变化或数学失败全部拒绝。

步骤 8 是从离线证据走到消费者时建议增加的明确连接检查：现有独立 fixed-query 成功和 coex→mechanical 成功不能在没有几何包含核验的情况下简单拼接成一个泛化证书。

## 3. 返回内容与实际 consumer 变更

新增模块建议 `mass_wet_pressure_interval.py`，暴露具体实现 `IAPWS95LiquidPressureProvider`，不接收任意 `pressure=lambda ...` 作为生产证明接口。低层 generic callback求证器继续仅供内部/纯测试使用。

接口建议：`evaluate(request, *, branch_policy, budget, cancel) -> LiquidPressureEvidence`。请求来自当前实际 rate，证据包括：原查询 digest、完整 T/V/P 区间、原 fixed-T误差、source before/after、共存/管/机械/固定查询计算记录、实际成本和失败阶段、原包络分类及模型 policy ID。用严格不可变类型封装；消费者核对请求身份，不能接受手工 `proved=True` 字段或过去 16 个点的缓存条目。成功证据仅对完整相同请求有效；来源、U、库存、模式、域或误差改变都令其失效。

目前 `pressure_radius(pair,state,inverse,cell,fixture)` 没有液态 native snapshot；`WetMixedInverse.point` 也未保存 native 密度。**优先传入已有 `WetCellRate.equilibrium.liquid.state`**：它已经在实际 `WetPair.evaluate` 中产生。stage的 full/fine比较和 controller的 event/common比较均可取得这个 rate。核对该snapshot的T/P、provider/原完整reference与机械液体体积。不要偷偷在 `pressure_radius` 里重复一次native查询，并把新值当原求解所用值；若将来必须新增查询，要明确计费、保存其身份，并核对与原体积的对应。

保持旧 fixture 参数位置，新增可选命名参数，如 `liquid_pressure_provider=None, liquid_observation=None, evidence_sink=None, budget=None`。dry路径与现有constant fixture路径保持现有数值；普通wet仅在显式选择上述source-bound provider及branch policy时启用。默认无provider仍 `pressure_temperature_envelope_unavailable`。

最终返回的 Fraction 仍是：

`max(abs(Pnominal−Plo), abs(Pnominal−Phi)) + original_fixed_T_pressure_error`。

不减重复误差，不把点native残差单独充当该全区间半径。现有 full/fine 和 event/common比较继续使用两路径各自半径，与原 `pressure_absolute_pa` 比较；kg/mol/U/T/time门槛完全不变。证据进入试算结果/失败诊断，由消费者保留，不改变既有原子提交语义。

为避免隐藏计算预算，provider内部每次数学EOS/区间回调记录实际entered/completed和来源，并接入原controller累计wall/cancel；新增数学求证预算显式配置且单独计数，不能冒充现有host evaluate次数。预算耗尽返回未解决；不能使controller已有实际成本或失败前缀归零。每个比较可能需要多个证据，不能只给每次内部调用重新开一个无上限的wall预算。

## 4. 条件性研究接入与“验证过的 native 模型”不同

可以立即实现的目标是 **conditional_native_liquid_pressure_interval**：在原显式包络/minCp/U假设及指定普通液水支下，给出每次实际查询的严格局部数学压力区间。调用者需要显式接受这一模型合同，结果应继承当前 `manufactured_solids_and_conditional_declared_water_numerical_envelope_not_material_admission` 类资格。

不能因为此次增加 pressure proof就让一个要求“所有误差已由物理来源保证”的上层服务把这些条件消失。若上层资格要求真实的全域 U/Cp/native误差证书，当前仍不满足，应返回资格不足。**这不是要求全局物相唯一性；是原能量和数值误差前提仍未独立闭合。** 两者不可混淆。

原 NEXT_INTERFACE 中“任一身份缺失，ordinary wet不得接受”应精确理解为：物理分支对应关系必须显式、可追溯，局部连接必须核验，native固定query必须核验；不应增加“必须穷尽所有物相”或“必须先证明整个295–310K/10⁴–10⁷Pa矩形”的额外门槛。后者是覆盖能力目标，未覆盖的具体查询可返回unresolved。另一方面，原scientific比较门槛和资格要求一项也不能降低。

## 5. 下一实现的最小验收包

先抽取已审区间原语为可导入模块并固定依赖/source manifest，再实现 request/evidence/adaptor，最后改stage/controller两处比较的参数传递。不要先改既有HEOS求解路径或全局缓存。

必须以纯负控验证：错误cell/U/库存/provider/新旧质量常量；来源回调中变化；原epsilon缩小；T/P超原域；共存strict包含或范数失败；管缺口/非正导数；query密度不在已证同一管；native体积差异超原声明；名义点成功但全T失败；预算/cancel且前缀仍在。原dry和fixture调用数值回归保持。

实际native验收先跑一个新鲜当前query，保存其真实host/equilibrium及所有数学证据，再做受预算控制的full/fine比较。原16已保存端点只用作回归证据，不能作为消费者新调用的通行证。只有原六gate按新鲜实际两路径通过，才有本次试算的数值接受；仍不自动取得全局物相、材料预测或上线控制资格。
