# 本轮实际读到的外部证据摘录

只保存与方向判断相关的逐字摘录；不是论文全文副本或独立实验数据。
抓取日期：2026-09-04。数据工作簿/README/元数据保持只读，位置见 source_registry.json。

## DTU 关联论文：仅摘要与 highlights

来源：https://www.sciencedirect.com/science/article/pii/S2214509525011854
DOI：10.1016/j.cscm.2025.e05387
Authors: Frederikke B. Feldthus; Lisbeth M. Ottosen; Ida M.G. Bertelsen; Gunvor M. Kirkelund (2025).
许可页面标为 CC BY 4.0。

> This study examines SSA’s fluxing properties, with a focus on SSA before and after P extraction, as a partial substitute (30 %) for brick clay, to determine the influence of P in SSA on fluxing properties.

> The SSA's fluxing effect was mainly due to Fe and Na, while P did not contribute to fluxing.

> For red bricks (low Ca content), vitrification increased at all firing temperatures with SSA addition.

注意：上面属于原作者摘要解释，不是本轮独立证明的元素因果效应。完整方法、烧成气氛/升温/保温以及矿物相证据尚未核读。

开放版本线索实际来自 DTU Orbit 页面 citation_pdf_url：
https://orbit.dtu.dk/en/publications/fluxing-properties-of-sewage-sludge-ash-in-brick-manufacturing-ef/
https://orbit.dtu.dk/files/418782101/1-s2.0-S2214509525011854-main.pdf
本机 curl PDF 返回 HTTP 403；web_extract 返回 Failed to fetch url；Wayback availability 返回 HTTP 429。
已停止同一路径重试，没有付费访问或使用新凭证。

## 原污泥层：已读方法与结果正文，未取得原始数值曲线

来源：https://www.mdpi.com/1996-1073/16/18/6634
DOI：10.3390/en16186634
完整作者名字由同 DOI 的 Crossref 元数据保存于 raw-sludge-crossref.json；source_registry.json 从该记录生成。
题目：Thermal Characterization, Kinetic Analysis and Co-Combustion of Sewage Sludge Coupled with High Ash Ekibastuz Coal (2023).

Section 2.1:
> Samples of SS were collected from the WWTP located in Astana, the capital city of Kazakhstan.

Section 2.2:
> Dry and powdered SS and its blends with coal particles were used in Simultaneous Thermal Analyzer (STA) 6000 between 30 and 900 °C, with a heating rate of 15 °C/min and constant air flow rate.

Section 3.2:
> Next, the kinetic analysis of the sewage sludge was carried out using three different heating rates and in nitrogen environment.

> Herein, the iso-conversional method with the FWO and KAS models was used to calculate the activation energy from experimental data on TGA analysis of sewage sludge at 10, 15, and 20 °C/min [50].

Section 2.3:
> Combustion tests were conducted at the atmospheric pressure and the bed temperature was kept at 850 °C for all tests.

Data Availability Statement:
> The data presented in this study are available per request from the corresponding author.

边界：干燥后的市政污泥仍归 raw_sewage_sludge，不是焚烧灰；文中空气TG、N2动力学和BFB气体检测是三套不同边界。本文不把 N2 活化能用作空气氧化速率，也不把 BFB 时间与气体浓度转成砖窑操作或排放结论。正文的组分归属/高温阶段解释并非本轮独立验证，不作唯一反应机理。
