# Cedrone 2024 原污泥 TG/DSC 实验锚点

本阶段把一份公开原污泥研究的热分析原图、有限读取值和复现入口保存到项目：[数据及运行说明](../../../../data/sandbox/research/cedrone2024-joint-thermal-v1/README.md)。这增加了高温模型可对照的实际实验约束，尚未得到完整反应产物、反应焓或跨材料预测资格。

来源为 Cedrone 等，*Optimization of Pyrolysis Parameters by Design of Experiment for the Production of Biochar from Sewage Sludge*，Environments 11 (2024), 210，DOI [10.3390/environments11100210](https://doi.org/10.3390/environments11100210)。实际核读原 PDF 方法与结果页，并查看 Figure 3 的两张原嵌图。PDF SHA-256 为 `7b7e7fc7a0e2c41971b90cd12f30ac483ae9681f3d7e458b4a005db502f0ae32`；全文保存在忽略目录 `runs/sandbox/source-cache/cedrone2024/cedrone2024.pdf`，不纳入本次提交。公开嵌图依据原文 CC BY 4.0，附完整署名及提取说明。

## 材料与读图结果

原料是经过消化的污泥，105°C 烘 24 h 后研磨、0.5 mm 筛分并均化 500 g；仍报告 2.4±0.6 wt% 水分。TG 和 DSC 使用不同约 10 mg 试样，均以 10°C/min 升温，但氮气分别为 60 与 50 mL/min。材料局部 ID 仅表示论文内这份均化原料，不能与 Arlabosse、GNEST 或工厂污泥合并为同一批次。

预选 6 个 TG 与 6 个 DSC 锚点，11 个可读；DSC 575°C 处红色曲线与黑色基线相交，存在缺少曲线像素的可行列，保留 unknown。TG 825°C 超出 DSC 的 600°C 上限。TG 保持相对初始 TG 试样的 wt%，DSC 保持原图 W/g 初始 DSC 试样、吸热向下；未换算绝干基，也没有把不同温度的锚点当成同温成对观测。

全部实际 RGB 像素、坐标、仿射校准可行顶点及精确有理数包围保存于 `extraction/ANCHORS.json`。标签中心 ±2 px、曲线余量 ±1.5 px 是分析员数值设定；这些是有条件的读图范围，不是实验置信区间。仪器、重复性、基线、压缩颜色识别及不同试样的迁移误差仍缺乏完整界限。初次颜色筛选误选橙色文字晕边的原记录保留；最终筛选没有用基线或插值补齐未知点。

## 实际复现与审查

[原始提取报告](ORIGINAL_EXTRACTION.md)保留当时状态；随后[独立源及提取审查](INDEPENDENT_REVIEW.md)实际查看原图，完成 17 项核对，并将一次重算写到新的输出文件。完整结果与原始结果逐字相同：SHA-256 `5c6f4cdb8ad4b1ecf48338790803200a3ded5d6f6f2c035b682ad921986f2b28`。

公开脚本仅改输出入口：必需 `--output`，拒绝已有文件或符号链接，并以独占创建保存。算法、校准常量、颜色条件和协议保持。[输出入口独审](PUBLIC_WRAPPER_REVIEW.md)通过；实际公开命令使用 Python 3.14.2 / Pillow 12.1.1 成功执行。新 JSON 的轴、像素、全部读数、协议和运行库记录与独立重算一致，唯一变化是指向公开脚本的 `script_sha256`。公开脚本 SHA 为 `3d37cb1cbc2ae022efdf606e0f5024184a38e06e532b5df21d3086ee33058199`，公开结果 SHA 为 `666784aa9f190509d5bb5a53047138b4bea939213dfb1be9771c953ef3e61409`。

没有运行新 EOS、拟合或模型轨迹。复现证明提取过程一致，不能作为新的实验观测或独立材料验证。原协议中的命令描述原提取入口，公开入口的实际命令以数据 README 为准。

## 对下一步模型的约束

约 100°C 的 108.83 J/g 打印吸热峰包含水分及水合物脱除，不能作为干污泥化学反应焓，也不能与既有干燥潜热重复计入。其他峰面积和表观热流同样需要参考基线、显热和物质进出项的解释。该文未收集分析全部气液产物，因此仅凭 TG 和 DSC 不能闭合产物元素、物流携焓及所有反应路径。

后续已完成[各自实验温程的观测算子与可识别量推导](joint-observable/JOINT_OBSERVABLE_DESIGN.md)。TG起温25°C、DSC起温50°C；不能仅按相同升温率合并时钟。由公开锚点实际算得5个区间的净失重与平均质量变化率，ROOT从公开精确读数复算7组关系通过，见[复算记录](joint-observable/ROOT_CHECK01.json)。例如225→319°C的18.7994%净失重对应名义564s，平均净失重率3.333228e−4 kg/(kg初始试样·s)。这是积分质量约束，不能拆成未测气液产物或拟合任意多步动力学。

推导明确了未来的TG称盘质量投影与DSC仪器差示热流投影；当前未知的基线、物种和共同能量参考仍挡在模型输入处。固定T/P的限定产物Gibbs平衡可以另作条件探索，不依赖未知A/E或原污泥参考熵；但尚需完整候选相G及明确元素子系统，不能自动得到原泥能量初态或动态热解。没有因此新增一个伪热源或空反应接口。`material_qualified=false`、`training_eligible=false`，完整 Goal 的高温、烧结、全周期与现实验证条件保持未完成。

原始提取、初筛、独立重算、公开复现及对照记录纳入本目录 `evidence.tar.gz`，成员与校验值见 `EVIDENCE_MANIFEST.json`。全文及原图不在该证据归档内重复分发；两张有许可的原图保存在数据目录。

后续推导作为单独文件保存在`joint-observable/`，未重写原归档；其中原稿路径指提取时的目录。数据目录的公开`derived/CONSTRAINTS.json`只把来源指向数值等价的公开锚点，并保留原锚点SHA；所有数学值与原稿一致，公开SHA见ROOT复算记录。
