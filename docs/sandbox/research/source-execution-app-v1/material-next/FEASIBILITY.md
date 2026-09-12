# 下一项材料闭合可行性：Arlabosse 同源湿态焓 / Cp

结论：**现有已核来源仍不足以准入带实测不确定度的非等温、变含水率湿污泥焓 / Cp 闭合。** 但“原文没有湿 Cp 公式”也不准确：本次实际查看了 Arlabosse2005 原 Eq1，作者明确报告质量加权式。它是有出处的近似，尚不是同污泥湿态量热及其误差证据，也不能自动与 95°C 的束缚水热 / 活动度组成一个已验证状态函数。

本轮只有来源核查和此报告；未改生产代码、未运行物性 / 原生模拟、未重做数字化、未提交 Git、未派新代理。现有 Arlabosse95 离散接口及干基 Cp 已完成，不重复计为新闭合。当前其他代理的工作区修改保持不动。

## 实際取得什么

| 来源与实际读取状态 | 可用方程 / 数据 | 限制 |
|---|---|---|
| Arlabosse2005 缓存出版 HTML，`Specific Heat`，HTML1108–1129；原 Eq1 GIF 本轮下载并实际 `view_image`；既有 Eq2 GIF也实际查看 | `cp_wet(T,W)=[cp_DM(T)+W cp_water(T)]/(1+W)`，单位 J/(kg湿料 K)；`cp_DM=1434+3.29 T_C`，干污泥实测温域35–105°C | 原文只明确叙述干污泥 C80 测量；未给湿态实测 Cp 表、含水范围实验校验、拟合残差或混合近似误差。水的状态/压力及束缚效应不能由这个式子默认为已验证 |
| Arlabosse2005 `Sorption Isotherm / Total Heat of Desorption`，HTML1135/1145；原 Fig1/2 及审核事实已核读 | 95°C 的9个离散 `aw(W)`，6个 `q_total(W)`；3个热量 unknown。q_total 为 J/kg移除水，含汽化贡献；已有 `RT ln aw` 为相对摩尔化学势 | 不是连续支持域；同分样、同测次与湿态校准误差未知。没有第二温度同身份数据 |
| [Ferrasse & Lecomte2004 作者上传全文](https://www.researchgate.net/publication/223808349_Simultaneous_heat-flow_differential_calorimetry_and_thermogravimetry_for_fast_determination_of_sorption_isotherms_and_heat_of_sorption_in_environmental_or_food_engineering)，先前本审查实际读过HTML渲染正文，printed1366 Eqs3–5、1368–1369 Eqs21–24及§3.2；未读PDF页图、无本地原PDF | 总热 / 等量吸附热 / 潜热关系；校正热流与失水率关系；热量对等含水率蒸气压力温度斜率的解释 | 方法采用样品平均状态和传递近似；不能把其他材料的测温误差、扩散系数或模型误差移给这份污泥 |

变量约定：`W=m_water/m_dry`；以下 `H(T,W)` 均为每 kg 干物的湿体系焓，`R_s=R/M_water`；所有需要参考态的关系均须先声明相同水/蒸气参考与压力约定。

## 非等温缺口的位置

写成分析分解，而不是现有已准入模型：

`H(T,W)=h_dry(T)+W*h_liquid(T,p)+H_ex(T,W)`。

在相容的水相参考和原方法热力学解释成立时，等温移除单位水的热满足

`q_total(T,W)=L_water(T,p)-∂H_ex/∂W`，

因此95°C的热读数最多约束该温度的**含水方向导数**，且仅限可读节点。它们没有给出连续 `H_ex(T0,W)`，不能跨缺口积分；更未给出

`Cp_per_kg_dry(T,W)=cp_dry(T)+W*cp_liquid(T,p)+∂H_ex/∂T`。

原 Eq1 相当于在这项分解下忽略 `∂H_ex/∂T`。若把它当作严格全域闭合，还会隐含 `∂(q_total-L_water)/∂T=0` 的交叉导数条件。当前来源没有验证该条件，也没有它的误差上界；不能因为公式见于原文就把这项温度导数当作实测为零。

活动度值给出 `mu_ex=R_s*T*ln(aw)`；即使有相容潜热可借助 Gibbs–Helmholtz 将 q_ex 转成单温的 `∂ln(aw)/∂T`，仍不识别湿态 Cp 所需的更高温度信息。缺项包括：同身份湿态 `Cp(T,W)` 或相容的多温量热/吸附数据；温度导数及误差；连续含水依赖；反应禁用条件；同基准参考差；若进入 U/T 逆解则还需要 `H-U=pV`、体积及压力响应。非反应固定组成的显热差**不要求编造绝对形成焓**，但这并不补出变含水率的参考桥接。

故：作者 Eq1 可登记为 `literature_constitutive_model`，误差保留 unknown；它不能提供“从真实实验获得的湿态不确定度”。当前已存在纯水+干物热储存，再包装同一加和式不是新的束缚水闭合。

## 原引用内仅跟进两条

1. [Arlabosse et al.2003](https://www.researchgate.net/publication/244603142_Comparison_Between_Static_and_Dynamic_Methods_for_Sorption_Isotherm_Measurements)，DOI `10.1081/DRT-120018458`，由2005原文参考B1直接引出。实际读作者上传原全文的文本：printed484–485 Test Materials、490–491 Fig4/Table2、492–494污泥比较及结论。多温25/35/50/90°C数据和BET/GAB表针对MCC；两份污泥为同一城市污水厂的初沉/生物泥，在45°C比较DVS和TGA-DSC。其材料与2005的85%工业/15%市政混合来水污泥未建立身份对应；两方法存在系统差异。不能把这些45°C曲线、±5°C标签、扩散估计或MCC多温参数移植过来。本轮不数字化此文图。
2. Chavez-Nuñez2004博士论文，2005原文参考B2；准确书目指向 [2004PERP0586](https://theses.fr/2004PERP0586)。目标theses.fr页面、`.pdf`及`api/v1/document/2004PERP0586`均返回工具访问错误。只找到书目 / 摘要索引，**没有读到论文正文**；其是否有同身份湿态 Cp 数据维持 unknown，不能根据摘要准入。到此停止，没有第三条新论文跟进。

## 建议的唯一最小物理增量

**给现有六个可读热节点增加95°C处的局部等含水率温度敏感度约束，而不是构造非等温湿状态函数。** 直接用 Ferrasse2004 printed1366 Eq3 的定义：

`chi_T(W)=[∂ln(p_v)/∂T]_W,T0 = q_total(W)/(R_s*T0²)`，单位 K⁻¹。

这是“源方法热力学解释下的局部斜率”，不是绝对蒸气压、速率或一段温度区间的预测。它把已有真实量热读数转成以后非等温本构必须满足的一阶约束，补的是物理导数含义。只接受六个节点；三项热 unknown继续 unknown；用同一个正的常数因子传播原读图上下界，实验/方法误差仍None。**不能把这一斜率沿T积分成常斜率曲线，也不能因此求湿 Cp。** 无需再拟合水活度、补W缺口或重复干基Cp实现。

常数约定须显式复用现有已登记水基准：本轮还核读 `data/sandbox/water/IAPWS95-2018.txt` printed3 §2及 `reference_alignment.json`。IAPWS固定质量气体常数与CODATA摩尔R不是完全同一数值约定；不得静默等同或修改IAPWS EOS的常数。局部斜率可在声明的质量基准下实现，其元数据必须说明所用 `R_s` / `R,M`，不能借该换算声称已完成与水EOS的压力/焓桥接。

若下一阶段要求的是“有实际误差证据的非等温湿储能”，本轮答案仍是**不可实施准入**。最小新外部输入是同身份、明确固定含水率与压力 / 密封条件下的湿态量热温度响应，或能够约束同一导数且带温度 / 热流误差的多温数据；不是更多制造仿真。完整Goal、材料资格、实际砖 / 本厂适用性均未完成。

## 新资产与访问记录

- 同篇原 Eq1：[出版方原GIF](https://minio.scielo.br/documentstore/1678-4383/mxGLvLxqCvys7VX4DpCyNvM/69e3a7166f60671728c02ac0abd77995433d39ff.gif)，私有文件 `arlabosse2005-wet-cp-eq1.gif`，1784 bytes，SHA256 `03f66a006455b6681146d6feaf484d9fd175717a230578659757cea5065e30e7`。普通沙箱curl先DNS失败；随后获准的同一精确公共URL下载成功，原图实际查看。未修改repo缓存/源包；版权原件只留本私有scratch。
- 既有出版HTML SHA256 `7dc682647cc70503820e6738b806b052ddccc9f1bc14650178e8813c7e203816`；原Eq2 SHA256 `3b406de01f7ac8bbf27c06c3245345a0966aee1d6fcd90e4f00541a06064cf85`。同一原文的Eq1获取不算第三篇跟进来源。
- Arlabosse2003正文为作者上传的网页文本渲染；未保存原PDF、未看PDF页图。Chavez2004正文不可得。所有新增经验不确定度均保持unknown。
