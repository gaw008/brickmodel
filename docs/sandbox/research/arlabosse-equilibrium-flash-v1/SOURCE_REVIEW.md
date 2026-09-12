# Ben Hassine 等（2017）来源用途独立核对

**APPROVE：仅作为局部平衡建模假设的文献先例。** 本文不能提供当前 Arlabosse 单胞的 Kph，也不能证明其内部瞬时化学平衡、时间尺度分离或材料资格。本次读取本地原文提取文本，实际查看 page-3/4/5.png（印刷 pp.653–655）；未联网、运行 EOS、增加论文或迁移参数。

来源：N. Ben Hassine、X. Chesneau、A. H. Laatar，*Modelisation and Simulation of Heat and Mass Transfers during Solar Drying of Sewage Sludge with Introduction of Real Climatic Conditions*，JAFM 10(2), 651–659 (2017)。场景是污泥作为多孔吸收层的太阳能温室干燥及强制层流，不是本项目 Arlabosse 样本的匹配单胞试验。

- **p.653 假设列表**确实写 air–sludge 的 local thermodynamic equilibrium，同时假设空气/水蒸气理想气体、忽略 Soret/Dufour 等。应保留其“thermodynamic”原词，不能改写成只有温度相等；但列为假设也不等于经过实测证实。
- **p.654 Eq.9/10**明确说界面只允许水蒸气通过，并在理想气体及流体—多孔层界面局部热力学平衡假设下处理界面质量分数。Eq.9 将界面法向速度与干质量/面积归一化的 −dX/dt 相接；Eq.10 是带组分修正因子的浓度梯度/界面速度关系。二者都不是本项目固定 Nt/V/U 的组成 flash，也没有给出 aw·pure_peq=pv 所需的本材料势函数或局部有限相变系数。
- **p.654 §5.2 Eq.11、p.655 Eq.12/Table 1**保留独立经验干燥动力学：常速段速率乘特征曲线 f(Xr)，Xr 使用平衡含水量 Xeq；Xeq 又由 Oswin 形式 k[Hr/(1−Hr)]ⁿ 给出。表列 A1=2.37、A2=−3.30、A3=1.92、k=.0938、n=.484，正文归于 Amadou 的经验确定。故该文即使采用 LTE，整体干燥仍需速率闭合；不能推论“LTE 就证明无限内部相变速度”，也不能移用这些数值。这里 Eq.12 的 k 是等温吸附式系数，不是 Kph 或命名表中的渗透率。

适合登记的陈述是：**已有污泥干燥模型显式采用局部热力学平衡/界面平衡假设，同时保留经验干燥速率；本项目瞬时单胞 flash 是另行声明的条件闭合，适用误差 unknown。** 该文不验证本项目统一 F、平衡热容下界、低 W 延拓、全湿载气边界或源数据相同性。其表面潜热通量记账也不能直接叠加到本项目已有完整 U/携焓账形成第二 latent 项。

出处状态：本地 PDF 提取首部印刷 DOI 为 **10.18869/acadpub.jafm.73.238.26854**。主代理先前 publisher 索引中的 **239** 差异继续保留；本次未重新访问索引，不能声称已解决。下载记录显示 publisher 原 PDF 两次失败，实际保存件来自 Semantic Scholar 镜像；本次核对 SHA256 为 `f32423f22d52ede3402adbbfadb0eecb29a2d346e1274c79fa18f024538de400`。开放读取不等于再分发许可：许可未确认，PDF/页图继续仅留忽略的私有缓存，公开材料只记录引用与必要概述。
