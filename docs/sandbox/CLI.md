# 沙盒统一入口

当前入口调用 `sludge_sandbox` 物理内核，包含制造的湿态反应—规定形变及自由形变模型；规定形变支持 2/4 格，自由形变支持 2/4/8 格。自由模型可显式选择耗尽事件及共享常数误差族，见 [PAIRED_EVENT_COMPARISON.md](PAIRED_EVENT_COMPARISON.md)。A/B 固体、载气、反应、输运和骨架参数仍是制造输入，水物性另有实际来源检查；不等于原污泥材料模型或完整烧制周期。

## 从仓库运行

在 Python 3.12 环境中按仓库锁文件安装项目及 `dev`、`water` extras。该案例还需要现有水物性流程核验的 CoolProp 8.0.0；`water` extra 当前只提供 iapws。不要用任意 CoolProp 安装替代已批准的二进制/配置清单。当前批准清单绑定已验证的平台文件，因此本阶段不构成跨平台干净环境交付。

```sh
python -m sludge_sandbox validate data/sandbox/cases/reacting-wet-slab-v1.json
python -m sludge_sandbox resources
python -m sludge_sandbox run data/sandbox/cases/reacting-wet-slab-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --output /tmp/brick-run-new
python -m sludge_sandbox trace /tmp/brick-run-new --quantity temperature_k
python -m sludge_sandbox trace /tmp/brick-run-new --quantity internal_energy_j
python -m sludge_sandbox replay /tmp/brick-run-new --output /tmp/brick-replay-new
# 若运行被协作取消并已保存至少一个接受步：
python -m sludge_sandbox resume /tmp/brick-cancelled-run --output /tmp/brick-resumed-new
```

安装后也可用 `sludge-sandbox` 代替 `python -m sludge_sandbox`。旧 `sludge-vme` 筛选入口保持原有含义。

`validate` 只检查显式案例结构、数值范围和受支持的模型选项，不加载 EOS，也不宣称来源资产已检查。缺少键、多余键、非有限值和错误材料分类会被拒绝；将验证材料改成“真实材料”不会自动获得准入。`resources` 当前显示代码、Python、依赖版本和平台身份，尚不是内存/CPU资源预测器。

## 结果与失败

输出目录必须不存在。每次运行保存原始 `case.json`、水来源文件、实际包内 Python 源码、`result.json` 和 SHA256 清单。结果包含初始化证据、初态温度重构检查、实际数值策略、接受状态、逐步守恒账本、终态诊断及前后实现身份。接受轨迹先落盘，终态诊断失败不会抹掉它。

`run`、`replay` 仅在 `status=completed` 时返回退出码 0；数值失败、越域、资源上限和取消都返回非零。若连输入案例都无法读取，仍尽量保存失败报告，但这类不完整目录不具备可重放案例，`trace` 会拒绝。

时间/步数/拒绝次数上限来自案例 `numerics/integration`。内部时间预算只覆盖积分过程；初始化和诊断也会调用 EOS，暂不属于该硬上限。CLI 的 Ctrl-C 使用协作取消，在下一次求解器检查时保留已接受前缀，不能即时打断正在执行的原生 EOS 调用。进程被操作系统强杀时只能保证此前已写入的文件，不能保证最后清单完成。本阶段验证另用 150 秒外部监督上限。

## 查询与重放

支持查询 `amounts_mol`、`internal_energy_j`、`temperature_k`、`pressure_pa`。库存和能量来自最后接受状态；温度和压力来自成功运行的终态重构。新运行中的 `dependency_graph` 给出本模型已登记方程的上游子图：公式、符号/单位、参数值与基准、计算依赖、实际源码行号、来源文件和具体定位。JSON 来源指针会实际解析；页码/公式号等文字位置保留核读声明，不冒充机器已经理解论文。原 `equations` 字段保留简短导航含义，旧运行没有图时不生成一份新图冒充当时记录。

目前目录覆盖这个制造湿态模型的19个方程声明、38项参数声明和4个输出入口。物理反馈按“当前阶段重构→通量/源项→接受步更新→新状态重构”表示，不能把无环依赖图解释为物理系统没有反馈。分组参数的混合单位明确保留。图验证引用、代码锚点、来源资产与原运行的一致性；**不证明公式对原污泥适用或已经获得实验验证**，也不覆盖尚未实现的全烧制模型。

`--evidence-data` 指向含 `transport/` 等子目录的证据根目录。只复制目录列出的来源和相应许可/署名文件；它不会扫描整份研究数据库。未提供或缺失的额外来源保留为 `missing`，不填默认数值。真实水运行所需资产仍由水提供器独立检查。`source_asset_coverage` 仅表示已登记来源位置对应文件的可读比例，不能当作物理参数、材料适用性或外部验证覆盖率。

文件清单用于检测相对于保存清单的变化，不是第三方签名。重放要求所有登记文件哈希一致、没有额外文件，且当前 Python/平台/包版本/沙盒源码身份与原运行相同；不执行保存目录中的 Python 文件。`replay` 从冻结案例重新开始。新目录记录原结果哈希以保留血缘。

`resume` 从协作取消后的最后接受状态继续，当前只接受普通积分器已有至少一个接受步、尚未到终点的 `cancelled/cancel_requested` 记录。输入、运行前后实现、目录、来源、原始策略和重新构建的初态/能量模型身份必须一致；已完成、数值失败、缺少接受步或原预算耗尽的运行会拒绝续算。显式自由耗尽事件案例另有完整累计历史审计与续算，见 [FREE_EVENT_APPLICATION.md](FREE_EVENT_APPLICATION.md)；v2 接受形状和数据审计已接入，但新共享族案例的真实 service 续算仍未验证。强杀进程后的恢复没有保证。

续算目录保留原始初态、全部原接受状态/账本、直接父运行结果和清单的原始字节、父结果哈希，以及单独的检查点诊断。`parent/` 是历史证据，不是独立完整运行目录。后续步数、拒绝次数与积分墙钟预算从整条已合并历史扣除，不能每次恢复重新获得完整预算；初始化/诊断仍不在积分时间预算内。

新的局部接受步先写入 `resume_suffix.json`，再逐步对照原始初态和原始绝对容差核算库存、能量与累计功分项舍入残差。超限时只保留此前通过的合并前缀，状态为数值失败，原始后缀证据仍保留。自适应初始步长及名义时钟会从检查点重新开始，因此一般续算不承诺与不中断运行逐位一致。当前注册的固定步长案例另有实际比较，不能外推成所有自适应问题的全局误差保证。

Python 使用同一服务：

```python
from sludge_sandbox.run_service import run_case, trace_run, replay_run, resume_run

result = run_case("case.json", "water", "/tmp/new-run",
                  evidence_directory="data/sandbox", cancel=lambda: False)
trace = trace_run("/tmp/new-run", "temperature_k")
replayed = replay_run("/tmp/new-run", "/tmp/new-replay")
# 对已取消且具有接受前缀的运行：
continued = resume_run("/tmp/cancelled-run", "/tmp/new-resume")
```

案例中 `refinement=1` 将显式初始/最大时间步减半；`grid.cells=4` 在相同物理域中对新构建的两格父态进行库存和能量守恒细分，同时检查同温储能广延性。`profile=uniform` 使用左父单元的库存和温度构造两侧一致初场；`transport_mode=control` 使用显式为零的传热/水扩散设置。这些选项用于验证，不代表材料设计的自由搜索域。

## 整个服务进程的监督

`supervise` 在独立子进程中调用同一运行服务，覆盖导入、初始化、积分和诊断。
下面的工作时限为120秒，到限先发协作取消信号，5秒宽限后仍未退出就强杀并回收：

```sh
python -m sludge_sandbox supervise run data/sandbox/cases/reacting-wet-slab-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --job-directory /tmp/brick-jobs/new --wall-seconds 120 --grace-seconds 5
# 在另一个终端查看或提交取消请求：
python -m sludge_sandbox job-status /tmp/brick-jobs/new
python -m sludge_sandbox cancel-job /tmp/brick-jobs/new
# 重放或续算仍使用冻结的 run/，每次创建新任务目录：
python -m sludge_sandbox supervise replay /tmp/brick-jobs/new/run --job-directory /tmp/brick-jobs/replay --wall-seconds 120
```

任务目录必须不存在；`run/` 保留独立的输入/结果/清单，`job.json` 保存监督状态，
`stdout.log`、`stderr.log` 保存子进程输出，`child-metrics.json` 在正常经过包装器退出时保存资源观测。
只有子进程退出码0、运行状态completed且清单验证通过才报告completed。
超时、取消、数值失败、异常退出和结果未验证分别记录；监督命令除completed外返回非零。
原始 `run/replay/resume` 仍是直接服务入口，整进程时限需显式使用 `supervise`。

实际边界是工作时限加取消宽限、轮询与回收调度，不能承诺实时操作系统式的精确截止。
同一解析后任务父目录最多一个活动原生子进程，忙时明确refused；不同父目录不共享此限制。
当前使用POSIX `flock`，没有Windows兼容实现。子进程继承锁句柄，监督器死亡不会立即放开
仍活动子进程占用的名额；但监督器死亡后没有独立看门狗继续执行时限，不保证自动恢复。

`job-status` 是保存状态的观察，不能凭旧PID证明进程存活。`cancel-job` 只写入绑定任务UUID的
请求，成功返回表示请求已保存；实际取消由仍持有子进程句柄的监督器确认，从不向保存的PID发信号。
强杀可能留下未封存的运行目录，这类目录不能冒充可续算检查点。

资源观测包括本子进程CPU用户/系统时间和原生 `ru_maxrss` 峰值。RSS明确保留平台原单位，
没有假定其为字节或KiB；不汇总后代进程，也没有设置内存硬上限。被强杀时缺少资源信息记为unknown。
`resources` 仍只提供安装身份，不能替代一次运行的实际成本测量。

Python同步调用与CLI共享监督器：

```python
from sludge_sandbox.job_supervisor import SupervisionPolicy, supervise, read_job, request_cancel

job = supervise("run", "case.json", "/tmp/brick-jobs/python-new",
                SupervisionPolicy(120, cancel_grace_seconds=5),
                water_directory="water", evidence_directory="data/sandbox")
```

## 本地中文研究界面

```sh
python -m sludge_sandbox ui --case data/sandbox/cases/reacting-wet-slab-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --storage /tmp/brick-ui --port 8765 --maximum-jobs 20
```

浏览器打开终端给出的 `http://127.0.0.1:8765/`。当前界面与Python/CLI使用同一案例校验器、
运行监督器、重放/续算及溯源服务。可切换2/4格、均匀/梯度初场、输运对照、时间步细化，
也可显式应用案例JSON编辑；非法字段或不受支持的真实材料声明会被拒绝。炉温程序和完整材料选择
须等待相应模型接入，当前页面明确显示这一缺项。

运行时可以查看保存状态、提交取消、在满足检查点条件时续算。服务器只向自己持有的监督工作线程
发送取消事件；旧记录的PID不会被用来声称进程仍活着。关闭服务器会请求取消并等待监督器回收子进程。
页面最多同时比较两条记录；服务一次只允许一个活动任务，默认最多20个历史任务，达到上限会明确拒绝，
不会自动扩张实验规模。

内能与水蒸气库存图使用每个已接受步；温度和压力仅显示已保存的初态/成功终态点，不补造中间曲线。
空间图当前按厚度单元编号展示，不能把编号当实际距离。库存与内能是单元广延量，不同网格的单元值
不能未经体积换算直接作同尺度比较。比较仅展示数据，不进行合格或优胜排名。

选择结果量后点“追查当前结果量”，查看参数、方程依赖图和来源节点；可打开清单内已验证的UTF-8来源文件。
大于1MiB或非文本资产保留明确拒绝，不能因此声称完整论文已经在页面显示。来源存在与材料适用性分别报告。
导出功能直接保留服务端JSON原文，避免浏览器舍入账本大整数；同时显示可复制报告并请求下载。
当前内嵌浏览器未确认下载成功，但页面中的完整报告已实际核对。报告不包括全部来源文件，不能把它当独立重放包。

服务仅监听127.0.0.1，校验Host、Origin及本次启动的API令牌；启动时的案例/水/证据/存储路径由本地操作者
指定，浏览器不能改成任意文件路径或远程地址。该接口是本地研究工具，不是公共网站部署方案。

## 显式共享常数误差族案例

`python -m sludge_sandbox validate data/sandbox/cases/reacting-wet-free-paired-events-v1.json` 已实际通过。该案例的内核运行完成两次耗尽及独立账本验证；不能把内核实验当作 service run/replay/resume 全链路验证。要生成标准服务运行目录，可用上面的 run 命令替换案例路径并选择全新 output；它保留原 800 秒积分上限。原记录中的独立压力界继续展示，新族不能中途替换旧运行的策略。
