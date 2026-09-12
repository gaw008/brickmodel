# 用户可运行的 Cedrone 有限加氧入口：最小设计

本轮只做静态接口核对和设计，未导入 Cantera、调用 Element、构相或求平衡；不改当前冻结试验或正式代码。实施与实际入口 smoke 等 ROOT 收到两个新增点结果后决定。

## 入口与一次计算范围

建议新增 `examples/sandbox/run_cedrone_oxygen.py`，中文帮助及短终态输出：

```sh
python examples/sandbox/run_cedrone_oxygen.py \
  --source-root /path/to/brickmodel \
  --output-dir /path/to/new-result \
  --lambda 1/4
```

`--source-root` 必需，只供读取公开数据；`--output-dir` 必须是尚不存在的新目录；`--lambda` 必需，严格枚举 `0`、`1/4`、`1`，精确转 Fraction。固定 800 K、100000 Pa、VCS、element_basis、18 气体＋C(gr)，没有算法/温度/额外物种/任意加气参数。一次命令只求所选一点，不自动比较三点、不先求基线。用户显式选 λ=0 时才求该点；独立于此次研究脚本中“复用保存 λ=0”的处理。

公开运行前提仅是可导入的本项目（含 equilibrium 可选依赖 Cantera==3.2.0）与公开来源目录；不需要任何 `/private/tmp`、旧 native JSON、安装机器路径、原监督状态、原 PDF 缓存或 profiling 文件。原论文链接/原件 SHA 用作追查信息，不能把本次读 JSON 写成重新读过原 PDF。

## 最小计算代码和数据位置

建议新建小模块 `src/sludge_sandbox/cedrone_oxygen.py`，不修改现有 TP 求解器：

1. `derive_cedrone_oxygen_pool(source_root, lambda_value, atomic_weights)`：读取当前公开 printed-pool 的固定字节，核其既有单文件 SHA `92feba43d25479d99a2607466fb902841d0afcffc5b1108ca2ff74a42145f7fd`；从同一字节解析原 kg Fraction。返回现有 `TPPool` 和一份小输入记录，含原 m/b、A、λ、D、加料分子/元素/质量、总量、来源/分类与 unknown。传入 A 在这一阶段只是明确待绑定读数，不自动授予实际来源资格。
2. `check_cedrone_oxygen_result(result, input_record)`：在完整结果保存后，核实际求解来源/原子量与输入相同，再从实际返回库存构造全部 19 物种的 mol、模型 kg、气相分数、C(gr)/原 bC、逐元素残差及加权质量恒等式。成功要求现有 core 原全部门通过；不增加任何产物方向门。

数值来源仍是 `data/sandbox/research/cedrone2024-element-pool-v1/{printed-pool.json,README.md}` 和 core 已核的 `data/sandbox/research/tp-equilibrium-v1/`。新模块内一个明确 `definition()`/记录即可声明公式、固定虚拟边界和分类；没有新数据测量，因此不再复制一套 facts 或创建通用 manifest。未来公开说明可放 `docs/sandbox/research/tp-equilibrium-v1/`，原论文数据、许可证和当前源追查记录不改。

## 已核的原子量接口及绑定条件

本机已安装 Cantera 3.2.0 的 `thermo.pyi:592–604` 声明独立 `Element(arg: str | int)`，属性 `symbol`、`atomic_number`、`weight: float`；`__init__.pyi:25` 从 thermo 公开导出。`thermo.pxd:257–267` 另声明 `Cantera::getElementWeight(string/int)` 的无相参数重载。安装 METADATA 名称/版本已静态核读，路径、SHA、行和摘录保存于 `LOCAL_API_READ.json`。

因此建议实际入口直接调用 `ct.Element(e).weight`，e 顺序固定 C,H,O,N,S；不需要先构造 Solution/Mixture 或求 λ=0。本轮证据是公开接口及 C++ 绑定声明，wheel 未含这段实现正文，也未实际调用，因此不冒称已测得值或已证明与相字段一致。

实际运行先核 ct.__version__==3.2.0，再逐个核返回 symbol、正有限 weight，原浮点和 `Fraction.from_float(weight)` 都保存。A 数值作为 kg/kmol（同 g/mol）用于 `b=1000m/A`；不要把打印的 12.011 等字符串当另一个精确值，也不回退到手写原子量表。独立元素表允许不建相；但自定义相元素可能不同，所以**同次** result.initial/final.loaded_definition.gas_atomic_weights_kg_kmol 必须逐元素与保存 A 严格相等。版本名相同不足以代替此检查。每个已完成 Element 读数先保留再查时间，失败保存已读前缀；即使相绑定失败也保留实际 solve 返回，不重求。

来源链为论文 Table4→公开 nominal_CHONS_kg→同次 Cantera Element A→精确 b/外加气→TPPool→同次相 A/19 物种源参数复核→结果质量账。原子量供应者信息和 TP 实际 provider/provenance 分开保存，最终才置 `atomic_weights_binding_checked=true`。

## 物理、基准与分类

原 m 总和 .704 kg；`D=bC+bH/4+bS−bO/2`，O₂add=λD，N₂add=(79/21)λD。每点从原 b 构造；O/N 原子增量分别为二倍分子数。总模型质量必须为 `.704+Madd`，全输出仍按原 1 kg 论文报告样本，不按加气后每 kg 重归一化。

原 C/H/N/S 读数是 measured_public_data；O 是原文差减的 derived_from_evidence；kg→mol/名义加料和质量账为 derived_from_evidence；21/79、λ、封闭库存和固定 800 K/1 bar 为 virtual_design_choice。将全部报告 CHONS 视为可进入限定气体/石墨的条件近似单独说明；它不消除矿物分配、严格干基、O/协方差、材料延伸误差等 unknown。

灰 .292 kg、Cl .0005 kg、n.d. Br 和 .0035 kg 打印缺口仍在外置记录，残余水和固定碳不重复加入。C(gr) 不能叫实测 char，标准参考 H/G 差不能叫烧成供热/放热，单点 TP 不等于动力学、开放流动累计排气或实际排放。λ=1 不以石墨消失为门；material_qualified 和 training_eligible 始终 false。

## 保存和原预算

新目录使用少数明确文件：`INPUT.json`（原始请求与来源/原子量前缀）、独占 `RESULT.json`（实际一次 TPResult）、`OBSERVABLES.json`、`STATUS.json`。只复用已有窄 Fraction/dataclass/Mapping JSON 转换，不保存 live provider，不建新 schema/恢复平台。先保存用户请求再导入可选库；记录阶段区别来源/依赖失败、原子量读取失败、about_to_call、已返回未核查、后验失败和 resource_limit。RESULT 写失败也不能退回 not_run；I/O 出错不保证未成功落盘的对象已完整保存。

保留模块 10 s、入口总 30 s，不开放资源调大参数。每次具体返回（导入/Element/solve）先保存已得对象或前缀，再 guard；同一个最终 elapsed 决定终态。成功需同时通过 core 原 T/P/非负/元素/G/KKT/来源门与薄层相 A、质量恒等式。元素门仍为 `|r|≤10⁻¹⁰(1+|bλ|)`，传播的质量界仍是 `ΣA·10⁻¹⁰(1+|bλ|)/1000`，不变成材料不确定性。

若公开入口承诺原生调用进行中的硬时限，应直接复用仓库已发布 `research-process-supervisor/supervisor.py:74–76` 的 `run_attempt(..., timeout_s=40, cleanup_grace_s=5)`：父入口只起同一 Python 的一个受监督 worker，代码位置从已发布示例自身定位，**不能把 --source-root 下任意 Python 当代码导入**。监督输出另放新结果目录子目录；只绑定本次入口、固定来源/核心等必要当前输入，不带研究历史。不要把仅函数边界的 10/30 s guard 声称可打断悬挂 native。ROOT 可决定复用薄父入口的具体接线，毋须另写监督器。

## 实施后的有限验收建议

先做无 EOS 的 help/参数/拒绝覆盖；用制造 Element 读取失败及相 A 不一致、RESULT 首写失败验证真实前缀和非零终态；用 Fraction 核三个 λ 的量纲、质量和原池独立性。实际物性验收仅由 ROOT 另登记一次新入口 smoke，选已通过新增点之一，与保存同条件结果做名义输出/元素质量对应；不为取 A、预热、profiling 再加 solve。只有这次调用实际核准后，才能说新 Element→相权重的应用路径通过，不能用本设计或制造检查替代。
