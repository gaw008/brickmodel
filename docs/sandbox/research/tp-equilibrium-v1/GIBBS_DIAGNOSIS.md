# 首次 Gibbs 元素漂移：官方源码诊断与有限数值策略

2026-09-12。原 native01 1000 K / element_basis 已失败，后三点未启动；本次只读该点必要输入/残差与官方 Cantera v3.2.0 精确源码，没有构相、EOS 或求解。原失败、原候选02三个文件及 SHA 均保留，后续新策略不使旧结果转为通过。

## 确定事实与推断边界

1. 原请求原子池 C/H/O/N/S = 1/1.6/.6/.1/.01 mol，初始读回投影过门，最终五元素残差约 −3.866e−9 / −6.447e−9 / −1.931e−9 / −5.552e−10 / −2.301e−9 mol。小化学势残差仅支持输出所在元素池附近的平衡，不能消除对请求池的物料差。完整输出独审另由 source_execution_review 完成，此报告不替代它。

2. 官方 Gibbs TP dispatch 在 MultiPhase.cpp:493–496 构造 `MultiPhaseEquil e(this)`；MultiPhaseEquil.h:42 的 start 默认 true，而构造器 cpp:122–127 会执行线性初猜估计。MultiPhase.cpp:644–699 对 Gibbs 不传 estimate_equil。因此 Python 虽传0，**该 TP Gibbs 路径并没有因此禁用其内部初猜估计**；仅调整该参数不能作为有效修复。来源：[分派](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/MultiPhase.cpp#L484)、[默认值](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/equil/MultiPhaseEquil.h#L37)。

3. Gibbs `error()` 只取形成反应 ΔG/(RT) 的最大误差；迭代停止和 finish 都没有相对请求元素池的残差门。rtol 控制这一化学势停止条件，并非元素容差。[MultiPhaseEquil.cpp:155–171,626–650](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/MultiPhaseEquil.cpp#L155)。所以本次“ΔG 很小、元素失败”并不与其停止判据矛盾；继续收紧 rtol 也没有元素误差保证。

4. 可定位一个非严格保元素的更新机制：基组分和 major 组分采用同一个 omega·N·dxi，minor 非基组分却独立设为 abs(n)·min(10,exp(−ΔG/RT))，不再保证整个更新仍在 A 的零空间。major/minor 阈值为绝对 **1e−12 kmol = 1e−9 mol**。finish 还把内部负量置零；本模型外部不裁库存，仍必须实查输出元素。来源：[step/threshold](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/MultiPhaseEquil.cpp#L400)、[finish](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/MultiPhaseEquil.cpp#L183)。MINOR_BRANCH_ALGEBRA01.json 用两物种人工零空间提议做精确 Fraction 代数：统一更新的元素变化0，单独替换 minor 项后为1e−13 kmol。它证明该更新形式可能破坏保元素，**并非本次内部轨迹回放或实际漂移总额的唯一归因**。没有修改官方源码或试着后处理补元素。

## 推荐并已获授权的最小新分支

显式选择同一官方 Cantera3.2.0 的 `solver='vcs'`，新 numerical policy V2；仍提供显式 `'gibbs'` 重现原数值分支，拒绝 `'auto'`，没有失败后自动改算法。VCS 分派传递 estimate_equil，TP bridge:413 将0存入 m_doEstimateEquil；vcs_solve.cpp:1415 的条件因此不执行估计函数。内部仍会做正常的基组分和物种处理，不能宣称内部完整轨迹等于用户初猜。[VCS bridge](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_MultiPhaseEquil.cpp#L406)、[初始化条件](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_solve.cpp#L1398)。

VCS 的元素检查实际计算 A n，普通非零元素要求相对目标1e−12，并在主循环和终态检查/纠正后重新检查化学势。它也存在重试校正次数和 range/give-up 路径，故不能只信正常返回；原外部每元素1e−10 mol+1e−10|b|、G/μ/TP/库存/来源/资源门全部保留。来源：[vcs_elabcheck](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_solve.cpp#L2128)、[循环/终态检查](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_solve_TP.cpp#L1059)、[异常路径](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_solve_TP.cpp#L1299)。

**VCS 的 rtol 元数据不能照搬。** v3.2.0 `vcs_MultiPhaseEquil::equilibrate_TP` 接受 err 参数，但函数体未使用；内部默认 tolmaj=1e−8、tolmin=1e−6、tolmaj2=1e−10、tolmin2=1e−8。来源：[未消费参数的函数](https://github.com/Cantera/cantera/blob/v3.2.0/src/equil/vcs_MultiPhaseEquil.cpp#L406)、[内置阈值](https://github.com/Cantera/cantera/blob/v3.2.0/include/cantera/equil/vcs_solve.h#L1284)。新记录因此分别保存 requested_native_rtol=1e−10、effective_native_tolerances 和来源位置/SHA，不声称请求 rtol 实际控制 VCS。原外部 μ/G 门更有必要；通过与否留待实际计算。

## 最小实现与下一次接受

按 ROOT 后续明确授权，只改 TPPolicy 默认/显式选择、V2 数值说明、结果 provider identity 和 CLI --solver；未改数据、温压、元素池、rtol传参、1000步、max_iter100、estimate0、10秒/外层资源门。旧候选02三个文件按原字节存于 *.candidate02.txt。新的5项制造测试先实际 RED 4fail/1pass，随后全部20项作者制造回归通过0.10s，见 VCS_POLICY_RED01/GREEN01.log/xml；并不说明新算法已经通过真实物性。

ROOT 负责新目录、计划/输入冻结、非 editable 重装和受监督执行。下一次先同1000 K / element_basis 单点，只有它全部原门通过才按新计划继续同池第二初猜与端点；任何失败均停止且保留，不能覆写原 native01 或改其分类。此项是数值算法更换试验，仍是相同限定热化学模型，不是改变物料、补测物性或现实验证。

实际下载仅上述7个官方源码文件及 src/equil 名称列表；一次猜测 vcs_elem.cpp 返回404，未当成有效证据。实际读取文件及旧候选 SHA见 SOURCE_AND_OLD_CANDIDATE_SHA01.json，最新源码/测试/CLI SHA见 VCS_CANDIDATE01.json。许可证沿用官方 BSD 条件；本诊断没有广泛论文检索。
