# B2 历史失败根因与修复证据

日期：2026-09-07 UTC。调查基线：`4b4f2d37913b96d30842f86d38f302d578887e72`。
本次修复的是 B2 给定温度的 synthetic 数值诊断模型；没有将它升级为真实原污泥材料模型，也没有增加能量、压力或烧结闭合。

## 1. 原始失败确切发生在哪里

原始文件保留于 `docs/research-status/evidence/b2-demo001/`，本次未覆盖其任何字节。
在 `/private/tmp/b2-root-cause-20260907/material_dynamics_v2b2/` 创建独立副本，复制原始 CSV/JSON，再通过 Python 的异常追踪读取原审计函数已经捕获的异常。没有改变审计容差、输入、原始 CSV 或参考积分。

历史运行完成全部 22 个情景，在审计第 147348 项停止，前 10 个情景通过。首个失败为：

| 项目 | 原始值 |
|---|---:|
| 情景 | W07 |
| 无量纲时间 τ | 1.5 |
| 检查 | reaction_exposure |
| 导出的 H | 0.5961645636313229 |
| 独立分段 Simpson 参考 H | 0.5961635448003981 |
| 缩放误差 | 1.0188309247372018e-6 |
| 原固定容差 | 1e-6 |

原 `audit.py` 统一把异常替换为 `export_audit_rejected`，因而丢失了具体失败量。新审计只增加受控、有限的比较数据：情景、时刻、检查名、观测/参考值、归一化尺度和误差。旧失败用新审计读取仍在相同检查失败。

独立重算全部历史 H 输出后，发现以下情景超过原门槛；L01 的缺陷原先被 W07 的提前停止遮住：

| 情景 | 最大缩放 H 误差 | 对应 τ |
|---|---:|---:|
| W07 | 1.2920221554857392e-6 | 1.8 |
| W09 | 1.2801620813407410e-6 | 1.8 |
| W11 | 1.2393711689151488e-6 | 1.8 |
| L01 | 7.9978527672806520e-6 | 1.4 |

依据：[原异常追踪](b2-root-cause-20260907/historical_failure_trace.json)、[逐情景误差](b2-root-cause-20260907/historical_exposure_errors.json)、[新审计读取旧数据](b2-root-cause-20260907/historical_detailed_audit.json)。

## 2. 数学根因与修复

SSPRK2 对被动系数积分 `H = ∫K dτ` 使用逐步梯形公式。旧步长只考虑正性、CFL、最大步长、温度 knot 和输出时刻；这些限制不能保证 H 的数值积分精度。较弱扩散、较大厚度使 CFL 允许更大的步长，而升温过程中的 Arrhenius 型 K 有曲率。保持质量/元素守恒并不能消除此项截断误差。

保留 SSPRK2 以及 u/v/f、反应进度、边界交换的原阶段权重。只增加一个独立推导的数值步长约束，所有状态仍随同一实际步长推进；没有重置 H、用参考值覆盖导出值或修正库存。

在每个温度线性区间，令 `A = theta*T_ref`、`s = dT/dτ`：

```text
K = K_ref * exp(theta - A/T)
K''(τ) = K * s² * A/T³ * (A/T - 2)
```

用 `x = A/T` 改写后，与温度有关的因子为 `exp(-x) x³(x-2)`，其导数为 `exp(-x) x²(-x²+6x-6)`。因此 `|K''|` 的区间最大值只需检查温度端点及位于区间内的 `x = 3 ± √3`。保温、零反应和 theta=0 的 K 恒定，无梯形截断误差。

令 `M_j = max|K''|`，`D_ramp` 为全部非恒温区间长度之和。设独立的数值积分绝对预算 `ε_H = 1e-7`，在第 j 段限制：

```text
h ≤ sqrt(12 ε_H / (D_ramp M_j))
```

单步梯形误差上界为 `M_j h³/12 ≤ ε_H h/D_ramp`。各非恒温步相加，任意输出时刻的累计截断误差不超过 `ε_H`；不依赖升温与降温误差抵消。保留原 `dt_scale` 对新增步长上限的缩放，故时间细化仍真实细化。

`ε_H` 是 `numerical_policy`，不是材料常数，也不是修改审计门槛。它比原审计最小绝对尺度 `1e-6` 严格十倍，为浮点累积和独立参考误差留出余量。上述推导控制的是 H 的积分截断误差，u/v/f 的精度仍由独立解和空间/时间收敛检验。原始输入、合同、接受矩阵和所有比较门槛保持原值。

## 3. 与历史失败分开的 macOS 问题

旧 `resources.py` 总是把 `ru_maxrss` 除以 1024，实际只适合 Linux 的 KiB。当前 macOS 返回字节，这会把约 76 MiB 的进程报告成约 77824 MiB，错误触发 512 MiB 上限。新换算在 Darwin 除以 1024²，在 Linux 除以 1024；512 MiB 上限不变。

已核读的原始平台来源：Apple XNU [`getrusage.2`，`ru_maxrss` 定义](https://raw.githubusercontent.com/apple-oss-distributions/xnu/main/bsd/man/man2/getrusage.2) 写明 bytes；Linux man-pages [`getrusage(2)`](https://man7.org/linux/man-pages/man2/getrusage.2.html) 写明 KiB。Apple 的部分旧归档手册写 KiB，与当前 XNU 不同，本次采用当前源码手册及本机实际读数。

测试分别注入两平台的 76 MiB 和 513 MiB 读数，证明前者允许、后者仍拒绝。这是平台单位测试，不是两平台都已经实机验证；本次实机只有 macOS 26.6.2 arm64。

## 4. 实际验证结果

先编写 W07/L01 原升温段回归，在修复前实际失败，两项误差与原 CSV 的最大误差相同。只在这一次定位运行中注入正确的资源读数，隔离已知 macOS 单位错误；该试验不会被当作资源验证。[修复前回归记录](b2-root-cause-20260907/baseline_regression.json)。

修复后，以下命令在主工作区使用 Python 3.12.13 完成，14 个测试通过，进程退出 0：

```sh
cd /Users/wanggaoying/Desktop/brickmodel-github/experiments/material_dynamics_v2b2
B2_TEST_OUT=validation/sandbox-b2-unit-20260907 ../../.venv/bin/python -B -m unittest discover -s tests -v
```

随后用独立副本的 `run_numeric.py` 实际求解默认 22 案，并执行原 32 次参考/回归/收敛积分。结果不是继承旧 PASS：

| 实际检查 | 结果与范围 |
|---|---|
| 默认 22 案 raw + derived 审计 | 全部通过，共 322204 项；固定容差仍为 1e-6 |
| 最大缩放 H 误差 | 6.917104489190251e-8 |
| 碳/氧库存最大缩放残差 | 分别 1.2989609388114332e-14、1.5987211554602254e-14 |
| 名义质量最大缩放残差 | 9.349246523159214e-15；仅原 C/O 简化物种域 |
| NUM004 密闭解析参考 | 3 个 Γ 条件通过；最大绝对误差 1.4371380974154135e-8，原限 2e-5 |
| NUM005 扩散级数参考 | 2 个热历史 × 3 个网格通过；N=31 最大误差 1.9918858415646223e-4，原限 5e-4 |
| NUM001 / NUM007 | 4 案 B1 独立副本回归及 mean/local 事件语义通过 |
| NUM006 | W03/L02/C03 空间和时间细化均通过，门槛未改，实际步数随时间细化增加 |
| 本机成本 | 默认含导出审计 10.13 s；focused 66.81 s；峰值 RSS 81.08 MiB |

完整数字见 [numerical_report.json](b2-root-cause-20260907/numerical_report.json)。原始输入、轨迹、参考值、每案执行记录、门槛比较、源文件副本及运行脚本保存在 [numerical_run.tar.gz](b2-root-cause-20260907/numerical_run.tar.gz)。[source_snapshot.json](b2-root-cause-20260907/source_snapshot.json) 记录实际副本字节；文件一致性不代表科学有效性。

`run_tests.py` 另用真实包装计数记录新增单元回归的 2 次积分，将其计入原共享 40 次上限。完整 focused 现在应为 B2 30 次 + B1 4 次 = 34 次。上表独立 numerical harness 的 32 次不含先前单元测试中的两次；不能漏计后声称总共只运行 32 次。

外部执行命令为：

```sh
/usr/bin/time -l /Users/wanggaoying/Desktop/brickmodel-github/.venv/bin/python -B /private/tmp/b2-root-cause-20260907/run_numeric.py
```

数值脚本运行至最终报告，实际数值门槛全部通过。外围 `/usr/bin/time -l` 在输出 real/user/sys 后，因为 sandbox 禁止 `sysctl kern.clockrate` 返回 1；不能把这个退出码说成 0，也不能把它当作模型数值失败。[采集记录](b2-root-cause-20260907/collection.json) 保留了此限制。没有为了获得绿色外围退出码重复全套计算。

## 5. 重现与剩余边界

在新临时目录解压证据包，把包内 `material_dynamics_v2b2/validation` 移到模块外的 `recorded_validation` 保留，再用当前项目 Python 执行包内 `run_numeric.py`，即可新生成整套 raw/参考结果。脚本仅使用标准库，按 180/300 s 分别限制默认与 focused 阶段。`run_numeric.py` 默认拒绝覆盖已有输出。

本次使用直接 numerical harness 验证未提交修改，没有生成或伪造 `passed_frozen_suite` 的源码绑定标签。原 CLI 的完整提交身份检查保留；在主代理集成提交之后，`run_tests.py` / `run.py --verification` 的绑定流程需再按当前源码执行，不能引用旧身份通过。

本次证据只支持“已查明并修复 B2 在已执行诊断域中的数值失败，保留原接受阈值”。它不支持真实污泥映射、完整能量、真实气体压力、孔隙关闭、烧结收缩、强度或工厂准确性。后续完整沙盒仍需要独立来源及耦合模型实现。

独立 Python/代码审查由主代理另行安排；本报告不把作者自查称为独立审查或外部专家认证。
