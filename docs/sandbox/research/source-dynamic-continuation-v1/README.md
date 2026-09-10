# 非静止来源续算与普通检查点保存

本阶段为耗尽事件后的新普通段提供显式步长选择，同时保留原误差、最小步长与计算资源限额。
连续段和暂停后继续段使用同一组已声明的政策。实际结果以[运行前合同](NATIVE_PLAN.md)、
安装测试和[实际报告](REPORT.md)为准。V2真实水父事件已通过原数值门槛，后续普通段
有两步非静止接受前缀，但触发原180s限额；完整三步和连续/暂停两路径比较尚未完成。

```python
from fractions import Fraction
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.source_trajectory import SourceOrdinaryStepSizes, open_source_trajectory

session = open_source_trajectory(
    parent_run_directory, new_segment_directory,
    end=ExactEventTime(selected_end.seconds + Fraction(3, 64)),
    step_sizes=SourceOrdinaryStepSizes(
        1 / 64, 1 / 64,
        'New conduction segment; original errors and resource limits retained.',
    ),
)
paused = session.advance(pause_after_steps=1)
if paused.status == 'paused':
    completed = session.advance()
```

`step_sizes`仅用于创建一个新段。省略时完全继承原参考步长；它不能更改材料、原始状态、
误差门槛、耗时或计数上限，也不能在暂停后修改。原研究的实际成本和原湿初态起的累计
守恒检查保持。案例中的温差和导热系数明确是制造测试设置，来源热容及真实水物性不使
这些设置自动成为实测材料参数。

新增`exact_integration_checkpoint_codec`的`encode_exact_checkpoint`和
`decode_exact_checkpoint`可保存/读取普通数值检查点：完整原问题、回调、拒步、账本、
时钟、步长和已耗预算均保留，并进行被动控制器核验。它不加载物性或重建来源会话。
源会话跨进程恢复仍需独立的来源身份、原运行关系、实际重建和时间记账准入，当前尚未提供。

完整Goal仍包括同材料的反应、烧结与冷却、三个机制公开留出验证、时空收敛、完整周期、
多代搜索和实际应用。新段的数值运行或检查点读回均不能替代这些验收。
