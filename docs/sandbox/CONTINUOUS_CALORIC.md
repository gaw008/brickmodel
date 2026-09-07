# 保留原 Cp 的连续 Shomate 焓派生模型

`continuous_caloric.py` 提供 `ContinuousShomateGas`：输入已验证的原始 `ShomateGas`、派生模型 ID/版本、显式锚温、派生方法来源 ID、气体常数来源 ID。不修改原模块或源系数，不接 IAPWS，不提供熵/自由能或尚未证明的相平衡接口。

## 定义与可追查偏移

从原曲线在指定锚温的原 `h(Tanchor)` 出发，沿已覆盖、相邻的原温度段积分：

```text
h_derived(T) = h_original(Tanchor) + integral[Tanchor,T] Cp_original(theta) dtheta
u_derived(T) = h_derived(T) - R*T
Cv_derived(T) = Cp_original(T) - R
```

锚通常可选某段内部；也支持域端点/接缝，接缝原焓锚采用原 `ShomateGas` 已规定的高温段。锚是对原拟合函数的求值，不是新增的实测值。改变锚可能改变整条派生曲线的常数能量偏移，必须建立新的派生配置身份，不混用基准。

方法 ID 为 `piecewise_shomate_cp_integral_v1`，原 A–H 系数和各段温区保存在不可变 `source_gas`/`source_segment` 中。`segment_offsets` 对每一段保存原温区、相对原焓方程的常数偏移（J/mol）、比较温度（该段下界）、该处原/派生 h 和原段来源。偏移按二进制输入系数对应的精确原焓公式计算；原浮点接口的显示值可能额外有末位舍入，因此“两个显示值相减”与记录偏移可能相差舍入量。

原 Cp 保持完全不变，其接缝跳跃保留；h/u 在接缝连续。精确节点由高温段拥有，最末端包含在最后一段。原 `ShomateGas` 本就拒绝不相邻温区；本模型不扩展原范围、不填缺口、不抹平 Cp 跳变。温度反解仍须单独处理分段导数，当前模块未新增温度反演或直接替换旧 `Thermochemistry` 接口。

## 来源与分类

`source_classification` 保存原分类。来自 `literature_constitutive_model` 的派生曲线分类为 `derived_from_evidence`；原 `manufactured_test_fixture` 始终保留人工分类，并要求 `allow_manufactured=True`。不能通过派生后重命名变成文献材料事实。

`source_ids` 合并原气体/各段、方法和显式 R 的来源。原 `ShomateGas` 不携带所属包的常数来源，因此调用方必须另外传入 `gas_constant_source_ids`（例如原 `Thermochemistry.constant_source_ids`）。原 R 数值不变。`provenance_status` 仍为声明来源链接与派生、尚未完成材料准入；真实资产/源 DAG 和材料适用性检查不由此模块替代。

这不是修复原 NIST 数据，也不声称更真实或误差更小。它是为了具有单值、连续热量状态而明确选择的派生模型。原热化学模块、接缝诊断与历史测试保持不变。

## 数值积分及分辨率

令 `x=T1/1000, y=T2/1000`，在单段上：

```text
Delta h = 1000*[A*(y-x) + B*(y²-x²)/2 + C*(y³-x³)/3
               + D*(y⁴-x⁴)/4 + E*(1/x-1/y)]
```

实现用原 binary64 系数/温度的精确 `Fraction` 算术，在最终输出时一次舍入。跨段积分及段低端锚也保持精确累加，不使用两个巨大原 h 值相减求小热量。`enthalpy_change_j_mol(T1,T2)` 和 `internal_energy_change_j_mol(T1,T2)` 直接积分，反向积分严格取反。

输出 float 的绝对 h/u 仍具有有限分辨率；不能声称巨大的生成能基准下能从两个绝对浮点值相减恢复任意小的热量。`resolution_j_mol(T)` 显式返回 h、u 和原 h 锚的 ulp（J/mol），只是表示分辨率，不是实验不确定性。原锚本身来自原浮点接口的求值，其已有舍入也不会被积分逆向恢复。

## 实际验证与范围

先写测试并实际观察模块缺失 collection error，再实现。验证命令：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_continuous_caloric.py -q
```

当前 22 tests passed。测试包括三段正向/反向热循环、节点两侧严格同 h、保留 Cp 跳变、锚在中段或接缝、每段偏移可重算、四种真实缓存 NIST 气体的独立 SciPy Cp 积分、全部多项式/倒温平方项的 90 位 Decimal 近邻浮点积分、巨大原 h 下小增量未丢失、绝对值 ulp 诊断、超域/非有限/fixture 分类及来源门禁。

以各气体第一段中点作原 h 锚的一次实际诊断（不是默认锚）得到：

| 气体 | 锚温 K | 依次各段相对原 h 的偏移 J/mol |
|---|---:|---|
| O2 | 400 | 约 0, 1.714022032, 0.476855365 |
| N2 | 300 | 约 0, -0.768385417, -0.874218750 |
| CO2 | 749 | 约 0, 3.167188533 |
| H2O | 1100 | 约 0, 2.928677143 |

这些偏移来自本仓库原 NIST 系数与明确锚点，不能解释成新测量误差范围。当前只覆盖原气体表已有温区；水汽仍从原 500 K 起，未桥接低温 IAPWS，也没有原污泥凝聚相或全砖热力学资格。

## 实际派生包与积分器连接

已验证可显式使用新的 `pack_id`，将 `ContinuousShomateGas` 实例作为 `Thermochemistry` 的气体对象，再交给原 `GasHeatModel`。当前运行时使用的分段查询、h/u/Cp/Cv、温区、R 和来源/分类接口兼容；没有更改原模型或加载器，也没有声称原 JSON 加载格式支持派生对象。旧 `Thermochemistry` 的类型标注仍为 `ShomateGas`，此验证证明当前运行时装配路径，不改变其静态类型声明。

实际集成制造测试为单格、固定几何、密闭一摩尔气体，施加明确人工电功率 1000 W，从 500 K 跨过 600 K 原焓接缝升温至 700 K。每一次试探实际调用 `GasHeatModel`（其内部反解温度），源人工分类与门禁仍保留。原 Cp 分段为 30/40 J/(mol K)、R=8，因此独立解析 Cv 为 22/32，600 K 时刻为 2.2 s，5.4 s 累计外功为 5400 J。所有保存温度按 1e-8 K 绝对门槛比较，所有状态及每步能量按 1e-8 J 绝对门槛比较，均通过；实际经过接缝节点且无拒绝步、无 gap/ambiguous 状态。

另用真实 O2 原始来源显式装配新的派生包，在 699.9、700 和 700.1 K 进行实际能量反解，按 1e-8 K 绝对门槛通过，同时保留原曲线非零接缝差。制造集成不是现实砖实验，真实 O2 物性往返也不是原污泥材料验证。
