# G2 气体与热耦合算子独立审查

审查者：`code_review_g1_b2`；2026-09-07 UTC。范围为 `src/sludge_sandbox/gas_heat_model.py`、`tests/sandbox/test_gas_heat_model.py`、`GAS_HEAT_MODEL.md`。审查者只读源码，执行测试和临时独立探针，仅维护本报告，没有修改实现或提交。

**最终 Approve：可作为固定几何、仅气相储能的局部耦合验证模块提交。** 初审错误分类问题已修复复验，本范围内没有遗留 CRITICAL/HIGH 问题。该结论不构成湿砖全周期、凝聚相热物性或原污泥反应机制的外部验证。

## 初审发现与修补

### [MEDIUM，已修复] 内部通量错误被转换成物理域退出

位置：初审 `GasHeatModel.__call__()` 末尾对 `ThermochemistryError/GasTransportError/ExchangeError/ReactionError` 的统一捕获，以及温度反解 helper 中无区别转换。

可复现：在有效模型上把内部 `_face` 返回对象的 net 置为零，保留实际 diffusive/advective rates。焓交换接口正确抛出 `Inconsistent net species flow and energy-bearing components`，但积分结果却为 `domain_exit`。同样，温度反解不收敛和数值能量分辨率不足不能作为材料温区不可用。

修补后的 `_raise_operator_failure()` 仅将明确列举的温区/公共温域、能量域/原拟合接缝、多根、空热库存以及明确动力学温域错误映射为 DomainExit。其他模块契约和数值错误转换为继承 IntegrationError 的 GasHeatModelError，保留原异常链；未预期 RuntimeError/KeyError 继续传播。独立复验 net 不一致、`temperature_inverse_not_converged`、`insufficient_energy_resolution` 三例均得到 numerical_failure，且不产生接受步骤。真实 NIST N2 接缝案例仍为 domain_exit。

文档先前把真正表温跳变交给 breakpoints，与积分器支持域不符；现已改为连续温程斜率节点可用 breakpoints，真正跳变须按两侧 operator 分段重启。公开状态构造、温度查询和状态/来源 property 的类型注解已补齐。

## 物理约定、离散和资格

- 每次试探从当前 n/U 反解 T，再用当前 n、固定气孔体积和 T 更新 EOS；不复用初态压力或温度。每个内部面计算一份物种与能量通量，后续由积分器两侧相反号装配。
- 传热半格距离为各自 dx/2，导热使用两段串联阻力。D 在共同面 EOS 近似下作半格串联；Darcy 串联的是完整 `K*kr/mu`，而非各参数分别平均。传入现有 gas face API 时使用 `K_argument=b_face*mu_face, kr_argument=1` 的代数重构；原始相对渗透率没有丢弃。
- 面 p/T/X 使用 `dr/(dl+dr)` 权重。扩散焓使用共同面温，对流焓使用真实供体温；总能量率再加单面导热。源形式沿用此前独立审查过的气体与热化学模块；没有新加反应热、潜热或压力功。
- 可选反应网络必须具有完全相同物种顺序、气相身份、摩尔质量和 R。反应浓度采用当前单元总体积，EOS 采用气孔体积，代码没有混用。模型不允许把缺失固/液相热容的反应塞入该气相储能模型。
- 左侧对称、右侧默认密闭绝热。显式外部 GasState 定义在表面，只跨越最后一个半格；它不是未经传质膜定义的远场炉气。Dirichlet 表温导热将一个半格拆成同 k 两个四分之一格，阻力仍为 dx/(2k)；不隐含新增气膜或对流辐射模型。
- 几何与系数复制冻结，气孔体积不得超过 bulk volume；热化学包装另作副本并检查后续参数变更。系数集 ID、版本和来源须声明；制造热化学、系数或反应必须显式允许。状态仍为 `operator_integration_validation_not_material_qualified`，来源 ID 没有被当作 runtime 资格凭据。真实 NIST 接缝测试只是真实气体热化学数据的域测试，其余几何和输运仍是制造条件。

## 独立验证

最终实际执行 integration 与本模块测试得到 **28+26=54 passed in 0.75 s**；其中本模块为 26 项，包含真实调用 integrate 的封闭多机制、关闭流动/导热对照、解析双格热交换和等热性扩散、气相生成能反应、开放边界账本及异常分类回归。作者所述历史红阶段按其记录保留，本审查另独立复现过原始 net 错误分类。

额外执行 5 个独立探针：

1. 两格宽 2/4、气体浓度 1/2、温度 600/900，左右 `K*kr/mu` 分别为 `3e-6` 和 `8e-6`；使用 60 位 Decimal 从阻力、面 c=10/7、供体 h 独立计算。实际摩尔率 `-0.023510204081633873 mol/s`，总能量率 `-824.4884897960072 W`，与 Decimal 的能量差 `-8.890310709830374e-11 W`。
2. 制造气体 A/B 的 cp 分别 30/40、生成焓差 1000 J/mol，纯扩散、非等格宽、D 串联得到 .4、交换率 ±.08；正确共同面 T=700 给 `-241.48 W`。实际 `-241.47999999993624 W`。使用不同 cp 避免相同 cp 抵消而掩盖错误面温。
3. 内部 net 契约错误明确 numerical_failure。
4. 反解不收敛明确 numerical_failure。
5. 数值能量分辨率不足明确 numerical_failure。

前两组系数均为显式制造条件，用于验证代数和接口，不是额外实验点。没有导入未知污泥导热率、反应产率或热容。

| 文件 | 最终 SHA-256 |
| --- | --- |
| `src/sludge_sandbox/gas_heat_model.py` | `6019ac11662e8cb79ce75d0ed786c753cfe419904f74901eee750e45737cdbd9` |
| `tests/sandbox/test_gas_heat_model.py` | `b6a639ae61e364ca2e3a37290de0fbe84d3dd437287b81285b8d958452edcc26` |
| `docs/sandbox/research/GAS_HEAT_MODEL.md` | `5458edf4e0ef3e58a9ff24df9180693d2f87576314c645a4e48b837948994430` |

当前环境没有 ruff/mypy/pylint/black 可执行文件，未虚报静态检查通过。独立积分器、反应及守恒审计的状态须分别见其报告，不能用本报告跳过它们的验收。
