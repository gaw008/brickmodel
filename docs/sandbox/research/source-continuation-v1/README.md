# 来源轨迹的暂停与继续

本阶段从数值接受的来源湿干转换末态，实际重建同一参数的混合湿干算子，启动后续普通积分段。
完整工作范围仍以[Goal合同](../../../GOAL_BRICK_PHYSICS_SANDBOX.md)为准。

Python入口为`sludge_sandbox.source_trajectory.open_source_trajectory`。输入必须是同版本
`source-run`的完整私有运行目录；需要其中的原配置、来源资产和已验证的来源研究记录。
输出目录必须不存在。`end`使用`ExactEventTime(Fraction(...))`指定，且必须晚于原研究末态。

```python
from fractions import Fraction
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.source_trajectory import open_source_trajectory

session = open_source_trajectory(
    parent_run_directory, new_event_directory,
    end=ExactEventTime(Fraction(end_numerator, end_denominator)),
    cancel=lambda: stop_requested,
)
paused = session.advance(pause_after_steps=1)
if paused.status == 'paused':
    result = session.advance()
```

`paused`表示已提交完整时间步后的暂停。恢复同一会话时，保留本段原始初态、精确时钟、
自适应步长、拒步、全部实际回调、累计守恒账本和已消耗预算。立即取消是合作式检查，
不能中断尚未返回的原生物性调用；中途取消不取得无损恢复资格。积分或结果写入失败后
会话关闭，已经返回的轨迹与失败仍保留。

新段每次提交都从原研究的湿初态累计经过正库存参考、事件前缀、水库存写回和干态参考，
再检查新段账本。原逐格和全域N/U绝对门槛保持。论文来源、参数和物性算子内容身份
经过真实重建核对，旧记录中的进程对象引用没有被复活。

原研究的实际回调次数和耗时计入原97次RHS/510秒运行限额。新普通段使用原每参考段
180秒、4步的积分政策；它没有把旧研究的多个独立参考段冒充为同一个180秒预算。
会话打开期间的检查、重建和暂停时间计入时间限额。

本次真实水来源算子的4步新段保持静止解，尚未验证非静止材料演化。它仍是固定几何、
固定干固体组成的短时间数值轨迹；材料资格与全烧成周期均为false。
原始事件日志落盘，但尚无持久化控制器读取协议，不能跨进程恢复本会话；旧来源研究的
`resume` CLI继续明确拒绝。该边界不能仅靠保存JSON或改标签解除。

实际安装和原生执行证据见[REPORT](REPORT.md)及预登记的[NATIVE_PLAN](NATIVE_PLAN.md)。
本目录不包含出版商原始资产，不能作为独立重放包。
