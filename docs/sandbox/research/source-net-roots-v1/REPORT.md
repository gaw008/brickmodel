# 来源库存的纯数值首根与竞争排序

本增量从基线 `80ea73d` 推进来源多格耗尽的软件基础。新增 `source_net_roots`，直接使用原 `InventoryPolynomial.minimum` 与提取的共用有理二分/GCD。完整原污泥湿烧冷 Goal 仍在进行；这里没有新增材料参数、真实动力学结论、物理事件提交或干态续算准入。

## 算法与适用范围

库存表示为 `p(t)=n+r*t+q*t²`，系数、时距均为精确 `Fraction`，`n>0`、`H>0`。严格正最小值给出无根记录；线性首根和切触可精确表示。凸二次式从起点到顶点或域终点寻找首个下降根，因此即使终点已经回升为正，或者恰好是第二个根，也不会漏掉先前根。凹二次式允许初期库存增加，下降分支可以从内部极大值开始。终点切触仍归为 `exact_tangent`。

新根记录重算原始分支与确定性二分历史；最小值、分支、区间、次数和类型不能通过等值浮点数或布尔数冒充。共同首根判断使用有理多项式 GCD，并验证共同线性根位于双方首根分支及当前包络内。共用后续根不构成同时首根。

`order_inventory_roots` 保留所有候选根、无根证据和原始多项式，区分 `no_roots`、`ordered`、`tied`、`unresolved`、`unsupported_zero_initial`。气体可以早于液水；同一时刻的全部库存作为群组返回，不按单元编号强选一个。任一零初始库存都会令本路线明确不完整，包括导数也为零的气体槽。总 U 不参加库存正性竞争。

`order_source_panel_roots` 先重新验证完整 `SourceAffinePanel`，再要求每格四类流体的完整有序标签，绑定精确起终时刻、算子和原始样本身份。其 `complete` 仅描述给定数值多项式集合的排序是否已判定；没有新增根时间误差容差，单个非有理根仍可能只有初始隔离区间。可以显式细化根包络，但物理事件精度及准入需要后续独立检查。原始 ODE 的轨迹不能由两个速率样本的插值自动认证。

## 旧路径保持

`rational_polynomial.refine_descending_bracket` 提供一次有理中点/符号更新，保持 `p(mid)>=0` 时移动下界，精确中点零值不自动压成点。旧 `locate_exact_affine` 与 `order_exact_affine_roots` 保留原初始区间、逐轮证据构造、dyadic 网格、迭代计数、错误路径以及全部蒸发/ULP/绝对与相对校正门槛。旧严格单调限制也保持。

`polynomial_gcd` 只提取原未归一化的有理 Euclidean 算术，旧共同首根包装语义保持。新净液流根计算不需要把排水或净消耗冒充正向蒸发量。没有修改 `exact_depletion_writeback` 或任何相间修正预算。

提取之前冻结了 17 组完整旧返回记录及失败诊断，见 `tests/sandbox/fixtures/rational-polynomial-legacy-v1.json`。覆盖实际保存蒸发样本、精确中点/上端零值、迭代预算不足、无蒸发预算、非单调拒绝、近根、无根、多个同时根和巨大精确时间原点。基线 32 项测试通过 0.48 s；提取后连同既有混合单位阶段/门槛测试共 67 项通过 8.61 s，17 组记录逐项不变。

## 验证记录

源码合并测试实际 123 项通过 17.99 s，覆盖新共用算术、新来源根、旧定位/排序、既有混合单位阶段，以及完整来源插值与实际来源接线。独立数学审查预先生成 117 组有理因式案例并执行 1152 项断言；代码审查另以 588 组因式案例核对首根及三方群组。它们是算法审查，不是公开材料实验或外部专家认证。

第一次非 editable 安装 123 项通过 18.11 s。代码与 Python 审查之后补充六处公共返回类型注解，独立去掉这些注解可逐字节还原之前的源码；再次安装实际 123 项通过 18.01 s，XML 零失败/错误/跳过。117 个 Python 模块及全部 124 个源包文件与安装内容一致，见 [安装记录](installed-tests.xml) 与 [包字节核对](installed-identity.json)。该核对覆盖全部源文件，不宣称排查了安装目录所有额外文件。

Python 独审最后 29 个反例通过 0.159 s。原审核探针曾错误假定旧只读数组能被改为可写，实际数组拒绝此操作；77 pass/1 探针失败的原记录保留。更正探针后，通过强制替换字段注入被修改数组也被来源检查拒绝。最坏 256 次细化的两个极近根探针构建约 2.188 s、重验约 2.157 s，正确保留两条区间并返回未决，不代表任意库存数量/系数尺寸的墙钟保证。详见 [Python 审查](python-review.md)、[代码审查](code-review.md) 和 [数学终审](physics-final-review.md)。

最终安装版实际回放原七个试步的 14 条保存来源求值，completed，0.283782917 s；[结果](native-roots-result.json) SHA `b1f45c66d896528e1ffe22fdeaed71cee85a6612794d51bf5c2091cd29238b87`。84 个库存全部返回严格正最小值的无根证据，未出现虚构耗尽；原三次拒绝/四次接受顺序及完整试步对象保持。实际调用屏蔽全部相关物理评价/反解/水物性入口，不运行新 EOS。30 s 内预算、45 s 外预算保持。

独立标准库 JSON/Fraction 审计实际 450 项通过 0.042049250 s，逐项核对来源标签、多项式、精确时间、源绑定和无根证据，包含三个内部凸顶点。最小数值库存为 `1/256 mol`。依赖的上一阶段多项式记录已有独立 445 项审计；本次在其固定哈希基础上重算最小值，不能称为重新独立求解了真实轨迹。[审计结果](native-audit.json)、[范围说明](native-audit.md)、[原生回放审查](replay-review.md)。

实际命令使用 `/private/tmp/brick-water-backend-probe/venv/bin/python`。源码测试设 `PYTHONPATH=src`；安装测试在 `/private/tmp`、`env -u PYTHONPATH` 下运行。测试文件为 `test_rational_polynomial.py`、`test_rational_polynomial_legacy.py`、`test_exact_affine_depletion.py`、`test_exact_root_order.py`、`test_mass_wet_exact_stage.py`、`test_mass_wet_exact_stage_guards.py`、`test_source_net_roots.py`、`test_source_net_panel.py`、`test_source_net_panel_integration.py`。离线安装命令保持 `UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache uv pip install --python /private/tmp/brick-water-backend-probe/venv/bin/python --no-deps --offline --reinstall .`。

`replay_native_roots.py <仓库根目录> <输出JSON>` 与 `check_install.py <仓库根目录> <输出JSON> <测试XML>` 保存了实际运行脚本。回放复用原固定哈希的 35 类被动记录解码器，没有按输入中的类型名动态导入类。[源码冻结](source-freeze.json) 与 [完整原始证据包](raw-evidence.zip) 保留本阶段测试、审核及原探针失败；全部压缩包成员重新打开并逐字节核对，清单见 [archive.json](archive.json)。root 24821、60569、52652、2112 与最终快速回放均已终态，无本阶段待跑数值过程。

## 尚未完成

本部件不能执行库存归零、相态切换、源事件提交或运输残余修正。排水残余若需要数值处理，仍须独立验证成对液体转移及同一供体焓对应的能量转移，不能转换成水汽。干界面/再润湿、源记录与应用、同材料体积/吸附/输运、原污泥反应及烧结冷却、三机制公开对照和全周期/多代验收继续保持未完成。

下一步按 [来源前缀积分与账本路线](next-route.md) 及 [独立约束](next-route-review.md)，提取共用积分/更新，不改变旧门槛；分别量化分量舍入、状态舍入及完整残差，并保留累计预算。该下一步继续拒绝所有零初始库存，不采用原路线提及的恒零特例。完整 Goal 的 `software_status=in_progress`、`scientific_status=incomplete`、`deployment_status=offline_research_only`，未标记完成或阻塞。
