# B2 HANDOFF：先 Manager 冻结，再隔离实现与独立 Safety

合同版本：`B2-1.0.1`。任务：`t_c6385001`；原规划：`t_d7507b62`。
状态：Planner 规划补正交付，`frozen_candidate_pending_manager_review`。
结论：本次仅修正验证状态契约并提出一套跨阶段证据绑定建议；无实现、无生产、无后续建卡。`implementation_authorized=false`，`production_approved=false`。字段规则为Manager已决定项；`B2-BIND-001`接口方案仍为`pending_manager_decision`，本卡done不等于G0批准，旧B1批准不放行B2。

补正保留原规划科学路线与历史证据文字；§2及§8的“本轮/实际读取”均指t_d7507b62原规划，不是本补正重做。当前实际工作单独列于§8.1和B2_G0_CHANGELOG.md。没有重新分解项目；以下E1–E5为原有路线，不是新建任务或授权执行。

## 1. 交付物与权威顺序

当前实际文件：
- `/home/ubuntu/.hermes/kanban/workspaces/t_c6385001/B2_CONTRACT.md`：科学范围、归一化、方程、输入输出、诊断、筛选、数值门、预算/人工审批。
- `/home/ubuntu/.hermes/kanban/workspaces/t_c6385001/B2_ACCEPTANCE_MATRIX.json`：稳定验收ID，以及唯一机器权威的默认情景manifest、参数包、参考fixture和数值/资源门。
- `/home/ubuntu/.hermes/kanban/workspaces/t_c6385001/B2_HANDOFF.md`：本文件，父证据读取记录、既有实施路线、独立验证与复现闭合补正。
- `/home/ubuntu/.hermes/kanban/workspaces/t_c6385001/B2_G0_CHANGELOG.md`：限域变更、原件身份来源、不可变域比较方法及Manager待决项。
- `/home/ubuntu/.hermes/kanban/workspaces/t_c6385001/B2_VALIDATION_STATUS_FIXTURES.json`：轻量状态schema examples，不是求解结果或验证证据。

这些文件均作为规划完成交接的顶层artifacts持久保存。后续不要依赖本scratch目录一直存在；通过本卡attachments清单发现真实持久路径，再读取，不猜新的attachment路径。旧B2-1.0.0附件只读保留在原卡，不覆盖、不删除。

权威顺序：Manager明确授权与硬权限 > 本版本合同及矩阵的一致定义 > 本handoff中的实施建议。发现合同/JSON字段或数值冲突必须停止并交Manager修订，不由Engineer自行选较宽条件。Planner文件不是模拟结果，B2 tests/solver/Safety全部尚未执行。

## 2. 原规划实际读取的证据与边界（历史记录，本补正不重做）

### P-B1：独立审核而非当前 Planner 的复跑

实际read_file：
- `/home/ubuntu/.hermes/kanban/workspaces/t_c787a990/SAFETY_REVIEW.md`，全文。
- 同目录`safety-review.json`，全文。
- `/home/ubuntu/.hermes/reports/sludge-material-design-v2/STAGE2B1_FROZEN_CONTRACT.md`，全文。
- 本卡kanban_show中两父卡的完成handoff、审批scope与限制。

定位：Safety报告§1–2，特别是第22–26行的ε/L/Γ/Robin/有限库归一化；§3真实命令；§6第82–88行的预算遥测LOW、审计非完整ODE、audit_only边界；旧合同§2–4、§5、§6、§8。

读回一致：审核提交`d051c0982835dbe54fc4f509f1819661b85de055`；approved=true，approval_scope=research_diagnostic_scope，production_approved=false，required_changes=[]。Stage1批准与提交`2620afe40faaf592fbb42b39e3a6a6a351009ad8`来自任务和B1 Safety明确父门记录；Planner本轮未重新审核Stage1或读取旧worktree。

历史实测仅引用Safety报告：默认B1演示34.947秒/41.285MiB，focused约65秒。不得把它写成B2资源结果。

证据包身份以下均为任务/父审核报告提供的既有记录，Planner没有重新计算hash或展开包：
- 外层`/home/ubuntu/.hermes/kanban/workspaces/t_c787a990/b1-safety-evidence.tar.gz`，父/Manager报告SHA256=`27af9c5a7e0d05e52cc0f557add5dc229989e3566ed4f3fbc55fb438758d8000`。
- 包内`evidence/submitted-source-repro.tar.gz`，父报告SHA256=`4d7875d30e634e325cdeb2536b966470fb8540eb292dc6630aa1bfcfe31a0d8c`。
- 旧合同父报告SHA256=`9d04fb234f2228381fe20f5c248161c58595f000e451986f68c2b2944a26bffd`。

Engineer在使用前必须工具实算并核对，不把这里复制的摘要当新鲜校验。两个旧worktree目录已不存在是Manager提供的事实，本轮没有尝试恢复。主仓库`/home/ubuntu/sludge-brick-first-principles`不修改；本轮没有terminal工具，未执行git show/状态/hash命令，也没有检查或修改仓库内容。

### P-2A：持久附件与具体原文核读

先实际调用kanban_attachments(task_id=t_f456bbd3)，再读取返回的真实路径：
- `.../attachments/t_f456bbd3/MECHANISM_EVIDENCE.md`（全文；§2.1、§3.1–3.2、§4.2重点）。
- `.../attachments/t_f456bbd3/source_registry.json`（全文）。
- `.../attachments/t_f456bbd3/DYNAMIC_MODULE_CONTRACT_DRAFT.md`（全文；它比B2范围广，仅作候选，不继承其多组分/能量/孔关闭模块）。
- `.../attachments/t_f456bbd3/parameter_candidates.csv`（定向搜索S02行、S09成组参数，并read_file第83–95行；非全量重新提取审计）。

父报告的102候选/9unknown、7组提取检查等是父证据，不是Planner重跑或可执行材料参数的认证。本轮不声称重新计数、核对全部数值或取得原曲线。

### S02：输运原文缓存已实际读取

发现路径来源：search_files在Manager报告目录返回，而非猜测。
- `/home/ubuntu/.hermes/reports/sludge-material-design-v2/stage2a-manager/S02-primary.txt`：定向搜索后完整读取第113–154行。
- 定位§4.2–4.4，Table4、Fig10讨论；URL https://www.mdpi.com/1996-1944/14/17/4942 。
- 已核事实：O2气相拟合至500°C；更高温O2平台未充分解释；A600拟合不一致；参数按样品/预处理成组；O2与CO2原试验的非等摩尔差异；0.011 cm²/s是特定样品环境温度模型值。
- B2决定：不执行此数值，不将m=0/1说成来源拟合；d_ref(T/T_ref)^m及共同D为synthetic。

保留必要短证据：“was limited to a temperature range from ambient to 500 °C”。不复制全文或作者联系方式。

### S09：失败缓存被识别，canonical正文成功核读

真实访问顺序：
1. 读取Manager的`S09-Table5-excerpt.md`，看到真实表级数值与WR定义。
2. `primary-2.md`定向搜索没有方法文本；read_file发现它只是WAF/JS挑战，不把HTTP页面或旧缓存文件名当正文。没有执行其中脚本，不保留或传播挑战载荷。
3. web_extract对`https://www.mdpi.com/1996-1073/17/21/5382/htm`实际失败。
4. 改用canonical `https://www.mdpi.com/1996-1073/17/21/5382` 成功获取题名、方法、Eq6–15、结果与表；再read_file工具返回的完整缓存`/home/ubuntu/.hermes/profiles/planner/cache/web/www.mdpi.com-8a465e55c2.md`第397–401等行核读§3.1。

本轮已核事实：波兰厌氧消化污泥；1/2 mm、10±1 mg；50 mL/min；准等温N2预热50 K/min后在873–1273 K各点切O2/CO2；40–60%转化窗口；80/100%O2因为自热剔除；成组E/n/K0原数与父CSV吻合。原式使用分压幂，K0报告mg/(m² s Pa)；非整数氧阶的单位/归一化仍未解决，不能擅改为Pa^n并称作者原值。

B2决定：借用温度比结构，不借用参数值、不把预热颗粒表观速率叫原泥空气砖坯本征速率；theta、K_ref为本合同假设。

保留必要短证据：“Heating to the target temperature was carried out in a nitrogen atmosphere at a heating rate of 50 K/min”。全文缓存不作为交付附件或复现依赖。

### S11：仅方法摘录，无新增图像验证

实际读取`/home/ubuntu/.hermes/reports/sludge-material-design-v2/stage2a-manager/S11-method-excerpt.md`第4–18行：小圆片、干基灰替代、平均升温及峰温保温3 h。来源 https://orbit.dtu.dk/files/418782101/1-s2.0-S2214509525011854-main.pdf 。本轮没有重抓PDF或做SEM像素/液相定量；SSA Raw不是raw sludge，不能提供B2真实Γ、K或供氧边界。

### 引用/验证工具边界

已加载plan、process-quality-modeling、grounded-citations及blocked-page-recovery技能。正文编号沿用实际读取的Manager台账`stage2a-manager/citations.json`（[1]S02、[2]S09、[3]S11），canonical S09为同文献的成功读取位置。

本运行schema没有terminal/execute_code工具，因此没有执行sources.py ledger/引用门、git/hash、独立代数检查或JSON schema脚本；没有安装依赖弥补。文件工具已实际写入并确认字节落盘，JSON获得其真实语法检查结果。数值门、代数验证和复现命令在本文件均为未来要求，不伪造已执行日志。缺少运行工具不阻断这张“仅规划”卡，但Manager可在G0另做标准库契约结构检查；若认为这是实施前必要证据，应先完成该轻量检查，不宣称Planner已跑。

## 3. 决策、未知与残余风险

已定（无需Engineer重复选择）：
- 模块/目录、输入输出格式、字段基准、单一反应、共同D、固定孔隙与几何。
- T_ref=600 K，450–750 K synthetic程序；τ无量纲且跨厚度固定同一t_star。
- K比值指数、d温度幂、恒定h_ref及膜/半格串联，rho按实际L。
- 固定manifest、U0/U1联合假设包、R/W/L/C分组、解析/收敛/审计门。
- 最大局部残余与平均分别输出，null、缺氧、数值失败互不混淆；guard不是材料误差条。
- 不接文献CSV执行、不校准、不做供应商/配方排名。
- 本次Manager已决定：verification_scope仅frozen_suite/audit_only；numerical_validation仅passed_frozen_suite/not_verified_for_custom_case/failed/not_run；默认未绑定为not_run、custom不继承PASS，详见§5.1。

未识别，不得默认事实：
- 原泥+基料+预处理映射到Γ/K_ref/theta/d_ref/m/Bi_ref的联合关系。
- 实际壁芯/表温差、热反馈、恒压供气的热膨胀流。
- 固定孔隙在氧化期间的材料合理性、O2/CO2共用系数的误差。
- 从局部残碳/产气到孔关闭、形变、强度与合规的映射。
- 实际B2耗时/RSS、冻结数值门是否能由最小实现满足。

Manager G0需确认本假设域、预算、本次B2-BIND-001待决方案，并决定未来隔离workspace/branch；不要求用户先做新工厂实验。若要求真实物理温度场/时间/材料评分，则本版本不满足，必须重新分期，而不是由Engineer自行补模块。

残余风险：
- 选择U0/U1包络不代表覆盖现实，屏蔽其他模型形式可能遗漏排名翻转。
- 相同给温下更早反应、降低负荷的好处仍需真实运行，不能把计划中的因果方向预填到报告。
- 网格代表验证与screening_guard不是全域严格误差界，接近阈值必须unresolved。
- 守恒可被协同重写的轨迹/通量满足，审计不是真实性签名或完整ODE认证。
- B1原CSV有CRLF/LF历史规范化；复现必须区别字节身份与数值相同。
- 本补正无terminal，未重跑Manager结构脚本或逐值比较脚本；具体CLI证据加载/覆盖绑定尚未获Manager决定及真实实现验证。

## 4. Task breakdown 与 dependencies（原有路线，不建卡）

执行顺序：G0 Manager → E1契约/fixture → E2系数和保守积分 → E3独立参考/回归 → E4导出/筛选 → E5路径资源/复现 → G1 Engineer交接 → G2独立Safety → Manager决定下一研究段。

以下每个动作按短步骤推进；每个实现单元先写失败测试、真实运行得到失败，再最小实现、重跑与自查。下面的预期均为验收目标，不是Planner实测输出。

### E1. 输入与契约先行

仅未来新worktree内`experiments/material_dynamics_v2b2/`：
- Create `CONTRACT.md`、`B2_ACCEPTANCE_MATRIX.json`快照、`README.md`、`__init__.py`。
- Create `model.py`：严格schema/domain、不可变Scenario数据、符号/单位定义。
- Create `scenarios.py`：将矩阵的命名program/bundle/run展开为完整输入；不接受文献CSV自动赋值。
- Create `tests/test_contract.py`、`tests/test_input_paths.py`。

动作：先验证非法数/重复key/温度knot失败；再实现load/validate；再验证默认展开与W03示例一致。记录manifest中全部默认case与输入内容身份；不能只按scenario_id授予验证scope。

### E2. 给温与反应—输运

- Create `temperature.py`：piecewise-linear T和K/d系数，纯函数。
- Create `solver.py`：固定FV/SSPRK2、a_D、b、g、finite库、阶段通量/反应账本、保正/CFL与资源停止。
- Create `tests/test_coefficients.py`、`tests/test_conservation.py`。

动作：先测knot/hold/cooling/ell；再测手工非均匀双向finite一步；再做K=0不变与sealed/finite；最后运行C04给温循环。不得写能量、压力、几何演化或气体膨胀流接口来扩大范围。

### E3. 指名数值证据

- Create `verification.py`、`run_tests.py`、`tests/test_references.py`、`tests/test_refinement.py`、`tests/test_b1_regression.py`。
- 解析参考应在测试/审核独立逻辑，不复用生产temperature/solver/diagnostics作为真值。

动作：先独立推导/验证uniform sealed参考，再diffusion-time参考；再R01–R04回归；最后仅W03/L02/C03空间/时间收敛。预算不足停止并留原始partial，不扩大网格或重跑旧full suite。B1提取内容只放验证副本/持久复现bundle，禁止恢复旧分支worktree。

### E4. 诊断、筛选、导出与浅色SVG

- Create `diagnostics.py`、`screening.py`、`exports.py`、`plots.py`、`report.py`、`audit.py`。
- Create `tests/test_diagnostics.py`、`tests/test_export_audit.py`。

动作：先测均值/局部/null/缺氧语义；再实现库存与时序；再按固定pairs做U0/U1包络；最后由CSV生成静态SVG与报告。拒绝从随机/虚构数组作图。Guard临界区与包络翻转保留unresolved。

### E5. CLI、预算、独立路径与复现包

- Create `run.py`、`resources.py`、`build_repro.py`、`tests/test_cli_resources.py`、`validation/README.md`。
- 仅创建新输出目标；不得覆盖既有目录或审计修改原研究产物。

动作：真实测试正常预算成功；真实短预算timeout；非法配置/路径/已有输出；补齐active/ceiling在所有失败路径的遥测；再建package并新副本复跑。

任何源码本地提交或worktree建立只在Manager未来实施卡授权后；无push/merge/deploy，不能把此handoff当现在创建branch的授权。

## 5. 内部/API/CLI接口及补正边界

以下为未来接口规范，不是已存在可调用代码；原接口保留，唯一增量--verification及其文件绑定须先由Manager决定（§5.1）：
- `model.load_scenario(path) -> Scenario`：只读受限本地JSON，路径/schema/domain验证失败给固定安全错误。
- `scenarios.expand_frozen_manifest(matrix) -> list[Scenario]`：只接受受审矩阵格式，输出完整确定性输入。
- `temperature.evaluate(scenario, tau) -> Coefficients`：含T_K,K,d,a_D,b；g依N在求解器边界层由这些量计算。
- `solver.integrate(scenario, budget) -> RunResult`：含原始轨迹、分段通量账本、实际步数和execution_status；不伪造材料结论。
- `diagnostics.compute(scenario, raw_result) -> Diagnostics`：库存、阈值、包围区间、not_modelled。
- `screening.evaluate(frozen_manifest, diagnostics, verification) -> ScreeningResult`：按manifest的配对及合同guard；自定义audit_only不得正式筛选。
- `condition_key`按uncertainty_pairs首个ID冻结（W03/W09共用W03），bundle另列；R/L/C仅diagnostic_only，不从单包判包络候选。
- `audit.audit_exports(run_directory) -> AuditResult`：只读原始输入/状态/积分通量，容差来自受审常量，不能复用结果自报pass。

在未来worktree内、先cd本模块后运行的建议顺序（现在未运行；B2-BIND-001为pending_manager_decision）：

```text
python3 -B run_tests.py --out validation/tests001 --budget-seconds 300
python3 -B run.py --suite frozen --out validation/demo001 --budget-seconds 180 --verification validation/tests001/verification.json
python3 -B audit.py validation/demo001
python3 -B run.py --suite frozen --out validation/timeout001 --budget-seconds 0.000001
python3 -B build_repro.py --run validation/demo001 --tests validation/tests001 --out validation/b2-repro001.tar.gz
```

CLI冻结细则（本次具体证据加载增量见§5.1待决项）：
- `run.py --suite frozen`运行全部默认清单，导出/报告/库存审计包含于180s；独立解析/收敛放run_tests的300s。自定义单例为`--config inputs/custom001.json`，与--suite互斥，scope只能audit_only。
- `run_tests.py`输出只到新--out，不像旧B1测试静默改原validation；重复输出拒绝。
- `audit.py`默认只读，JSON结果写stdout，拒绝修改被审目录；run.py自己的audit.json不能替代这一独立重算。
- 正常完成exit0；数值/审计失败exit1；非法输入/路径exit2；timeout/资源限制exit3。
- 安全拒绝时不得创建不安全输出目录；安全失败JSON可写stdout/stderr，由测试harness保存到审核员自己的目录。
- `--budget-seconds`有效时所有路径都记实际active及ceiling；参数本身非法不可回显原值，active=null并给budget_parse_rejected，ceiling仍180。这不是把非法值默认成180。
- 使用单worker/thread；不安装依赖。实际环境指令包括Python版本、OS/架构、编码/locale、cwd、线程环境约束、PYTHONDONTWRITEBYTECODE=1，禁止导出完整env或凭据。

### 5.1 验证状态与跨阶段证据绑定

A. Manager已决定的状态契约（不是待选API）

- `verification_scope`只允许`frozen_suite`或`audit_only`，含义为拟适用检查范围，不是通过结果。
- `numerical_validation`只允许`passed_frozen_suite`、`not_verified_for_custom_case`、`failed`、`not_run`；`audit_only`不是该字段值。
- 默认情景在同一源码、完整展开输入内容和实际验证覆盖尚未绑定前为`frozen_suite + not_run`；integrated或库存audit通过不足以升级。
- 当前integrated、当前raw审计通过、适用指名数值门真实通过且身份/覆盖全部绑定后，才可为`frozen_suite + passed_frozen_suite`。实际适用数值/审计门失败为failed；缺失/未跑/失配/覆盖不全为not_run。partial_timeout/resource_limit且未发现数值失败为not_run，execution_status照实保留。预期拒绝的负向测试通过不等于模型实际失败，必须区分test expectation与运行状态。
- 合法custom为`audit_only + not_verified_for_custom_case`，即使名字仍为W03或audit通过也不得继承默认PASS；custom的执行失败、未运行与逐门结果另外记录，不隐藏。所有material_mapping/mapping_status为unknown_real_material。
- W配对未绑定不得出正式sampled候选或正式sampled未达结论：缺覆盖为unresolved_in_assumption_envelope，实际失败为unknown_numerical；氧预算必要排除不是数值通过，R/L/C仍diagnostic_only。数值通过也不能代替G0或独立Safety批准。

B. 已验证的原文缺口

旧B2-1.0.0合同§5.2/§7.2枚举冲突已由Manager脚本复现。旧合同§9（原行284–294）列了manifest/输入hash/verification文件；旧handoff§5（原行164–177）给screening.evaluate的verification参数及demo→tests命令，§7（原行208–222）要求归档，但没有从tests产物到demo报告的显式消费者、身份匹配规则与重算时点。合理结论：有组件与证据原则，但缺可执行闭环；不声称旧三件已足够。

C. 唯一最小建议：B2-BIND-001（pending_manager_decision）

只加run.py可选`--verification <module-relative verification.json>`，run_tests原CLI不变。先tests后demo，避免为了补绑定自动跑第二次demo或覆盖旧报告。Manager应明确接受/拒绝本整个方案；未决定时不派实现，不让Engineer临时选核心API。本段文件字段与矩阵evidence_binding_proposal一致，均为建议，不是本卡已存在的运行产物。

1. 同一未来源码快照先运行300s focused/reference/convergence。run_tests保存完整默认展开输入清单（登记不是求解）、实际执行的参考/收敛变体输入、原始结果、命令/退出码与逐门coverage；不预写“默认全部passed”。没有执行的门写not_run。
2. 再运行原180s demo，传入上述verification文件。加载和核验也从demo启动就计时，包含当前积分、导出、raw库存审计、证据合并、筛选、报告/SVG；不增设额外finalize预算。该参数缺省时依然可输出诊断，但默认numerical_validation必须not_run。
3. 在输出正式报告前才合并当前审计与focused证据。先建立原始结果身份，再判定状态，最后生成summary/screening/报告/SVG；不先写PASS再希望tests补齐。任一W配对资格必须由同一次绑定中两个成员的真实结果与原guard共同决定，不由fixture的expected字段决定。
4. 如果已先跑无证据demo，它永久保留未绑定诊断身份。后来的tests不能修改该目录或使旧报告自行升级；本建议选择tests先行，不增加第二次demo或独立finalize接口。需要另跑/改源码而现有预算不足则停止交Manager，不自动重试。

D. 文件/身份建议（pending_manager_decision，同B2-BIND-001）

`validation/tests001/verification.json`建议固定字段：kind=`executed_focused_evidence`，contract_version，source_commit，source_files，contract_artifacts，frozen_inputs，executed_inputs，coverage，command，exit_code，resources_path。

- source_commit是实际运行源码提交，不能只写B1基线或沿用旧提交字符串。source_files为当前模块实际参与执行的源码/测试/独立参考脚本完整清单，每项`{path, sha256}`，按path排序；全部模块Python源码及本地导入支持文件均纳入，排除生成输出和缓存。接收者重新枚举对应范围、读实际字节实算核对，防止同commit下dirty/untracked代码漏报。tests结束与demo开始/报告前均检查源码未变；不通过修改manifest自报hash来“修复”失配。
- contract_artifacts为本版三份合同/矩阵/handoff快照的`{path, sha256}`；模块中CONTRACT.md可保留原合同字节。版本和实算字节都须相符，不能把旧B2-1.0.0 pass迁移到本版。source_files与contract_artifacts不包含它们要写出的verification/manifest，避免自哈希循环。
- frozen_inputs为本版全部完整展开默认输入的`{scenario_id, path, sha256}`；executed_inputs为真正求解的输入/参考测试配置清单，不用只记录改变项。将完整严格解析输入以`json.dumps(full_strict_input, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)`加LF、UTF-8持久化，实算这些字节的SHA256。canonical化只固定键序/空白，不删字段、不转换数值类型，不把schema版本排除在身份外。消费者同样展开、序列化、核对实际文件，不能只信输入自报hash。数值等价不等于字节身份相同。
- coverage每行固定`{criterion_id, target_input_sha256, executed_input_sha256s, coverage_kind, result, evidence_files}`。result为逐门`passed/failed/not_run`，不是numerical_validation枚举；evidence_files每项`{path, sha256}`，指实际原始参考、轨迹、误差/命令日志，不只有一个pass布尔值。逐门失败优先于旧pass；没有证据就是not_run。
- coverage_kind仅`per_case`、`representative_frozen_domain`、`suite_semantics`。沿用既有B2-NUM-001–008门及指名域：R哨兵回归只覆盖R01–R04直接比较；A-SEALED/A-DIFF及W03/L02/C03证明对应机制/代表域，不冒称对每个W都做了独立参考或收敛。默认整套获得的是冻结代表覆盖加各自当前数据审计；不增case、不自动为custom授权。当前demo对全部默认case完成B2-NUM-002的逐例库存/状态核验，并提供C04、R04/C03事件等当前证据；与focused中原有参考/回归/收敛/语义控制共同构成适用覆盖，缺任何必要部分均不得passed。所有24验收门仍保留，数值标签不把GOV/Safety未执行写通过。
- final demo的manifest增加`focused_evidence`（path、sha256）、source_commit、source_files、contract_artifacts、expanded_inputs、raw_result_files、current_audit、coverage、binding_status、binding_reason。expanded_inputs同上述输入结构；raw_result_files与current_audit引用当前实际原始CSV与audit.json的实算字节；不哈希最终manifest自身。demo的verification.json保存这次绑定及逐情景结果；summary.json、screening.csv、报告/SVG只消费这次结果，不再各自从scenario_id推PASS。报告引用manifest与focused证据身份，逐结论能回到配对输入和raw数据；没有真实证据时引用为空并解释，而非编造hash。
- binding_status仅`bound/missing/mismatch/incomplete/failed`，是绑定诊断，不是第三种numerical_validation。文件缺省或覆盖未完成→missing/incomplete及not_run；源码/输入/合同/文件hash失配→mismatch及not_run；已证实当前适用数值/审计失败→failed及numerical_validation=failed。声明bound仍须真实逐门通过才能升级。custom永不因此升级。
- 所有新路径字段只在受控CLI及生成manifest/verification出现，不加入被禁止含路径的scenario输入。引用是模块相对普通文件路径；禁绝对路径、..越界、符号链接、外部URL。resources_path指同次实际resources.json；上述证据列表必须包含其文件身份。显式传入畸形/非法路径/schema example证据按输入拒绝exit2；实算身份失配拒绝绑定并安全报告exit1，保持not_run，不触发正式筛选。实际数值/审计失败exit1；timeout/resource限额仍exit3。安全失败不回显原始内容，不覆盖tests/demo。
- `B2_VALIDATION_STATUS_FIXTURES.json`的kind=`schema_examples_not_solver_results`必须被运行证据加载器拒绝。示例中的条件是假设前提，不是实测结果。不存在真实证据不得以占位hash、空文件或旧artifact的pass填充。
- 复现包保持模块相对布局，包含被引用的tests/demo、源码/合同与全部证据；不能只有外部scratch链接。build_repro应核对--run与--tests身份为报告实际消费的同一组，路径名相同但字节变化也拒绝。保持20MiB上限及原有离线新副本复现要求。字节hash核验不是完整ODE真实性或独立Safety签名。

E. 不变的执行/审批界限

180/300/600/900秒、单worker/thread、40额外求解调用等原上限一律不变。证据读取/合并不是另收费或另给时间的阶段；未通过、不足预算、需新case或扩科学域均停止报告。Manager对B2-BIND-001的明确决定是G0残余事项；本卡交接仅表示Planner补正已交付。

## 6. Safety独立验收方法

Safety必须由Manager另行指派真实独立角色，不由Engineer自签。此卡只列路线，不创建/重建审核图。

1. 定位：读取Manager冻结记录、B1明确批准scope和新的Engineer提交/manifest，不只看父卡done。核对所有changed paths均在新B2目录。
2. 复现包preflight：实际hash、成员路径/文件类型/体积检查；拒绝绝对路径、..、链接、设备或特殊文件。审核副本与源码blob比较，CRLF/LF差异只能按既有说明单独记录，不静默放宽其他字节差异。
3. 冷读物理：独立重推ε、L_ref/ell、Γ、rho，验证固定c_star/非恒压承诺及K(T)、d(T)的假设来源。发现真实材料/能量/压力越权直接阻断。
4. 独立数值：自己构造A-SEALED H积分与闭式，A-DIFF cell-average级数及T插值；不导入Engineer的solver/temperature/verification/diagnostics做oracle。按冻结门真实运行，并保存reference数组/误差，而不只存PASS。
5. 真实运行默认suite与指名收敛/B1哨兵，核查null、局部/平均、氧预算和数值失败路径。代表收敛不代表自定义点全域验证。
6. 独立导出审计：从profiles边界、初始输入、flux_intervals重算C/O/名义质量、finite交换、事件与图形坐标；不读预写residual作真值；固定1e-6而非artifact tolerance。
7. 篡改测试：仅在自己创建的副本改变库存/通量/空事件/局部字段/非法数/假模型声明/多层容差，保存真实退出码。正常对照无audit.json也应可进行库存一致性审计；不承诺协同重写检测。
8. 路径/资源：真实成功与超短预算、覆盖拒绝/符号链接/越界/非普通输入；核读active与ceiling不同含义。峰值RSS和墙钟需真实测量，不能引用B1值充数。
9. 科学输出：检查每条条件方向有真实paired结果，未知真实材料映射、边界及U0/U1覆盖限额都在正文；缺结果、失败或排序翻转不能藏掉。
10. Verdict：结构化approved、approval_scope、production_approved=false、required_changes、未覆盖域、证据路径。只有全部适用blocking门通过才能研究scope PASS；修复项给Engineer，不用review-required block代替正式review。外部授权/工具访问等真正阻塞才block。

如Safety需要SVG像素/CJK可读性，须实际render并声明环境；本合同要求结构+数据对应，不虚称已有GUI验证。

## 7. 复现闭合与归档清单

Engineer包必须包括：
- 受审的B2全部源码、固定版本合同/矩阵、README和环境/命令指令。
- 测试入口/fixture/参考代码、展开输入及manifest；不能只保留defaults patch。
- 真实原始timeseries/profiles/flux_intervals、summary/screening、audit/verification/test_results/resources、报告和SVG。
- 回归/解析/收敛的原始输入与输出、CLI失败路径日志、安全错误码和实际资源记录。
- 真实源码提交、文件hash清单、archive hash/成员/大小检查结果；摘要不得包含凭据/PII。

Safety包必须包括：
- 原提交复现包或清楚的持久附件引用及核验hash。
- 自己编写/使用的独立审核脚本、源定位、独立参考数值与raw replay输出。
- 实际命令/退出码、攻击输入的安全fixture、正向对照、收敛/事件/SVG对应检查、资源日志、最终机器verdict及中文报告。

任何复跑必要文件都须进入本地commit或声明的持久包；不能只写临时`/tmp`、profile缓存或旧scratch路径。原文全文/WAF响应/不相关数据不打包；只保留必要短证据与公开来源。包不靠联网重新下载文件才算复现；源码/输入/测试/原始结果须离线闭合。新的包hash必须由实际工具计算，不手填本计划占位。

归档前在新副本离线复跑，并区分：确定性CSV/模型结果应一致；墙钟/RSS/时间戳为新测量，不要求字节相同。复现包安全不等于原材料科学标定或源文献可信度认证。

## 8. 原规划 Verification plan 与交付自查记录（历史，不是本次复跑）

本轮已实际做的工作：
- kanban_show读取当前卡及父handoff；attachments发现并读取Stage2A真实持久文件。
- 定向核读B1合同/审核与S02/S09/S11方法边界；对WAF/失败请求使用有界替代，S09 canonical成功。
- 通过write_file真实写入合同及JSON矩阵；JSON文件工具返回lint.status=ok，Markdown工具无专用linter。
- 合同逐项包含目标/non-goals、状态/参数/单位、方程/边界、温度、假设/未知、场景/数值/资源/人工门；矩阵每个criterion明确id/requirement/evidence_expected/verification_method/blocking/scope。

完成前实际使用search_files做轻量结构检查：默认manifest有22个scenario_id；criterion的id、requirement、evidence_expected、verification_method、blocking各有24处匹配，scope逐项列出并核读；工作区文件发现结果为要求的三个交付物。这不是JSON Schema全量验证或唯一性自动证明，后续仍需Manager独立检查展开/参数域。交叉审查只检查交付规格与引用一致性，不将它改名为独立Safety、运行测试或材料验证。没有运行B2、B1旧全套、安装、认证、仓库更改或任何生产动作。

Manager G0推荐额外轻量标准库检查：JSON解析、criterion必需字段/唯一ID、program/bundle/run引用与输入展开、参数域和knot端点、W/L配对、数值门同合同、artifact存在；实际执行后记录结果。该检查不应变成长期现场数据前提或大规模研究。

### 8.1 本次补正t_c6385001的实际工作与待核查

已验证事实：完整读取原三附件及Manager的validate_g0.py、g0-structure-check.json、g0-expanded-inputs.json；后者分段读完，无扩大历史恢复。Manager旧报告记录37项通过、唯一失败custom_numerical_validation_enum_consistent，gate_result=needs_contract_correction；这是旧B2-1.0.0的结构核验而非求解验证。本次无terminal/execute_code，未重跑该脚本、未实算新hash、未执行逐值diff/状态逻辑或B2求解。本次仅加载plan、process-quality-modeling技能，无网络/文献复审。

本补正用write_file真实保存三件修订文档及changelog/fixture，JSON经文件工具语法检查；最终轻量搜索定位及工具结果由本卡交接metadata列示。Manager应在自己的安全目录使用原脚本的副本，改ROOT到本卡实际附件、OUT到新报告目录、版本断言到B2-1.0.1，原脚本/旧报告不覆盖；补检查完整枚举和状态fixture，不能只检查custom枚举包含关系。逐值不可变比较规则及明确变更allowlist见B2_G0_CHANGELOG.md；只允许schema版本与列明补正文本差异，不凭Planner声明认定已通过。

## 9. 人工审批与停工/回滚

- 当前：Planner补正文件齐备后供Manager审阅；无需新卡、不自动实施，补正done不等于G0批准。
- Manager接受B2-1.0.1并明确决定B2-BIND-001后：确认新worktree/branch与受审B1基线、一次预算，再派Engineer。Engineer不得改变S02/S09证据含义或添加孔关闭/能量模块。
- Engineer完成后：独立Safety研究scope审核；Manager可允许下一段研究，但本轮production_approved始终false。
- 涉及费用、OCI变更、外发/公开发布、部署、删除、工业/训练/金融控制：必须另行人工审批，当前硬权限未开放。
- 不满足数值/资源门：停止输出正式筛选，保留unknown/partial及证据，交Manager决定是否修订；不无限重试、不升配。
- 无部署，因此当前无实际回滚；后续只停止使用隔离模块并保留证据。若需撤销代码由Manager批准revert，不删除B1/Stage1、不改写历史pending或旧分支。
