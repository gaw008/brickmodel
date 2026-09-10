# 实际来源前缀试算与同区间参考

2026-09-10 UTC；基线 `cc94ecb`，分支 `codex/physics-sandbox-v1`。本阶段将保存速率的仿射前缀接入实际来源算子，验证真实预测中点、终点及同区间参考。`software_status` 为本组件已验证、完整系统仍未完成；`scientific_status` 为限定数值验证、材料资格仍 false；`deployment_status` 为离线研究。

## 实现与边界

`exact_integration.advance_exact_euler` 提取原积分器的 Euler 预测更新，保留“已表示净导数 → 精确时长乘积投影 → 状态更新”的原顺序、机械正性、异常分类及原乘积下溢行为。新入口检查正 Fraction 时长和政策；旧合法子类仍可使用。原积分器的控制器、SSPRK2 两半步、误差尺度和累计账本未复制或放宽。提取前冻结的 12 组完整回调/状态/账本/失败结果保持一致，只排除不确定的墙钟耗时。

新 API：`evaluate_source_prefix_trial(adapter, initial, *, start, end, integration_policy, maximum_callbacks, cancel=None)`。

1. 复制并绑定原政策，核对来源、固定干质量、储能身份、精确时刻及炉程节点。全部 4N 流体库存必须正，任一零初值仍不支持。
2. 实际求值起点；用共用 Euler 更新得到中点预测态，并实际求值中点。复用 `source_net_panel`、`source_net_prefix` 的整个前缀最小值及共享账本；数值切触/零端点不授予物理事件权限。
3. 对正库存前缀的原始输出实际求值终点，执行来源储能反解、液汽/液流/气流及炉程计算。保留实际温度、逆解误差、压力及包含可用体积误差的来源压力界；仅 unpack 不能替代这一步。
4. 从同一初态调用既有 `integrate_exact`，要求参考完整到达同一精确终点。数值政策不变，仅记录剩余墙钟资源。直接比较 `max(|ΔN|/(atolN+rtol*Nscale), |ΔU|/(atolU+rtol*Uscale)) <= 1`，不除以 3。
5. 每次实际调用保存原始输入、时间、顺序、返回内容或失败种类/消息。总墙钟、取消和调用上限覆盖试算及参考。成功记录用原积分器被动重放全部保存的参考速率和可恢复 DomainExit，核对原请求状态/时间及全部确定性参考结果，不再次计算物性。

被动重放不证明历史耗时。记录检查保留原政策、剩余政策、控制及结果快照；失败输入同样绑定。`validated_positive_numerical_trial` 仅是数值一致性状态，不是物理事件、干态续算、供体历史或真实原污泥材料的准入证明。报告温度处的压力误差也不自动覆盖完整逆温度误差传播。

## 真实缺陷与修复

- 参考账本加 1 J 后仍能通过原检查：现被动重放原积分器，核对完整参考而非只比较终点。
- 结果可被改成虚构的 unsupported 原因：现保留原结果和控制快照。
- NaN 能量因 `max(0, nan)` 被误当成零差异：现四个输入数组均需为非空、有限 float64 数组后再运算。
- 失败终点调用的输入可被替换：现全部尝试都绑定原输入及失败信息，已知阶段也与实际预测/前缀关联。
- 空异常消息被误当成无失败：现区分失败种类、字符串和 None。
- 原参考成功缩步恢复 DomainExit 后，新试算却误报数值失败：实际 20 调用反例及作者 RED 保留，现按原类型/输入重放失败，让原积分器复现拒步与恢复。

运行器另有实际超时持久化测试：自身 SIGALRM 显式标记外部资源超时，顶层记录 `resource_limit`，同时保留原始 TimeoutError 及嵌套试算结果。没有据嵌套异常推断材料失败。

## 实际验证

| 检查 | 实际结果 | 证据 |
|---|---|---|
| 提取前旧基线 | 17 通过；12 组完整冻结记录 | `legacy-before.xml`、仓库 fixture |
| 提取后 helper/旧链 | 27 通过，4.90 s | `euler-green.xml` |
| 作者来源试算 | 31 通过，29.46 s | `implementation-report.md`、原始日志 |
| 最终源码集成 | 143 通过，55.59 s | `source-tests.xml` |
| 最终非 editable 安装 | 143 通过，47.69 s；零失败/错误/跳过 | `installed-tests.xml` |
| 安装身份 | 119 Python 模块、126 源包文件逐字匹配 | `installed-identity.json` |
| 独立代码审查 | 46 通过，39.17 s；最终运行器另 5 项持久化测试通过，3.02 s | `code-review.md`、`runner-review.md` |
| 独立 Python 反例 | 11 helper + 14 trial，共 25 项通过 | `python-review.md` |
| 最终三格制造水独审 | 56 检查，6.55137 s；前后源码一致 | `physics-review.md`、`physics-result.json` |
| 一次安装版真实水物性试算 | 完成；11 次实际调用，参考 1 接受/0 拒绝 | `native-result.json`、`native-summary.json` |
| 最终原生记录标准库独审 | 235 检查，0.026472 s；无新 EOS | `native-audit.json`、`native-audit.md` |

实际案例为既有开放三格来源构造，时段 `1/16384 s`。初始/最大/最小步长仍为 `1/1024`、`1/1024`、`1/16384 s`，原相对容差 `1e-8`、库存绝对容差 `1e-7 mol`、能量绝对容差 `1e-3 J`、尺度 `1 mol`/`1e5 J`、接受/拒绝上限各 4。事前资源为试算 180 s、全运行 210 s、32 次调用；实际试算 81.125177 s、全运行 82.732120 s。没有重跑或更改科学门槛。

实际回调为 3 次前缀求值和 8 次参考求值。直接差异 `0.001086768806259706 <= 1`；参考自身的 SSPRK2 误差指标为 `0.00036442473617906006`，二者不是同一个误差估计。前缀总 U 增量 `0.012114676166675054 J`，参考增量 `0.012113521705032326 J`；参考全域能量和总水账本残差分别为 `-3.723089544993563e-12 J`、`-2.2523029583965473e-17 mol`，均显式保存，不假定为零。

235 项独审从保存速率独立重构 Euler、共享前缀及参考 full/two-half SSPRK2、接受账本和直接差异。区间最小值从保存的多项式系数重算，未在该审计内再次独立推导这些系数；温压误差核查为保存来源记录的核算，不是重新证明 EOS 的误差。该审计针对固定三格成功案例，不是任意失败记录的通用校验器。审计器初版的序列化属性位置 KeyError 及扩展脚本缩进错误均已保留，模型输出未因此改变。所有审查均为本任务子代理工作，不称为外部专家认证。

## 复现与完整产物

最终测试集：`test_exact_euler.py`、`test_exact_euler_legacy.py`、`test_exact_integration.py`、`test_exact_source_column.py`、`test_source_prefix_trial.py`、`test_source_net_prefix.py`、`test_source_net_panel.py`、`test_exact_depletion_integration.py`，均位于 `tests/sandbox`。源码通过 `PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest` 执行并保存 JUnit；离线 `uv pip install --no-deps --offline --reinstall .` 后，在 `/private/tmp` 清除 `PYTHONPATH`，以相同虚拟环境和测试绝对路径复验。`check_install.py ROOT OUTPUT_JSON XML 143` 核对实际安装字节和零失败 XML，不声称排除任意额外安装文件。

`run_native.py ROOT OUTPUT_JSON` 为已执行的一次性有界运行器，构造/数值政策见 `native-plan.json`；再次运行会产生新的计算和记录，不冒充原产物。`audit_native.py` 保留实际审计时的绝对路径和固定输入 hash。原生 JSON 为 3538988 bytes，SHA-256 `7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505`；最终源码/测试/fixture 身份见 `source-freeze.json`。`raw-evidence.zip` 与 `archive.json` 保留原始 RED、旧脚本、测试和审核，并逐成员重开核对。

下一步按 [来源端点比较与接近事件路线](next-route.md) 和 [独立约束](next-route-review.md)，先用已经保存的真实端点检查原事件 N/U/T/报告温度处 P 容差，无需新增 EOS。完整逆状态压力界、独立事件时刻精度、运输残余成对液体/同供体焓修正、干界面/再润湿、来源保存/应用仍未完成。同原泥材料域、完整反应/烧结/冷却、三个机制公开实测留出、全周期时空/多代及应用验收均继续属于完整 Goal 的必需项。
