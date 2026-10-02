# P48：生产采样、单位、湿度输入与嵌套分区接口

P48 C/F/G/H生产能力已additive集成（2026-10-02T07:20:42.461752+00:00）：C原生面/完整能量采样及普通CLI/baseline writer接线静态，根采样0、缺合同直接报错，P47逐相保留；F原JSON/CSV单位CLI真实1调用rc0/回收，0.043822s/CPU0.035008s、293715B<30s/512KiB，3来源12条件23观测原manifest/conditions/CSV全保留，12缺总压分压仍null，admissionfalse、0L。P38先原mapper再附视图但wrapper未执行；G复用既有reader去重复通用校验，RH/Psat未知null仅文档，API/CLI未调用；H实际保存fine面/rebin生产脚本已合，旧固定P44一次0.011271s/38862B/13格提案沿用，不重跑、不接solver。根587=144literature443assumed0measured，旧575完整保持，新7采样+5运行政策，名义mode0/directoff保持；0新构造/RHS/Jac/ODE/fit/UQ。原P45/P34/P40/P44失败、P46/P47CaO undefined、名义余水0.135892078740%>0.1%与wholefalse保持，当前host新接线动态/加密/八阶段/交叉项未资格；交付及历史容量分列。

| 生产能力 | 实际验证范围 | 留待验证 |
|---|---|---|
| C 原生面与完整能量采样 | additive应用、8源码语法中的对应文件及独立静态源审查；原一次summary rates及同hg/完整U五项计账保持 | enabled=1动态捕获、gzip侧文件、主机运行；compare/fit/UQ writer未扩展 |
| F 单位CLI/API | 本轮真实f-data读取已合3来源/12条件/23观测，原manifest、条件、CSV逐条保留 | P38 wrapper只静态，其他单位例子未执行；无实砖L或材料拟合准入 |
| G 显式RH/干基到湿基 | 单位/同温Psat/液水或冰/完整干基/来源合同静态；CLI复用read_parameters | 当前RH/Psat未知，未调用API/CLI；null模板仅docs，原入口/温压/阶段边界未改 |
| H 保存数据嵌套分区提案 | 生产脚本与既有C映射接口相容；沿用外部固定一次P44保存转换收据 | 不接solver、不重构粗格状态、不授P44/P46网格收敛或更小误差 |

C 使用 `configured_sampler`、`FaceEnergySamples`、`write_sample_bundle`；普通 full-cycle CLI 与 acceptance baseline 通过 `write_full_cycle_artifacts` 输出独立gzip侧文件，普通fields仅留收据。根明确enabled=0；整个合同缺失不隐式关闭。面选择/已有summary时刻/字节额度来自根，未来运行需另分配；本轮没有采样sidecar或物理计算。原native热面向外为正 `-internal/-qext`，气体分量共享已有hg与唯一flow账本，完整U五项及原热源计数保持。P47 `calcium_phase_ledger` 接线未覆盖。

F 的 `convert_record / normalize_f_evidence / load_f_evidence / map_p38_record` 已进入生产。唯一执行为根登记路径的 `f-data`，2026-10-02 00:13:51.916498–51.960300 PDT，deadline00:14:21.916498 PDT；实际1producer/1task/1worker，成功不重跑，窗口关闭。输出293,715B，CPU0.035008s、监督0.043822s。12个CO2边界分压仍null，不猜总压；时间/观测关系、基准/域和Arias排除保持。普通F转换仅stdlib；P38先原样config/record调用旧mapper再添视图，其依赖沿既有VME/NumPy/SciPy，未动态执行或放宽旧拒绝。

G API接受现有reader已读取配置；去除新建通用_required/_number及重复finite/range/source/status层，保留换算合同及候选元数据。缺项直接索引报错。初次文本编辑遗漏CLI的encoding关键字匹配，在任何G调用前读回发现并静态修正，记录声明；不是科学失败或G运行。当前模板未知值不入根。见 `HUMID_GAS_BOUNDARY_INPUTS.md` 和文档模板；该CLI非纯stdlib安装入口，但未新增依赖。

H 原输出38,862B/0.011271125s只属旧保存数据提案：coarse9插入fine face19后13格，outer格rank8，fine广延量守恒rebin。没有新网格求解，也不将提案视为3.01853436%误差已改善。实际旧收据和输出以H前缀保留在本轮runs目录，不重算。

8个受修改Python文件实际语法解析、4补丁实际apply检查均通过；根既有reader读取587条通过，旧575完整参数条目保留。新7采样/5运行政策全source=policy，说明在note。原材料/solver阈值、名义选择与气氛不改；当前host源码已变，不能继续说45源码全未变或授新动态资格。原净U/逐相/网格/strict/余水失败及CaO零分母资格保留，measured=0，wholefalse。

本次源码和必要文档一次聚合正常Git后继、普通push/remote和单小科学包，实际receipt另读；0恢复下载/SHA/tests/guard/新物性/新文献/自动任务。Desktop登记symlink阻塞的另两local续作未重试、不称完成；采用父明确保留的原G/H成果。历史20GB/独有Git/容量告警仍未解决。

实际资料：`runs/full-cycle/p48-production-integration/F-execution.json`、`F-output-readback.json`、`f-units.json`、`declaration.json`、`independent-source-reviews.json`。各功能使用说明分别在 `FACE_ENERGY_SAMPLING.md`、`research/DIRECT_CARBONATION_UNIT_CLI.md`、`HUMID_GAS_BOUNDARY_INPUTS.md`、`NESTED_REFERENCE_PARTITION_PROPOSAL.md`。
