# Native controller 冻结稿独审合同

用途：审查随后冻结的接入实现；不是未冻结稿批准、native 执行许可或材料认证。依据当前正式 `mass_wet_exact_controller.py`、已审 stage6ece806a/session7a7e8376、原 terminal/writeback 和 exact-record 定义。这里只增加接入所必需的证据，不修改原科学门槛、事件选择或回滚语义。

已核实：正式 `Stop` 继承 `ValueError`，原 terminal compare 的 `except (ValueError, OverflowError)` 能保存当前 ref/path；没有据此确认“path 丢失”缺陷。需要针对性验证的是 compare 内部已完成 rows 在后续 query 异常时能否保留。以下是验收条件，不是对未冻结候选的缺陷结论。

## 最小必须项

1. **唯一 session、累计成本。** 同一具体 `PressureSession` 对象贯穿普通 trial、rejected trial、缩步、各 terminal refinement、两个连续比较及独立减半 approach；不得按分支/模式/比较重建。保留入场/最终 snapshot 的原配置、起始时钟、全部先前 attempts；seed/proof entered/completed 累计只加一次。控制器 host/panel 成本与 session 数学成本分开，不把 snapshot 历史重复收费；未知 child cost 继续 fail closed。controller/stage/session 剩余墙钟取各自原预算约束，host 间隔不能从 session 耗时中删除。

2. **事件后仍湿格必须证明。** 每个事件比较及最终共同端点比较，分别使用两条路径各自实际 operator、mode、state、observation 和 cell。第一格耗尽后第二格仍 wet 时，该格仍需本次 fresh pressure query；只有精确零液且 `depleted_no_nucleation` 的格可沿用原 dry 解析半径。禁止把一次 dry 模式、旧 query PASS 或另一条路径的水状态用于仍 wet 格。绑定完整原 T±epsilon、U/Cp/体积条件、实际水源/public-native 换算和名义 P，禁止漏掉原 fixed-T 误差。

3. **比较证据可定位。** query context 至少可追到 refinement level/terminal或independent、event index/selected cell或common endpoint、比较左右路径、实际采样时刻、cell、source/modes、原 initial/policies。同一 observation 参与后续比较时仍记录当前实际 query，不隐藏缓存许可。四项数学证据、失败 stage/kind/reason 与 attempt 序号留在 session 中；成功半径必须是匹配该实际 request 的非负 Fraction。

4. **任何比较失败保留当前 refinement。** terminal 比较发生 resource/cancel/domain/binding/unresolved 退出时，必须保存当前已经完成的 path/refinement，以及本次已产生的比较行/尝试上下文、先前 successful queries 和失败 query；不能只在外层捕获 `Stop` 后丢掉当前 `ref`。独立最后比较同样要求。尚未计算的比较分量保持明确缺失，不补零/冒充已比较。状态按结构化类别传递，不能用 reason 子串猜测；completed child 成本先入账再执行会失败的 guard。

5. **原子发布与两次连续收敛。** 仅当事件顺序/逐事件 modes 匹配、全部原六单位 gate 通过、连续两次比较通过、独立减半 cap 与 safe fraction 的实际前事件网格不同且其全部比较通过、原 prefix/writeback 审计与最终 guard 通过，才能发布 accepted path。中途失败—even 完整 path 或部分证明已成功—外层仍返回原 `times=(start,)`、原 states/operator、无 steps/packets、原 empty correction totals；失败 paths/frames/observations/query history 只作为诊断保存。不得把候选事件投影或第二条独立路径提前变成外层 accepted state。

6. **原输入/政策不可变证据。** native opt-in 入场冻结原 initial/start/end、stage/controller/roundoff 政策、原 fraction limit 与源上下文的不可变 bytes；前后 guard 检查变更即拒绝。失败结果即使还引用被变更的诊断对象，也必须另外保留原 bytes，不能把变后值标作原请求。mode 迁移只能更新当前 operator/source binding，原 initial、原 fraction budget、每格 correction 累计不得重置；每个事件 correction 必须从真实 projection record 恰好累计一次。

7. **默认行为与 codec。** 无 session 的原 fixture/default 路径保持完整非 wall 值和调用语义；fixture 与 native session 同时提供应在工作前拒绝。新 result subtype 保存全部原字段和额外历史，原 `pack` 与 `encode_mixed_run` 都须拒绝，而不是去掉 native 字段后降级为旧 record。新 codec/resume/controller-service 许可不属于本次接入。

## 最小纯测试故障注入

| 注入位置 | 必须可见结果 |
|---|---|
| ordinary reject 后再次 trial、下一 refinement、independent approach | 同 session，attempt 历史严格前缀，累计工作/起始时钟不重置 |
| 第一个事件后的 wet cell query | 实际新 mode 与该格液水 snapshot；仍有 fresh proof，已 dry 格零 query |
| terminal compare 第2个或之后 query resource/cancel/domain | 保留当前 refinement/path、失败 attempt、前面成本；外层原子回滚 |
| independent 最后 query失败或六 gate 不通过 | independent ref 与原事件诊断完整，无 accepted packet |
| callback 中变更原 policy/initial | fail closed，原 bytes 可复原，失败工作已计入 |
| session已带历史、预算恰耗尽、child未返回成本 | 不重置、不低报、不继续未知成本工作 |
| 新 subtype交旧两个codec入口 | 显式拒绝；默认旧类型完整非wall parity |

完整 manufactured 双事件/多路径 pure 测试可验证调度、账本和回滚；若 session.query 被仪器化，必须明确它没有验证真实压力证书。随后实际 native 运行另行预登记成本与输入，保留首个失败，保存证据审计时不以 PASS 标志作数学依据。原 U/Cp/体积条件、液相模型选择与 native 内部调用数量未知的边界继续保留。
