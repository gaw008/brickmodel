# 来源试算正式运行入口

此入口从显式配置和来源资产重新构造真实 HEOS 水物性、NIST 气体热容和
Arlabosse 污泥干质量热容，执行三格柱的一个湿转干事件比较。
当前几何、输运和数值误差包络仍为明确标记的数值验证设定；化学反应关闭，
没有实现完整烧成周期或材料性能预测。

以下命令在已安装本项目的 Python 环境中运行。`ROOT` 是本地项目根目录，
其中必须存在配置列出的 17 个合法来源资产；安装 wheel 本身不会生成或下载
这些资产。当前验证使用已有本地缓存，不能视为全新机器的材料数据准备已完成。

```sh
python -m sludge_sandbox.cli source-validate "$ROOT/data/sandbox/cases/source-multicell-heos-v1.json" --assets-root "$ROOT"

python -m sludge_sandbox.cli supervise source-run "$ROOT/data/sandbox/cases/source-multicell-heos-v1.json" --assets-root "$ROOT" --job-directory /tmp/source-study-job --wall-seconds 570 --grace-seconds 10

python -m sludge_sandbox.cli job-status /tmp/source-study-job
python -m sludge_sandbox.cli cancel-job /tmp/source-study-job

python -m sludge_sandbox.cli source-study-inspect /tmp/source-study-job/run/source-study-record.json --capture-index 16 --cell 1 --path transition/cell_selected_pressure_gates
```

每个输出目录必须是新的目录。监督器拥有计算子进程，超时或取消后负责终止并
回收该进程。最后一个 `started` 事件不代表计算已经返回；必须查询对应返回或
失败事件以及监督器保存的终态。

Python 对应入口：

```python
from sludge_sandbox.source_run_service import run_source_case
from sludge_sandbox.run_service import read_run, export_run, replay_run

result = run_source_case(case_path, assets_root, output, cancel=lambda: False)
verified_result, manifest = read_run(output)
exported = export_run(output)
```

`run_source_case` 的取消是合作式检查；直接 Python 调用没有跨原生调用的硬中断
保证。需要整个进程时限时使用上述监督器。`replay_run` 使用冻结输入和资产重新
构造并重新计算，要求实现版本相同。原有 `resume` 对这种来源试算明确拒绝，
不能把从头重算称为从检查点继续。

输出包含原输入、规范化配置、实际推导的时刻与政策、来源副本、实现快照、
逐次输入/返回/失败事件、完整来源试算记录和清单。部分资产包含尚未授权公开
再分发的出版商缓存；整个运行目录只用于本地复现。公开证据包不包含这些原文。

成功执行、数值事件通过、材料资格分别记录。有效比较可以给出 false 的数值
门槛；未知、取消、计算失败或记录校验失败不能通过改摘要状态升格为成功。
没有材料数据闭合及独立实验验证时，`material_qualified` 仍为 false。

验证范围与实际结果见 [REPORT.md](REPORT.md)，下一项工作见
[NEXT_STEP.md](NEXT_STEP.md)。完整范围继续以
[Goal 合同](../../../GOAL_BRICK_PHYSICS_SANDBOX.md)为准。
