# 单面换热与气体焓通量独立审查

审查者：`code_review_g1_b2`；2026-09-07 UTC。范围仅为 `src/sludge_sandbox/exchanges.py`、`tests/sandbox/test_exchanges.py` 和 `HEAT_EXCHANGES.md` 的公式及来源范围。气体输运离散的独立审查由 `physics_architecture` 负责，本报告只检查其公开通量接口与热化学的连接。审查者没有修改生产源码、提交或撤销其他工作。

## 结论与边界

**Approve：允许该模块随 G1 做本地阶段提交。** 初审发现的两个接口/数值问题已经修补并独立复验，公开接口类型注解也已补齐；本次范围内没有遗留 CRITICAL/HIGH 问题。最终文件指纹见文末。这里验证的是单面交换率的代数、单位、数值拒绝和接口一致性；它**不构成污泥砖的外部物理验证，不证明完整能量积分器已经完成，也不意味着可跳过实测验证**。

## 初审发现与修复记录

### [HIGH，已修复] 气体净通量与能量分项未绑定

位置：初审 `exchanges.py:112` 的分项 species-set 检查及 `:115` 起的循环；修补后检查覆盖三个集合并逐物种校验净值。

初审仅比较 `diffusive_mol_s` 与 `advective_mol_s`，不读取 `net_mol_s`。`GasFaceExchange` 是公开 dataclass，类型检查不能证明其内部数值一致。把正常 `gas_case(thermo)` 经 `dataclasses.replace` 的 `net_mol_s` 全部改为零，函数仍返回 `18.84521305338889 W`。后续若质量组装读取 net、能量组装读取分项，会静默使用不同的流量。

修复要求三个物种键集合相同，逐物种 net 为有限实数，且严格等于相同的 `math.fsum((d, a))`。本接口不是拟合误差检验，不应以宽容差默许两个账本不一致。复审确认正常气体模块生成的通量满足这一约定；全零 net、缺键、多键、NaN net、bool net 均抛 `ExchangeError`。

### [MEDIUM，已修复] 相反方向溢出乘积泄漏原生异常

位置：初审 `exchanges.py:31–35` 的 `_sum` 与 `:121/:128` 的 `rate * enthalpy`；修补后逐乘积检查有限值。

初审用 O2/N2 扩散摩尔率 `1e308/-1e308`、对流率为零，可以在求和前生成 `+inf/-inf`。`math.fsum` 随后抛出原生 `ValueError: -inf + inf in fsum`，原代码只捕获 `OverflowError`。该输入应给出明确的交换失败，不能泄漏与物理域无关的底层异常。

修复在每个物种焓率乘积生成后立即检查有限值，并将求和中的 `OverflowError/ValueError` 转为 `ExchangeError`。独立复验使用一致的 net/diffusive rates，排除了提前命中净通量检查而掩盖乘积缺陷的可能；现在明确拒绝。额外验证 `BoundaryHeat(inf, -inf).total_in_w` 也得到结构化失败。

## 公式、来源和适用条件

1. **两段串联导热。** 每半格采用恒定 k、平面同一面积、无接触热阻的 Fourier 关系，消去共同面温得到 `Q = A (T_L - T_R)/(d_L/k_L + d_R/k_R)`。单位为 W，正号为左到右。交换两格及其距离、导热系数后得到相反的同一面率；显式零 k 为绝热。这里的 k 是调用者提供的当前有效系数，函数不推断材料组成或温度依赖，也不把未知 k 变成零。
2. **分离炉气和辐射环境。** 2026-09-07 实际打开并核读 [BUW / Team Fire Dynamics §6.2 Heat Flux](https://firedynamics.github.io/LectureFireSimulation/content/modelling/06_heat_transfer/02_heat_transfer_example.html#heat-flux)。该关系允许独立的入射辐射与炉气温度。代入等效黑体入射并乘面积可得本模块的 `A ε σ (T_rad⁴ - T_surface⁴)` 与 `A h (T_gas - T_surface)`。这一步是明确推导，适用视因子为 1 的声明模型；不覆盖有限灰窑壁、参与性气体或半透明表面的完整辐射问题。没有使用讲义示例材料数值。
3. **物种焓通量。** 核读官方 Cantera 3.2.0 缓存 `data/sandbox/transport/cantera-3.2-governing-equations.md` 的 Energy、Species 和变量定义。缓存 SHA-256 为 `24a7f39ea07a1737af8aee88592fecc06241eea136c1980e088f94fc4bed23ed`，与 `equation_sources.json` 的官方原始文件记录相同。[官方源文件](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/doc/sphinx/reference/onedim/governing-equations.md) 是关系来源；本轮在线重取渲染页超时，没有将失败访问写成成功。Cantera 的质量通量/质量比焓约定换算为本模块的 mol/s 与 J/mol 后得到 W。该来源支持导热和物种焓的物理约定，不直接证明本项目的有限体积离散收敛，更不是砖体实验。
4. 扩散焓使用共同 `T_face`，对流焓使用实际 `T_donor`，两项独立求和；不能先相消成净流再统一乘上风温度的焓。负的生成焓不会被误认为非法热量。理想气体焓含流动功，本接口不再另加一份 `RT`，也不重复加反应热。最终整砖能量账本仍须明确库存内能、移动几何、反应及相变的共同参考态。
5. 气体非零通路必须满足对应物种 Shomate 段温区；EOS 与热化学必须使用相同 R。水汽在 499 K 的非零扩散或对流通路均被拒绝。没有液水或固体热容替代值，也没有真实污泥导热、换热、发射率默认值。
6. `thermochemistry_source_ids` 反映调用所声明的气体/常数/温区来源；`provenance_status` 仍为 `source_links_declared_not_registry_validated`。它不是 runtime EvidenceRegistry 的通过凭证，不能提高材料域或来源覆盖率。

## 独立验证

- 原有 8 项测试实际运行通过；作者补充两条回归后，本审查实际运行 `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_exchanges.py -q`，得到 **10 passed**。作者报告补丁前两条新测试失败；本审查另用上述原始反例直接观察过错误行为。
- 临时脚本用 60 位 Decimal 和实际输入的精确二进制浮点值进行独立公式复算：9 组导热含跨越数个数量级的两侧 k、换向和等温，最大缩放误差 `1.716706338126563e-16`；12 组辐射含 ε=0/1、热冷两向及近等温，最大缩放误差 `1.2693424949847749e-16`。
- 6 组四物种带符号焓流，用原始 JSON 十进制系数独立计算 Shomate 多项式，覆盖 O2/N2/CO2/H2O、600–1700 K、不同面/供体温度和双向流；扩散、对流和总率最大绝对差 `1.7053025658242404e-13 W`。这些是人工设置的接口条件，不是气体输运或砖体的实测数据。
- 9 个非法接口/聚合探针全部结构化拒绝；另有 2 个水汽越域探针拒绝。正常气体模块输出仍能通过净流一致性检查。与上述高精度复算合计是 **38 个独立审查探针**，不冒称为 38 项入库 pytest。
- 检查 PATH 与 `.venv/bin`，未提供 ruff、mypy、pylint 或 black；没有虚报静态分析通过。使用已锁定的 Python 3.12 环境，并显式 `PYTHONPATH=src`。

## 最终快照

公开标量函数的参数/返回值和两个 total property 已补齐类型注解；独立 `inspect.signature` 检查通过。最后一轮注解改动后实际复跑该模块测试，仍为 **10 passed in 0.02s**。审查者未运行或代替主代理的统一非 editable 安装及 G1 提交绑定验收；那些结果应以主代理保存的真实收据为准。

| 文件 | 最终 SHA-256 |
| --- | --- |
| `src/sludge_sandbox/exchanges.py` | `09f148ff097ac6467e38905b36da6de1e6093209b8ff598ff8fcf2befde4d983` |
| `tests/sandbox/test_exchanges.py` | `c6f33a21b46e0e387561946d2b713f2cae3d514b2e77aab73a678b4da37bbff0` |
| `docs/sandbox/research/HEAT_EXCHANGES.md` | `a9c4e880a51a23ac873cd35ea660aa34795f035d00942b0f33f6ea8c59e85e6a` |

最初生产文件指纹为 `23b3699ec5fb39d17ae90379cd177237113a35c6c2c57019d1a85afd6dcecf24`，对应上文初审缺陷；保留它是为了区分修补前后证据。
