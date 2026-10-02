# P47：生产三相独立账本

P47生产三相账本已接入并完成受影响保存输出验收（2026-10-02T06:29:13.191257+00:00）：新增calcium_phase_ledger及calcium_phase_ledger_report，FiniteGasFullCycle.summarize复用已有端点rows/self.reaction_config，无新增rate/thermo/RHS或重解码；原signed逐格残差再全局求和、cell/global nofloor预算及原0.001阈值保持。唯一保存P46数据任务rc0/回收，report42613B，监督0.593627s<独立30s/512KiB、CPU0.341216s；0构造/RHS/Jac/ODE/fit/UQ。每相15旧字段、whole/onlystage共90字段一致（同区间重复而非独立验收），calcite/portlandite passed；lime(CaO)原残差/预算零，relative=null、passed=false、undefined_zero_budget，绝对零仅保存观察。主summarize接线仅静态独立复核，不冒称执行或全八阶段资格。根575=144literature431assumed0measured，旧569完整保持，仅6运行政策，名义mode0/directoff及原whole flags保持。P45净U、P34/P40/P44、名义余水0.135892078740%>0.1%失败与当前mode1加密/完整阶段/交叉项未资格保持，wholefalse。Git、Drive、恢复与历史容量分别读回。

生产输出现在增加 `report.calcium_phase_ledger`，schema 为 `sludge_vme_calcium_phase_ledger_v1`。`calcium_phase_ledger(config,start,end)` 接收已有逐格库存和独立反应进度，`calcium_phase_ledger_report(config,endpoints)` 生成 `whole_cycle` 和 `stages`。主汇总在已有气体端点索引处收集原 row 引用，并传入含 active direct 计量的 `self.reaction_config`。未增加速率、热力学、RHS、解码或积分调用；原物理、工艺及整体标志不由此账本改写。

算术严格沿 P46：逐格 `end-start-sum(stoichiometry*signed_extent_delta)`，全局残差再从逐格残差求和。逐格预算为初值、终值、各反应来源绝对值和的最大值；全局预算保持 `max(abs(sum(start)),abs(sum(end)),sum(abs(sum(each reaction source))))`。各区间自己的原始起始库存作为初始归一参考，所有带符号量保留，无 floor、seed、clip、Ca 池或气体预算替代。阈值只读根 `acceptance.balance_relative`。

| 实际 P46 保存端点的生产结果 | calcite | lime / CaO | portlandite |
|---|---:|---:|---:|
| signed residual / mol | +1.364146562e-18 | 0 | −4.508332862e-18 |
| budget / mol | 0.1464338674 | 0 | 0.03036737232 |
| budget_relative | 9.315785929e-18 | null | 1.484597618e-16 |
| passed | true | false | true |
| relative_status | passed | undefined_zero_budget | passed |

`absolute_global_residual_mol`、`saved_global_residual_exact_zero` 和 `saved_cell_residuals_all_exact_zero` 单列绝对/逐格保存观察。CaO 的 `initial_reference_status=undefined_zero_reference`、两相对值 null 和原 passed=false 保留。定义相对值才可能通过；零库存/源/残差并不把 0/0 定义成 0，也不证明连续正性或一般守恒。

唯一保存数据任务在 2026-10-01 23:23:54.969509 PDT 启动，23:23:55.563972 PDT 回收，独立截止 23:24:24.969509 PDT。report entry1、interval helper2、六条相记录实际对应一个窗口的三个相；whole 与唯一 stage 重合，不是六次独立科学验收。生产 helper 实际处理原 P46 21 行中的两个既有端点，每相15个旧字段共90个逐字段结果一致。42,613 B 输出低于512 KiB，workerCPU0.341216s/wall0.502139s、监督0.593627s。根现有 reader 实际通过575条；没有模型构造、RHS、Jacobian、ODE、fit 或 UQ。

只读独立审查确认主接线、算序、direct计量、原布尔和零分母处理无阻断缺陷。`FiniteGasFullCycle.summarize` 本轮未执行，因此只授予保存端点 helper 执行和主源码静态接线资格；P46 原科学报告保持，当前模式时间/网格、八阶段、三方案、反演、UQ 和完整 CLI 仍未资格。P45 净U原失败、P34 30/81、P40 7.33335%网格差、P44 CaO3/9及direct3.01853436%与名义余水失败不翻判。目标材料0measured，没有识别实砖L。

变更为两个生产源码、根6条运行政策及必要计划/报告/矩阵。原569条参数值、单位、范围、来源和身份完整保持；根名义mode0/directoff不改。本轮30秒保存任务独立登记并关闭，未复用P46窗口，不自动补跑。无新软件测试、SHA、护栏、物性、文献或自动任务。

完整实际结果见 `runs/full-cycle/p47-calcium-phase-ledger/production-report.json`、`execution.json` 和 `independent-source-review.json`，简明汇总见同名JSON。正常 Git 与唯一小科学增量读实际本地收据；Drive名称/大小/父目录核对不等于恢复。原件和独有历史保留，20GB、GitHub容量告警及历史完整备份仍未完成。
