# 热湿材料证据的有界续查

本轮按缺失的湿坯 k/cp、收缩、水活度及输运关系查询，未下载付费正文、未联系作者、未将摘要值送入运行时参数包。检索结果不等于实际核读全文。

## 已有 Wang 干燥几何复核

原文件 `data/sandbox/research/raw/energies-14-07722.pdf` SHA256 `e462a21b472c81b350d94d5a448af5e49c99dd2d5aa32f0af58399dae42a1778` 已重新核验。p4 Sec2.2明确样品为2mm厚污泥层，载体是200×200×2mm钢板；`source_candidates.json`原本已记录污泥层厚度。本轮将SOURCE_COVERAGE较含糊的钢板载样表述与原注册表对齐，没有改动原始来源或图中读数。

这支持以2mm实际层厚制定一维干燥验证域，不支持把2mm当对称半厚度，也不能假定钢板热容/接触热阻为零。顶部暴露和底部钢板需要不同热湿边界。论文没有直接给出足够的材料吸附/有效输运及随含水率变化的热容，因此几何明确不等于完整干燥模型已经闭合。原40/60°C拟合、50°C留出方案保留。在线出版商页面本次返回429，核读使用已保存完整PDF。

来源：[Wang2021](https://doi.org/10.3390/en14227722)。

## 新线索及准入结论

| 线索 | 实际可读级别 | 对当前任务的决定 |
|---|---|---|
| Al Ahmad等，Thermal and mass transfer properties of a shrinkable industrial sludge，DOI10.1080/09593330.2020.1871419，2021在线/2022卷期，43(14):2230–2240 | 出版商摘要与PubMed记录已读；标题/DOI/PDF及HAL定向检索未取得合法公开全文，出版商full页面读取失败 | 摘要指向一套热湿/收缩关系，但材料为industrial sludge，身份、完整函数、基准和适用域未核读。不能把摘要的端点热物性或临界水分填入市政原污泥砖。保留正文线索，所有待核参数为unknown。 |
| Saha等，Implication of Rheological and Thermal Properties of Sludge for Energy Optimization in a Sludge Treatment Train Incorporating Thermal Hydrolysis and Anaerobic Digestion，DOI10.1002/wer.70388，2026 | 仅出版商搜索提取片段；文章正文打开失败，补充数据尚未读取 | 线索涉及不同处理段及温度的热物性，但没有核读样品身份/原始表/测试方法，不新增材料参数。后续可尝试合法开放作者版本/补充文件。 |

实际查询包含原泥黏土砖热湿/渗透/膨胀仪关键词、第一篇完整标题+PDF/author manuscript、DOI+HAL。未发现可立即核准的同一原泥全周期包；这不是不存在公开数据的全局结论。软件上的多相储能、动态边界和独立解析验证可以继续，Goal不因本轮访问失败标为blocked。

直接入口：[出版商摘要](https://www.tandfonline.com/doi/abs/10.1080/09593330.2020.1871419)、[PubMed](https://pubmed.ncbi.nlm.nih.gov/33402063/)、[Saha出版商](https://onlinelibrary.wiley.com/doi/10.1002/wer.70388)。此文是检索/核读状态记录，不是正文资产清单，也不声称新增了可再分发全文。
