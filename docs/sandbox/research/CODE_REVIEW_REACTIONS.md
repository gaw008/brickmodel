# G2 单元反应算子独立审查

审查者：`code_review_g1_b2`；2026-09-07 UTC。范围为 `src/sludge_sandbox/reactions.py`、`tests/sandbox/test_reactions.py`、`REACTION_OPERATOR.md`。只读审查，不修改实现、不提交；最终修补结论追加于文末。本模块没有提供真实污泥反应网络，本报告不构成外部材料验证。

## 初审发现

### [HIGH，已修复] 库存更新不可表征时仍生成产物

位置：`ReactionNetwork.amounts_after_extents()` 中 `math.fsum((amount, change))` 的库存更新。

使用测试中的 feed/char/O2/CO2/H2/water 网络，原库存 `(1e20,0,0,0,0,0)`、进度 `(1,0,0)`，返回 `(1e20,1,0,0,2,0)`。feed 没有减少，却生成了 char 和 H2。`fsum` 正确舍入最终加法也不能把低于库存 ULP 的非零改变量存进单个 float。部分量化也需检查，例如 `feed=1e16`、热解进度 3，实际 feed 减少 4，产物仍按进度 3 生成。

输入反应矩阵配平和有限库存上界都不足以保证这一浮点状态更新守恒。需要拒绝不可表征的更新或采用明确的补偿机制，不应仅信任元素在输入时已经配平。作者收到反例后将修补交主代理统筹。

## 守恒、来源与模型边界核查

- 每个物种源来自同一 signed stoichiometric matrix 与非负反应进度。元素计数用 `Fraction` 精确配平；全部声明摩尔质量另外用有理数验证 `abs(residual)/sum(abs(terms)) <= 1e-12`。该数值闭合政策已在文档明示；它不把圆整摩尔质量或制造物种变成真实材料。
- `maximum_forward_step_s()` 汇总所有路径的总消耗，再使用同一初始库存限制；`amounts_after_extents()` 对有限进度重复这一联合检查，不能用同时生成物抵扣初始库存不足。零库存的必要反应物使对应速率为零；热解与耗氧路径由显式 O2 元素身份和气相判定，不依赖字符串名称。
- 网络不输出反应热；当全系统使用一致的含生成能库存时，这能避免重复热源。它不代替后续固液气总内能闭合、物种热化学域和公共常数的一致性核查。
- 2026-09-07 独立打开 [Cantera 3.1 Reaction Rates](https://www.cantera.org/3.1/reference/kinetics/reaction-rates.html#reaction-orders) 的质量作用和显式反应阶次说明，以及 [Rate Constant Parameterizations](https://www.cantera.org/3.1/reference/kinetics/rate-constants.html#arrhenius-rate-expressions) 的 Arrhenius 形式。`b=0` 和正阶次是本版明确限制；这些来源支持关系形式，不支持测试中的任何原污泥参数。
- 归一化形式 `q=A exp(-Ea/RT) product((N/V)/c_ref)^order` 中 A 为 mol/(m³ s)，`q*V` 为 mol/s。由传统未归一化形式得到 `A_normalized=A_traditional*c_ref^sum(order)` 的关系正确。当前 bulk volume 与孔气浓度、固体活度和面积速率不同，文档没有混用。
- ID/版本、来源、单位、温域、反应物阶次均必须声明；相同候选 ID/版本冲突被拒绝。`manufactured` 需要显式模式；全部路径的 `material_qualified=False`，文献候选也标记为 sources not resolved。非空来源 ID 不自动授予资格；未实现真实动力学拟合、离子电荷、催化剂、第三体或反向平衡。
- 复制后 MappingProxyType 及 tuple 保留不可变输入。源乘积进入次正规范围、浮点非有限、速率非零下溢均明确拒绝。该政策限制支持的数值范围，不把慢反应伪装成物理零。

## 独立验证

- 实际执行 `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_reactions.py -q`：初审 **47 passed in 0.06 s**。作者此前报告的两条红绿回归已在源码和测试核读；本审查没有冒称亲自运行过作者的历史红阶段。
- 100 个确定随机种子的进度/库存案例：独立写出的 C/H/O 元素行与摩尔质量向量复核源守恒，再把总消耗上界的 0.9 倍代入联合库存更新，全部非负。最大缩放元素残差 `5.4854799878688266e-17`、质量残差 `1.327567039287074e-16`。
- 9 个温度、体积、非整数阶次组合，以 60 位 Decimal 独立计算归一化 Arrhenius 乘积；与 log-domain 实现比较，最大相对差 `6.035798146750804e-16`。
- 上述 109 例均为独立临时数值探针，没有冒称额外入库 pytest，也没有充当实验点。另实际复现了前述库存 ULP 缺口。

## 修补复审与最终结论

**最终 Approve：本反应算子可以做局部阶段提交。** 初审库存量化问题已由主代理修复并独立复验，本范围内没有遗留 CRITICAL/HIGH 问题。运行时配套的守恒积分器和资格层仍须单独审查，不能以本反应算子通过代替全流程验证。

修复使用 `fsum(after, -before, -change)` 计算实际残差，比较每个非零提议变化量的相对误差，数值上限为 `1e-10`，只允许调用者收紧；分母没有使用可能很大的总库存。无法表征时明确抛出 `unresolvable_inventory_increment`。这是支持数值范围政策，不是某个材料参数，也没有凭空生成补偿物种。公开向量参数的 Iterable 类型注解已补齐。

修补后实际与 integration 联合运行得到 **22+49=71 passed in 0.19 s**；其中反应测试为 49 项。另独立执行 9 个复审探针全部通过：原始完整丢失与部分量化两反例拒绝，非法或放宽上限的 5 个配置拒绝，2 个可精确表征的更新在更紧 `1e-12` 上限下保留正确产物计量。本反应报告不采用仍在修补中的 integration 作为放行依据。

| 文件 | 最终 SHA-256 |
| --- | --- |
| `src/sludge_sandbox/reactions.py` | `ae6ca26681d03190095e774691fa99761da07f45f4bea498eeb36d7afc8e17b0` |
| `tests/sandbox/test_reactions.py` | `6ce0b7a4e83880e9fd20d8cad465ec1dce68e7f5ac796e77fd31212be9d734bb` |
| `docs/sandbox/research/REACTION_OPERATOR.md` | `00360f9391091d51bbf3d4ded6fa5831a1477afeb81eccb9a67a74c83c6807fc` |

当前环境没有 ruff/mypy/pylint/black 可执行文件，没有虚报静态检查通过。审查者仅更新本报告；没有修改反应实现或提交。以上检查不构成真实污泥动力学或外部材料验证。
