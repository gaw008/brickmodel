# 单元反应算子 v1

复验更新：新增 `(feed=1e20, extent=1)` 与 `(feed=1e16, extent=3)` 两项库存量化反例，先失败，再加入实际增量分辨率检查。`amounts_after_extents` 将 `after-before-change` 与每个提议变化量比较；默认最大相对误差 1e-10，是数值政策而非材料参数，调用者可收紧，不可放宽。无法表征则报 `unresolvable_inventory_increment`，不生成不匹配的产物。当前 49 项反应测试通过；下文 47 项是修补前历史记录。独立复审见 CODE_REVIEW_REACTIONS.md。

日期：2026-09-07 UTC。实现位于 `src/sludge_sandbox/reactions.py`。本模块提供可运行的计量与候选动力学计算，不提供真实原污泥反应机制或产物分配，也不因来源 ID 非空而授予材料资格。

## 数据与来源边界

`SpeciesDefinition` 必须显式提供物种 ID、相态、元素正整数计数、摩尔质量 kg/mol、来源 ID 和分类。元素名称沿用材料模块的元素符号集合；没有调用原子量表，没有从元素计数推算或修补摩尔质量。分数计量用反应系数表达。当前没有离子电荷或电子库存模型。

`ReactionDefinition` 保存反应 ID/版本、完整有符号计量、路径类别、完整动力学候选和计量来源。`ArrheniusMassAction` 保存候选 ID/版本、A、Ea、每个反应物的阶次、浓度基准及参考浓度、温度有效域、显式 R、各单位及来源。同一候选 ID/版本不能指向不同成套参数。所有映射复制后只读，外层数据对象冻结，网络输入顺序冻结。

源公式参考于 2026-09-07 实际核读的两个官方页面：

- [Cantera 3.1 Reaction Rates](https://www.cantera.org/3.1/reference/kinetics/reaction-rates.html)：Elementary Reactions 与 Reaction Orders，分别给出浓度乘积形式和非基元反应的显式阶次；后者提醒 A 的传统单位依赖总阶次。
- [Cantera 3.1 Rate Constant Parameterizations](https://www.cantera.org/3.1/reference/kinetics/rate-constants.html)：Arrhenius Rate Expressions 给出 `A T^b exp(-Ea/RT)`。本版限定 `b=0`，仅作普通 Arrhenius 候选。

这里引用的是形式依据，没有移植文档示例的任何材料参数。IUPAC Arrhenius 条目搜索可返回摘要，但本环境实际打开条目及 PDF 均为 HTTP 403；该访问未被记为已核读全文。模块不联网，也不复制来源全文。

测试中的 feed、char、H₂ 等名称、计量、圆整数摩尔质量、`R=8 J/(mol K)`、A 和 Ea 均只属于 `manufactured:reaction-tests-v1`。其中 feed 的指定元素式不表示真实固态甲烷或原污泥。它们不是生产默认值，不是文献拟合值，也不借用旧 synthetic 包。

分类仅允许 `manufactured` 或 `literature_candidate`。包含制造物种或制造动力学的网络必须显式 `allow_manufactured=True`。两种路径的 `material_qualified` 都为 false；后者状态为 `candidate_sources_not_resolved_not_material_qualified`。真实原泥的身份、产物、参数配套性和适用域仍需独立证据解析。

## 计量与守恒

矩阵 `S[i,r]` 的行按 `species_order`、列按 `reaction_order`。负数消耗，正数生成，系数为 mol 物种/mol 反应进度：

```text
source_mol_s[i] = sum_r S[i,r] * extent_mol_s[r]
delta_amount_mol[i] = sum_r S[i,r] * extent_mol[r]
```

所有反应进度必须有限且非负。每条反应必须同时有反应物和产物。未知物种、零计量项、缺失/额外阶次、重复物种或反应 ID 均拒绝；不自动补物种或配平。

元素检查使用有理数算术，要求每个元素的 `Σ a[e,i] S[i,r]` **精确为零**。整数和 `Fraction` 保留其值，浮点系数按其显式十进制表示转为有理数。质量另外使用调用者声明的全部摩尔质量检查：

```text
abs(sum_i S[i,r] M[i]) / sum_i abs(S[i,r] M[i]) <= 1e-12
```

质量判据也先在有理数上比较。`1e-12` 是固定数值输入闭合政策，不是材料误差或可调物理参数。通过元素检查不能跳过质量检查。源计算转换为浮点矩阵，因此运行后的守恒仍由积分器独立账本检查，不能把输入配平冒充全程浮点精确守恒。

## 浓度与速率定义

本版只接受 `current_cell_bulk_volume`：所有参与物种的表观浓度为实际单元库存 mol 除以当前单元总体积 m³。它**不等于气孔浓度**，也不是固体活度或比表面积。对异相反应只有明确采用这一表观基准的整套候选才可套用；本模块不把气孔速率或面积速率自动转换过来。

```text
c_i = amount_mol[i] / cell_volume_m3
q_r = A_r exp[-Ea_r / (R_r T)] product_i (c_i / c_ref,r)^order[i,r]
extent_mol_s[r] = cell_volume_m3 * q_r
```

这里 `q` 为 mol/(m³ s)，A 明确为 mol/(m³ s)，Ea 为 J/mol，R 为 J/(mol K)，`c_ref` 为 mol/m³；幂的底数和指数均无量纲。这是明确归一化后的参数化。与传统未归一化形式的代数关系是 `A_normalized = A_traditional * c_ref^sum(order)`，转换必须记录版本、单位和依据。改变参考浓度却保留原 A 会改变模型，不是无害的单位切换。

阶次必须显式给出且为正，恰好覆盖全部消耗物种，可以是非整数；并不默认等于计量数。当前不支持催化剂、第三体、零/负阶次、反向平衡或表面覆盖模型。所有候选先检查温区，随后任一必要反应物库存为零则该路径速率为零；不存在用少量虚构氧气继续耗氧的处理。A 显式为零也返回零速率。

`oxygen_free_pyrolysis` 禁止消耗定义为气相 O₂ 的物种；`oxygen_consuming` 必须确实消耗该物种。识别依赖显式元素式与相态，不依赖字符串名称。这一分类让无氧路径能够单独运行；它不证明给定热解反应或产率真实。其他明确反应可声明 `other`。

## 有限库存与积分接口

`maximum_forward_step_s(amount_mol, extent_mol_s)` 累计同一物种被所有路径消耗的总速率，以初始库存除以该总消耗求最小步长，并向零取相邻浮点数以避免除法向上舍入。无消耗时返回 infinity。这只是**冻结速率下的库存限制**，不保证数值稳定性、时间精度或新状态下速率不变。

`amounts_after_extents(amount_mol, extent_mol)` 对有限进度提案执行同一联合消耗检查，随后使用同一矩阵生成所有物种改变量。共享氧库存只能使用一次。同一提案中一条路径新生成的物种不能用于抵销另一条路径超出初始库存的消耗；需要更小步或分阶段提案。超额消耗直接报 `insufficient_inventory`，不裁剪、归一化或重新分配进度。积分器应把这一检查用于实际试探步，不应仅依赖一次步长估计。

输入可以是 list、tuple 或 NumPy 一维数组，数值次序必须匹配网络固定顺序。返回的是不可变 tuple。与守恒积分器的接口示例：

```python
rates = network.rates(amount_mol, temperature_k, cell_volume_m3)
# rates.extent_mol_s: reaction_order
# rates.source_mol_s: species_order
inventory_dt = network.maximum_forward_step_s(amount_mol, rates.extent_mol_s)
proposal = tuple(rate * dt for rate in rates.extent_mol_s)
next_amount_mol = network.amounts_after_extents(amount_mol, proposal)
```

`network` 必须由外部显式物种/计量/候选构造，上例未隐含提供真实材料实例。储存形式是实际 mol；若积分器使用 mol/m³ 初始体积，必须先乘参考单元体积，得到源后再按相同体积转换。

本模块不输出任何热源。反应改变库存后，由保持同一本步总能量账本的热化学反解更新温度；含生成能的库存变化不能再叠加一次反应焓。

## 数值失败与实测验证

速率在 log 域计算，避免幂的中间溢出。溢出、非有限项、非零速率下溢为零均明确拒绝；计量乘积进入次正规区也拒绝为 `source_outside_float_range`，以免丢失某个元素源。求和采用 `math.fsum`，并统一把求和溢出转为 `ReactionError`。不默默把慢反应置零。此政策是支持数值范围的限制，不代表现实反应速率为零。

先完成测试，再实现模块。第一次真实命令因 `sludge_sandbox.reactions` 不存在而 collection error。实现后增加的两个反例——同候选 ID/版本冲突、分数计量的次正规乘积丢失——分别先得到失败，再修复。

实际命令：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_reactions.py -q
```

结果：Python 3.12.13 / macOS arm64，**47 passed in 0.07 s**，退出码 0。覆盖独立 C/H/O 计数与质量求和、分数计量、元素和质量分别拒绝、无氧与零反应物、非整数阶次与 Arrhenius 独立算式、多路径联合氧限制、非法输入/温域/单位/来源、未知物种与参数冲突、数据冻结、浮点溢出和下溢。测试属于软件与数值验证；没有开展真实原污泥动力学拟合或外部材料验证。
