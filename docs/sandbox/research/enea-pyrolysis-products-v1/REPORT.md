# ENEA 热解产物约束：新增实测终态，尚无动态反应模型

2026-09-22。来源为 ENEA 官方报告 `RdS_PTR22-24_PR1.6_LA5.2_292`（December 2024），[原报告](https://www.ricercasistemaelettrico.enea.it/archivio-documenti/send/600-report-progetto-1-6-2022-2023/5546-strumenti-e-tecnologie-per-la-gestione-sostenibile-dei-flussi-di-materia-ed-energia-del-settore-della-depurazione-la5-2.html)。本轮实际取得 PDF，核读方法，目视核对印刷 p10 Table2、p11 Figure4/Table3 及原嵌入图。完整原文许可尚未核定，保留在忽略缓存；发布有限数值事实、像素定位和派生算术。

## 能增加什么

报告研究预干燥消化污泥的氮气半批热解，回收并分离炭、油、水相和气体。Figure4 的终态质量产率和 Table3 的油相 CHONS 约束此前仅凭 TG 失重无法区分的产物分配。它们不是样品随时间的反应速率，也未证明与 Cedrone2024 的每个试样同批；不转移到 MIA3 配方。

| 炉温 °C | 炭 wt% | 油 wt% | 水相 wt% | 气体 wt% | 原图四项和 wt% |
|---|---:|---:|---:|---:|---:|
| 350 | 58.4 | 15.9 | 17.6 | 7.6 | 99.5 |
| 500 | 43.9 | 29.9 | 14.9 | 11.3 | 100.0 |
| 650 | 41.2 | 28.9 | 17.3 | 12.7 | 100.2 |
| 800 | 38.5 | 27.8 | 15.2 | 18.1 | 99.6 |

这些是读图值。完整精度仅用于复算，不是实验有效位数。像素轴锚 ±2 px、柱边 ±1 px 与原图误差线共同形成外包围；不称置信区间或完整实验误差。没有把四项强制归一化到 100%，没有把水相视为纯水。

油相的 C/H/N/S 库存按“图示油产率 × Table3 质量分数”计算；扣除后只得到其余产物与未回收部分的总待分配元素，不能分给特定气体或残炭。O 是差减量，不单独作为实测守恒约束。原始近似分析和为 100.1%，CHONS+灰+Cl 为 99.65%；均保留原值，没有自动修正水分/干基或缺项。

报告给出的油低位热值范围 31–33 MJ/kg 只用于油相燃烧能含量外包围。它不是热解吸热，也没有直接与进料高位热值相减。油回收的难度、溶剂处理、质量基准及总回收误差仍需澄清。

## 离线复算与实际核对

- 根参数：[parameters.enea_pyrolysis_products.json](../../../../parameters.enea_pyrolysis_products.json)，包含逐项原值、来源页码、读图政策及未知项。
- 原图坐标：[figure4-bar-pixels.json](../../../../data/sandbox/research/enea-pyrolysis-products-v1/figure4-bar-pixels.json)。记录 16 个柱顶和误差线端点，实际与原图目视核对。
- 当前派生：[product-accounting.json](../../../../data/sandbox/research/enea-pyrolysis-products-v1/product-accounting.json)。保留最初直接图像派生 `derived-constraints.json`，没有删除旧结果。
- 独立表达式：[independent-decimal-accounting.json](../../../../data/sandbox/research/enea-pyrolysis-products-v1/independent-decimal-accounting.json)。用 60 位 Decimal 另算 16 项坐标和 16 项元素库存，与 Fraction 派生最大差为 1e−58 wt% 和 1e−60 kg/kg；这是算术复核，不是第二位人工审稿或实验准确度。

仓库根目录运行，输出必须使用新文件名：

```sh
.venv/bin/python -I examples/sandbox/derive_enea_product_constraints.py \
  --parameters parameters.enea_pyrolysis_products.json --mode account \
  --output /tmp/enea-product-accounting.json
```

此计算只读已发布坐标和根参数，使用 Python 标准库，无网络或图像依赖。重新提取图像属于资料准备：先按根参数的原 PDF 页码和 `pdfimages` 指令准备缓存，再用 `--mode extract` 写入新的坐标文件；需要已有 Pillow/NumPy。未生成/比对 SHA，未新增或运行软件测试。

## 仍不能放行的内容

缺少同试样的实际温程、供氧依赖速率、完整气体/炭/水相定量组成及相容热量基准，故 `finite_time_reaction_law=null`、`material_qualified=false`、`training_eligible=false`。

定向续查官方 [LA5.1 报告](https://www.ricercasistemaelettrico.enea.it/archivio-documenti/send/600-report-progetto-1-6-2022-2023/5249-neutralita-energetica-e-sostenibilita-dei-servizi-idrici-in-riferimento-agli-obiettivi-delineati-dalle-politiche-comunitarie-la5-1.html) §7.4 与 [LA5.6 报告](https://www.ricercasistemaelettrico.enea.it/archivio-documenti/send/600-report-progetto-1-6-2022-2023/5550-produzione-da-fanghi-civili-di-hydrocrude-utilizzabile-a-fini-energetici-la-5-6.html) §7：前者强调装置变化会改变结果，后者主要研究油品后处理，未形成可直接并入本包的同试样热解闭合关系。未将其不同油组成替换 Table3；PDF 截图工具失败，不声称目视核对这两份报告的表格。

下一项有价值的材料增量是把本报告产率与对应样品热历史、定量产物分析及热量参考配对，再判断少数总括路径能否识别。旧 Cedrone TG/DSC 数据与来源审查不重做，不能把新增产物终值称为完整烧砖模拟。
