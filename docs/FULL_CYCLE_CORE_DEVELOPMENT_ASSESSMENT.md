# 当前完整模型目标：能力与验收缺口评估

P59 原生完整signed S输出/replay已静态实现（2026-10-02T20:50:29.822311+00:00），尚未生产执行或replay，0constructor/RHS/Jac/ODE/physicaloperator/fit/UQ/search。共享gas summary复用已有completeS及原生累计末两槽，无新状态/热源/物性/采样rate求积；按各区间起点分别作差，保存signed/abs/relative/原尺度和阈值完整record，旧native熵误差/flags不改。直接文件stdlib重算只读必需新字段，P57/P58缺序列不回填；package -m会导入模型，不作为此纯入口。原escale仅初凝聚相参考Cp尺度，不含孔气Cp。根681=144literature537assumed0measured，旧669完整records/所有旧live合同/名义配置保持；新增12为未分配两stage边界记录，无材料物性增加。两互异stage end5/10×time_scale6→实际0–30/30–60，原T/gas/geometry/tols/step/domain/原生初态保持；未来1ctor/1integrate/2solve_ivp(中点restartBDF)，900s/12MiB仅提案，完整manifest估算另列，不能提前运行或称非零起点已验证。当前矩阵directcycle absent/P41非均匀未实现已精准归历史，生产能力/元数据/材料/待执行验收分层；观察候选不导入，inverse/UQ Ca留存未改。P58最终158必要路径12922129B>12582912B超339217B，预检及actual资源均FAIL/partial；旧数值PASS不追认。P34/P40/P44/P45/P50撤回/P51失败、名义余水0.135892078740%>0.1%、CaO零预算nullfalse及wholefalse全部保留。科学、静态实现、工艺、材料、Git/Drivemetadata/实际恢复/历史容量分别判断。

当前具体剩余项：生产新ledger/纯保存replay尚未执行、独立完整势导数/原8段及三方案反演验收未通过；观察声明条件候选未整合、inverse/UQ Ca证据留存未实现；材料参数待同批实测。下方完整P58评估原样保留为历史提案，其“拟改/本轮未实施”属于P58当时，不是P59当前状态。

## P58 历史目标评估原文

状态：静态评估完成，后续研发范围为提案；本文件不分配科学预算或宣称模型完成。

当前目标是单砖湿坯→干燥→升温反应→烧结→冷却的可替换近似模型、至少三方案条件化比较及观测/标定接口，见 BRICK_PHYSICS_PROJECT_SPEC.md「当前目标和顺序」「现行§0.5」。不要求已代表本厂砖，不扩整窑/完整微观相图/UI。参数数量、低温synthetic时长、旧P01–08勾选都不能代替当前组合验收。此次评估只读既有源码、缓存公开证据及报告；未新检索、构造、拟合或执行后续物理代码。

| 类别 | 当前具体事实 | 所需下一工作 |
|---|---|---|
| 真正生产输出缺口 | 完整S已算、累计产生与交换已原生积分，却未持久完整signed序列和逐阶段账本 | 直接输出已有量与区间起值，无新state/heat/物性或rate求积 |
| 真正既有材料条件接口缺口 | observation_contract.condition_parameter_keys遗漏recipe.portlandite | 沿现有固定条件合同补该成分，不新增泛化校验；当前targetnull，不能称已有实材误准入 |
| 真正下游证据留存缺口 | inverse.forward_audit、UQ比较未完整保留新calcium_phase_ledger及当前热力学资格 | 将实际前向report必要字段接入既有audit，不再解模型、不把oldflag当三相PASS |
| 已有科学能力而新验收不足 | 热物性/有限孔气/持水/三相Ca/直接通道/有限速率相态/热弹性/黏度/八阶段调度均存在 | 为最新组合另登记受影响守恒/热力学/一次time及space、独立势导数证据；低温时间比较不能替代 |
| 必须目标材料信息的鉴定 | 库存/孔结构、持水、反应速率、黏度/模量、真实产品映射 | 明确同批试件/条件/原始数据，未知保持null，不能以文献类比或synthetic拟合升级measured |

## 已实现能力与证据边界

drying_ramp/drying已有混合与结合水自由能、双向汽液相交换、共享液水和孔汽输运（full_cycle_gas.py:523）；heating/reactions已有共同化学势、有限供氧、有机竞争反应、Cc/CaO/OH三相及条件化direct通道（:649–684）。sintering/hold已有相态、载体生成、本征应变、相依模量与结构黏度（full_cycle_solid.py:86,235,449）；cooling/cooling_hold保留石英应变、有限速率玻璃代理及骨架U/S（:329,505）。气体壁阻/成对阻力及Darcy携能已在gas.py:317，八阶段积分已在:816。没有新的证据要求重造这些科学方程；完整光谱、全相图、损伤、窑炉燃烧不在当前必要范围。

P34具全温程历史普通预算证据，但相预算30/81未通过；P40/44的原网格及phase/strict失败保留。P45原12格净U判据FAIL由P56保存操作归因，当前不支持擅改物理核，也不证明任意状态正确。P58只给固定60s26格的原四量时间比较；60s空间/一般全状态/独立势/全八阶段尚未完成。原名义干燥0.135892078740%>0.1%，不得用关闭机制或延时synthetic结果替换。CaO0预算null/passedfalse，不可改用总Ca池分母求PASS。

## 已有公开依据可继续什么，不能继续什么

USGS Bulletin2131的既有缓存 carbon-gas-thermochemistry-v1/source.json、hydrogen-steam-thermochemistry-v1/source.json及calcite-thermochemistry-v1/facts.json已保存Cp多项式、h/s参考和温域；原来源链接 https://pubs.usgs.gov/bul/2131/report.pdf。这些已读记录支持现有源限定热化学与同源能熵记账；新熵账本只是将已有存储/原生积分量输出，不需要额外物性。书中标准压力纯组分来源不能识别砖的宏观动力学或消除工程外推。此次没有从未读原论文推断新的物理参数。

Cantera缓存 DustyGasTransport.cpp/.h 与根dusty_gas_host说明支持其声明的气体摩擦关系，实际砖孔结构、非等温延伸和有限离散仍是assumed；不能以纯气来源判砖内输运准确。Wadsworth玻璃孔类比也不提供本砖孔径/表面张力实测。现有Criado/Steiner参考数据有各自转化/湿度/钝化定义，但direct-carbonation-workpackage-f/evidence.json仍缺目标砖负载/有效面积/局部气氛分离；Arias的A/E属于脱水，不能改充direct迁移率L，更不能把当前synthetic L扩到高温。

DTU P17已读同试件称量和实验定义足以实现可选的原始干/饱和/水下称量→吸水率/开口孔隙/体密度来源适配器（FULL_CYCLE_P17_APPLICABILITY.json:446,630）。三指标共用称量，不能视作三份独立验证，也不能直接识别host连通系数。该来源材料是SSA及黏土，Raw仍为焚烧灰，不是原污泥动力学。当前已有reference观察接口及Saeki双DoC/source_tg接口，不应把已实现接口再列缺能力。Septien有效k条件不齐与纯气k不能叠加的边界仍保留。称量适配器有公开来源足以开发，但不是本轮选定核心先决项。

## 最小目标材料数据，按识别目的分开

任何实测拟合先要材料/配方/批次和原文件定位，同试件几何/初始干质量/水质量/干燥基准、完整温程/总压/气体组成/共同时间原点及测量单位。干燥还需同批质量或液水时间序列和表面/内部温度，MR/湿基转换必须有同源分母。direct/OH需初始和随时间CH/Cc/CaO分相、明确分母和初始碳酸盐，以及RH对应温度/总压；仅失重或总CO2无法唯一归给direct。烧结需同试件尺寸变化与热程，产品需烧后干/饱和/水下称量；强度另需加载/几何协议，缺陷需明确定义。保留原始重复和仪器不确定性，残差scale不是测量误差。无需先收齐工厂历史；可以先针对一个明确参数子集提供数据。缺实测不阻下面的代码闭合，仍是0measured。

## 下一最有价值具体研发范围：原生完整signed S账本

既有gas.py:802已经积分Ip/Ie，:976–985计算完整S（凝聚、气体混合、持水及骨架/相态），:1170只有entropy_error，:1224–1225主要留下maxabs/relative。P57/58落盘没有三个完整累计序列，从最大残差和采样rate无法恢复；不能事后rate积分补成原生证据。

拟改 full_cycle_gas.py 原summary保存S、Ip、Ie signed J/K及times；full_cycle_diagnostics.py 增加全窗口/每阶段报告，仅使用既有量。原区间i的定义：R_S(t;i)=S(t)−S(i)−[Ip(t)−Ip(i)]−[Ie(t)−Ie(i)]。原尺度escale/Tr、acceptance.entropy_relative不改；各段必须分别减其累计起值，不能套全程零起点。当前native两个初槽为0，尚无证据说明现式使P57/58错；此工作是必要输出能力补齐，不是已有误差修复。根合同与既有离线producer只选择新输出；不加状态、热源、率求积、物性或独立算子。保存同源S闭合仍不是独立完整势导数验证，也不提供每个熵产分支的独立累计量。

独立预算建议仅是提案：先实现并静态核对，再单独批准1job/worker/attempt/constructor、2个既有低温stage的native solve_ivp，在一个900s固定窗口/完整必要≤12MiB内验证nonzero阶段起值与signed账本；提前明示2ODE，不能伪报1ODE，无retry。这是生产区间账本验收而非继续时长/精度窗口循环。此后回到最新核原八阶段受影响验收，先独立登记有界数值预算及真实适用域；不能为高温场把synthetic directL290..350K扩大，不能以directoff结果代替direct机制资格，不能替换名义工艺FAIL。若域输入不足，报告该明确缺口而非继续低温加密。

P06 portlandite固定条件与Ca账本audit留存是下一独立最小接口范围，可沿现有合同/报告修接，不重写校验或反演。三方案/反演/CLI代码已存在；在当前核和新字段接线后仍需真实离线入口与明确限定演示验收，旧24次UQ与synthetic恢复不会自动授当前范围/概率/材料准确。qualified_fit的优化成功/满秩/前向flag也不代表全局唯一或过程达标。

本轮未实施以上后续代码或分配其预算；未新增测试/SHA/护栏/环境参数/物性/搜索/恢复/历史清理。下一决定由父任务采用。Git/Drive、实际恢复与历史存储保持独立于模型/物理/工艺/材料判定。
