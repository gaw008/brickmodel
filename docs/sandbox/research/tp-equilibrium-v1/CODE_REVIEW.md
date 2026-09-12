# TP 候选代码独立审查

APPROVE：最终候选可进入原预登记的最多四次受监督验收。仅审新增 TP 模块、测试、薄 CLI、固定来源包及相关官方接口；没有导入 Cantera、构相、EOS、平衡计算、安装或运行旧测试。最终逐文件身份见 `FINAL_READ01.json`。

模块 SHA：`8f051abea50b4f21f9a12f92129f249967f591b5f2197760ed2f8015a7ce964f`；正式测试 `5deff05176ec68f78c461552e6fc5f3fad9f685e0a9d35f4e3a4c41444a0e86b`；CLI `be1d1dd7ae2a93ffdd41dcda01dc0ac6bad40adad992786f98d42f16fec7dbac`。

[MEDIUM, 已关闭] 完整返回的物性向量在后续读取失败时丢失。

位置：`tp_equilibrium.py:snapshot/equilibrate`。独立制造探针让全部 19 项 h 正常返回，再让 s getter 抛错；原失败记录只留下读取前库存。`PARTIAL_RED01.log/xml` 实际 1 failed / 0.09 s。最终每个完整向量更新 `partial_snapshot`，原生求解已返回后的快照失败不再重试，保留首次读取前缀；独立 `PARTIAL_GREEN01` 实际 1 passed / 0.04 s。作者另有薄包装器单项通过，核原生返回标记和仅一次 entropy 读取。所有原失败保存。

[MEDIUM, 已关闭] 快照函数的同步注释未由所调用 Python API 实现。

官方 v3.2.0 [mixture.pyx](https://github.com/Cantera/cantera/blob/v3.2.0/interfaces/cython/cantera/mixture.pyx#L162) 第 162–164 行仅返回已有对象；不能把它等同于 C++ `MultiPhase::phase`。最终从保存 T/P/实际气相库存显式设置 gas.TPX、carbon.TP，原始绝对 kmol 不回写，并在同步前拒绝非法库存/域。作者真实制造 stale-phase RED→GREEN 已保存。必须准确限定：官方 [MultiPhase.cpp](https://cantera.org/3.2/cxx/df/d2b/MultiPhase_8cpp_source.html) 的温度设置等路径本身也更新相状态；本探针验证独立 snapshot 契约，**没有证明原 prepare/native 曾实际读到陈旧物性**。

其余审查结论：

- 固定 model SHA 和五项文件绑定控制实际 derived 数据；真实后端核 18 气体与 C(gr) 的系数、元素、温域、1 bar 参考、相模型与石墨密度。固相使用同一个派生定义，未误载原件的默认参考。源文件在调用末重新复核。
- mol→kmol→实际读回的 Fraction×1000 保留投影差；零结构元素、非负库存及两种 seed 的元素池均有明确规则，不裁负或填 epsilon。标准 Gibbs 使用当前 P，再仅加理想混合项；1000 K 属低段，形成焓不重复加入。
- 正元素子空间拟合元素势；全结构允许气体参与 logsumexp，非仅活动阈值以上物种。`L(b)=λ·b−RTδΣb` 分别作用于读回池与请求池，精确保留 `gap_requested−gap_out=λ·residual−RTδΣresidual`。前一设计审查的两项澄清已落实。gap/KKT 和小量石墨活动阈值仍为名义数值判断。
- 单次固定求解器、有限步骤及调用边界时钟，返回后越时保留对象；原生在途强制终止属于外层监督。计数是 factory/prepare/equilibrate 包装器边界，不是内部多项式次数。失败和成功均保存请求、可用初/终态、来源及诊断；私有制造 backend 不能取得实际来源资格。
- CLI 参数先验证、输出独占创建，先存输入；序列化支持 Fraction、只读映射和具名非有限失败数。I/O 错误不保证文件完整。没有放开旧低温主机或修改其接口。

验证证据：作者合跑记录 `AUTHOR_GREEN03` 为 14 项当时正式测试加独立部分读取探针，共 15 passed；最终新增正式包装器回归单独 1 passed。本次没有重复整套。独立最终仅重跑直接受影响的 1 项，生产字节此后未变。

本结论不是实际 Cantera 运行通过。后续必须依照原计划保存成功或失败及源身份。受限封闭 TP 平衡不提供反应速率、原泥反应热、烧结全周期、材料误差或全热化学区间证书；`material_qualified=false`、`training_eligible=false` 与遗漏相/非理想性 unknown 均保持。

## Review Summary

| Severity | Unresolved | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | 2 resolved; original evidence retained |
| LOW | 0 | pass |

Verdict: APPROVE — 本次有限代码审查通过，可执行原限定验收；不代表整个 Goal 完成。
