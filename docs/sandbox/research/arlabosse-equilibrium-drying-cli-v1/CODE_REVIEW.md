# 中文两格平衡排湿入口独审

APPROVE，当前没有未解决问题。仅审查新 example 薄层；没有改核心、调用 EOS、运行原生例子或重跑旧测试。最终源码 SHA-256：`c1e567f6f1fd74d488d0e64c66b650d494711c3ed786f4f3aae7d79c430b1df8`。

原两格逐项 binary64 库存、实际水/热量来源构造、热与含水输运 provider、零旧相变系数、边界、fast inverse 与 nominal flash 策略保持一致。步数明确限 1/2/4，总物理时间 1 s；初始化40 s、积分100 s、driver150 s 和累计 E/N 预算透明。底层完整 U/化学/源域门继续由已审主机负责；入口不把 completed 宣称材料或全周期验证。

输出以 x 模式独占创建；输入先存。构造返回点、初始化及完整 run 在返回后检查时钟之前保存，失败 trial/已接受前缀随主机返回对象保留。Fraction、dataclass、Mapping 在有限 JSON 语义中序列化，序列化失败发生在改写旧字节之前；I/O 中途故障明确提示文件可能不完整。累计观测求和全部动态账本，初始化单列；没有重复叠加潜热。

唯一 MEDIUM 问题是运行库加载已越过150 s时仍开始 source construction。独立制造探针实际 INDEPENDENT02 为1失败、1通过（0.03 s），成功4步探针证实全部账本累计与保存。作者仅增加 runtime_loaded 保存及前置 guard，受影响同一探针 RUNTIME_GUARD_GREEN01 1通过（0.01 s），最终静态字节核实关闭。原 INDEPENDENT01 是系统 Python 无 pytest 的启动错误，保留且不计作行为 RED；作者此前9项制造/静态测试通过，不重复执行。

CLI 本身明确只有协作式时钟，不能中断正在执行的 EOS，也不自带外部监督。本次尚未运行真实 CLI；后续受控 smoke 才能证明该新入口的实际物性路径。

## Review Summary

| Severity | Open count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | one resolved |
| LOW | 0 | pass |

Verdict: APPROVE — bounded CLI review only.
