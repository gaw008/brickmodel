# N格单事件实际源码静态审查

已只读 source_terminal.py、source_terminal_liquid.py、source_dry_transition.py；无EOS、模型check或测试。以下是代码数学审查，不是终态N3运行验证。

目前9项合同的主要路径已正确接线：唯一完整4N液根导出k，原index仍路径索引；源phase与液三项完全绑定，E全域正、旧ExactAffineSamples净导数严格下降；所有其他库存在clock.upper前的完整最小值严格正。完整N格prefix进入原writeback，仅k液汽改变、其余库存和所有U逐位保持。液面依原decoded/config/geometry重建原Darcy与donor焓，使用exact n*h投影，保留represented J*h差；全声明面板J符号检查不等价于真实全逆解方向，fixed_decoded_temperature/false原资格仍保留。

液体v/h字段被明确视为原保存EOS观测，helper本身不重新计算这些物性；它绑定T/P/N/saturation/完整eP/source metadata，实际v/h真实性还依seed/capture完整binding。不得宣传该passive重算为第二套独立EOS证据。

全链_audit_path现为N×4/N能量，从原始初态累积；各内部面以同数反号入邻格，terminal额外用精确积分full；rho只作用k，U不变。每prefix对逐格和全域分别用原同一IntegrationPolicy绝对门槛，不暗乘N；水/H/O/N/流体质量由逐格残差独立加总。事件专属storage/元素/质量门槛仍由原totals/writeback负责，普通full仍是原步账本+terminal精确积分，非连续ODE真误差。

压力记录确为2×N且绑定实际cell/source状态；成功路径要求所有格都有界。仅dry k用SourceDryPressure并可选同live参数joint，其余仍wet原SourceInversePressure；未选格选择max(报告P界,原全逆解条件界)，任一None传到globalNone，任一湿格P失败不能被dry joint覆盖。顶层N/U/T/P仍逐格max，另保留全部cell rows；最终接受包含全局N/U/T和各格selectedP经max后的门槛。事件两路径同k/模式与energy/operator绑定。

本次未发现具体数学错误。尚需真实制造N3/k1成功/域退出终态保存审核：独立Fraction Darcy（不调用被测face helper）、共享面积分、全链局部/全域余额、各格压力/选用策略及dry原配置zero-mobility。尚未取得终态结果，因此不声称执行通过。

## 审查时源码SHA

- source_terminal.py: `9f7a7f5f8d4b1b825f95105a1d2be10b1068d09cb7e8ce0ad4ed0492ca19e9b6`
- source_terminal_liquid.py: `5f96e0e67c873ce709562aef5ecf821b3198322c5a334019136c32d9fa4b3305`
- source_dry_transition.py: `d8c4effd839b2d7fc734da48682c2ca178acacc0a2234d075b7e28f69bfc31e0`
