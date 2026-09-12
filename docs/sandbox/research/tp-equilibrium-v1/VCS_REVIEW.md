# Explicit VCS 差异独审

**APPROVE：可在新 `root-vcs-execution` 执行原限定最多四点计划。** 本次只审候选02到新候选的源码/测试/CLI差异、官方求解器语义证据和薄监督差异；没有构相、EOS、平衡计算、安装或重跑测试。

正式 module SHA `da382eead7211e5a91a1630fbe30a75a8c7feca9cb1af6814398c57f8914849c`；tests `44114d4c71882da6a85624042bfe22477cca5262213ab067931bdefcc4eaa474`；CLI `5553a152153f2bcc32feaaf5af2fe1a076d9f76c3f2c9bca54f4c47697910f82`。本次全部固定身份与原失败保留核对见 `VCS_FINAL_READ01.json`。

实际差异符合约定：TPPolicy 默认 vcs，只允许 vcs/gibbs；auto/其它策略拒绝。CLI 显式保存并传递 --solver；旧 Gibbs 可显式重现，绝无失败后换 solver 的控制流。V2 policy 和 provider identity 记录请求及有效容差语义。后端调用、源读取、初猜生成、属性比较、元素池和 G/KKT 后验函数字节未变；原 T/P、所有数值门、库存投影、max_steps、时钟/失败保留均保持。

官方 v3.2.0 缓存逐段核读（文件 SHA 已固定）：

- `MultiPhase.cpp:655–698` 把显式选择送入各分支；只有 auto 才能跨分支回退。Gibbs TP 分支未转发 estimate_equil，而其构造器默认使用线性初估。
- `MultiPhaseEquil.cpp:401–420,440–479,626–650` 对非组分微量气体使用独立更新、阈值为绝对 1e−12 kmol，终止误差取反应 ΔG/RT。它说明值得尝试另一算法，**不是旧五元素偏差因果归属的完整证明**。
- `vcs_MultiPhaseEquil.cpp:406–481` 的 TP bridge 没有消费 err；`vcs_solve.h:1284–1293` 给出 major/minor=1e−8/1e−6、secondary=1e−10/1e−8。新的 `requested_rtol_consumed=false` 与源码相符，不能宣称请求的 1e−10 已控制 VCS 收敛。estimate_equil=0 被转发，`vcs_solve.cpp:1415` 因此不执行初始化估计器。
- `vcs_solve_TP.cpp:1250–1357` 有元素复算/修正，也存在 give-up/range-error 路径；内置检查不代替原外部元素门。新计划没有承诺 VCS 必然通过。

新 native_series 仅增加显式 VCS 参数及结果 policy 核对；launch 与原脚本逐字相同，由自身目录产生新的独占输出路径。原 1000K 两初猜→800K→1200K 顺序、两初猜比较、19×4×2 属性检查、首次失败停止和 10/40/50+5 秒资源门均未变。原 1-bar 派生源与独立 REFERENCE 不改。

作者新增5项制造测试保留实际 RED（4 fail/1 pass）；最终20项制造回归 0.10 s 通过，覆盖两种显式派发、有效容差和 CLI 保存。这里核读真实日志/XML，不把它们当作 native 结果。原 `root-execution/native01` 的单点五元素失败、SERIES 和监督记录仍与上一独审一致，四点原计划保持失败。

本次没有新未解决问题。即使 VCS 后续成功，仍只支持受限候选、虚拟元素池的名义封闭 TP 组成；热化学完整区间误差、遗漏相、真实原泥适用性与材料资格继续 unknown/false。

## Review Summary

| Severity | Unresolved | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 可执行新独立计划；原失败不覆盖，未声明 VCS 实际验收通过。
