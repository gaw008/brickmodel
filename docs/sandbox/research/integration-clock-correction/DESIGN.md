# NUM-TIME-CLOCK-EXACT-BINARY-1

分类 numerical_policy，适用于普通 integrate 的有限binary64时刻；不是材料参数或物理定律。原失败与解析复现在 aab23b4 的 heos-active-phase 证据。

原调度重复使用浮点 at+h，舍入偏差累计，.5→.51的名义8步停在.5099999999999998，再产生2ULP尾panel。旧局部尾合并条件不能处理这种累计偏差；禁止直接修改末state的timestamp或放宽误差门槛。

新调度保留有理名义时钟 C=Fraction(start)。trial候选C*=min(C+Fraction(h),Fraction(target))，next_time=float(C*)；若表示后的next_time等于真实breakpoint/end，同步C*到Fraction(target)。实际RK和所有ledger使用next_time-at及实际midpoint差，照常完成物理回调和守恒门禁后才接受/推进C。未接受时不推进；两种拒绝分支均重新锚定C=Fraction(at)，以保持下一试探严格缩小表示端点的既有约束。

maximum_step仍限制名义h，表示后的绝对时刻各自舍入，实际间隔可能微大于h；这一点原算法已存在。新算法避免跨接受步累计这种舍入，不改变空间、物理参数或误差尺度。所有断点仍实际计算，subULP/无法分辨中点仍失败。Fraction只累计一个标量二进制时钟，分母为2的幂，不引入模拟状态缓存或浮点状态重置。

测试先10例7失败3通过，再修复；后补独立3W cell_work整段计量第11例，联合integration/conservation/boundary共117通过。原始测试XML、源快照、额外审查中一次任意全局误差界被准确quadratic积分误差公式替代的全过程保留。额外审核只改测试真值推导，没有改生产门槛。

原活动相变三档物理输入/设置不改，在实际安装环境重新运行并计算2/4/8步端点差。相邻误差比只报告观察值，不能当任意问题阶数证明或外部材料验证。完整suite须另读实际终态。

## Final v2 correction after the real v1 full-suite failure

The preceding description records v1. Its full installed suite had 1121 passes and two actual depletion restart failures (installed-full-tests.xml). Exact accumulation alone leaves one ULP for the separately rounded .15 -> .2 interval at nominal .01. The final v2 retains exact nominal accumulation AND the original narrowly bounded guard: 0 < target-next_time <= min(ulp(target),32*ulp(min(h,target-at))). It then synchronizes the nominal clock to Fraction(target) and integrates the full actual endpoint difference. No state-only timestamp snap, error tolerance increase, or physical parameter change occurs. Both rejection branches reanchor the clock to Fraction(at).

The added twelfth clock test checks five accepted panels and the entire 3 W work integral over that interval. The isolated combined regression has 50 passes; independent compatibility review covers the previously failing restart cases and rejection at a large absolute origin with an unresolved short step. The final v2 installed evidence is separately stored under brick-clock-final, not relabeled from the successful v1 manufactured three-scale runs.
