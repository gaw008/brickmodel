# 来源数值前缀与共享库存/能量账本

2026-09-10 UTC；基线 `1fd9e87`，分支 `codex/physics-sandbox-v1`。本阶段实现保存来源速率的前缀积分与审计。软件增量通过下列限定验证；完整原污泥材料模型和全周期 Goal 仍未完成，部署范围仍为离线研究。

## 实际实现

`exact_terminal_panel` 提取共用 `affine_integral_value`、`affine_integral`、`affine_update`。以精确有理数计算

`I(h) = r0*h + (rm-r0)*h*h/(2*hm)`，

随后每个共享面/局部源积分只投影一次为 binary64；更新库存时精确相加这些已表示的交换量，再投影一次状态。原终端面板调用共用函数，保留原预算、负库存/机械边界与上溢/下溢拒绝。提取前冻结的 13 组完整旧结果/失败诊断逐项保持，包括非半步采样、精确大起点、内部负值、端点零及舍入失败。标量函数保留液体供体焓诊断中原有 Fraction，不先转 float。

新 `source_net_prefix.build_source_prefix` 从完整 `SourceAffinePanel` 构建 `ExactStepLedger` 和原始数值状态：

- 共享面在相邻格使用同一积分；液汽相变使用一次投影及其相反数。固定干物 kg 不混入四列液/气 mol 库存。
- 全部 4N 库存在整个所选前缀上求最小值；任一零初值均拒绝。内部负值拒绝，内部切触或端点零仅为 `numerical_boundary`，严格正值为 `strictly_positive_numerical_prefix`。
- 分别保留并检查分量积分投影、状态投影、状态相对精确多项式的完整残差。继续使用传入的原 `IntegrationPolicy`，不放宽原蒸发修正预算。
- 总面 U 是更新依据；导热、气体焓、液体供体焓及各自投影/分解差另存诊断，避免重复计热。液流反向标记只描述仿射通量，不证明真实全区间供体身份。
- `SourcePrefix.check()` 重建派生内容，并比较原政策字段快照及数组类型、形状、字节。共享面板入口补上两时刻的严格 float64 数组及整数面/邻接编号要求。

`audit_source_prefixes` 要求精确时刻连续、上一原始输出等于下一实际输入、政策/来源算子/储能/固定质量一致。它同时累计已表示交换和精确积分交换，在**每个前缀**检查两类累计残差。两者均为带符号净残差门槛，不声称累计绝对误差成本有界。此审计只证明算术连续性，不授予物理轨迹、事件或接受步资格。

## 真实发现及修复

1. 累计审计原先只加已舍入账本，漏掉积分投影累计误差。独立构造两段连续前缀，每段误差 1 mol、小于原 1.5 mol 门槛；累计完整误差 2 mol 却被错误接受。真实 RED 保留，修复后按原门槛拒绝。
2. 原政策对象可被改成另一个有效宽容差而继续通过复核。现在独立保存全部原政策字段并复核，不能追溯性放宽已存记录的门槛。
3. `True`/相等浮点编号可冒充整数面编号；两个采样时刻的数组 schema 也缺少完整入口检查。现已集中在来源面板入口修复。原 6 项面编号 RED、12 项数组入口 RED，以及独立审查发现的 2 项内部状态 dtype 漏检均保留。

## 实际验证证据

| 检查 | 实际结果 | 产物 |
|---|---|---|
| 提取前旧测试 | 6 通过 | `legacy-before.xml` |
| 提取后 helper/完整旧结果/旧执行器 | 30 通过；黄金比较覆盖 13 组完整返回或失败 | `legacy-after.xml`、仓库 fixture |
| 最终源码集成 | 131 通过，pytest 显示 10.37 s；XML 10.367 s | `source-tests.xml` |
| 最终非 editable 安装 | 131 通过，pytest 显示 10.79 s；XML 10.784 s；零失败/错误/跳过 | `installed-tests.xml` |
| 安装身份 | 118 Python 模块、125 源包文件与实际 site-packages 字节一致 | `installed-identity.json` |
| 独立代码审查 | 累计反例及组合 56 项通过；helper/旧结果另 12 项通过 | `code-review.md`、原始日志 |
| 独立 Python 审查 | 32 项反例通过；政策/类型/记录篡改问题已关闭 | `python-review.md`、`python-final.json` |
| 独立制造解算术 | 79 基准检查及 144 实现对照，0.03138 s | `physics-result.json`、`physics-review.md` |
| 安装版原生记录回放 | 7 个独立前缀完成，0.382550 s，无新 EOS 求值 | `native-prefix-result.json` |
| 原生记录独立标准库复算 | 818 检查，0.050866 s | `native-audit.json`、`native-audit.md` |

最后两行使用已保存的真实水来源求值，不是新的真实水积分轨迹。独立审计直接读取固定原始 JSON，以 Fraction 重算 245 个共享积分值、105 个状态值、84 个最小值、28 个面诊断及各自残差。最大完整残差为 `2.3817631510377932e-17 mol` 和 `6.874738982948538e-12 J`，原门槛仍为 `1e-7 mol` / `1e-3 J`。原七个试步的三拒四受身份保持；七个新仿射输出并非连续输入，因此只审计七个 singleton，没有拼接成新轨迹。

独立原生审计器首次错误假设气体边界也有液体诊断字段，产生 `KeyError liquid_mol`；原脚本/失败日志保留。修正仅识别既有 gas-only 零液流边界并增加明确 schema 检查，模型输出未修改。审查由本任务子代理完成，不称为外部专家认证。

## 命令与冻结产物

最终源码命令为 `PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest`，测试文件为：

```
tests/sandbox/test_affine_quadrature.py
tests/sandbox/test_affine_quadrature_legacy.py
tests/sandbox/test_exact_terminal_panel.py
tests/sandbox/test_exact_terminal_executor.py
tests/sandbox/test_source_net_prefix.py
tests/sandbox/test_source_net_panel.py
tests/sandbox/test_source_net_panel_integration.py
tests/sandbox/test_source_net_roots.py
```

保存 JUnit XML。安装使用 `UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache uv pip install --python /private/tmp/brick-water-backend-probe/venv/bin/python --no-deps --offline --reinstall .`；随后在 `/private/tmp`、清除 `PYTHONPATH` 后，按上列测试的绝对路径执行同一测试集。`check_install.py` 的第四参数为预期测试数 131，其仅此参数化变化已独审。安装验证检查全部源包文件的对应字节，不声称排除了任意额外安装文件。

`replay_native_prefixes.py ROOT OUTPUT_JSON` 从仓库固定原生记录被动解码，禁用来源求值、反解和 EOS 入口；预置 30 s 内部、45 s 外部预算。`audit_native.py` 原样保存执行时绝对路径和输入 hash，用于固定历史产物的复核；新回放含新的耗时字段，不冒充同一个冻结 JSON。

最终回放 SHA-256：`8ca3d79c533801f70002b3ad6bace09e84446c87e62d9bd4233d8fce57fc95e0`。完整八项源码/测试/fixture 字节身份见 `source-freeze.json`。`raw-evidence.zip` 保留 85 个实际文件（排除缓存），包括历次 RED、审查、回放脚本和日志；全部成员重开并逐字比较通过。归档 136303 bytes，SHA-256 `c6e0ee481a7e4403e416e987c917c2b093e6dab51ea008849535372bf92eb648`，细项见 `archive.json`。

## 下一步与尚未完成的范围

按 [实际来源试算路线](next-route.md) 和 [独立约束](next-route-review.md)，只提取原精确积分器的 Euler 更新，构建真正求值的起点/预测中点/前缀终点，再与既有 `integrate_exact` 完成同一精确区间的结果比较。原政策、实际温压反解界和全部回调资源必须保留；直接归一化差异不除以 3，不把一致性门槛叫严格截断误差证明。先完成廉价制造水测试、独审，再按事前预算执行一次安装版短真实水案例。

该后续试算尚未实现。本阶段也未完成真实事件时刻精度、运输残余成对液体/供体焓修正、干界面与再润湿、来源记录/恢复/应用。不得用原蒸发预算给排水修正提供额度。原污泥同材料体积/吸附/输运、完整反应/烧结/冷却、三机制公开实测留出、全周期时空验证、多代及应用验收仍属原 Goal 的必需未完成项。
