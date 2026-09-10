# 原泥 kg 固体 / mol 流体主机：实际代码审计与最小接入顺序

范围：只读审计；未修改仓库、未增加PDE、未搜索新物性。输入文件SHA保存在同目录INPUTS.json。目标仍为完整原泥到烧结砖模型，以下是解除实际软件阻碍的依赖顺序，不把无反应干燥阶段宣布为完整目标。

## 1. 已有可直接复用的能力

| 现有接口 | 可复用能力 | 实际限制 |
|---|---|---|
| `arlabosse_caloric.py:ArlabosseDryCaloric.cp`，88–92行 | 固定来源的干基比热；精确Fraction输出；每次操作复查元数据与资产 | 仅原85%工业/15%市政混合来料；35–105°C；拟合误差未知 |
| 同文件`delta_h`，94–99行 | Cp解析积分，J/kg干物；不需要干物摩尔质量或绝对形成焓 | 两端温度均须在来源域；不能外推到298.15K |
| `mass_wet_storage.py:WetMixedState`、`state/check`，160–167行 | kg干物、mol液水、mol气体、总U与模型身份 | 库存固体数量本身可以不是2，但当前储能构造器只接受MassSolid |
| 同文件`evaluate`，169–199行 | 真实水/气热力学、压力反解、容积舍入传播、总U与闭合热容、身份复查 | 固体项写死常Cp与参考网络；体積写死mass×常specificvolume |
| 同文件`invert`，201–214行 | 有界温度反解、能量/温度双误差条件、不剪裁、不无声越域 | 变量Cp时须正确给出整段导数下界 |
| `mass_wet_transport.py:WetPair.evaluate`，131–173行 | 内部相变库存转移、化学势方向、气相分压、共享气体面通量、扩散面温焓/对流供体温焓、导热 | 两格、A/B氧反应、单一界面以及制造运输系数强绑定 |
| 同文件`integrate_wet_pair`，202–237行 | midpoint、accepted prefix、取消/墙钟、共享面一次积分与反号应用 | 固定两格及正液相分段，不处理一般N格或真实新事件 |
| `mass_transport_bridge.py`的SharedFace/PairLedger/advance | 同样的共享面通量与能量记账模式，可作为干态回归参照 | 干态也强制MixedCell/A/B，不是现成通用关闭反应主机 |

## 2. 目前并非缺少“固体摩尔质量”，而是以下硬编码

`MassSolid` (`mass_storage_bridge.py:59–74`)同时封装常比热、常比容与manufactured分类，只允许制造系数。`WetMixedStorage.__post_init__` (100–128行)要求fully-anchored manufactured ReferenceSolution、指定NIST298.15参考、参考点严格处于温度域。Arlabosse来源域始于308.15K，直接替换Cp或把reference标签改成source都不成立。

`WetPair.__post_init__` (94–96行)强制固体ID为A/B、一个反应且向量(-1,2,-1,0,0)。`evaluate` (142、160–162行)即使反应速率常数取0，仍读A质量、氧参考、reaction[0]和反应能。因此“传rate=0”不能摆脱虚构A/B物种；它也没有表达“此阶段无化学反应”的独立语义。

## 3. 推荐的最小接入方式

保留旧`WetMixedStorage`/`WetPair`构造路径、默认语义、身份和测试。新源材料分支通过显式policy/typed adapter进入共享储能及运输计算；不能删去现有限制让新对象冒充旧manufactured主机。可以在现有模块提取公共聚合内核，并增加源材料构造分支/类型；这不是重新实现一个独立PDE。

**先定义干物储能适配器和反应关闭对象。** 干物适配器至少提供component_id、材料/基准身份、temperature_domain、source_ids/binding、`specific_sensible_u(T,T0)`、`specific_heat_capacity(T)`、`minimum_specific_heat_capacity(Tlo,Thi)`，以及独立的体积关系/证据。Arlabosse的既有`cp`/`delta_h`原样被调用，数值输入建议传`Fraction(float_value)`使主机的binary64含义显式，而不是无意切换为provider的float最短十进制语义。

在明确的**刚性不可压缩固体、常固体比容**假设下，固体Δu=来源Δh；可定义`u_s(T)=u_s(T0)+delta_h(T0,T)`，T0选来源域内例如308.15K，固定保守固体质量下u_s(T0)=0只是能量坐标。对应h_s=u_s+p*v_s。此假设属于适配器的条件性本构，不是来源测到了Cv；若引入热膨胀、可压缩或形变，必须补充dv/dT、压力依赖和机械功，不能继续声称Δu=Δh。**无反应且无固体质量输运时各固体参考常数完全不影响温度演化；无需形成焓锚点。** 恢复化学反应时才重新要求反应所需可识别参考差和组成闭合；不能用当前无反应零点跨反应运算。

建议明确`ReactionDisabled`语义：不创建ReactionNetwork，不访问reaction[0]，不要求A/B或氧参考；返回与真实固体列表同长的零kg/s，气体列表同长零mol/s，chemical_reference_power=0。液水↔水蒸气仍允许，是相变而非已关闭的化学转化。水液/气来源、实际摩尔质量、R与能量参考一致性检查保留，不把水的相变热额外叠加到总U。

**再接入储能聚合。** `WetMixedStorage.evaluate:191`的常Cp项由适配器的精确积分替换。193行energy_error继续只代表数值误差；Arlabosse未知拟合误差应另字段传播`unknown`，不能设为0或声称物理置信界。194–195行区分点值热容与整个温度反解区间的最小热容：Arlabosse斜率为正，可以在区间下端计算严格最小值并向下舍入。把当前点Cp直接加到`minimum_heat_capacity`会让207行残差/导数下界失去证明。源、材料、参考坐标、不可压缩假设、体积与不确定性策略必须进入binding。

源适配器接入本身只证明源码调用真实关系，并不构成材料包准入；新的真实闭合参数缺失应显式拒绝建模，不能自动回落到MassSolid默认值。

## 4. 真实体积证据还缺什么

来源元数据`data/sandbox/research/arlabosse2005/source.json`明确未提供intrinsic solid volume。现有172–179行需要`V_available=V_bulk−Σm_s*v_s`，然后水EOS在剩余流体空间内求液水体积与气体压力。来源干基Cp和初始含水率**推不出v_s或孔隙率**；湿bulk density、干骨架密度、粉体堆积密度不得互换。

可走两条物理上明确的输入路径：(a)同批同制样状态的骨架比容/密度及bulk几何；(b)独立测得的实际可用流体孔隙容积及bulk几何，直接给mechanical available volume。第二条不需要虚构固体摩尔质量，但仍须体积证据和误差，不等于设固体体积为0。两者目前都没有在此Arlabosse来源中落实；Nylen的另一材料球径/收缩不能填补它。

若比容带不确定性，现有176行只有bulk误差+浮点减法误差，需要新增各固体质量/比容对占据体积区间的贡献，并检查完整区间的正余隙。若体积随T或含水变化，原有“替换一个常porevolume”的闭合热容导数也必须重推，不能只在evaluate里更新体积值。

## 5. N格不是把len==2改成N

先提取`evaluate_cell`（储能逆解+显式反应/相变）和`evaluate_face`（相邻单元的气体通量+焓+导热），在旧WetPair里调用并证明N=2输出回归。N格主机应持有有序cells、faces及明确face-left/right邻接；每个内部面只计算一次，按拓扑关联矩阵分别加−/+到相邻格。现有`zip(...,(-1,1))`仅适用于单面两格，不能保留。

每个face的ledger需包含face_id、物种积分、导热、扩散焓、对流焓与总能量；cell ledger包含反应/相变源和边界源。对每个格先用Fraction聚合所有入出面，再做明确binary64投影及舍入累计；相邻格不应分别重算同一面通量。内部面总和精确抵消；外部热/气reservoir必须有独立边界账，不能当作无库存“第N+1格”而不计交换。

几何提供真实volume、area和每侧传热/传质阻力；平面half_width/area只适用于当前平面公式。球壳的守恒几何可接进同一face接口，但需要径向阻力/传递模型，不能把当前平面距离公式直接冠名球形。中心零面积面作为对称无通量边界，不应塞进WetFace.area>0构造器。

**必须扩展的下游：**

- `mass_wet_exact_stage.py:265–288`写死2格/2固体/3气体与无face_id的键；311–315写死12个库存多项式；335–342写死两格反号。
- `mass_wet_exact_controller.py:138`拒绝非WetPair/非2格；383–388单面能量及每格误差预算；N格时逐面一次记账与每格多面舍入必须保留。
- `mass_wet_writeback.py:28,89`限定AB和三气体，事件投影与不变量布局必须带真实固体ID/数量。
- `mass_wet_pressure_session.py:75–76`、controller_pressure等限定WetPair，两格状态context与cell索引。水EOS内部2×2数学求解是液体状态维度，**不是空间两格限制，不能机械改为N**。
- exact_record里的operator引用、mode长度、codec/version需显式扩展；旧record不能自动解码新N格类型。多格脱水先后/同时事件必须逐格排序和去重，不只支持两个事件。

## 6. 实施依赖顺序与能证明什么

1. **固体caloric adapter +明确关闭反应：** 接入Arlabosse来源函数、域内参考坐标和导数下界，单格检验ΔU/逆解、参考平移不变性、真实材料ID，无需A/B。纯储能适配器可以先完成，缺体积时不伪造完整湿格实例。
2. **有来源体积契约及源湿储能构造：** 共享现有RigidStorage聚合/逆解，保留液气参考与数值误差；实际体积证据缺失明确阻止来源材料运行。不要因缺物性而停止第1步的软件解耦。
3. **抽出cell/face计算并保持旧两格行为：** 原AB反应回归不变；关闭反应分支明确无氧消耗、无固体转化，仍保留相变及共享总U通量。
4. **N格固定网格积分+面ledger：** 使用相同cell/face内核和几何接口，检验内部通量抵消、边界能量/物种平衡、失败保留prefix、非均匀网格与N=2回归。不能把N格固定步路径声称为已有exact事件控制器验证。
5. **N格exact stage/event/pressure/record迁移：** 以真实布局生成库存键、面键、误差预算及脱水事件；保存原策略门槛、整体墙钟、query累计及旧codec拒绝边界。
6. **来源材料实算与公开观察比较：** 使用匹配材料的caloric/体积/传输/水活度等关系；Arlabosse只能其自身低温域，不能冒充Nylen/Wang配方或完整高温原泥。反应、烧结、形变仍需要后续完整范围工作。

最优下一编码任务是第1步连同第3步所需显式NoReaction接口，直接解除真实源比热被AB网络挡住的现有内核限制；不是再建一种几何演示，也不是为了跑通而填制造密度。
