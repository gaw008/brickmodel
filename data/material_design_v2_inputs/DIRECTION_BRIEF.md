# 污泥烧结砖：材料设计地图 v2 — 研究方向与首阶段执行约定

状态：用户已批准按新方向推进；本文是研究任务约定，不是生产配方、产品认证或模型验收结论。

## 结论

不等待工厂长期采集数据。先用公开实验数据约束“材料组成—烧结行为”的关键关系，以物理模型研究原污泥的反应/供氧/排气时序，再输出有基料、几何和窑况条件的材料设计窗口。第一阶段不是寻找一个最高分配方，而是回答“优先追求什么特征、为什么、有哪些证据、哪些未知会使结论翻转”。

默认研究目标：兼顾结合/致密化与尺寸稳定性，不以最大污泥掺量或最大孔隙率为唯一目标。具体强度等级和生产阈值尚未指定，不擅自补造。

## 已实际取得的起点

已通过 DTU 的公开 Figshare API 核对数据集合及其 10 个条目，选取其中 4 个与首阶段直接相关的工作簿。集合关联论文为 Feldthus、Kirkelund、Ottosen、Bertelsen 的 *Fluxing Properties of Sewage Sludge Ash in Brick Manufacturing: Effect of Phosphorus Extraction and Brick Clay Composition*，论文 DOI 为 10.1016/j.cscm.2025.e05387。[7]

已下载并完成文件大小、发布方 MD5 和本地 SHA-256 验证：
- XRF 化学组成：`30156127/XRF DTU Data.xlsx`。[8]
- TGA：`30157066/DTU Data TGA.xlsx`。[9]
- 制样、烧成、尺寸、吸水率、孔隙率、密度：`30157108/DTU Data - Brick Pellet Production.xlsx`。[10]
- 粒径分布：`30156970/DTU Data - Laserdiffraction.xlsx`。[11]
- 共用 README：另保存一份，避免重复下载相同文件。

这些数据集的元数据均标注 CC BY 4.0；所有衍生图表和数据保留作者、DOI、许可、原文件及单元格来源。[8][9][10]

本机证据：`download-manifest.json`、`selected-datasets.json`、`workbook-inventory.json`。工作簿已经做只读 sheet/非空行/公式缓存清点，尚未完成全部语义清洗或材料方向比较。原始文件在同目录的 `public-data/` 下。

## 不可跨越的证据边界

1. 这组研究对象是污泥焚烧灰 SSA，不是原污泥；其中 Raw SSA 意味着未进行该研究中的后续处理，不意味着未焚烧的原污泥。只能先约束无机部分、基料交互及烧后物性。[8]
2. 这组 TGA 在氮气环境中进行。不能将其质量损失曲线直接拟合成空气中原污泥的氧化动力学，更不能据此证明窑内黑心已经解决。[9]
3. 小试砖圆片不是隧道窑整砖。处理方法、砖型、尺寸、升温、停留时间与供氧边界不能静默混同。
4. XRF 是该来源约定的氧化物/LOI报告基础，不等于矿物相组成；原始比例与经归一化比例分列，不静默重算。
5. README 和工作簿中 A2P、P1/P2、#0179、Silica Sand 等标签存在需核对的身份线索。不得猜测映射或自动“修正”原标签；无法解决的行保留并标识 identity_ambiguous，不能进入定量比较。
6. 数据集的生产与物性测量说明不自动提供抗压强度、玻璃相黏度或完整液相分数。缺失项单列，不从孔隙率精确反推出真实强度。[10]
7. 元数据、搜索摘要或下载成功不代表论文全文已读。本轮普通网页抽取超时、浏览器启动失败；DTU数据API和原始Excel已成功获取。PMC11808077全文虽已通过Europe PMC获取，但研究的是mosaic工业污泥，不用它冒充市政原污泥证据。

## 科学主线：固定三个问题

### A. 无机骨架与助熔匹配

先比较文献中的低碳酸盐红砖基料和高碳酸盐黄砖基料，以及实际记录的SSA来源/处理类型，建立基料依赖的方向图。不把“增加某元素一定更好”作为先验结论。

### B. 反应、供氧、排气与致密化的时序

原污泥层另建证据表，按材料类别和气氛检索多步反应及产气规律。原污泥、SSA、工业矿物污泥严格分组；单升温速率TGA不足以唯一识别一组可靠的动力学常数时明确保留不可辨识性。

### C. 可实现的材料及预处理

分开理论理想层和现实可实现层。元素/矿物/颗粒与密度、比热、导热、渗透的关联不得全部解耦。优先评估混配、分级/粉碎、脱水等有明确物理影响的候选操作；本研究不授权工厂实施任何处理。

## 第一阶段：公开证据约束的方向图

负责人：真实 Engineer profile；Manager已完成范围与验收决策，不冒充Planner产出。Planner目前认证不可用，不为本阶段另建一个会失败的规划任务。

交付目录：独立worktree内 `experiments/material_design_v2/`。

必交付：
1. 可复跑的只读数据导入与分析脚本；保留所有原始表，不覆盖来源文件。
2. `source_registry.json`：来源URL/DOI、作者、年份、许可、材料类别、实验气氛和测试几何、覆盖/不可转移范围。
3. `materials.csv`：`source_id, material_id, material_class, original_label, property, value, unit, basis, file, sheet, cell, identity_status`。材料类别仅用 `clay, sewage_sludge_ash, raw_sewage_sludge, other_industrial_sludge, unknown`。
4. `observations.csv`：`source_id, specimen_id, matrix_id, additive_id, additive_fraction_dry, firing_temperature_C, property, value, unit, replicate_id, file, sheet, cell, evidence_status`。缺失值留空；evidence_status为 `measured, source_derived, model_derived, missing, identity_ambiguous`；derived值附机器可读计算来源。
5. `DATA_AUDIT.md`：sheet全量清点、样本/重复件/均值层级、公式与缓存核对、单位、标签冲突、缺失及排除计数。图表辅助表不是新增独立样本。
6. `DIRECTION_REPORT.md`：至少三条可证伪方向假说，每条含支持/反例/未知、适用基料、数据依赖、置信层级和下一步最值得补的公开证据。可以得出“尚不能判定”，但不能只给泛泛的收集数据建议。
7. 两张可重生成的浅色中文图：材料—基料—烧成条件的观测对比图；组成/处理—性能折衷图。没有可靠配对的数据点不得画连续可行域。若定量标签阻塞，改为有出处的覆盖/缺失图并明确原因。
8. `MODEL_GAP_PRIORITY.md`：按“是否改变候选排序”排序液相/黏度、供氧、渗透、能量闭合等缺口；给第二阶段最小物理模块方案，不在第一阶段擅自扩展整个核心求解器。
9. `verification.json`：准确命令、输入/输出计数、输入checksum、测试结果、耗时/峰值内存（若测量）、已复核与未复核项。

首阶段验收：
- 四个已下载数据集全部被检查，任何不用的表/行有理由，计数可对账。
- 材料身份、处理方法、干基及测试条件保留；未解决的身份冲突不进入比较。
- 至少独立重算一种源表的派生量并与缓存比对；不得把自己的输出互相印证当成外部验证。
- 模型校准与外部验证明确分离；同一材料的重复件不能拆成伪独立train/test。
- 所有结论标明“文献观测/模型推断/未识别”；不编造精确适用组成或工厂最优掺量。
- 不以SSA的N2-TGA模拟原污泥氧化，不以吸水率/孔隙率代替实际强度认证。
- 不修改既有verifier，也不把大部分预算花在新增hash/重放框架。

## 第二阶段方向（尚未授权具体实现）

Manager核对第一阶段产物后，再冻结最小动态模块：原污泥反应与供氧、产气与逃逸、受证据约束的烧结/软化关系。采用多个合理model-form/参数场景比较方向稳定性，而不把主观参数采样叫实际置信区间。

最终设计地图至少区分：`excluded_by_supported_constraint`、`candidate_under_assumptions`、`unknown`。数值失败、数据库缺项和域外预测属于unknown，不能伪装成物理不可能。候选点的包络不是已经连续验证的可行窗口。

## 已创建的真实任务

- Engineer：`t_e36c9d82`，公开数据约束的污泥灰—基料方向图。
- Safety：`t_c6aa7e5f`，同时依赖 `t_e36c9d82` 和既有认证/模型审核 `t_dce3aa2b`。
- 研究资料与执行约定已经完成；Engineer分析和Safety审核是后续阶段，尚未在本文中宣称完成。

## 工程、费用和审核

- 主仓库 `/home/ubuntu/sludge-brick-first-principles` 保持原样。起点commit `eef479cdf41e1ccfb7cabc1b63b7d8a92c57b910` 的旧Safety审查仍未完成；不把它标为已批准。
- 新研究在独立worktree `/home/ubuntu/sludge-brick-design-v2`、branch `research/material-design-v2` 开展；不自动merge/push/发布。
- 单worker，串行计算；初阶段无需重跑旧项目完整的长耗时验证套件。针对新增导入/分析脚本实际测试。
- 不创建OCI资源，不升配，不启用付费插件，不购买数据库/软件，不换付费API或Anthropic，不碰PLC、机器人、窑炉或生产控制。
- Safety独立审核卡同时依赖本阶段Engineer完成和现有认证/模型审核卡 `t_dce3aa2b` 完成，使用真实父依赖防止已知无效认证继续消耗重试。认证未恢复不批准研究代码；不因认证问题阻塞公开资料的前期研究。
- 这份路线及首阶段都不需要用户先提供长期工厂数据，不安排现场试验或生产变更。

## Sources

[7] https://api.figshare.com/v2/collections/8098909
[8] https://api.figshare.com/v2/articles/30156127
[9] https://api.figshare.com/v2/articles/30157066
[10] https://api.figshare.com/v2/articles/30157108
[11] https://api.figshare.com/v2/articles/30156970
