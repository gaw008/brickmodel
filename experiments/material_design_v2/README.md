# 材料设计 v2 首阶段（研究用途，待独立审核）

直接结果见 artifacts/DIRECTION_REPORT.md；数据问题见 artifacts/DATA_AUDIT.md；后续模块优先级见 artifacts/MODEL_GAP_PRIORITY.md。

本目录独立于既有 solver/verifier。仅用 Python 3.12 标准库解析公开 OOXML、CSV、JSON 和生成浅色中文 SVG；不执行 Excel 公式/宏/外部链接，不联网运行，不安装包。原始DTU输入仍留在授权只读目录，没有复制/改写工作簿。

## 复跑

从 /home/ubuntu/sludge-brick-design-v2 运行：

    python3 experiments/material_design_v2/verify.py

该命令实际串行执行完整pipeline、focused unittest、compileall、git diff --check；若本机存在已安装的grounded-citations工具，也执行三个报告的证据引用检查。命令、原始退出码/输出、耗时、输入hash、计数、峰值RSS和边界写入 artifacts/verification.json。测试不是旧项目full suite。

仅重新生成数据/图/报告：

    python3 experiments/material_design_v2/pipeline.py

更换输入根或保留另一次输出（输出必须是本目录的子目录）：

    python3 experiments/material_design_v2/pipeline.py --input-dir /home/ubuntu/.hermes/reports/sludge-material-design-v2 --output-dir /home/ubuntu/sludge-brick-design-v2/experiments/material_design_v2/replay

单独测试：

    python3 -m unittest discover -s experiments/material_design_v2 -p test_pipeline.py -v

默认输入必须包含Manager提供的 DIRECTION_BRIEF.md、download-manifest.json、selected-datasets.json、workbook-inventory.json、四份dataset-metadata.json、dtu-collection.json、dtu-items.json和public-data。下载源/DOI/作者/许可见 artifacts/source_registry.json。共享README只取一份。原始五文件的MD5/SHA256/字节数在读入时检查，十五个授权输入的SHA256在运行前后核对。

## 交付结构

- pipeline.py：只读OOXML含共享公式读取、原表导入、身份/干基/精确试件质量join、源派生复算和组统计。
- reporting.py：全sheet/逐行/公式审计、来源注册、图表与中文报告生成；templates/保留人工审定的解释，数值表由真实数据填入。
- test_pipeline.py：RED→GREEN开发的focused tests；含真实工作簿重算、变更灰标识的反例、Ref被伪装30%灰的反例、源高度均值填补排除、全部source_derived观察的lineage覆盖、列schema与图表计数、重复运行。
- inspect_sources.py / explore_import.py / inspect_lineage.py：只读诊断工具，供查原表与审计来源；不是额外数据或模型。
- citations.json / sources_block.md / literature_evidence.md / raw-sludge-crossref.json：本轮已获取的文献证据和引用元数据。DTU正文PDF没有成功取得，不声称全文已读。
- artifacts/materials.csv 与 observations.csv：严格采用 DIRECTION_BRIEF 的列名/顺序；缺失数值为空，所有源文件/sheet/cell可定位。
- artifacts/material_evidence.json：materials固定schema之外的证据状态；DTG内部算法unknown。
- artifacts/derivations.json：源派生值的逐项外部缓存比对；TGA百分比局部解释诊断单独标role，不算通过的源量验证。
- artifacts/source_imputations.json：真实高度数据的均值填补及依赖统计排除记录。
- artifacts/conditions.json / group_summary.csv / chart_data.csv：实验条件、系列成员/计数、组均值/样本SD与图表点对账；统计不是独立验证。
- artifacts/sheet_audit.json / row_audit.csv / formula_audit.csv：所有sheet及非空行的用途、排除、原公式与缓存信息。
- artifacts/*.svg：两张中文浅色图。无远程字体/脚本/图片依赖；客户端需要中文字体。本机未进行CJK渲染器逐像素验收，已验证SVG结构、坐标/点数及出处。
- artifacts/verification.json / pipeline_run.json：实际执行证据，耗时/时间戳会随重跑改变；CSV/SVG/报告不依赖随机数。

## 科学与权限边界

Raw SSA是焚烧灰；DTU TGA是N2且单速率。A2P/#0179的P1/P2/Silica Sand身份冲突保留且排除定量配对。P&D全局旧模板说明与逐行身份链的不一致仍是chain-of-custody不确定性。R-P2-ED/1030°C/G的高度来自其他六片均值，不能作为独立高度样本；直径分析不受影响。

图中只比较同研究、同基料和名义最高温度的离散系列；完整热历史尚未取得。不开优化器、不制造连续可行域、不认证强度/环境合规、不声称工厂最优配方，不把unknown当物理不可能。

本轮只提交 research/material-design-v2 本地研究分支，不push/merge/publish，不改主仓库工作树，不创建资源或使用收费API，不连接PLC/机器人/窑炉。已存在独立Safety子卡 t_c6aa7e5f，审核前本产物不标approved。

回退：仅对本目录做经批准的定点恢复/后续revert；没有数据库/生产系统迁移或原始数据变更。不要改写历史或对主仓库reset。
