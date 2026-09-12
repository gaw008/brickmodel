# 最小构相候选：完整输入改用 block YAML

**建议仅改序列化布局：对同一已验 SHA 的完整 `derived` 字典生成 block YAML，仍创建两个全新的 `ct.Solution(yaml=text,name=...)`，其余 prepare、Mixture、snapshot、VCS 和接受门不变。** 这是有依据的待验证性能假设；本轮只静态读取源码、类型声明、已有 profile，没有执行新构相、EOS、平衡或 benchmark。

## 1. 已有测量究竟定位到哪里

实际读取 `finite-oxygen-execution/native01/point01/first_solve.prof` 与 `first_solve_profile.txt`，从保存的 pstats 中取值：

| 已保存函数 | cumulative s | 解释 |
|---|---:|---|
| solve_tp | 4.779134042 | 本次单次 solve 的整个被剖析成本 |
| prepare | 4.727445 | 主要成本所在；self time 为4.726997915s |
| json.dumps | .000135334 | 很小，不能说 Python JSON 序列化本身耗4.7s |
| _loaded | .000193375 | 已有物性定义检查成本很小 |
| equilibrate | .000404 | 包含 native VCS 和返回 snapshot；不能称本次 VCS 很慢 |

当前 `tp_equilibrium.py:379–390` 在 prepare 中先用 JSON 文本作为 YAML 输入，顺次构 gas、graphite，再 `_loaded()`、构 Mixture、设 T/P/库存并 snapshot。该 profile 没有把两个 Solution 的 C++ YAML解析/模型初始化成本分开，也没有把 Mixture 的本地初始化单独分开。**长单行 flow/JSON 文本的解析只是候选原因，尚未证明它贡献了全部成本或 block 必然加速。** 读取保存 profile 不是重跑或新增计时样本。

## 2. 单一最小改法及需要守住的等价项

现有 Cantera3.2.0 依赖声明包含 `ruamel.yaml>=0.17.21,<1`；当前隔离 runtime 实际为0.19.1。建议使用局部、每次新建的 `YAML(typ='safe',pure=True)` 与 StringIO：

```text
保留 json.dumps(derived, allow_nan=False) 的原有限值/JSON类型拒绝行为
writer = YAML(typ='safe', pure=True)
writer.default_flow_style = False
writer.sort_base_mapping_type_on_output = False
writer.dump(derived, local_StringIO)
text = local_StringIO.getvalue()
随后两次 Solution(yaml=text,name='gas'/'graphite') 原样继续
```

这不是“先解析再重建一套数据”：输入就是原 `_load_pack` 从冻结 JSON 读出的完整 dict/list。一个调用内生成一次文本、给两次构相复用，**不缓存任何可变 Solution/Species/Mixture，不复用前次相状态**。不新增省略 transport/kinetics 的构造参数、不精简 species/phase 字段、不改 source/model 文件和 hash，也不改变错误后 retry/fallback 行为。若采用直接依赖 ruamel 的实现，应在既有 equilibrium 依赖范围中明确它的使用；本轮无需安装或改变当前冻结 runtime。

新 provider 身份应明确记录构造表示法和实际序列化器版本，例如 `construction_input_representation=ruamel_block_yaml_full_derived_v1`、`yaml_serializer=ruamel.yaml`、`yaml_serializer_version=0.19.1`；版本取实际运行环境，不能只硬写目标值。可同时记录safe/pure及两个布局设置。它们属于实现身份，不改变物理 model/source SHA、标准态或VCS容差。保留旧模块/安装字节与身份；旧结果不能被改名成使用新构造分支，完整provider身份也不应假装位级未变。

本地 ruamel `main.py:102–109,175,326–340` 和 `representer.py:204–232,280–299` 支持上述设置：safe representer 默认可能对普通 mapping 排序，故必须显式关闭；float 用 `repr(data).lower()`，不设置输出精度或把数值另转短格式字符串。`pure=True` 选择本次已读的 Python emitter/representer 路径，避免隐含 C emitter 配置差异；它不是“Python 一定更快”的声明。原 `allow_nan=False` 检查可保留，其已测成本约0.000135s；safe YAML自身可输出 `.nan/.inf`，不能因换布局而丢失原拒绝语义。

必须完整保留：

- 顶层 description/phases/species 及字典键顺序；phases 顺序 gas→graphite；gas elements **C,H,O,N,S**，graphite C。
- gas18物种和末尾 C(gr) 顺序，全部 composition、NASA7两支7系数、temperature-ranges、note、显式reference-pressure=100000Pa。1000K仍由原Cantera低段规则处理。
- gas `thermo=ideal-gas`；graphite `fixed-stoichiometry`，C(gr) species EOS `constant-volume`、原密度字符串 **2.16 g/cm^3**，不能改成2.16kg/m³或另以猜测密度补回。
- 两相原 `state: {T:1000.0,P:100000.0}` 以及原构相后实际 pool.T/P、seed kmol赋值顺序。不把 YAML state 误当最终计算点，也不因稍后覆盖T/P就删去它。

Python float 的原十进制文本及可逆表示不意味着自动证明 C++读取位级相同；字符串 quoting（含 NO、C(gr)、单位）、整数/浮点类别、负零等应在后续纯序列化检查中保留。实际 `_loaded` 对名字/组成/相模型/系数/参考压/温域/密度的原检查必须仍运行；不能只看 Python YAML round-trip 就声称 Cantera 物性已经等价。

## 3. 为什么本轮不优先 Species.from_dict

本地 `cantera/thermo.pyi:74–105` 明确提供 `Species.from_dict`，其输入包含 thermo 和 equation-of-state；`solutionbase.pyi:41–59` 及 `composite.py:60–83` 支持由 species 列表和 thermo 字符串直接构 Solution。可行的表面API不等于与整份 YAML 构相完全同义：

| 必须另证的差别 | 具体风险/未确认项 |
|---|---|
| 元素声明与排列 | 直接传 species 可能按加入物种发现元素；本物种顺序从H₂/H₂O/CO开始，推断次序可能H,O,C,N,S，而非明确的C,H,O,N,S。当前pyi没有显式 `elements` 参数，只见 `**kwargs`；不能由此声称任意 `elements=`会被实现消费。字典数值相同也不保证库内部元素列序相同。 |
| 相级和物种级EOS | Species.from_dict 能接收EOS键，不足以证明直接 fixed-stoichiometry factory 已按相同路径消费 C(gr) 的constant-volume/单位密度。需实际核相EOS、density和全部读回值，不能仅有NASA7就认为石墨相相同。 |
| 初态和名字 | thermo/species 构造并不自动携带原phase的name/state/elements；原1000K/1bar初态、gas/graphite名字须另行明确。当前官方 Mixture源码 `__cinit__` 会先 addPhase/init，再承接首相T/P；初始化差别可能影响该早期路径。 |
| 浮点/转换路径 | Python dict→C++ species输入与decimal YAML→C++不是同一路；需另核元素原子量、reference-pressure、单位解析和低/高NASA系数。19个from_dict调用也不能静态保证比两个整份文档构造更快。 |
| 来源范围 | 当前本地只取得NasaPoly2、Mixture和若干equilibrium C++源码；未取得 Species.from_dict / Solution factory 的完整实现，不能宣称已核其内部元素排序或EOS传播。此任务不联网补源码。 |

直接构相可能是后续更有收益的路线，但改动面和证明义务均较大；本轮只推荐 block YAML 这一候选，不组合缓存、Species factory、transport开关或求解器变更。

## 4. ROOT 后续唯一有界验证应回答什么

先做与EOS无关的冻结输入→block文本→普通类型结构检查：完整键/列表顺序、全部标量与float.hex一致，原非有限输入拒绝仍在；不要在本轮执行。随后按ROOT安排，**与用户CLI原计划的唯一smoke合并验证，不为性能另跑一个点**。固定其输入、源、policy和全部原门（包括模块10s），在该一次调用内分别记录序列化、gas构造、graphite构造、Mixture设置及solve总时长，避免再次将C++黑盒统称VCS成本。输入若不同于旧profile点，时间只能如实分别报告，不能称严格同算例加速比。

实际运行须仍保留原完整来源定义、实际元素顺序/原子量、全部物性与元素/Gibbs门、初末状态、失败前缀及资源监督；对照已保存旧结果中的物性和库存，不以“更快”抵消任何原门失败。不修改已完成记录，不把一次旧/新时间差当稳定性能统计或材料精度证书。如果一次验证没有显著改善，就保留结果并重新判断瓶颈，不能在同次未经批准的运行中切换直接构相或循环benchmark。

只读定位：当前repo `src/sludge_sandbox/tp_equilibrium.py:161–185,340–435`；隔离runtime `cantera/{solutionbase.pyi,thermo.pyi,composite.py}`；既有官方 `review/official-mixture-v320.pyx:47–65`；ruamel0.19.1上述main/representer与包METADATA。本报告仅新增于construction-design目录，0EOS/平衡/native/benchmark，未改src/data/已保存运行文件。
