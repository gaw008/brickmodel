# 刚性气体导热极限：空间与时间收敛预登记

登记版本：rigid-heat-convergence-v1。登记日期：2026-09-07 UTC。**本段在首次基准运行前落盘**；结果另见文末实际运行记录及同目录 JSON。实现范围仅为基准脚本，不修改核心求解器。

## 制造问题及独立参照

单一制造气体，cp=30 J/(mol K)、R=8 J/(mol K)、Cv=22 J/(mol K)，摩尔密度 1 mol/m³，长度 L=1 m、截面积 A=1 m²、k=1 W/(m K)。气孔体积等于格体积；扩散系数和 K 均显式为零，左右边界密闭绝热。无反应，无体热源，无额外固相储能。摩尔质量只为显式制造账目取 0.012 kg/mol，不标为真实气体物性。

初始温度为 600+10 cos(πx)。第 i 格初值严格采用有限体积格平均：

```text
Tbar_i(0)=600+10 sinc(pi/(2N)) cos(pi*(i+1/2)/N)
sinc(z)=sin(z)/z
```

连续导热方程的格平均解是将振幅乘 exp(−π²t/22)。这个解析函数独立于 GasHeatModel 和其热化学反解，比较温度也由制造关系 `T=(U/n+cp*298.15)/Cv` 独立重算，避免把被测反解函数当作 oracle。

## 预先固定的空间判据

空间格数 N=8、16、32，完整步长 h=0.002 s，终止 t=0.2 s。每个完整步由现有 integrate 实际执行两个 SSPRK2 半步。报告最大格平均温度误差（K）、L2 误差（K）、以初始 10 K 扰动为尺度的最大误差。

- 每相邻两档的观测阶 p=log2(E_coarse/E_fine) 必须在 [1.8,2.2]。
- 最细格最大温度误差/10 K ≤1e−3。
- N=32 另运行 h=0.001 s；两条实算终温的最大差 ≤N=32 原空间误差的 1%，证明空间序列的时间污染足够小。
- 不用最后一档误差替代三档阶数，不在失败后换范数或尺度。

## 预先固定的时间判据

固定 N=8，完整步长 h=0.1、0.05、0.025 s，终止 t=0.4 s。参照是该有限体积离散矩阵第一余弦模态的**独立解析解**：

```text
lambda_discrete = 4 sin²(pi/(2N)) / (22 dx²)
Tbar_i(t)=600+[Tbar_i(0)-600] exp(-lambda_discrete*t)
```

相邻两档的最大误差观测阶同样必须在 [1.8,2.2]。不拿连续解混入时间误差。每案事前检查完整显式 Euler 子阶段的扩散条件 `2 h/(22 dx²)≤1`；这里包括为误差估计实际执行的完整步，不只检查接受的半步。

## 固定步长与独立账本门槛

仅为收敛研究，积分器截断误差策略设 relative_tolerance=0.01，energy_scale=220 J（全域 Cv×初始 10 K 扰动），amount_scale=1 mol。这个较宽截断判据的唯一目的是使预选 h 保持固定；**不代表研究级或生产级积分精度**。必须检查零拒绝、完整结束、接受步数和实际每步长度；发生自适应变步即不能声称本固定步长序列通过。

库存绝对容差仍为 1e−12 mol，能量绝对容差仍为 1e−8 J，用于核心步增量/累计账本的数值表示门槛。独立重算另要求：

- 任意保存时刻的全域 U 与初始 U 的绝对差 ≤1e−8 J，以 math.fsum 计算；
- 每格期末 U−U0 与全部接受步骤净面能量累计之差 ≤1e−8 J，以独立 math.fsum 计算；
- 每格库存和初值逐值相同；全域 mol 残差 ≤1e−12 mol；
- 两边界账本为零，所有气体面库存交换、反应源、体热源账本为零。

这些是数值验证门槛，不允许倒算边界热或归一化来通过。

## 资源、复现和失败

每案最多 1000 接受步、10 拒绝试探、120 s 墙钟；整次基准最多 360 s，进程峰值 RSS 上限 512 MiB（macOS ru_maxrss 是 bytes，Linux 是 KiB）。资源超限必须区分于数值/物性失败。完整报告记录 Python/NumPy/系统、实际步骤/函数调用、墙钟、RSS、全部输入、各末态和独立参照、源码 SHA-256。Git 提交号仅作上下文；未提交文件不能冒称已绑定到该提交。

脚本调用实际 GasHeatModel 与 integrate，不替换为制造 ODE。非 completed 核心结果、任何门槛失败、导入/执行异常均输出失败记录并以非零状态退出。输出路径已存在时拒绝覆盖；复跑选择新 JSON 路径，保留旧失败。执行期间依赖源码发生变化也使报告失败，避免混合版本的结果。

## 实际运行记录

首次运行尚未执行。预登记完成后才执行：

```sh
PYTHONPATH=src .venv/bin/python experiments/sandbox_validation/rigid_heat_convergence.py --output docs/sandbox/research/RIGID_HEAT_CONVERGENCE.json
```

本基准只验证刚性气体热容量及导热的极限；不验证湿砖、相变、烧结、收缩、力学或真实污泥材料。

## 首次实测结果追加（2026-09-07 06:39 UTC）

以上预登记文本原样保留。JSON 的 `registration_sha256` 对应本节之前的原始文档字节；新增本节不是修改原门槛。实际输入、完整已接受状态与面能量账本、独立解析终温、源码前后 hash 均见 [RIGID_HEAT_CONVERGENCE.json](RIGID_HEAT_CONVERGENCE.json)。7 个算例全部 completed，零拒绝，实际步长/步数符合登记，所有输入源码在运行期间未变化。

| 空间 N | 完整步长 / s | 最大格平均温度误差 / K | 相邻细化观测阶 |
|---:|---:|---:|---:|
| 8 | 0.002 | 0.0102253230 | — |
| 16 | 0.002 | 0.00261537435 | 1.96705705 |
| 32 | 0.002 | 0.000657590408 | 1.99175630 |

最细格归一误差为 6.5759e−5，低于预登记 1e−3。N=32 再以 h=0.001 实跑 200 步，其与 h=0.002 的最大终温差为 2.05698e−8 K，仅为空间误差的 3.12806e−5（约 0.00313%，门槛为 1%）。

| 时间完整步长 / s | 固定 N | 最大离散模态温度误差 / K | 相邻减半观测阶 |
|---:|---:|---:|---:|
| 0.1 | 8 | 0.000120164949 | — |
| 0.05 | 8 | 0.0000297924456 | 2.01199767 |
| 0.025 | 8 | 0.00000741723886 | 2.00599242 |

空间案各 100 个接受步、701 次 operator 调用；空间时间污染复核 200 步、1401 次调用；时间案分别 4/8/16 步、29/57/113 次调用。所有保存时刻的全域 U 残差为 0，期末每格 U 与全部接受面账本的独立最大残差为 3.88578e−16 J；库存逐格不变，封闭边界/物种/反应/体功账本均为零。另对 JSON 原始字节值用 `Fraction` 独立重放首案第一格，得到 2.498e−16 J，与 math.fsum 报告一致。

首次完整命令退出码 0，实际总墙钟 8.52169 s，进程峰值 RSS 40.625 MiB。均未触及资源门槛。结果绑定的是 JSON 中实际文件 SHA-256；其中未提交的脚本/模型不被宣称为已绑定 Git HEAD。

## 冒烟与故障传播检查

真实 `--smoke` 模式运行 N=4、h=0.002、t=0.004 的同一模型，仅检查可执行性/账本，不宣称空间时间收敛：

```sh
PYTHONPATH=src .venv/bin/python experiments/sandbox_validation/rigid_heat_convergence.py --smoke --output /private/tmp/rigid_heat_smoke_20260907.json
```

该命令实测退出码 0。随后在测试进程中保留实际积分调用，只将其返回的状态改为明确的 `numerical_failure`，检查基准不能因有终态数据便报告 PASS。以下实际调用得到 main 返回 1，并生成 status=failed 的 [故障冒烟记录](RIGID_HEAT_CONVERGENCE_FAILURE_SMOKE.json)。这是**显式注入的状态传播测试**，不是材料失败记录，也不是伪造数值轨迹。核心源码没有修改。

```python
import importlib.util
from dataclasses import replace
import sludge_sandbox.integration as integration

spec = importlib.util.spec_from_file_location(
    'rigid_heat_benchmark', 'experiments/sandbox_validation/rigid_heat_convergence.py')
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
actual_integrate = integration.integrate

def failed_core(*args, **kwargs):
    completed = actual_integrate(*args, **kwargs)
    return replace(completed, status='numerical_failure',
                   reason='injected_core_failure_for_smoke')

integration.integrate = failed_core
assert benchmark.main(['--smoke', '--output',
    '/private/tmp/rigid_heat_failure_smoke_20260907.json']) == 1
```

复跑须选择新输出路径；旧路径存在时脚本拒绝覆盖。当前完成的是可复查的二阶数值收敛证据，仍没有扩大到真实湿砖或全周期材料验证。
