# 完整来源运行记录与公开 TG 数据

基线 `be506b6`，分支 `codex/physics-sandbox-v1`。完整 Goal 合同未改。
本阶段实现当前来源试算/事件协议的完整被动读写、累计账本审计及 CLI/Python 查询，
同时补充一组同文命名配方的公开热重观测。

## 已实现的接口

`source_study_record.py` / `source_study_schema.py` 使用96类闭合类型及完整字段集，
复用已有精确数值编码和完整来源观测验证。保存原始 stages、captures、其余顶层 metadata、
明确 contexts 和 provenance；共享内容可去重，原捕获序号、精确时钟、数组与分数不变。
旧文件省略的 adapter/storage 只生成显式 unavailable 引用，不能恢复为 live 对象。

`source_study_audit.py` 重核实际成功/失败试算、原政策、保存的 RHS 数值回放、
前缀/根/写回、阶段连接、压力界/门槛及每格/全域累计账本。
`source_dry_transition._audit_balance_fields` 是从原数值循环提取的共用纯账本函数；
旧运行入口仍执行原 live trial.check() 与连接验证，原绝对容差和计算公式保留。

服务复用常规文件限额读取和独占发布；查询在展开过程中限制字节、节点及深度。
CLI/Python共享服务，可查询原阶段、`captures/原下标/...` 和 `metadata/...`。
失败后返回的未通过验证内容仍完整保留，原位置的 observation 为None；失败摘要提供原返回路径。
使用方法见 [SOURCE_STUDY_RECORD.md](../../SOURCE_STUDY_RECORD.md)。

## 实际发现与修复

- 原服务不识别真正的 SourceStudyNode，导致阶段/失败字段查询不完整；原反例已修复复验。
- 小型共享DAG会在最终大小检查前展开；改为过程中的字节、节点和深度预算。
  核心关联比较另发现共享tuple递归耗时问题，使用局部有界DAG比较，未改旧全局函数。
- 保存文件重新计算哈希后，原失败压力门槛曾可被改为通过；现在由原界、原容差和策略重核。
- 已返回但校验失败的观测曾无法完整保存；现在保留raw返回并明确不授予成功观测资格。
  同一错误返回去掉失败标签后仍被拒绝。
- 服务与核心对失败字段的理解曾不一致；现在共用四字段分类函数，包括只有异常类型或空消息的情况。

初始失败、错误接收、修复前代码、错误测试夹具设置和证据脚本错误均保留。
脚本或夹具设置失败没有被表述为物性失败。最终审查只代表代理独立审查，不是外部科学认证。

## 测试和安装

| 实际范围 | 结果 | 原始证据 |
|---|---|---|
| 压力/失败分支修复前的七文件源码组合 | 141 passed，114.83s | root/source-final.xml/log |
| 最终核心及当时服务的受影响源码组合 | 50 passed，42.72s | root/source-fixed.xml/log |
| 最后失败分类同步后的全部服务 | 31 passed，1.80s | root/service-final.xml/log |
| 最终非editable安装七文件组合 | 149 passed，115.30s | root/installed-final.xml/log |
| 最终源码与安装字节 | 138模块/145包文件一致 | root/installed-identity.json |

安装测试在 `/private/tmp`、清除 PYTHONPATH 后执行；无失败、错误或跳过。
上述源码验证按实际版本分别报告，不能把修复前141项说成最终149项源码单次运行。
Python为 `/private/tmp/brick-water-backend-probe/venv/bin/python`，离线安装命令保存在归档日志。

## 原始运行的被动验收

原输入为前阶段的46,566,617字节完整JSON，SHA256
`6c55383e8d2063ed6c81f2126b40542ba44ee173fc1671b227573b908bfbfc53`。
原件已保存在前阶段 raw-evidence.tar.gz 的 `root/native01/native-result.json`；
本阶段 `root/INPUT.json` 记录该归档及原件摘要。
检查器、180秒限制及独立审核记录均先于完整验收保存。
唯一安装版完整验收已通过，26.321774667秒，物性调用和新物理运行均为0。
所有原字段逐项保留（442,942次值访问，另按数组字节核对），32条接口 observation 的
state/evaluation/role/time/operator/energy/modes逐个原索引对应。
可用记录为805,727字节/1,371个DAG节点，SHA256
`5aa6746744e8804409669466f72d839c9fa869a0c59b88fafbabc9498d29a024`。
保存的3条完整参考回放、7行累计账本和2条失败试算通过声明的被动审计；
原capture16/格1与完整2×3压力门槛的 CLI/Python查询相同。

结果见 [PASSIVE_RESULT.json](PASSIVE_RESULT.json)、[PASSIVE_AUDIT.json](PASSIVE_AUDIT.json)，
完整可查询例子为 [example-study.json](example-study.json)。从项目根目录可运行：

```sh
sludge-sandbox source-study-inspect docs/sandbox/research/source-study-record-v1/example-study.json \
  --capture-index 16 --cell 1 --path transition/cell_selected_pressure_gates
```

这一读回不认证原live对象、来源文件或全域EOS误差假设，也不执行续算。
所有最终10个源码/测试摘要与[独审批准](CODE_REVIEW_FINAL.md)相同；安装包145文件另行逐字核对。
完整原始失败、日志、审核和最终源码快照见 `raw-evidence.tar.gz` / `RAW_MANIFEST.json`。

## 材料观测新增

[Areias2025 图3](../../../../data/sandbox/research/areias2025/tg_digitization/README.md)
两条TG固定44个读图目标，35点可读、9点保留unknown。独立实际看图和356项计算核查通过。
原坐标、条件读图误差、CSV/JSON、叠图、复现脚本和具体来源位置已入库。
数据源是 CC BY 4.0 的 DOI 10.3390/min15080879，PDF第8页图3右侧TG轴。

图3与图4只建立同文MIA1/MIA3命名配方关联，不证明同试件。
TG气氛、实验误差和归一化仍未知；微伏DTA不提供反应热。
污泥经预处理，且配方差异同时涉及石灰石，不能用两曲线差值替代孤立原泥反应。
没有拟合动力学、产物计量或授予材料预测资格。

## Goal 状态与下一步

`software_status=in_progress`，`scientific_status=incomplete`，`deployment_status=offline_research_only`。
本阶段是实际实现与验证进展，完整 Goal 继续 active。
原N3物理共同末端仍约1.093759627e-6秒；材料资格仍false，不能当作完整干燥或烧成。
原独立压力失败与新条件数值接受分别保留。

接下来的具体实现见 [NEXT_STEP.md](NEXT_STEP.md)：连接实际来源运行、取消、完整失败保存和显式配置重建，
再做受控恢复与中文界面。完整原污泥同材料反应—烧结—冷却、三机制公开留出、
空间/时间收敛、全周期、多代搜索及全套使用验收仍是合同必需未完成项。
