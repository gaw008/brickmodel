# P76 原降温与降温保持实际结果

P76 原cooling与cooling_hold两段真实完成：hold133200→154800→162000s，共用窗口wall81.361072333s/CPU80.567048000s，八科学文件合计4012487B/4194304B；2CLI/load/ctor/原BDFsolve/新y275/source51端点，0initial/势/state_dynamics/summary/fitUQ，第二输入严格是首段实际输出，deadline重置0/重试0。真实RHS23116/Jac134；降温端T327.619110–333.983568K，最终T298.153449–298.154181K。实际原8stage端点及5原生continuationlinks齐全，但无保存t0原生y或完整各端U/S库存，producer原prefix/fullcyclefalse保持；不等于物理验收。两冷端域内不授温热中途source/material资格，三项高温assumed延拓、原干燥FAIL与其他失败保持。758records原样、144literature614assumed0measured、criterionNA/wholefalse。下一最小9state完整库存/端点账本候选仅登记未采用未启动；不自动重复瞬时投影。详见docs/FULL_CYCLE_P76_COOLING_COMPLETION.json/md。

|阶段|区间 / s|端点温度 / K|BDF nfev/njev/nlu|实际 RHS/Jac|原生长度|
|---|---|---|---|---|---|
|cooling|133200.0 → 154800.0|[327.6191101277857, 333.9835684767656]|[1344, 63, 240]|[11172, 63]|275|
|cooling_hold|154800.0 → 162000.0|[298.1534491344298, 298.15418102321024]|[868, 71, 250]|[11944, 71]|275|

首段实际写出的 native-checkpoints.json 就是第二段严格加载的输入，全部原生状态、累计原点、物理参数和机械参考保留。原工艺终态冷却温差 0.0041810232102648115 K，对照根参数 1.0 K，此独立端点门槛为 True；完整工艺仍因原名义干燥失败而未通过。

|阶段|q 范围|q signed 变化|char signed 总量 / mol|
|---|---|---|---|
|cooling|[-2.299768356119118, -2.291209573468879]|[-2.299633257126888, -2.2910680926239024]|-7.928085616090529e-19|
|cooling_hold|[-2.299768356119118, -2.291209573468879]|[0.0, 0.0]|5.707842076253811e-19|

负 q 和微小负 char 不裁剪；本段没有额外计算相分数、固相库存、相变功率或势导数。

|阶段 / 账本|累计值|本段 signed 增量|
|---|---:|---:|
|cooling / heat_j|81329.51350363476|-201469.86819343484|
|cooling / carried_energy_j|772123.2085396524|-1954.294541794328|
|cooling / exterior_pressure_work_j|0.09504890496134821|0.17456026108967843|
|cooling / entropy_production_j_k|357.518193406542|11.785993968378074|
|cooling / entropy_exchange_j_k|-499.15158430164894|-294.86440069577515|
|cooling_hold / heat_j|75513.17055697962|-5816.34294665514|
|cooling_hold / carried_energy_j|772121.7575199917|-1.4510196606841312|
|cooling_hold / exterior_pressure_work_j|0.10007737960332652|0.0050284746419783175|
|cooling_hold / entropy_production_j_k|358.5437827486998|1.0255893421578137|
|cooling_hold / entropy_exchange_j_k|-518.6006538426648|-19.449069541015817|

七反应及四气体 in/out 的累计 mol 和本段 signed 增量保存在配套 JSON。已有热、携带能、外压功和熵积分槽不等于完整储能/库存残差，不能仅凭这些槽给出守恒 PASS。

|实际端点|时刻 / s|源文本数|
|---|---:|---:|
|drying_ramp|14400.0|50|
|drying|86400.0|50|
|heating|97200.0|50|
|reactions|115200.0|51|
|sintering|126000.0|51|
|hold|133200.0|51|
|cooling|154800.0|51|
|cooling_hold|162000.0|51|

从 P68 三段到 P71/P73/P75/P76 共八个原工艺端点；五次 continuation 的 origin 与此前实际 native_y、stage、time 普通逐值一致。所有 758 原物理记录、完整 context 及各自完整 50/51 源文本对照本次冻结一致。此处只做文件身份和原始字段比较，未动态重载旧端点或重算旧轨迹。producer 原有 prefix_completed=false/full_cycle_completed=false 保留，另列端点覆盖事实。

|类别 / 物种|源温度范围 K|cooling低/高于格数|cooling_hold低/高于格数|
|---|---|---|---|
|caloric/O2|[298.15, 2500.0]|[0, 0]|[0, 0]|
|caloric/N2|[298.15, 2500.0]|[0, 0]|[0, 0]|
|caloric/H2O|[298.15, 2500]|[0, 0]|[0, 0]|
|caloric/CO2|[298.15, 2200.0]|[0, 0]|[0, 0]|
|caloric/calcite|[298.15, 1200.0]|[0, 0]|[0, 0]|
|caloric/lime|[298.15, 1800.0]|[0, 0]|[0, 0]|
|caloric/portlandite|[298.15, 700.0]|[0, 0]|[0, 0]|
|viscosity/N2|[120.0, 1700.0]|[0, 0]|[0, 0]|
|viscosity/O2|[120.0, 1700.0]|[0, 0]|[0, 0]|
|viscosity/CO2|[100, 2000]|[0, 0]|[0, 0]|
|viscosity/H2O|[273.16, 1173.15]|[0, 0]|[0, 0]|

两个新冷端温度在列出的源范围内，但 P75 输入约 1223.15 K 与温热路径仍涉及 portlandite caloric 700 K、calcite caloric 1200 K、H2O 黏度 1173.15 K 三项原 assumed 数学延拓。端点域内不能反向验证中途 BDF/Newton/complex 采样或目标材料，0measured 不变。

下一最小工作是读取八个实际原生端点，由已有 native_potential_state 和 potential_values 给出完整固/气库存、体积及原 global U/S，再与原累计槽做区间差。无须再次做 14 方向瞬时投影，也不需重算 ODE。原 P68 没保存 t0 原生 y，因此若要八阶段及全程账本，需另范围明确调用一次真正的 initial_state，生成新的同源名义初始参考，并标明其并非历史原始 y 的恢复。只用已保存状态则最多覆盖 drying_ramp 末端之后的七区间，不能把缺失首段或全程写为 PASS。

仅登记下一独立候选：1load/ctor、1真实initial参考、8实际savedendpoint、9native_potential_state/9complete_potential_values，0RHS/Jac/ODE/rates/梯度/state_dynamics/summary/fitUQ；根参数既有120s/全科学4MiB/完整64MiB和原八reserve+2MiB重新核算。其生产导出代码、根合同、归一化和实际执行都不属于本轮完成项。

|验收项|本轮真实状态|
|---|---|
|原8stage端点覆盖及续算连续性|已核对保存字段；不是物理验收|
|完整全程/分段质量、元素、U/S|未新增计算；缺完整库存和真正t0参考|
|反应和相变热只计一次 / 热力学|源实现保持；本轮未授新完整验收|
|最终冷却温差|既有独立端点门槛通过|
|原名义干燥|历史FAIL保留，不由冷却端点替代|
|受影响时间/网格加密|未完成最新实现验收|
|最新三方案/反演|未完成最终更新|
|目标材料 / 实测|待实测；0 measured|
|模型整体|whole_model_complete=false|

已有 CaO 零预算 null/passedfalse、P34/P40/P44/P45/P50撤回/P51/P58/P60/P61/P63、微小负库存与旧成本受限失败保留；旧固定渗透率 UQ 和 syntheticdirect290–350 不验证新机制。

本次仅七 root/docs 文件正常后继提交并普通推送，原 Drive 目录一次必要增量及名称/大小/父目录读回；实际恢复 0，完整历史轨迹/独有Git/history20GB/GitHub容量未解决。完整最终分配与收据在 runs/full-cycle/p76-native-cooling-completion/final-delivery-state.json，末收据不递归提交或补包。
