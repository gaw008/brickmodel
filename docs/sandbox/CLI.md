# 沙盒统一入口

当前新增入口调用 `sludge_sandbox` 物理内核。它支持一个严格声明的、两格或四格的湿态反应—规定变形数值验证模型。A/B 固体、载气、反应、输运和骨架参数均为制造的验证输入，水物性另有实际来源检查。**这不是原污泥材料模型，也不是完整烧制周期。** 原污泥材料准入、自由烧结冷却、完整来源依赖图、批量实验、搜索和界面仍须完成。

## 从仓库运行

在 Python 3.12 环境中按仓库锁文件安装项目及 `dev`、`water` extras。该案例还需要现有水物性流程核验的 CoolProp 8.0.0；`water` extra 当前只提供 iapws。不要用任意 CoolProp 安装替代已批准的二进制/配置清单。当前批准清单绑定已验证的平台文件，因此本阶段不构成跨平台干净环境交付。

```sh
python -m sludge_sandbox validate data/sandbox/cases/reacting-wet-slab-v1.json
python -m sludge_sandbox resources
python -m sludge_sandbox run data/sandbox/cases/reacting-wet-slab-v1.json --water-data data/sandbox/water --output /tmp/brick-run-new
python -m sludge_sandbox trace /tmp/brick-run-new --quantity temperature_k
python -m sludge_sandbox trace /tmp/brick-run-new --quantity internal_energy_j
python -m sludge_sandbox replay /tmp/brick-run-new --output /tmp/brick-replay-new
```

安装后也可用 `sludge-sandbox` 代替 `python -m sludge_sandbox`。旧 `sludge-vme` 筛选入口保持原有含义。

`validate` 只检查显式案例结构、数值范围和受支持的模型选项，不加载 EOS，也不宣称来源资产已检查。缺少键、多余键、非有限值和错误材料分类会被拒绝；将验证材料改成“真实材料”不会自动获得准入。`resources` 当前显示代码、Python、依赖版本和平台身份，尚不是内存/CPU资源预测器。

## 结果与失败

输出目录必须不存在。每次运行保存原始 `case.json`、水来源文件、实际包内 Python 源码、`result.json` 和 SHA256 清单。结果包含初始化证据、初态温度重构检查、实际数值策略、接受状态、逐步守恒账本、终态诊断及前后实现身份。接受轨迹先落盘，终态诊断失败不会抹掉它。

`run`、`replay` 仅在 `status=completed` 时返回退出码 0；数值失败、越域、资源上限和取消都返回非零。若连输入案例都无法读取，仍尽量保存失败报告，但这类不完整目录不具备可重放案例，`trace` 会拒绝。

时间/步数/拒绝次数上限来自案例 `numerics/integration`。内部时间预算只覆盖积分过程；初始化和诊断也会调用 EOS，暂不属于该硬上限。CLI 的 Ctrl-C 使用协作取消，在下一次求解器检查时保留已接受前缀，不能即时打断正在执行的原生 EOS 调用。进程被操作系统强杀时只能保证此前已写入的文件，不能保证最后清单完成。本阶段验证另用 150 秒外部监督上限。

## 查询与重放

支持查询 `amounts_mol`、`internal_energy_j`、`temperature_k`、`pressure_pa`。库存和能量来自最后接受状态；温度和压力来自成功运行的终态重构。查询给出结果位置、案例参数 JSON 指针、全部冻结实现与水来源文件，以及若干已实现方程的函数定位。**方程列表只是导航入口，尚不是完整的方程级来源依赖图。** 各量存在耦合，因此当前返回保守的完整案例参数集合，不能把它当作敏感性排序。

文件清单用于检测相对于保存清单的变化，不是第三方签名。重放要求所有登记文件哈希一致、没有额外文件，且当前 Python/平台/包版本/沙盒源码身份与原运行相同；不执行保存目录中的 Python 文件。它从冻结案例重新开始，尚不是中断检查点续算。新目录记录原结果哈希以保留血缘。

Python 使用同一服务：

```python
from sludge_sandbox.run_service import run_case, trace_run, replay_run

result = run_case("case.json", "water", "/tmp/new-run", cancel=lambda: False)
trace = trace_run("/tmp/new-run", "temperature_k")
replayed = replay_run("/tmp/new-run", "/tmp/new-replay")
```

案例中 `refinement=1` 将显式初始/最大时间步减半；`grid.cells=4` 在相同物理域中对新构建的两格父态进行库存和能量守恒细分，同时检查同温储能广延性。`profile=uniform` 使用左父单元的库存和温度构造两侧一致初场；`transport_mode=control` 使用显式为零的传热/水扩散设置。这些选项用于验证，不代表材料设计的自由搜索域。
