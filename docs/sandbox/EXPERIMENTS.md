# 有预算的顺序虚拟实验

实验入口复用同一求解、进程监督和结果读取服务。目前只准入明确标记的 manufactured_verification 案例；真实材料模式返回 evidence_incomplete。该入口是后续敏感性和多代搜索的基础，不包含随机候选生成、选择或产品合格排序。seed 仅记录，不表示已实现随机生成器。

在仓库根目录、安装本项目及 water 依赖后：

```sh
sludge-sandbox experiment-prepare data/sandbox/experiments/wet-transport-comparison-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --output /tmp/brick-experiment-new
sludge-sandbox experiment-run /tmp/brick-experiment-new
sludge-sandbox experiment-status /tmp/brick-experiment-new
sludge-sandbox experiment-compare /tmp/brick-experiment-new
sludge-sandbox experiment-cancel /tmp/brick-experiment-new
```

输出目录必须不存在。取消命令可以从第二终端发出；请求写入不等于取消已完成。再次 experiment-run 继续尚未完成的候选，已完成或失败候选不会自动重跑。完成的实验表示队列已处理，可能包含无效或失败候选，须查看逐候选状态。

准备阶段冻结原始实验配置、完整候选 JSON、分类、当前代码身份、水数据及白名单来源。运行与继续前核查完整性和当前实现；版本变化需要新建实验。冻结文件与 SHA 只证明局部一致性，不证明来源适用于真实材料。运行报告中的 case、运行时及方程目录也须与实验绑定。comparison 仅从通过完整性核查的保存结果计算温差、末态压力、水库存和内能变化；内能不是窑炉燃料耗能。

最大尝试数包括失败和续算，最大总 wall 计入各次运行的活动编排时间，暂停的空闲时间不计。每次调度从剩余预算预留取消宽限时间。总预算是准入控制及实测记账，系统调度、收尾与文件写入可能使实测超出；此时明确返回 resource_limit，并保留原始状态与原因。它不是独立硬实时看门狗。单个原生子进程由已有监督器负责终止和回收。

仅保存了终态回收证据的取消任务才可继续。存在已接受前缀时，调用原有 resume 服务进行检查点验证；零步取消可以重新开始，均计为新尝试。遗留 running 记录或无法核实的中断拒绝继续，不能凭保存 PID 推断进程已死亡。包括 pid=null 的 supervisor_failed 启动失败，目前也保守地拒绝继续；该限制尚未放宽。

验证证据见 research/experiment-batch-v1。人工封存记录测试只证明编排分支；实际两候选运行证明完整服务路径。公开原污泥参数、自由烧结冷却、全周期、多代选择和三组公开机制留出验证仍未完成。
