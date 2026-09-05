# B2 G0 小范围补正变更日志

交付版本：B2-1.0.1；原版本：B2-1.0.0。
当前卡：t_c6385001；原规划卡：t_d7507b62。
结论：已将验证范围与数值结果分离，补充默认未绑定不得通过、custom不可继承PASS的明确规则与schema examples；给出唯一的tests先行、demo显式消费证据建议B2-BIND-001，状态为pending_manager_decision。本次是Planner文档交付，不是G0、Engineer实现、数值验证或Safety批准。

implementation_authorized=false；production_approved=false。已审B1基线d051c0982835dbe54fc4f509f1819661b85de055仅保留父记录，不在本卡重验git或改动。旧B1批准不放行B2。

## 1. 本次依据：已验证事实、合理推断、待验证项

已完整read_file以下限定文件，无网络抓取、文献复审或扩大历史恢复：
- /home/ubuntu/.hermes/kanban/attachments/t_d7507b62/B2_CONTRACT.md
- /home/ubuntu/.hermes/kanban/attachments/t_d7507b62/B2_ACCEPTANCE_MATRIX.json
- /home/ubuntu/.hermes/kanban/attachments/t_d7507b62/B2_HANDOFF.md
- /home/ubuntu/.hermes/reports/sludge-material-design-v2/b2-manager/validate_g0.py
- /home/ubuntu/.hermes/reports/sludge-material-design-v2/b2-manager/g0-structure-check.json
- /home/ubuntu/.hermes/reports/sludge-material-design-v2/b2-manager/g0-expanded-inputs.json（分段读完）

已验证事实：Manager旧报告记录22情景、24验收ID、37项结构检查通过，唯一失败custom_numerical_validation_enum_consistent；旧报告gate_result=needs_contract_correction。任务提供脚本实际exit1；本卡通过读取脚本及报告核对原因，没有再次执行脚本。旧合同§5.2原行129、JSON input_domain原行96–97、B2-NUM-008原行376–381要求custom not_verified_for_custom_case/audit_only；旧合同§7.2原行197却把audit_only放入numerical_validation枚举。

已核身份来源：下列SHA256原样引用Manager旧g0-structure-check.json的artifact_identity，非Planner本次实算，亦非新文件hash：
- B2_CONTRACT.md：a976cf71cee715bd92cc8fe11f8a531105d222d02c9dc7b4949bfae9797bdfd2
- B2_ACCEPTANCE_MATRIX.json：c530b2ccdf4dcc2d18981eb63d9394441588281b07bbd880192e7ed44da159b1
- B2_HANDOFF.md：21885bce43ee9669cd9fca53e9f7ad97ac9b800828f4011b699ebc3e257cc567

合理推断：旧合同§9原行284–294与旧handoff§5原行164–177、§7原行208–222提供了组件/文件及归档要求，但没有定义demo从tests读取证据的接口和报告状态合并时点。因此不能声称旧三件已形成跨阶段闭环。

待验证/决定：Manager对本版做新的结构检查、不可变域逐值比较与状态fixture检查，并明确决定B2-BIND-001。B2真实数值、参考、收敛、资源消耗、独立Safety仍未执行；材料映射仍未知。

## 2. Manager已经决定的项（本补正落实，不重新选方案）

- verification_scope只允许frozen_suite、audit_only，表示拟适用检查范围，不代表通过。
- numerical_validation只允许passed_frozen_suite、not_verified_for_custom_case、failed、not_run。audit_only不是其值。
- 默认未将同一实际源码、本版完整展开输入内容和真实验证覆盖绑定之前为not_run；积分或库存audit成功不等于passed_frozen_suite。
- 默认实际适用数值/审计门失败为failed，未执行/缺失/失配不能冒充通过；partial/resource状态另外如实记录。
- 合法custom为audit_only + not_verified_for_custom_case，不能凭相同scenario_id或旧PASS继承。custom的执行失败/未运行仍保留execution_status与逐门结果，不被custom标签隐藏。
- 全部material_mapping/mapping_status仍unknown_real_material；科学scope仍synthetic_prescribed_temperature_equimolar。
- 默认W没有已绑定覆盖时不允许正式sampled候选或正式sampled未达结论；不放宽原配对、guard或任何数值门。

对应位置：修订合同§5.2、§7.2；修订矩阵validation_status_contract、input_domain、B2-NUM-008；修订handoff§5.1 A。状态fixture仅为条件性schema examples，不是新增模拟case。

## 3. 唯一待决项：B2-BIND-001（pending_manager_decision）

建议在未来run.py加可选--verification，保持run_tests原CLI；先300s focused/reference/convergence生成真实证据，再180s demo读取并核验，合并本次raw审计后才出筛选和报告。默认不带证据的demo可运行诊断，但标签not_run、无正式sampled候选。已生成未绑定demo不被后来的tests改写或自动升级。

具体CLI/文件字段、来源身份与输入canonical字节规则、逐门coverage、代表域和逐例证据区别、受控路径/失败语义、归档闭合均定义于handoff§5.1 C–E和矩阵evidence_binding_proposal；合同§9.1交叉引用。不是让Engineer临时决定API，也未在本卡实现CLI。Manager应明确接受/拒绝整套建议；在其决定前不得以本卡完成当作G0放行。

预算不变：证据读取/核验、当前audit、状态合并、筛选/报告仍包含在原demo180s，不额外设finalize预算；focused300s、独立Safety600s、每角色累计900s等原上限不变。不增加默认case、额外求解或自动第二次demo；预算不足/源码改变需重验时停止并报Manager。

该绑定只是来源/输入/覆盖链，不是任意协同篡改检测、完整ODE真实性证明、材料标定或Safety独立批准。

## 4. Only diff：逐文件允许变化清单

旧附件仅作为只读输入；所有write_file/patch均指向本任务scratch，未覆盖原文件。修订保留原科学/历史正文，不对历史“本轮已验证”重新背书：新增版本范围说明，明确原规划记录与本次补正分开。

### B2_CONTRACT.md

允许变化：
- 顶部版本/任务身份更新为B2-1.0.1/t_c6385001，保留原卡引用；新增补正范围和历史证据限定段。
- §5.2将不精确的matrix.json文件名落实为B2_ACCEPTANCE_MATRIX.json；原custom标签保留，并补verification_scope、默认not_run及失败不冒通过的说明。
- §5.3仅schema_version升级，示例W03所有物理/数值字段不变。
- §7.2把旧numerical_validation行替换为合法枚举，新增独立verification_scope行及证据绑定/失败/custom/fixture规则；事件和其他原状态规范不改。
- §9 screening.csv说明明确分别输出verification_scope与numerical_validation；新增§9.1待决绑定建议；§11增加Manager需决定B2-BIND-001。
- 其他公式、参数域、温度、来源、数值门、资源/审批边界保持原文。只允许上述补正，不以“格式化”为由静默改科学含义。

### B2_ACCEPTANCE_MATRIX.json

JSON key/path allowlist（其他路径应严格逐值相同）：
- $.schema_version、$.contract_version、$.task_id；新增$.original_planning_task_id。
- 新增$.changelog_document、$.validation_status_fixture_document。
- 新增$.validation_status_contract（Manager已决定字段规则）。
- 新增$.evidence_binding_proposal（仅pending_manager_decision建议）。
- $.scenario_manifest.defaults.schema_version：只升级版本；其余defaults及整个programs/bundles/runs/所有pairs等不变。
- $.fixed_numerical_gates.tolerance_source：仅版本文字B2-1.0.0→B2-1.0.1；所有实际容差及策略不变。
- $.screening_output_required_fields：仅在numerical_validation前增加verification_scope，既有字段及顺序不变。
- $.criteria中id=B2-GOV-001的requirement：仅版本文字升级。
- $.criteria中id=B2-NUM-008的requirement、evidence_expected、verification_method：细化状态与实际证据绑定；id、blocking、scope不变，不新增验收ID、不改数值门。
- input_domain（包括custom标签）、units、evidence_policy、reference_fixtures、resource_limits、screening_policy原值不变。

### B2_HANDOFF.md

允许变化：
- 顶部版本/当前卡/无授权声明、历史记录限定；§1更新为本卡五文件与持久化发现规则。
- §2/§8标题明确原规划历史证据，原证据/历史实测记录保留；新增§8.1仅记本次限定读取和工具能力边界。
- §3增加Manager已决定状态项、待决B2-BIND-001与未重跑限制；G0说明补该决定。
- §4标题注明原有路线，E1–E5内容保留，不重新分解或建卡。
- §5标题/说明区分原接口与待决增量；CLI示意改tests先行，demo增加--verification；新增§5.1 A–E唯一状态/绑定建议。原预算及退出码不放宽。
- §9升级待接受版本，并明确B2-BIND-001由Manager决定、done不等于G0。

### 新增B2_VALIDATION_STATUS_FIXTURES.json

- 顶层kind=schema_examples_not_solver_results、executed=false、usable_as_runtime_verification_evidence=false；actual_numerical_validation=not_run，真实身份为null、证据为空。
- 条件性例子覆盖默认未跑、demo audit不足、仅真实绑定后可passed、同名custom不能继承、旧身份失配、实际失败压过旧PASS、旧audit_only错误枚举拒绝。
- expected仅是schema期望，不填求解轨迹/误差/hash，不把条件性passed_frozen_suite当真实测试结果；不进入scenario_manifest或reference_fixtures。

### 新增本日志

仅记录上述变更、依据、允许diff、工具验证边界与Manager下一步，不修改主工程/B1/Stage1/Hermes配置/服务。

## 5. 不可变域与Manager逐值核验方法（尚未执行）

1. 从本卡kanban_attachments返回的实际持久路径读取新五件；对旧三件重新实算hash，与§1的旧Manager记录比较。不得只信文件名或本日志。新文件hash由Manager工具实算，本Planner不编造。
2. 严格解析新旧JSON（拒重复key和NaN/Inf），比较原criteria的全部id及顺序、blocking/scope；须仍为Manager原报告中的24个稳定ID。除B2-GOV-001版本文字、B2-NUM-008指定文本字段外，其余criterion对象逐值一致。
3. 深比较scenario_manifest。只允许defaults.schema_version升级；全部defaults其余值、programs/bundles/runs及配对列表、收敛case等必须一致。按原validate_g0.py的展开规则重新展开本版22输入，对Manager原g0-expanded-inputs.json逐个比较：仅schema_version允许变化，不删除/归一化其他字段。W03完整展开须等于新合同§5.3输入例。此版本比较豁免不适用于运行证据继承：运行时新版本仍需新身份链。
4. 深比较input_domain、units、reference_fixtures、resource_limits、screening_policy、evidence_policy；fixed_numerical_gates只忽略已列版本文字，不忽略任何数值/公式/布尔策略。screening字段只允许新增verification_scope。对JSON剩余路径采用§4 allowlist，意外差异立即停止，不自动修参数。
5. 对Markdown做新旧文本diff，以§4允许段落核查；重点要求合同§2–4、§5.1、§6、§7.1/7.3/7.4、§8、§10及Sources科学内容不变。原三件持久附件不能被更新。
6. 原Manager脚本已硬编码ROOT=原卡附件（行10）、OUT=脚本父目录（行11）、B2-1.0.0版本断言（行40）。应由Manager在自己的安全新目录保存副本：ROOT指本卡实际附件，OUT指新报告目录，版本断言改B2-1.0.1；其他原检查保留。不要直接在旧脚本上跑并覆盖旧报告，也不要把旧版本断言失败当成本版枚举失败。Planner未修改此脚本。
7. 原脚本只检查custom值是否在合同枚举内（原行109–113）；应补精确集合检查：scope恰为frozen_suite/audit_only，numerical_validation恰为passed_frozen_suite/not_verified_for_custom_case/failed/not_run，audit_only不得在后者。同时核对JSON、合同及handoff。
8. 对fixture检查顶层标记、实际证据为空、expected合法（错误枚举负例必须拒绝），核查默认not_run、条件性bound才passed、custom不继承及失败语义。没有执行状态机就只能叫schema检查；不能因为fixture里有expected passed而生成B2数值PASS。
9. 记录新结构报告、真实退出码/逐值比较结果与hash，再明确G0决定及B2-BIND-001决定。结构通过仍不是求解门通过。只有未来真正运行后才能填原B2数值/审计/资源门，独立Safety另执行。

## 6. 本次实际验证与未执行清单

已执行：
- kanban_show读取当前卡、父handoff与约束；限定六文件全文read_file。
- write_file确认三修订件与状态fixture落盘；矩阵和fixture返回lint.status=ok；后续矩阵增加verification_scope字段的patch再次返回lint.status=ok。Markdown无专用linter，不声称Markdown语义自动验证。
- search_files实际检索：新矩阵默认run行匹配22；24条criterion ID逐条列出；三件版本及合同独立scope/numerical_validation枚举、pending_manager_decision位置已读回。计数搜索不等于完整JSON Schema、唯一性或逐值diff证明。

未执行：Manager脚本复跑、独立JSON Schema/状态机/逐值diff程序、新旧hash实算、git命令、代数/材料数值/参考/收敛、B2实现、独立Safety、B1复跑、图形渲染。没有安装依赖、访问凭据/网络、改模型provider、创建收费资源/OCI、部署/push/merge/删除或工业/训练/金融控制。

本卡工具集中没有terminal/execute_code；任务已明确允许用可核验文件差异与fixture交接Manager实测，因此这不阻断规划补正交付，但不得把“保存了规则”改称“运行规则已通过”。

## 7. 交接、依赖与回滚

交接产物为B2_CONTRACT.md、B2_ACCEPTANCE_MATRIX.json、B2_HANDOFF.md、B2_G0_CHANGELOG.md、B2_VALIDATION_STATUS_FIXTURES.json，使用kanban_complete顶层artifacts持久化；之后通过attachments读回真实路径。未建立Engineer/Safety卡，也不要求本卡额外同卡review来代替Manager G0。

依赖：Manager新结构/逐值核验与B2-BIND-001明确决定 → 另行授权隔离实施 → 原数值/资源门真实执行 → 独立Safety。完成本卡只完成文档补正，implementation_authorized与production_approved仍false。

残余风险：绑定方案尚未批准/实现；数值门与预算可达性未验证；真实材料映射、能量/压力及其它研究边界仍未识别。本次无生产部署需回滚；文档若被拒，保留原附件及本版证据，交Manager修订，不删除/覆盖历史，不扩大科学或费用范围。
