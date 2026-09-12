# Cedrone 2024 报告样品的条件 CHONS 元素池

来源为 Cedrone 等，*Optimization of Pyrolysis Parameters by Design of
Experiment for the Production of Biochar from Sewage Sludge*，Environments
11(10),210，2024，DOI https://doi.org/10.3390/environments11100210。
作者为 Giacomo Cedrone、Maria Paola Bracciale、Lorenzo Cafiero、Michela Langone、
Davide Mattioli、Marco Scarsella 和 Riccardo Tuffi，版权归2024年原作者。
原文采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。本文档及 JSON 是从第4页方法与第8页
Table4 提取的记录及明确标注的算术推导。原件校验信息在 JSON 内；合法本地
PDF 位于忽略的 source-cache，未在此重复分发。

每 **1 kg 论文报告的干燥后样品分析基准**，取原打印中心值：

| 元素 | kg | 原打印 ±，wt% 的百分点 |
| --- | ---: | ---: |
| C | 0.360 | 1 |
| H | 0.053 | 0.2 |
| O | 0.222 | 未给出 |
| N | 0.058 | 0.2 |
| S | 0.011 | 0.1 |

这五项合计0.704 kg，不归一化为1 kg。C/H/N/S直接分析，O由测得元素和灰分
差减；原文没有明确绝干基换算，打印±也没有明确统计定义及协方差。它们不能
直接当成五个相互独立的概率区间。残余水分2.4 wt%不再额外加进元素池。

29.2 wt%灰分、0.050 wt%氯及未定量的溴在受限CHONS模型之外。已打印元素、
灰与氯合计99.65%，0.35%的算术差原样保留，不能补给氧。灰分缺少元素/矿物相
分解，碳和硫的矿物分配也未知；全部报告CHONS都允许进入气体/石墨相是明确
的条件近似，并不构成完整污泥组成。

可按 `b_e[mol] = 1000*m_e[kg]/A_e[g/mol]` 转换，A须取实际绑定的热化学模型
原子量并保存。[printed-pool.json](printed-pool.json) 保留原提案的精确分数和
未填写的转换值；实际原子量转换及一次800 K条件平衡结果另见
[计算报告](../../../../docs/sandbox/research/tp-equilibrium-v1/REPORT.md#论文报告样品的条件计算)。

输出用途是条件终态组成探索。固定TP、闭合元素池和纯石墨与论文流动氮气下
的有限时间TG试验不同，石墨量不能直接叫实测焦炭产率。完整材料验证、反应
时间、原料初始焓和烧成热耗仍需后续独立证据。
