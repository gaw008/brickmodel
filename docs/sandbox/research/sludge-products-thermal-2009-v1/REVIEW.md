# Hossain / Strezov / Nelson 2009：有界来源取得结果

2026-09-12。仅追查指定论文及其合法版本，未增加论文数量，未联系作者、购买、登录、安装、拟合或运行EOS。

**本次未取得合法可读的原论文全文，因此不能确认它能锚定一个总括反应或原料H。取得并读到的是作者机构的完整摘要/书目、出版社搜索索引中的有限预览，以及开放版本登记；这不是“全文已核而数据不足”。原PDF与其SHA均为null，未把摘要数值迁入材料模型。**

论文：Mustafa K. Hossain, Vladimir Strezov, Peter F. Nelson, *Thermal characterisation of the products of wastewater sludge pyrolysis*, **Journal of Analytical and Applied Pyrolysis 85(1–2), 442–446, May 2009**，DOI [10.1016/j.jaap.2008.09.010](https://doi.org/10.1016/j.jaap.2008.09.010)。DOI中2008不是把刊出年改为2008的理由。

## 实际取得与停止依据

- [Macquarie作者机构登记](https://researchers.mq.edu.au/en/publications/thermal-characterisation-of-the-products-of-wastewater-sludge-pyr/)已通过网页工具实际读到：仅摘要、书目、DOI及Scopus链接，没有原稿/PDF下载。随后尝试私存HTML超时，不能声称本地缓存了该原页面。
- [ScienceDirect文章/预览入口](https://www.sciencedirect.com/science/article/abs/pii/S0165237008001228)在搜索索引中有摘要和有限章节开头；直接打开全文路径与abs路径均403，未读取Table1、热分析方法全文、图表或完整结果。
- 精确题名、DOI和作者机构域的定向检索未发现同文公开原稿。ResearchGate结果明确是Request full-text；没有发出请求。
- OpenAlex同DOI公开元数据实际HTTP200并已私存：`is_oa=false`、`oa_status=closed`、`best_oa_location=null`、`any_repository_has_fulltext=false`，唯一登记入口为出版商，`pdf_url=null`。这支持本轮停止，不证明所有未索引合法版本永不存在。没有继续尝试访问控制后的文章内容。

## 摘要确实支持的线索，不作参数准入

作者机构摘要说明该研究区分三个不同来源污泥，固定床升温率10°C/min；监测CO、CO₂、CH₄、C₂H₄、C₂H₆和H₂，并使用computer-aided thermal analysis。摘要给出室温到550°C的过程需热：生活来源1180、商业来源730、工业来源708 kJ/kg。出版社索引预览将B/C/M对应商业/生活/工业来源，但未核读原Table1，不能把三种污泥合并成一个材料或跨样本拼最有利数字。本文也不是Cedrone、Arlabosse或GNEST的同批实验。

这些热量被描述为升温至碳化温度的**过程需热**，不是已取得定义/基准的反应焓或原料形成焓。尚未确认其质量干基、样品预处理、密度换算、CATA校准/基线、显热/水分/反应项的分离和不确定性。摘要中的气体燃烧可回收能量/自持判断，不能替代char、liquid和gas联合的质量—元素—焓闭合。

## 能否补当前两个关键缺项

| 目标 | 目前能够确认 | 原文必须核对而本次未读到的字段 |
|---|---|---|
| 一个总括热解反应 | 有三种独立污泥、固定升温程序、部分气体监测与过程能量线索 | 各样本进料ultimate/proximate及O/灰基准；char和液体是否独立回收；水/油/焦油分相；各气体绝对量及载气扣除；各相CHONS/矿物和回收误差；是否同温程同批样本；参考焓与量热端点。 |
| 同材料原料参考H | 摘要没有提供可核读的原料bomb HHV及反应定义；仅过程需热不够 | 如Table1确有进料燃烧热，须核其测量方法、质量/含水/温度基准、定容到定压校正和燃烧终产物（含S/N/卤素/灰）。满足后才可能用Hess关系锚一个整体原料H，无需捏造有机分子式；原有机参考S不是HP初态能量的必要条件。 |

即使上述过程需热完整可信，在同一控制体写 `H_feed + Q_process = H_char + H_liquid + H_gas`，目前右侧未知项仍多；气体燃烧热不能单独给出全部右侧焓，不能反解H_feed或指定反应q。反过来，**由于全文未取得，本次也不能断言论文没有这些字段**。

最小外部变化是取得这同一篇的合法全文/作者已公开原稿，然后优先读Table1、CATA方法和产品回收/量热表；在此之前不建议新增数值接口或用708/730/1180作能量闭合。固定T/P、限定元素/最终相的条件平衡方案可以独立继续其热化学准入，本次访问失败并不否定这条不依赖动力学的路径。

检索、实际访问状态、摘要限定线索和未取得字段见 `SOURCE_RECORD.json`；原HTTP尝试及OpenAlex响应绑定见 `RETRIEVALS.json`。原件未取得，故没有渲染、数字化或原页图的成功声明。
