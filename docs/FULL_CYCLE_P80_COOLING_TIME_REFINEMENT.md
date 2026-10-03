# P80 实际冷却时间步比较

一次真实冷却窗口成功结束。实际入口：既有离线venv、正常source cwd，P75保存hold133200s至154800s；唯一数值差max_step60→根conditional30s，rtol1e-5/atol1e-7/758原参数及物理、初態、8阶段绝对时间温气程序保留。科学wall36.516589209s/CPU36.182987s，四科学文件合计2,868,740B；固定120s/4MiB内，窗口关闭、回收、无重试。

实际完成1strictload/constructor、0initial、1BDF/新y275端点/解码/完整势值/interval。RHS9809、Jac51，nfev/njev/nlu1853/51/292。内部rates次数没有独立现存counter，明示未独立测量；额外publicrates、state_dynamics、梯度、瞬时投影、summary、predict/fit/UQ为0。postsolve现存potential/helper计数1，fixed-volume decode0；继承constructor/Newton预测不冒充动态测量。

全部53源逐字节保持；输出完整53source文本、原P75配置、37numeric/partition/phase0/liquidreference和输入y均核对一致。计算case与nativebundle的完整effectiveconfig一致，solver实际maxstep30来自同一conditional记录；唯一相对原P75参数差为numerics.max_step，根758原记录仍60。历史50/51输入身份、原staticproposal0与notes保持，P80独立采用记录明确实际窗口。

| 量 | 原60s相对残差 | 30s相对残差 | 原→新signed残差 |
|---|---:|---:|---|
| N元素 | 0.050865556% | 0.025452828% | +1.476203812e-6→+7.383998740e-7 mol atoms |
| O2 gas预算 | 0.045102942% | 0.022650411% | +2.477573071e-7→+1.244222906e-7 mol |
| N2 gas预算 | 0.036230527% | 0.018122556% | +7.381019060e-7→+3.691999370e-7 mol |
| 完整U | 0.001458559% | 0.000522665% | −2.967064090→+1.063239615 J |
| 完整S | 0.000799926% | 0.000351209% | −0.003062536→+0.001344613 J/K |

原/新各自真实分母、全mass/all元素/四gas预算与初始归一化、完整U/S及signed变化全部在JSON保留。12个主relative项lower、2个Al/Si项unchanged；当前局部账本全部低原0.1%。这是一组时间步敏感性结果，不证明精确收敛阶、唯一误差原因或全周期收敛。mass/元素/gas initial分母依赖P78新声明初始参考，不是P68历史t0恢复；energy两端ptp不是路径极值；entropy canonical与原slot-sum顺序差均保留，原escale/Tr不是新floor。反应/相变热只由原完整storage计入一次，外压功带符号减入残差。

冷却端温度327.619077463–333.983538342K。char最小负值由原−1.264680732e-18降至−8.581861577e-20mol，但negativecells由5增至6，strictnonnegative=false。两指标分别保留；不clip/seed、改阈值或断言单一成因。原char/OH线性、Ca fraction/lime池差分类保持历史。

当前缺失是实际匹配的最终cooling_hold终态三产品time比较，以及独立连续峰温/网格证据；不能用本cooling端温差代替。下一候选仅静态新增独立finalcomparison接口/明确cooling_hold条件和原finalproduct/分母定义，保留53源，未来才从本实际新端点接最后原阶段，并只求一个新终态势值。候选未采用、未启动。本轮不自动再加密或继续cooling_hold。

原名义干燥历史0.1358920787402553%>0.1%、CaOzero null/false、三源高温assumed延拓、0measured、directsynthetic290–350K及P34/P40/P44/P45/P50撤回/P51/P58/P60/P61/P63和所有旧FAIL保留。总体criterionNA/wholefalse；最新三方案/反演及材料实测资格未完成。

本次仅七个根参数/报告路径交付，53生产源未变；原始native场只留run。Git正常后继/普通push、原Drive一次增量metadata、实际恢复与历史存储独立核算；晚到收据不循环提交或重打包。
