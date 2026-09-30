# P10：反演记录器与必要预算留存修正

两个实际输出缺口已修复：后续记录器读取顶层 `report.gas_species_ledger`；完整合成真值和最终拟合前向保留独立回读需要的预算。物理方程、271项根参数、名义工况、优化预算及0.1%/2%判据均未改变。

## 维护入口和输出

实现位于 `src/sludge_vme/inverse/full_cycle.py`，由现有CLI/Python入口直接使用，不增加命令选项或新优化器。

| 位置 | 保留/新增内容 |
|---|---|
| `forward_call_summary(report)` | 原物理结果、最坏普通预算残差、前向耗时；气体顶层存在标记、`present`/`missing`、路径与缺失诊断 |
| `fit` 的 `evaluation_history` | 使用上述共同记录器，每次只存轻量诊断，不复制全部预算 |
| `forward_audit(report)` | 全程及分段质量/元素/能量预算、热力学、状态域、量纲检查、原顶层气体账本和实际阶段范围；不含fields |
| 完整 `synthetic_demo` | 在fit前写入 `synthetic.observations.json.truth_audit`，原 `truth_example_endpoints` 保留 |
| `fit` 最终前向 | 保留原 `forward_*` 字段，追加 `forward_gas_species_ledger`、可用性诊断及 `forward_scope`；原 `forward_elapsed_s` 命名和含义保持 |
| 单参数/双参数干燥合成入口 | 同一提取接入既有 `truth_window_audit`，保留 `window_balance` / `forward_window_balance`；scope仍只有实际两阶段 |

账本存在只表示数据可用，不是气体守恒已通过。缺失或空顶层账本保留为 `null`，并记录 `gas_ledger_status=missing` 和明确诊断；不读取whole_cycle内同名字段，不生成空对象或PASS。普通物理结果和拟合资格保持原判定，不能代替缺失账本的独立验收。必需的普通预算字段仍直接读取，缺失即报错。

当前维护入口是以上受Git管理的函数及既有CLI/Python入口。`runs/full-cycle/final-inverse-20260930/entrypoint.py` 是原批次历史快照，其中错误路径原样保存用于复现；后续开发不得复制它作为新运行记录器。外部包装若需要记录实际前向，应调用 `forward_call_summary(report)`，不再自行检查错误层级。

## 本次实际核对及限制

- 用已保存 `runs/full-cycle/final-uq-0-standard.json` 提取八阶段完整审计并写盘回读，所有必要字段、气体账本、耗时和阶段列表与输入一致；202001字节。它是旧UQ样本，不是旧完整合成真值。
- 用旧联合合成真值 `truth_window_audit` 逐项映射其自身保存的预算名和耗时名，写盘回读两阶段审计；59105字节。其气体账本确实未保存，新输出如实为missing/null，不从其他运行拼接。
- 用P01保存的同次窗口普通预算及顶层气体账本核对共同轻量记录器，结果与输入一致。该窗口汇总未保存dimension_check，因此本项没有把它称为完整审计，也未借用其他工况补齐。
- 对保存完整报告的结构投影移除/置空顶层账本，同时保留错误嵌套层级，得到missing/null及明确诊断；这些只是数据结构核对，不是新物理场景。
- 独立源码复核确认完整真值在fit前保存、两个窗口接线及旧字段/计时保持；predict、fit、make_cycle、least_squares的原调用及实参保持，predict/map_observations函数体保持。

新增积分0、优化0、求根0；没有重跑22+17次旧反演或P05，也没有新增软件测试文件、原始场、参数搜索或SHA。实际提取/序列化/回读耗时0.138796s，自声明至实现/验收收口墙钟454.494s；独立审查未单独计时。执行session48799已退出0。这里不声称新版本CLI/完整优化被重新执行；验证依据是实际保存报告的数据操作和调用接线源码复核。机器记录见 `FULL_CYCLE_P10_INVERSE_EVIDENCE.json`，必要重序列化输出见 `runs/full-cycle/p10-inverse-evidence/`。

## 历史证据仍然缺失

原39次 `gas_ledger_present=False`、原执行器、完整合成观测/拟合/联合结果及原独立回读均保持。旧False不表示账本物理失败；当时账本未逐次保留，不能将这些False批量改成True。

旧完整真值的全程/分段/热力学/状态域/量纲及顶层气体账本没有落盘，不能从已存标量重建。本次修复未来留存，不恢复或替代旧真值。完整拟合末态或新旧其他工况均未被冒充为该真值。

名义余水0.13505646%初水仍超原0.1%门槛，工程验收仍False；材料仍38 literature / 233 assumed / 0 measured。真实材料约束需同材质量-时间、持水/脱附、温度、水汽及几何资料，本项输出修复不提供这些材料数据。

Git和Drive实际结果分别记入 `runs/full-cycle/p10-git-delivery.json`、`p10-drive-delivery.json`。元数据验收、实际云端恢复和历史存储继续分列；不删除唯一源包，不创建定时任务。
