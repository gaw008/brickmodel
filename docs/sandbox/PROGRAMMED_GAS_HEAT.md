# 动态气氛与表面对流辐射边界

`programmed_gas_heat.py` 为已有刚性纯气体 `GasHeatModel` 接入 `BoundaryProgram`，不提供凝聚相储能或材料系数。其 `material_qualified` 始终为 false；这是实际运行的边界耦合模块，尚不代表湿砖全流程。

## 物理组装

每一次 `evaluate(state,time)` 或积分器 `__call__`，均执行：

1. 由当前库存与内能反解单元温度，同时检查原始基模热化学签名未被修改。
2. 从连续边界程序取得当前炉气温度、有效辐射环境温度、总压与所有物种摩尔分数，构造当前外部 `GasState`。边界物种及其顺序必须与基模完整匹配。
3. 在末格中心与真实外表面之间保留半格导热热阻，求表面温度 `Ts`：

   `A*(2*k/dx)*(Ts-Tcell) = A*h*(Tgas-Ts) + A*epsilon*sigma*(Trad^4-Ts^4)`。

4. 在临时基模中设置当前 reservoir 与求得的表面温度，调用原有共享面输运与焓组装。对流/辐射经半格导热进入边界面账本；气体物流焓按原有扩散面温与对流供体温另外计入一次。没有额外叠加第二份外部热源。

实际表面积来自基模 `face_area_m2`。`Tgas` 不是材料表面温度，`Trad` 是有效黑体辐射环境温度，沿用灰表面对该环境、视角系数 1 的近似；不自动代表有限灰壁或参与性气体辐射。基模已有 reservoir 或物面温度边界时拒绝构造，防止重复设置。

所有 `h`、`epsilon`、`sigma` 必须显式给出，单位分别为 W/(m² K)、1、W/(m² K⁴)，并提供系数组 ID、版本、来源类别和来源 ID；无材料默认值。系数类别为 `literature_candidate` 或 `manufactured`，后者和任何人工基模依赖均要求显式 `allow_manufactured=True`。来源身份尚不等于全部参数适用性准入，调用者仍须提供系数各自来源与有效域。

## 表面求解与极限

表面平衡残差为“入体导热 − 对流入热 − 辐射入热”，单位 W。使用三温最小值与最大值括根，单调二分，不依赖 SciPy。`SurfacePolicy` 明确给出绝对 W 残差、相对残差与最大迭代数；停止界为 `abs_tol + rel_tol*max(|导热|, |对流|, |辐射|)`。这些是求根数值政策，不是材料不确定性。两个端点及每次迭代都按同一公式验证。

- 纯对流极限满足串联关系 `qin/A=(Tgas-Tcell)/(dx/(2*k)+1/h)`。
- `k=0` 时没有入体导热；若外膜非零，仍求外表面对流与辐射的零净热平衡。
- `h=epsilon=0` 时无膜热；`k>0` 时 Ts=Tcell。三者全零时表面温度不唯一，报告 `insulated_surface_undetermined`，仅选择 Tcell 作为无热流的表示值。
- 超过迭代数或浮点无法进一步分辨根时抛出 `ProgrammedGasHeatError`，积分器保存为 numerical_failure，不把失败解释为材料不可行。

`ProgrammedEvaluation` 提供实际 `Rates`、原始 `BoundaryState`、reservoir、表面温度、独立对流/辐射热、入体导热、实际残差/允许界、迭代次数与状态。

边界程序自身从不归一化组成。已有 `ideal_gas_reservoir` 对已获准的浮点总和误差作显式归一化；此 wrapper 不隐藏这一步：evaluation 同时保留未改变的边界组成、`reservoir_input_mole_fractions`、`reservoir_input_fraction_sum` 和 `reservoir_max_abs_fraction_correction`。程序准许总和误差仅为 8 ulp；这不是允许改变实测配方的依据。

## 积分连接与失败分类

使用 `integrate(..., breakpoints_s=operator.breakpoints_s(start,end))` 使所有斜率节点成为实际积分端点。每个试探阶段重新读取程序和求表面根，包含被拒绝的试探；连续程序不能表达同时间跳变，真实跳变仍需左右侧分段重启。

有效有限时间超出程序域为 `DomainExit`。非有限查询时间、无效配置、表面数值失败为数值/合同错误；原基模物性域错误保持原分类，不吞掉意外代码错误。边界气体的物性使用域由现有气体交换/热化学层检查。本模块仍属于固定几何、纯气体储能模型。

## 实际验证

先写测试，初始运行因模块不存在而 collection error；完成实现后执行：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_programmed_gas_heat.py -q
```

当前 15 tests passed。验证包括实际半格热阻与面积缩放、纯对流解析串联、辐射非线性平衡的独立 SciPy brentq 参考、动态压力/组成改变实际流量和焓、独立手算有限压力流入及供体生成焓、绝热/零 k 极限、求根失败保存及热化学修改检测、来源和 reservoir 修正可见性。

真实积分采用分段升/降温程序，温度响应与分段线性驱动的一阶系统解析解对照，所有保存步骤重算外部能量账本。最初 0.05 s 最大步长得到约 1.25e-5 K 误差，未通过预先的 2e-6 K 比较门槛；随后收紧求解设置为起步 0.002 s、最大步长 0.005 s、相对容差 1e-8，通过原门槛。没有放宽结果门槛。

本机有 tracemalloc 的 100 次辐射/对流完整 boundary evaluate 测量：0.241 s，Python 跟踪峰值 88004 bytes，表面最多 41 次二分。此为单格制造测试的粗成本记录，不是全砖耗时、RSS 或性能承诺；基模每次临时替换会有额外构造成本。

## 绝对门槛的显式化复验

后续审核将所有声明绝对门槛的 `pytest.approx` 调用显式写为 `rel=0`，保留原绝对门槛。压力 EOS 对照明确为相对 `1e-12`、绝对 0；端点组成明确为绝对 `1e-15`、相对 0。物理实现与积分政策均未修改。

原粗步运行的实际 pytest 输出确为 `1 failed, 11 passed`，解析比较为 `602.5795230577728` 对 `602.5795355951195 ± 2.0e-06`。在本项目 pytest 8.4.2 中，显式 `abs` 且未提供 `rel` 的比较已经只使用绝对门槛；对该历史数值直接重新比较返回 False，显式 `rel=0` 同样返回 False。因此这次修改使数值合同更清楚，不能据此声称历史门槛曾被默认相对容差放宽。最终显式门槛测试实际复跑为 `15 passed in 0.60s`，其中 2e-6 K 解析门槛保持通过；保留旧提交和审核绑定历史。
