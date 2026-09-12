# 下一条材料接线路径（八文件只读定位）

**建议下一模块：把低含水尾段、明确水汽排出边界和干态显热接成连续动态路径。** 当前 Arlabosse 吸附储能与 K/D 分支按已完成阶段的声明只覆盖有限 W/T；不能因程序到达下界就把剩余水删掉、取消吸附能或直接跳到高温。完成这一过渡后，首个原污泥热反应候选应优先考察 **GNEST 同研究的拟合热解分支**。Nowicki 已有代码可复用为独立预制炭响应模块，但不能直接替代原泥热解或耗氧库存方程。

这里的“能接”指有计算路径、来源与显式选择，尚不授予材料资格；unknown 是需要保留的误差/自由度，不是自动停止实施的理由。

| 现有路径与实际接口 | 能复用的部分；必须守住的区别 |
|---|---|
| `src/sludge_sandbox/source_dry_transition.py`：`execute_source_dry_candidate(...)`、`evaluate_source_dry_transition(...)`、`SourceTransitionBalance` | 已有实际湿/干候选推进、事件比较、逐格水/能量与舍入账。它接收既有 `SourcePrefixTrial` / `SourceRootRefinement`，不能据此声称新吸附/K/D 类型已经获准接入。当前账固定四列水/O2/N2/H2O，后续加入碳气体需要明确扩展。 |
| `src/sludge_sandbox/reaction_reference.py`：`Component`、`Reaction`、`Anchor`、`ReactionReferenceNetwork.solve(required_outputs=...)` | kg 组分/明确反应进度基准，检查质量、元素、热化学循环；保留未确定参考能的零空间。`identified_value(...)` 可区分真正可辨识输出与需要额外锚点的输出。不能把表示时自由坐标取零叫作反应热为零。 |
| `src/sludge_sandbox/solid_reactions.py`：`SolidReactionConfig(...).evaluate_cell(row, decoded, cell_index)` | 可复用真实库存/相提供者绑定和净生成率汇总。当前只接 `SolidFluidStorage`、摩尔物种以及按当前总体积浓度的 `ArrheniusMassAction`；要求统一 NIST 298.15 K 元素标准生成参考。GNEST 拟组分 kg 产率或 Nowicki 图坐标都不能直接塞入此摩尔接口。 |
| `src/sludge_sandbox/nowicki_oxidation.py`：`calculate_nowicki_oxygen_times(source_directory, temperature_c=..., conversion_levels=...)` | 已实现 450–550°C、固定 10 vol.% O2 的端点拟合插值与 `alpha_plot` 到达时间。源码明确：预制市政污泥炭，`mass_or_molar_conversion_admitted=false`，耗氧、产气计量与反应热均未知。适合独立源条件对照，尚不是原泥耗氧/放热模块。 |

**第一步的可交付范围与需要的来源。** 接线时保持同一液水库存、干质量和总 U；给出低 W 的新自由能分支，由同一函数导出 μ、偏焓、储能及正热力学因子，再显式处理到干态的参考能差。外界温度、水汽分压/排出量和几何可以是 `virtual_design_choice`；封闭总水列本身不能当成已排湿的砖。验收应包含实际热驱动/排湿轨迹、W/T/压力反馈、边界排水与携能账，以及过渡前后同一能量基准的反解；仅验证恒等式不是这一模块完成。

| 待补数据或选择 | 按合同 §4 可立即采取的限定路线 |
|---|---|
| 当前下界以下的吸附/脱附与低 W 导热、迁水关系；何时称为“干”的定义 | 优先补原材料低湿段来源；也可另立**标明域外的自由能延拓/替代供体分支**，记录连接条件和参数来源，以 `derived_from_evidence` 与 `virtual_design_choice` 分开登记，延拓/跨材料误差保持 unknown。阈值若只是输出分类，保留真实残水库存；不得按阈值无账删除水。 |
| 干态及继续升温后的 Cp(T)、相变/反应前适用区间 | 当前湿态的截温值不是高温 Cp 证据。可选择公开干泥/矿物供体热容并显式桥接参考值、说明材料转移；也可做明确温域内的正 Cp 延拓。未知模型误差不改成零，发生分解后必须更新组成与储能，不能让恒定干物质身份贯穿烧成。 |
| 湿态原料到反应物种的质量/元素清单，以及共同 h0/反应热锚点 | 不必等完整材料包才建 `ReactionReferenceNetwork`：先登记已知元素、已知热量和未定自由度，算可辨识的组合。未测伪组分组成、矿物比例或能量自由度若要选定，必须成为可审查的虚拟材料定义/供体迁移；这授予计算分支，不授予原材料事实。 |

**GNEST / Areias / Nowicki 应怎样进入后续反应阶段。** `data/sandbox/research/gnest2021/source_facts.json` 已登记 GNEST 六个拟合过程的 Ea、ln(k0)、n、yi 和产物系数，附接受稿及发表版来源 SHA/定位。它是 El Salitre 消化调理泥，不是 Arlabosse 原料；Table3 系数按 Eq11 与反应基准关联，不是摩尔化学计量。按现有打印数精确相加，R3/R4 的“产物和−yi”各为 +0.001，R5/R6 各为 −0.05；Table4 的 960°C 产品和为 0.9507，缺额 0.0493。**可先实现源条件六过程动力学/总失重与分项生成响应，但不能归一化这些表格后伪称元素和能量闭合。** 将其接进自洽温度反解，还需要：反应进度与干/灰基准映射、凝液/残炭/未解释产品的组成约束，以及反应能与演化 Cp。守恒一致的虚拟伪组分构成可以作为独立候选；若原表约束互相矛盾，应保留差额与分支选择，不靠一个“未知桶”隐去元素超额。

`data/sandbox/research/gnest-char-energy-v1/source_facts.json` 进一步给出同研究 TG3：570°C 固体收率 0.6919、LHV 7.77 MJ/kg；960°C 为 0.5687、5.19 MJ/kg，原料 LHV 11.3 MJ/kg。这有助于约束保留燃料能，却**不是**热解反应焓或升温需热；不得直接充当 `Reaction.enthalpy_j_per_kg_extent`。`data/sandbox/research/raw-sludge-closure-audit-v1/audit.json` 列出的伪组分、元素回收和温变储能缺口仍可作为资料清单，不能把其历史“不具完整包”解释成永久不可实施。

`data/sandbox/research/areias2019/facts.json` 已确认实验室加熟石灰为加料前采集污泥干质量的 15%，不是最终配合料的 15%，也不是经确认的纯 Ca(OH)2 库存；厂内此前加灰量未知，2019/2025 同批材料未确认。它可支撑明确的配料/处理条件与后续源曲线比较。若下一步选定氢氧化钙或碳酸盐分解子网络，应另取实际矿相/有效比例及纯物种热化学/动力学依据，或声明受控虚拟配料，不能把这条加料说明直接变成矿物计量。

因此可执行的顺序是：**低 W 与干态能量桥接 → 来源/虚拟选择明确的演化组分反应模块 → 烧结与冷却所需的组成、体积、热容和力学状态传递。** 最后一段还需来源明确的收缩/致密化与力学本构及独立比较数据；本轮没有把已有通用主机名称当成已经串联的材料模型。

本报告只读取上述八个文件，实际路径及 SHA 见同目录 `READ_SNAPSHOT.json`；当前 K/D 阶段范围引用本任务已有共享上下文。未联网、未执行 EOS/原生轨迹、未修改生产文件，也未扩读材料历史。
