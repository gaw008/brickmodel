# 物理沙盒 Goal 进度

更新时间：2026-09-07 UTC。完整任务合同：[GOAL_BRICK_PHYSICS_SANDBOX.md](../GOAL_BRICK_PHYSICS_SANDBOX.md)。最新证据以文末检查点为准，较早段落保留当时状态。

## 当前恢复入口（后续详细历史保留）

最新检查点：dcabd8d 生产源码未改，HEOS 原四步湿压缩短前缀已实际尝试并暴露成本瓶颈，证据 research/heos-wet-stage6。预登记保持原 0..1/64s、4步、1e-6J/K逆解、T2e-5K/P.2Pa/各功1e-6J、25秒积分/30秒外限，独立 Python entropy oracle 原文件不改。初态库存精确、新旧身份规范化后不同且各自匹配 operator；同300K初能差1.74623e-10J通过原1e-6J，未覆盖能量。执行前修正测试tuple/list假身份差异，审查记录保留。

attempt01 缺pytest导入失败未进EOS，离线补锁中pytest8.4.2及已记依赖后原脚本attempt02实际exit1/28.734s；积分wall_time_limit，26.853s/10eval/1接受/0拒，未到熵参照或末端门槛，不能称湿轨迹通过。没有放宽门槛重跑。session29821已终态。

一次实际同初态求值profile exit0/4.56048s（session19385终态）：求值约2.72s，205水状态，410事务/820生成器进出，事务累计2.648s，JSON encode/decode自身约1.077/.610s；累计项不相加。独立审查核脚本、输入、失败和profile，表明当前主要成本是反复完整fluid JSON核验，不是原生EOS计算，未证明整体加速。生产41模块/1112完整安装测试仍是dcabd8d证据，本轮只有制造诊断而无新完整suite。

下一动作明确：隔离候选仅将runtime流体canonical重编码检查改为构造时已同时核读的原始字符串SHA，保留每次前后读取/配置/lock/warnings及全部数值门禁；格式变化更严格拒绝。先单变量故障和公式验证、更新真实实现manifest后再回原四步短前缀。不要同时缓存/嵌套去重或提高超时。完整原污泥域、活动相变/全周期、烧结冷却、公开对照及CLI/UI/搜索仍为完整Goal必需缺项。上一轮和本轮均为progress；Goal active，无运行句柄待轮询。

最新检查点：HEOS stage5 已把显式可选混合后端接入生产源码。真实液汽 EOS 用已审查 HEOS 内核，理想部分保留 Python IAPWS；物理参考态与不可变软件实现身份分开，完整 canonical 身份绑定 provider/schema/source IDs/定义及代码。身份贯穿水状态、化学、相、闭合储能与目标记录。默认 Python 不变，状态 dataclass 新增 implementation=None 字段；不宣称历史全部 JSON 字节不变。

清单固定 SHA、实际运行 descriptor 二次比对与来源路径已独立审核；不接受调用者自行改写清单来准入未验证构建。来源记录 data/sandbox/water/heos-8.0.0-source.json、固定 manifest 与 docs/sandbox/HEOS_BACKEND.md 可查询软件、许可证、原始流体及 IAPWS。缺少可选依赖时明确 WaterSourceError，无静默降级。实际已安装默认环境没有 CoolProp，该拒绝已验证。

隔离候选默认相关 212/298 测试通过；最终固定清单候选 smoke 与原闭合储能制造测试逆解合并实际 exit0/3.948618084s，保留原逆解 1e-5J/1e-4K 等门槛。默认 canonical 与旧记录相同，替代实现身份不同且稳定、剥离身份与混用拒绝。早期 descriptor 摘要未涵盖完整 envelope 的碰撞已修复；原候选、失败/修复及独立复审归档 research/heos-stage5。应用的 13 个源码文件与最终审查候选逐字节一致。

冻结非 editable 离线安装后，实际从 /private/tmp、无 PYTHONPATH 运行全 sandbox 套件：**1112 passed in 519.65s**，XML 1112 tests/0 failures/0 errors/0 skipped、time519.651s。session34061 已 exit0，41 个实际 site-packages 模块在测试后重新导入并与当前源逐字节及 SHA 一致。证据 research/installed-sandbox-heos-interface-tests.xml 与 identity.json。本套件证明默认安装回归，替代后端的有界运行证据来自单独已核查的 HEOS 环境；不将二者混称替代后端完整主机测试。目前无待轮询测试/EOS句柄。

下一动作：完善可选依赖锁定/安装契约及替代后端集成故障测试，再以原门槛验证活动相变湿逆解、短前缀和实际成本。尚无整体提速证明，不能直接扩大为长湿扫描。全原污泥材料证据、反应/输运/自由烧结/冷却、三公开机制与留出对照、全周期 CLI/中文 UI/逐代搜索仍是完整 Goal 必需项。Goal active，当前为阶段性实现和验证，尚未完成全模型。

最新检查点：HEOS stage4隔离TP改进与扩大验证已归档research/heos-stage4，生产src仍6dc5aa9。初30state网格28pass/2fail，293/300K100MPa液体energy残差2.314e-6/2.096e-6>1e-6保持失败。新增nativePT只做phase-verifiedseed，再解pEOS(rho,T)=原targetP，logrhoNewton slope=rhoRTD，max8/step<.1，目标min1e-4Pa,rho*1e-7。nativeh/u/s与targetP不重置，原全部gate不变。新同30cases全部通过1.52217s/exit0，两原失败实际一步密度更新改善，raw迭代独立重算通过。

另外7原liquid/vapor中心差分案例通过1.50251s，原33IAPWS印刷点通过1.03654s；实际5snapshots/导数差分与单位/API经独立复审。math.isclose symmetric与原pytest.approx尺度略异，已对实际21+33数值额外按原expected尺度重算54项全部通过，不重标代码执行方式。275/625K是raw backend公式核，不扩candidate293–500K域，也不算实测材料验证。

参考态初测试错误预期existing实例跟随global setter，identity01 failed保留。核读官方Reference States后不改kernel/gate、更正验证对象：旧snapshot完全不变，新nativeh实际变，新candidate被原anchor拒绝；DEF恢复后4workers/12calls（4独特点重复3次）sharedinstance结果与sequential相同，identity02exit0/1.40425s。不是多实例或并发全局mutation安全证明。所有research脚本/失败/实际过程及review保存；没有待轮询运行句柄（13010/5191/52153/27773已终态，其余本轮工具直接exit）。

下一工作保持完整Goal：完成HEOS剩余故障/种子拒绝与显式loader/immutable公共descriptor，贯穿caloric/chemical/provider/closed-storage身份后才准入原wet逆解与短前缀，不把30点称为全域或完整stage4。测完整验证后端成本再扩大湿积分。cache尚未新增，需先定义契约；全原污泥物性/反应/输运/自由烧结/冷却/三公开机制对照/CLI/UI/多代全周期仍未完成。Goal active，本回合真实代码/失败修复/验证属于progress。

最新检查点：隔离HEOS stage3候选已实际实现并归档research/heos-stage3，生产源码仍6dc5aa9。初始QT饱和蒸汽h-u-p/rho2.74099875e-6J/kg未过1e-6；独立子进程关superancillary反而.00182574，两失败保留，不声称开关唯一根因。改用QT种子、DmassT原生EOS评估与同T双相p/Gibbs共存门禁，能量/熵不代数重置；Newton Jacobian已独立核对。seed重评已过gate，最终删除强制更新，不能称为Newton误差改善或广域收敛证明。

最终attempt05实际exit0/1.169895s、59声明输入不变：300K两饱和相+两液态TP点4对照、6域拒绝、3不可变、5故障拒绝均通过。原pressure/caloric/Gibbs/cp-cv/energy等门槛不变，最大h-u-p/rho9.818086e-8J/kg。raw JSON、不同版本候选、原失败/运行日志/监督器证据与review03均保留。实际来源/28package文件/loadedextension/完整fluid/精确M与R/adapterSHA/effectiveconfig进入区别于Python的descriptor，ideal h/s anchor及前后config/fluid检查已实现。原设计R字面值舍入已纠正。不代表完整backend/主机准入或已提速。

下一可执行工作：HEOS stage4分批验证官方点、293–500K液/汽与高低压、响应有限差分、确实需要迭代的共存种子与拒绝路径、fluid/reference故障、并发与cache契约；随后才能把descriptor贯穿现有桥接/化学/储能身份并接原湿前缀。保留受控单进程研究范围，不能把instance lock当进程全局修改安全。无EOS运行句柄待轮询（40652/18934/94515/72418/64056/82691全部已终态）；生产38模块/212相关安装测试为上一轮，旧1112完整套件是更早源码证据。全原污泥域/全周期/公开机制对照/CLI/UI/多代搜索仍未完成。Goal active；本回合有真实代码、失败诊断与验证进展。

最新检查点：默认Python水后端调用层已独立审核并应用（下文ecfb3e9/1112为历史完整suite）。新增私有固定静态调用类，仅转发当前native对象，不改变来源、单位、参考、容差、异常作用域或缓存。独立AST九调用逆变换后与旧模块整体相同。隔离117+95相关测试通过；冻结非editable安装后212相关测试实际1.46s通过，38实际site-packages模块与源逐字节一致，session12878已exit0。没有运行新全套或湿轨迹，不把旧1112升级为本版本完整证据。

初轮golden因直接执行candidate目录脚本可能污染sys.path，不作为旧/新比较证据，原记录保留。修正bound_golden.py在stdin独立进程运行，先断言实际加载路径并记录不同源码hash；old ed7adf/new66ccc，5温度30数值+4域错误、reference is和冷热canonical检查，JSON逐字节相同。证据research/water-python-seam。本轮有实现与实际验证进展，Goal active。

下一动作：按water-backend-feasibility/ADAPTER_DESIGN第3步，在隔离目录实现显式HEOS来源/二进制/流体/常数身份与小范围TP、饱和及Helmholtz检查。先原两液态点与300K两饱和相，原门槛不变；尚未准入任何替代后端，不应修改生产科学引用来伪装，也不立即跑长湿扫描。全原污泥材料域、反应/输运/自由烧结/冷却力学、公开三个机制组、CLI/UI和逐代实验仍未完成。

最新源码ecfb3e9：当前孔隙模板、规定变形程序边界与相变显式组合已应用。冻结非editable离线安装从/private/tmp无PYTHONPATH实际 **1112 passed514.98s**；37个真实site-packages模块与源码匹配。research/installed-sandbox-wet-admission-tests.xml及identity.json保存实际证据。session45600已exit0；旧75509/89265/46721均已结束，不再轮询。当前无运行中的测试/EOS进程。

真实callback01在相变化学前被参考孔体积门禁拒绝，保留后修复当前bulk减固定固体占积；9noEOS独立通过。callback02实际1.387s/exit0、113声明输入不变、非零K/液汽精确成对/无额外潜热/当前几何/单次反解通过独立审核。其原fixture反解1e-5J/1e-4K，不能混同下一段1e-6J/K。原候选/失败/先RED/回调与应用34测试73s在research/deforming-wet-admission。

独立湿态熵端点2.07s通过不等于轨迹。原0→1/64s短前缀2接受/15评估的孔压功2.97406436e-6J未通过1e-6J，保留research/wet-deformation-entropy。refinement02同原1s/10%运动及同短终点，将initial/maxstep1/128→1/256；实际4接受/29评估/0拒，25.5696s/exit0，初始N/E/tag精确匹配原失败，所有原精度门槛保持，孔压功7.35992551e-7J通过。原生u/s及全部账本保留，已归档research/wet-prefix-refinement。因含当前孔隙源码修复，不宣称严格同源码收敛阶；只有末端独立组件真值，全部prefix检查是账本闭合。完整10%湿轨迹、活动相变积分/变形耗尽仍未验证。

研究监督器research/research-process-supervisor已独立17测试1.38s通过，实际TERM取消清理/failed传播通过；历史子进程残留与EPERM失败保留。它已用于callback02/refinement02，不是通用进程沙箱。默认生产水EOS仍为iapws1.5.5。可选快后端只有两点可行性与设计，见research/water-backend-feasibility；不要把原始flash倍率冒称完整主机加速。

新增Arlabosse2005低温比热来源记录，原文/3图、4资产哈希、干基单位与35–105°C温区已独立核读；原始文件在ignored .tools缓存，登记data/sandbox/research/arlabosse2005。进水85%工业/15%市政、初始水分正文/表差异保留。它只是特定材料低温关系，缺绝对参考能/误差等，未准入运行材料包。

下一可执行步骤：依据已审查ADAPTER_DESIGN，在隔离目录实现可选后端接口的**现有Python默认路径**，先证明原源码行为/来源/相域/错误/缓存等价；通过后才准备HEOS实现，不能直接替换EOS或启动数小时2048步湿扫描。并保持同原污泥域热化学/动力学/输运/烧结/力学及三个公开机制组、CLI/中文界面/逐代搜索等必需缺项。Goal active，软件仍在实现，科学状态无完整原污泥材料域，部署仅离线研究。

## 当前状态

- Goal：active；持续实现中，本回合已修补数值缺陷并完成阶段提交，属于 progress。
- software_status：implementation_in_progress。
- scientific_status：partial_sources_no_complete_raw_sludge_domain；完整原污泥材料域尚未成立。
- deployment_status：offline_research_only。
- 当前阶段：G0 历史B2故障已修复；G1 基础模块已提交；G2 守恒积分、配平反应、刚性气热、独立账本、纯水适配器已通过有界验证与独立复审；完整湿砖全周期未实现。
- 基线：`4b4f2d3`；分支：`codex/physics-sandbox-v1`。
- 开始时已有未跟踪文件仅 `docs/GOAL_BRICK_PHYSICS_SANDBOX.md`，为本 Goal 合同，保留并纳入本任务。
- 当前工作目录 `/Users/wanggaoying/Desktop/brickmodel-github`；未修改 Hermes、同步任务或远程仓库。

## 已核对

- 适用父目录及仓库无 AGENTS.md；Git 历史与既有研究记录已读取。
- 已读取完整任务合同、模型架构/公式/参数与研究状态、B1 冻结合同、B2 推导/失败范围。
- 早期 VME 的固定有效热容能量恒等式、累计供氧上界、synthetic 黏度/收缩/性能关系不能直接承担新模型的材料结论。
- 当前机器 macOS arm64；系统 Python 3.14.2，使用 Python 3.12.13 的隔离 `.venv`。锁定 numpy/scipy/pytest/Pillow 已安装。使用 `UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache`。

## 本轮已实现与验证

- 本地阶段提交 `0634e80b1fa4d69c195022f1c7ecd79a16110fe2`：B2 暴露量积分曲率步长界、真实失败审计、Darwin RSS换算与回归；没有改原1e-6门槛。
- 实际提交绑定 `run_tests.py`：14单元测试，全部8类NUM门槛通过，34次focused积分；77.61s、41.52MiB。实际default 22情景完成，绑定bound；15.92s、94.63MiB。独立audit 322204 checks通过，最大暴露误差6.9171e-8。
- 完整原始源码/输入/结果/验证打包在 `research/b2-bound-0634e80/reproduction.tar.gz`（565成员），摘要和命令在同目录 `summary.json`。这是实际绑定验证和离线包，未宣称对离线包做了全部重新积分。旧失败原样保留。
- `sludge_sandbox` 新包：证据DAG/分类/域/未知阻断、单位、干湿料账目与独立分析类别、相容半板几何；所有制造值仅是测试。
- NIST四气体10段80个Shomate系数核读与移录；真实表点/导数/能量反解测试。原始接缝保留，能量间隙、多解及浮点精度不足会拒绝；没有低温水汽/液水/固体补值。
- 实际集成基础测试：`PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_evidence.py tests/sandbox/test_units.py tests/sandbox/test_materials.py tests/sandbox/test_geometry.py tests/sandbox/test_thermochemistry.py -q --junitxml=docs/sandbox/research/g1-core-tests.xml`，122 passed。
- 公开研究：7篇候选资料、Wang 12条件186图中实验符号派生读数、Mohajerani24终态值、Nowicki9拟合率等。条件冲突/基准争议均隔离；没有拼成完整原污泥材料包。
- 气体中心修正曾从零物种格移出物质，已添加先失败回归并改为correction drift成分上风，79测试与独立150场景/450方向复查通过；不能靠无限减步长补救。物质焓接口有10项实际测试，net与diff/adv分项必须一致。
- 干净非editable冻结离线安装已实际验证：从/private/tmp运行，未用PYTHONPATH，site-packages真实导入；最终211 sandbox测试通过。报告 `VALIDATION_REPORT.md`，原始XML `research/g1-installed-final-tests.xml`。仍未完成全流程CLI/UI安装验收。
- `WORLD_SPEC`、`EVIDENCE_POLICY`、`VALIDATION_PLAN`、`SUPPORTED_DOMAIN`、`KNOWN_GAPS`、方程映射已建立并明确已实现/未实现。

平台细节：本地工具回合会使 `.venv` 文件隐藏，Python3.12跳过隐藏 `.pth`，editable导入不稳定。开发显式 `PYTHONPATH=src`；最终必须另测干净非editable安装，不能靠该路径声明安装验收。外部`/usr/bin/time -l`曾因sandbox kern.clockrate/sysctl被拒绝，内部RSS/耗时单独报告，未反复重跑掩盖该问题。

## G2 已完成的有界能力

| 本地提交 | 实现与验证 |
|---|---|
| `e3dda49` | 配平反应、库存分辨率守卫；49测试、独立复审通过 |
| `a18310b` | 13份IAPWS原始/派生资产；33个官方数值独立重算 |
| `e259c29` | 守恒积分器28测试、刚性气热26测试；实际stage时刻、累计舍入、正性/取消/超时与独立审核 |
| `8bb92ca` | 独立精确加权审计37测试；系统/单元分步和前缀，保留权重舍入与局部漂移反例 |
| `2842691` | 来源门禁IAPWS适配器78测试；Cp/Cv导数和SI有限性修补，独立66状态复验 |
| `f2f2f31` | 刚性气相导热7个实际收敛案例；空间阶1.967/1.992、时间阶2.012/2.006；独立解析审核 |

水适配器使用IAPWS原生R与同相统一参考偏移；未与混合载气/高温Shomate拼接。审计器检查存储U账本，不冒充多相热物性重建。收敛案例为明确制造解，不是现实砖试验。

收敛脚本提交前 `git diff --cached --check` 曾报告文件末尾多一空行，编排未在该非零结果后停止提交。保留这项格式检查失败记录；不把它称为通过，也未改变绑定数值产物的源码字节。独立数值审核与源hash验证通过。

## 完整安装复验与来源增量

从 `/private/tmp` 在 `/private/tmp/brick-sandbox-g2-install-20260907` 运行冻结、非editable、离线安装；无PYTHONPATH。最后实际429测试通过（16.01s，0失败/跳过），13个实际site-packages模块源码hash与工作区一致。证据：`research/g2-installed-final-tests.xml`、`research/g2-installed-final-identity.json`。较早排除审计/水模块的314测试与11模块hash快照作为历史证据保留，不能混作最终版本。

Baloi2025出版商HTML/JATS原文、5组配比/终态热物性及派生提取已独立审核通过；4份清单资产逐一核验bytes/hash。详见 `research/BALOI2025_COVERAGE.md`、`research/CODE_REVIEW_BALOI2025.md`。体积配比没有擅自转质量；烧后低温有效cp没有冒充湿坯/高温热容。

独立代理的早期额度错误已终止；实际账户限额重新读取后可继续，未使用重置信用。恢复后的水、收敛和Baloi审核均完成。审核是代码/数值独立核查，不是外部科学专家认证。

## 当前关键缺项

1. 同一原污泥材料域的成套组成、产物、参考能、湿热/烧结/力学关系及独立实验覆盖尚未闭合。
2. 纯水/载气的闭合储能及已存在液界面的相变已实现；单相固体provider已有，固体整体储能/占积耦合、液态跨格迁移与泥中吸附/毛细仍缺，不能将纯水EOS当泥料干燥本构。
3. 烧结、闭孔/渗透演变、几何反馈和冷却应力尚未实现。
4. 全周期CLI/界面、可恢复批量运行、多代搜索与公开实验预测对照尚未完成。

## 当前增量检查点

- `34dbfe1`：Baloi成对来源与提取独立审核后本地提交。
- `a0f5697`：保存429测试安装证据、广延mol/J世界定义和当时支持域。
- `622d376`：连续边界程序41测试及独立审核，真实积分节点/解析能量检查通过。
- `7d3aaca`：显式理想水汽转换28测试，独立2071温点审核，保留h和生成能参考，固定R的u/Cv差及来源公开。
- 新增后完整冻结非editable离线重装：498 passed in1.99s，15安装模块hash与工作区一致；证据 `research/g2-installed-boundary-vapor-tests.xml`、`research/g2-installed-boundary-vapor-identity.json`。未修改已绑定G1/G2原源码来刷新旧报告。

## 最新已核验进展

上一回合属于progress：已有实测与阶段提交。本回合继续新增实际模块，没有把边界/储能原语缩为整个Goal。

- `b004db5`：Wang原PDF hash复核，SOURCE_COVERAGE与已存在来源注册表对齐2mm污泥层/钢板几何；有界热湿材料检索未得到两条新线索的完整合法正文，未引入摘要参数。
- `a84f46e`：动态气氛与半格/膜串联物理边界15测试、独立80表面根及真实积分通过。
- `23cee3d`：给定相压力物种储能22测试；大能量平台、相消、下界下溢与身份风险先失败后修补，独立审核通过。
- 上一检查点535项非editable安装测试通过（2.94s），17模块源码hash一致；最终 `research/g2-installed-programmed-storage-final-tests.xml` 和 `research/g2-installed-programmed-storage-identity.json`。上一份同535测试快照保留；当时绑定的17模块源码未再修改。
- 审核关于pytest abs/rel语义的误判已由实际源码与反例纠正，报告不再称原门槛被放宽；显式rel=0只作澄清。

## 最新机械闭合与连续热量检查点

- `e46321b`：RigidWaterGas平界面固定流体腔的液水—理想气压力/体积闭合，17测试及独立审核；保留压力域、受压液体占积、微量分压与数值失败证据。另有闭合热容推导及独立3状态差分验证，最大偏差2.79e-7 J/K，小于预登记1e-4 J/K。
- `1c1a019`：原Shomate Cp连续积分派生，原系数/温区/能量偏移均保留；22测试和独立120点Decimal核查。真实GasHeatModel制造例跨接缝至700 K，5400 J解析热量和每步账本通过；该例的接缝时刻显式提供，未验证自动事件探测。
- 最新冻结非editable离线安装，实际 **574 passed in5.63s，0失败/跳过**，19个site-packages模块hash与工作区一致。证据 `research/installed-sandbox-574-20260907.xml`、`research/installed-sandbox-574-identity-20260907.json`。报告绑定最终22项连续热量测试源码；旧535项检查点保留。
- 两项实现已独立审核，无关键未关闭代码问题。此处的APPROVE不等于材料物性资格或外部科学认证。

## 当前闭合储能检查点

上一回合为progress：连续热量模型、独立审核、574项安装证据均已提交。本回合继续实际接口和耦合反解实现，未缩减Goal范围。

- `94257d6`：新增水state_tp_response局部α/κ及摩尔体积/内能导数，21新测试+78旧水测试；压力模型现23测试，并返回最终数值括区、端点残差和求解路径。两个接口独立审核通过，均不冒充EOS严格误差界。
- `315337a`（rigid_storage）：固定液水/理想气库存，每次温度试算重新解压力/液体占积，得到U/H/闭合热容；条件温度反解保存数值envelope和有向误差区间。18测试实际通过18.48s，独立审核复跑18.72s并APPROVE；错误H2O跨相质量和温度区间向内舍入均保留反例后修补。
- 真实integrate单格热量反馈试验每次operator均执行实际闭合反解；库存保持、功账本与U变化在1e-8 J内、终温与独立嵌套压力/能量求根在1e-4 K内一致。此检查不自动证明时间离散收敛，更不是完整湿砖实验。
- 最新冻结非editable离线安装 **619 passed in23.27s，0失败/跳过**，20个site-packages模块hash与工作区一致。产物 `research/installed-sandbox-closed-storage-tests.xml` 与 `research/installed-sandbox-closed-storage-identity.json`；18项模块原始XML为 `research/rigid-storage-tests.xml`。旧574项/旧源码身份快照保留。

## 最新多格与证据检查点

上一回合为progress：闭合储能、独立审核及619项安装证据均实际提交。本回合增加多格面耦合、连续相适配及新的原始实验文件。

- `e24a560`：IdealGasPhase显式支持连续Cp派生全温区，旧原Shomate单段与水桥门禁保留；新增3测试，独立7个NIST O2跨缝反解最大误差5.30e-11 K。未自动拼接低高温水汽。
- `b8ae2aa`：RigidFluidHeat每trial每格实际U/库存→P/T/气孔闭合，共享面导热与气体/焓输运；16测试独立通过40.10s，含真实两格积分、双气列/质量修正/焓、进出气供体焓、域退出和半格热阻。液水库存固定但占积参与P/T闭合。保存原反解诊断与条件资格。
- 多格审核发现同一来源独立加载的IdealWaterVapor因私有EOS实例身份被误拒；已先RED，改按来源hash、共同参考、方法、R、域和数值政策等完整语义身份匹配并复验。跨格不同能量曲线/锚/分段仍拒绝。关于ContinuousCaloricError继承的主代理疑问经源码确认原本已被ThermochemistryError捕获，没有虚构修补；新增域退出仅是覆盖。
- `eacdad3`：Ghodke2022公开CC BY原TGA工作簿、单页拟合表、官方元数据/文件清单/manifest，11575条逐行提取已独立复核。单次氮气运行没有独立升温条件，DTA µV未当反应热，动力学拟合表尚未准入。原CSV因CRLF触发暂存检查失败后停止提交，旧脚本/CSV/audit归档，改LF并核字段完全不变，最终检查通过。
- 当前冻结非editable离线安装 **638 passed in63.82s，0失败/跳过**，21个site-packages模块与工作区hash一致。证据 `research/installed-sandbox-fluid-heat-tests.xml`、`research/installed-sandbox-fluid-heat-identity.json`；旧619项原始证据保留。TGA提取审核独立于软件单测，不能把11575行叫11575次实验。

## 638测试检查点的后续计划（历史）

本轮有界实现/代码/数据审核完成，主代理保存统一阶段记录。Goal继续active，未满足第11节完整完成条件。

1. 现有RigidFluidHeat已经真实接通多格气体/热量与液体储能/占积，不重复停留纯气或固定压力primitive。下一步加入液水迁移与相间质量转移，并在同一库存/能量定义下处理携带焓；需要有源毛细/有效输运/活度关系，不能假设已具备污泥干燥参数。
2. 先明确相容的气液化学势/焓参考和相变模型。理想水汽桥有固定R转换、液水保留IAPWS原生R；不能只用饱和压公式和任意相变常数绕过热力学一致性。低高温水汽热量衔接仍待推导；连续气体相适配本身已实现。
3. 补多格时间/空间收敛、液相/气相/热量各极限和独立全系统能量审计；目前两格0.001s有界制造案例验证连接与守恒，不等于生产时间尺度效率或收敛。记录数值成本后可针对实际热点优化，保留有效域和原门槛。
4. DeclaredNumericalEnvelope全域界仍未独立准入；现误差结果为条件性声明。补可审查的水EOS/气体热量数值误差预算，不能把局部导数、求根残差或所有有限点测试当严格全域证书。
5. 新Ghodke原TGA可作为已取得的单次源曲线，但还缺独立热历史、完整制样/元素基准/产物计量及反应热。继续同一原污泥域的干燥、有限氧反应、烧结/连通性/几何和冷却力学来源与实现，随后完成多代搜索与CLI/UI。未知材料参数不能用制造值顶替。

恢复入口：`RIGID_FLUID_HEAT.md`、`RIGID_STORAGE.md`、`CONTINUOUS_PHASE.md`及三个本轮独立审核报告；新数据详情为 `data/sandbox/research/ghodke2022/README.md`。全部当前软件资格仍限定数值研究，液迁移/相变/固体反应/烧结/应力、完整材料包和公开预测验收均未完成。

## 最新化学势与相间迁移检查点

上一个用户问答回合重申了Goal提示词，但未改变实现，按no-progress重新核查工作区与仍运行的三个代理；本回合实际完成以下实现、独立证据和提交，属于progress。完整Goal保持active。

- `f92de4f`：WaterChemicalPotential固定1bar标准态，共用native水熵参考与能量平移，液/汽mu相等派生peq；36项新测试、独立导数与数值检查通过。主代理另按Table1显式系数计算8温点，不调用新模块或_phi0作为参考；最大peq相对实现差2.59e-13。真实液EOS仍共用，独立性没有夸大。500K相对nativepsat约−11.24%是理想汽近似差异，原始结果及范围保留。
- `f8b5a86`：WaterPhaseTransfer用明确K(peq−pv)在已有液界面等摩尔变更液/汽库存，保持同一U源，不重复潜热；下一trial真实反解T/P。16项最终独立测试通过61.11s；蒸发冷却/凝结升温均实积分，水库存≤1e-11mol、U≤1e-7J；零汽、无液成核域退出、有限库存超步拒绝、微小K下溢等通过。局部熵产有代数审查，完整轨迹熵验证尚未执行。K/载气与数值误差envelope仍是明确制造/条件声明，没有泥料预测资格。
- 冻结非editable离线重装，在/private/tmp无PYTHONPATH运行全量sandbox：**690 passed in124.57s，0失败/错误/跳过**；实际23个site-packages模块与工作区hash一致。证据 `research/installed-sandbox-phase-transfer-tests.xml` 与 `research/installed-sandbox-phase-transfer-identity.json`。旧638项和来源原始文件保留。
- 实际一次闭合反解性能定位：5次储能前向、200次压力trial、205次饱和对；带profiler约1.543s，不是裸吞吐基准。`research/CLOSED_STORAGE_PERFORMANCE.md`、`closed-storage-profile.json`与只读`WATER_CACHE_DESIGN.md`给出下一步有界缓存方案。尚未实现缓存，不能声称已加速。

### 690测试检查点的后续计划（历史）

1. 依据实测热点优化重复饱和求解，保留当前来源/域/数值门禁与原容差；先验证容量与失效行为，再测实际加速，避免把长时多格实验直接扩大。
2. 将固体储能与占积、液态跨格迁移及对应焓接入同一库存/能量定义，补真实动态外边界、多格时空收敛和完整轨迹热力学诊断。现相变制造例只有0.01s，不能冒充完整干燥。
3. 明确耗尽后无液分支、泥中活度/毛细/迁移速率和低高温水汽衔接，取得同材料域的依据；不得靠无液时截小正数延续烧成。
4. 原污泥热解/有限供氧、烧结/连通性/几何、冷却应力、三机制公开预测验证、完整材料包、多代搜索与CLI/UI仍属必需未完成项，沿用原合同，不缩减范围。

三个有界代理任务已完成，无其声明中的计算进程待恢复。下一回合先看本最新段、实际Git状态与上面的来源/性能产物，不重跑已通过且未变更的同一测试来代替实现。Goal尚不符合第11节完成条件，也未达到无法继续推进的阻塞状态。

## 最新固体来源与性能检查点

上一Goal回合为progress：化学势、相变及690项完整安装验证已实际提交。本回合继续完成实现、来源与测量，未将单相provider缩为完整湿砖Goal。

- `3ed9aa1`：水饱和求解每实例容量1缓存不可变成功快照，命中仍检查当前两相EOS/Gibbs；18新缓存测试及181相关独立测试通过。审核发现预热后删除底层求解器会逃逸AttributeError，经RED后恢复原WaterNumericalError，未放宽门槛。相同反解输入3次裸计时中位1.3000s→0.8261s，约1.57倍，T/P/残差/最终括区/迭代数逐值一致；旧新源码hash与完整计时代码保存在 `research/water-cache-performance.json`。只作为单例单机测量。
- `77b4515`：取得NIST Quartz与JANAF O-037原HTML，有限事实2温段/16系数、19温点×4输出=76值独立复核。847K JANAF双行差728J/mol、Shomate拟合差729.127J/mol/非零Gibbs接缝差均保留，不能连续化抹去相变。原完整SRD页仅ignored本地缓存，有限事实/许可/位置/hash及旧三列提取归档在 `data/sandbox/solids/quartz/`。纯石英不代表泥中含量、体积或全砖热容。
- `12f6f06`：SolidShomateCaloric与IncompressibleSolidPhase单一晶相温段、恒摩尔体积、u=h0−p0v/h=u+pv；全域Fraction正Cp下界不要求气体Cp>R。29新测试及与旧PhaseStorage组合51项独立通过，实际储能求和/反解已连接；另50组独立驻点/内能导数检查通过。u误差至少包含p0*εv，其余误差仍明确条件声明；体积/误差来源与制造门禁保留。尚未接rigid整体固体库存与占积。
- 当前冻结非editable离线安装，从/private/tmp无PYTHONPATH运行全量sandbox：**737 passed in78.91s，0失败/错误/跳过**。24个实际site-packages模块与工作区hash一致；证据 `research/installed-sandbox-solid-cache-tests.xml`、`research/installed-sandbox-solid-cache-identity.json`。旧690项及旧水源码身份快照保留。

### 当前下一步：整体固液气闭合

1. 按已审查 `research/SOLID_COUPLING_DESIGN.md` 实施真实固体库存和占积：流体腔体=bulk−ΣNs vs，整体U含ΣNs us，每个试探温度重新求固液气体积/压力/总储能，不能从目标U减去固定热容后调用旧inverse。先有界惰性固体阶段，为后续反应/收缩保留真实库存列。
2. 扩展体积误差→压力→液相内能传播，尤其无液纯气支也不能忽略固体体积误差。保持来源/数值条件区别、方向舍入和域检查。接新固体模型后，再扩展共享面输运与WaterPhaseTransfer主机接口，实际验证固体改变蒸发冷却幅度。
3. 补液水跨格迁移/携带焓、真实动态边界、多格时空收敛、完整轨迹热力学诊断；低高温水汽衔接与液界面耗尽后路径仍需实现。不要再以缓存微调或重复单相自测代替这些必需耦合工作。
4. 同一原污泥材料包、成套热解/有限氧计量与反应热、烧结/连通性/几何、冷却应力、三机制公开预测验证、多代搜索、CLI/UI仍保持原Goal必需未完成范围。Quartz只补一个固相来源，不能掩盖这些缺口。

本轮代理任务及所有测试进程已结束；关键代码/来源独立审核均APPROVE，含义仅限各自有界范围，不是外部科学认证。完整Goal继续active，没有满足第11节完成条件，也没有发生无法继续的阻塞。


## 最新固液气实际耦合检查点

本回合为progress，完整Goal继续active。原合同§11仍未满足；没有因为局部模型通过而缩减原污泥全周期范围。

- `96d70dd`：SolidFluidStorage整体固体库存/占积/储能，每trial真实闭合P/T。23项独立测试及单独Decimal三状态/反解/25W十秒积分通过；固体体积误差连干支压力也传播。几何virtual_design_choice保留ID/版本/来源和制造材料门禁，不能给材料升格。实现说明及独立oracle在SOLID_FLUID_STORAGE.md和research目录。
- `3f69e34`：SolidFluidHeat共享多格气体/焓/热量通量，WaterPhaseTransfer明确支持完整固体布局。固体Cp实际改变蒸发降温，两个终温条件误差区间分离。独立审核发现wrapper制造固体/几何门禁缺项，已修复复验。裸ConservedState不带列身份，未宣称自动识别同形状列置换。
- 审核29项原收集版与2项后强化版分别保留XML；最终全量安装执行全部强化断言。冻结非editable离线安装，在/private/tmp无PYTHONPATH实际 **773 passed in96.01s，0失败/错误/跳过**，26个安装模块与当前源码hash一致。产物research/installed-sandbox-solid-fluid-tests.xml与installed-sandbox-solid-fluid-identity.json。旧737项证据保留。

下一步执行：液水跨格迁移及携带焓、完整主机动态炉温/气氛边界、多格时空收敛与轨迹账本仍需接入。低高温水汽参考衔接、液界面耗尽后路径、反应库存与能量、烧结/连通性/变形、冷却应力继续按原合同实现；制造例不替代来源支持的材料域。原污泥同域参数、公开三机制预测、全周期和多代搜索、CLI/UI仍未完成。不要重复无变化测试代替这些工作。


另取得并核读USGS Bulletin1248石英离散体积/密度表：有限事实、原文hash与温度/晶相/历史常数/误差边界在data/sandbox/solids/quartz/usgs-b1248/。压力保持unknown；两个不同温度点不成为高温恒体积关系，纯石英来源不解决同一原污泥材料包缺项。完整原文仅ignored缓存，不作为可发布原文。


## 最新动态固液气炉温与气氛检查点

上一回合真实完成固液气耦合/USGS来源及阶段提交，属于progress。本回合同样有实现、独立计算与完整安装证据；完整Goal继续active，软件与科学资格未满足§11。

- `427ead1`：ProgrammedSolidFluidHeat每trial只做一次完整固液气解码，构造完整动态气体库与半格导热/对流/辐射表面平衡；WaterPhaseTransfer显式第三主机外包，保留完整诊断/源身份及breakpoints。8项新program测试+5项新phase组合，含真实升温保温冷却、真实气氛入流与供体h、外热和水相变账本。独立32项含旧主机回归通过68.29s，报告和原XML已提交。
- 主代理单独60位Decimal解析对照实际40s程序，首轮十进制dt非均匀节点余步导致整体判定false，原script/plan/result保留zip。第二轮仅将实验步长改二进制精确.5/.25/.125，原门槛和积分器不变；均匀且零拒步，maxTerror .000520179/.000127759/.0000316464K，ratios4.07158/4.03707，逐步与前缀账本均通过。独立审查重算JSON和公式，不冒称代理重复执行整套积分。反解界和表面累计数值扰动均远小于观察误差。
- 当前冻结非editable离线安装，从/private/tmp无PYTHONPATH实际 **786 passed in109.64s，0失败/错误/跳过**；27个安装模块与工作区源码一致。最终XML与身份research/installed-sandbox-programmed-solid-tests.xml / installed-sandbox-programmed-solid-identity.json。旧773项及首轮非均匀证据保留。
- 下一步液水面输运的方程与接入设计见research/LIQUID_FACE_DESIGN.md，独立审核REVIEW_LIQUID_FACE_DESIGN.md。已实际核读已有MOOSE原始快照的每相Darcy与质量通量乘比焓，并核其hash；没有新造材料参数。冻结mobility/upwind离散并非任意可压缩两半格精确解，限制已加入设计。

### 下一步实际执行

1. 在SolidFluidHeat共享面层接真实液水库存和同参考供体焓，保留单次decode与现有动态炉温/相变组合。须有显式液相mobility/饱和度关系/连通条件；不可把气相krel直接当液相值，平界面P_l=P_g只支持受限压力流，不冒充毛细干燥。先独立面手算和真实两格守恒积分，再接来源支持的材料本构与公开数据。
2. 补实际湿相变/液迁移多格时空收敛、完整轨迹账本与误差预算；本轮40s干极限仅证明所选固定步时间阶数。十进制节点余步效率问题仍在，不以反复改时钟策略取代物理工作。
3. 低高温水汽参考衔接、液界面耗尽后路线、原泥热解/残炭有限氧计量与热效应、烧结连通性/几何、冷却应力、同一原污泥材料包、公开三机制预测、多代搜索与CLI/UI仍属必需未完成项，不缩减合同。

所有本轮代理任务与实际测试进程均结束；没有待轮询的运行句柄。来源/设计审核不是外部科学认证，制造系数运行不成为真实泥料性能结论。本轮没有不可继续推进的阻塞。


## 最新液相共享面与整体接入检查点

上一Goal回合实际完成动态炉温/气氛、解析程序与安装验证，属于progress。本回合继续实现液水跨格mol/焓与完整固液气反馈；Goal保持active，未满足§11，不因面算子通过缩小原合同。

- `7bd4a38`：新增LiquidTransportState、SaturationMobilityTable、LiquidConnection及Fraction单供体Darcy面。独立20测试0.04s通过，正反供体/极端量程另核对。每cell液相关系独立于气相krel；frozen_manufactured只测试，tabulated允许真实来源局部平台或常值，不以数值变化代替准入。source/域/连接始终显式，material_qualified=false。
- 同提交将液面接入SolidFluidHeat，单次整体decode后从同参考真实水provider取供体v/h，S=Vl/(bulk−Vs)，共享mol与焓进入同一面。ProgrammedSolidFluidHeat/WaterPhaseTransfer保持完整诊断并补仅液制造参数门禁。6项新host独立测试22.89s，实际两格0.001s逐prefix水/U与面账本通过、固定solid/封闭gas不变。T变化仅名义，不宣称超过inverse预算；压力方向资格只fixed-decoded-T，未虚构全域dp/dT界。
- 主代理真实生成300K、50→1MPa、制造λ下纯水可压缩连续流参考：独立Gauss/brentq，共用水EOS，2353调用9.35s；参考0.00274052205113mol/s。4/8/16/32候选面实际误差比1.97752/1.98862/1.99428，最细相对误差.000346795，预登记门槛通过。Gauss16/32一致性非严格误差证书；恒温外约束的面收敛不叫完整湿砖时空验证。所有节点/面、脚本/源身份保留，独立review报告限定APPROVE。
- 最终冻结非editable离线安装，从/private/tmp无PYTHONPATH全sandbox **812 passed in134.01s，0失败/错误/跳过**，28个安装模块与当前源码一致。research/installed-sandbox-liquid-transport-tests.xml和installed-sandbox-liquid-transport-identity.json为最终证据，旧786项保留。所有本轮代理与实际进程均已终止，无待轮询session。

### 下一步保持完整Goal继续

1. 固体反应与有限供氧仍需实际接入当前共享库存/总U核。本轮已读现有reactions.py：SpeciesDefinition已区分固液气，ArrheniusMassAction明确按current_cell_bulk_volume归一化，反应算子不额外加热。因此下一步可审查显式网络→完整InventoryLayout映射、各相摩尔质量/元素/能量参考、真实T/库存/体积输入，再连接产物库存与总U反解。不能把文献表面/气孔浓度速率擅自改成现有bulk浓度形式；不为原污泥编造伪组分、A/E/产物或生成焓。需要时扩展有源速率形式，而非强行套旧公式。
2. 湿相变+液迁移+热/气完整多格时空收敛、液界面耗尽后的受控路线、低/高温水汽共同参考衔接仍必需。不能将这一轮恒温面离散对照冒充整体瞬态验证，不能在无液/孔体积耗尽时clip继续。
3. 同一原污泥材料域的毛细/饱和度输运、热解/残碳氧化计量与热效应、烧结/连通性/几何和冷却力学仍缺来源或实现；三机制公开持出预测、全周期、多代搜索和CLI/UI保持原必需范围。现无有源材料表被自动准入，方程真不等于泥料参数真。

恢复优先读LIQUID_TRANSPORT.md、LIQUID_SOLID_FLUID_HEAT.md及CODE_REVIEW_LIQUID_TRANSPORT.md。不要重复无变化的812项测试代替反应/干燥完成路径和真实来源工作。当前仍有可独立继续的实现与证据任务，不符合blocked条件。


## 最新固相反应与整体热力学反馈检查点

上一Goal回合仅给出任务书入口，按no progress处理；本回合重新核对实际工作区并完成实现的独立解析验证、来源审核及本地提交，属于progress。完整Goal继续active，§11仍未满足。

- `82f9f15`：SolidReactionConfig显式多相provider/网络/全列绑定，反应源接入SolidFluidHeat单次整体T反解，改变真实Ns/Ng及Vs/Vg/P/T，形成能留在总U中不重复加热。13项绑定与8项host最终独立通过，有限O2/零氧无氧通道/正Ea比/诊断组合/制造门禁覆盖。位置参数兼容和kinetic域分类两处审核缺陷已修复。连续净源ODE并未调用旧gross-extent限步工具，不宣称通用刚性网络已验证。
- 三档2s独立解析候选最终attempt002实际32/64/128均匀步、零拒步，最大Ns误差6.13022e-7→1.51459e-7→3.76428e-8mol，比4.04745/4.02358；最细T误差0.000352617K、P1.56026Pa，U/step/prefix差0，质量max5.421e-20kg。原预登记门槛未改；001首次PASS记录保留，002只补报告字段。独立审核重推227个节点及全部误差/hash，不冒称重跑积分。制造Xsolid→Xgas不是真实碳或污泥。
- 最终冻结非editable离线安装，在/private/tmp无PYTHONPATH实际 **833 passed in136.56s，0失败/错误/跳过**，29个真实安装模块与当前源码一致。证据research/installed-sandbox-solid-reactions-tests.xml及installed-sandbox-solid-reactions-identity.json。独立局部XML也复制到research保留，旧812项证据未覆盖。完整回归进程12298已exit0，不再轮询或重启。
- `b4dd270`：Areias/Maciel/Holanda2025官方来源有限事实与独立审核已提交。先干燥并混熟石灰的市政污泥，不是SSA也不是未经处理原泥；Table3、TG/dilatometry与四峰温烧成方法可追查，TG气氛/膨胀仪几何未知，图文阶段失重2.808/2.806差异保留。未数字化、未材料准入、未外部预测。

下一步：先实现液界面耗尽后的守恒事件/干态路径及低高温水汽共同参考。现water_caloric_join_probe已实际测得500K高减低h/u=0.17481133254477754J/mol、Cp/Cv=−0.007918945959858092J/(mol K)，仅模型端点差，不是物性误差证书或实现了拼接；方案见research/WATER_CALORIC_JOIN_DESIGN.md。液耗尽方案已写入research/LIQUID_DEPLETION_DESIGN.md，独立设计审查中；它明确原SSPRK2中间Eulerstage限制会使有限时间耗尽难以到达，拟用有误差控制和完整账本的终端事件panel。尚未实施，不可用静默clip、关闭相变或纯干例替代湿→干实际路径。

之后仍需湿相变/液迁移/热气多格时空收敛、真实原污泥计量/形成能/动力学、烧结连通性/几何与冷却力学、同域公开三机制持出验证、全周期、多代搜索和CLI/UI。以上原合同范围全部保留，软件通过不替代材料适用性与现实验证；目前仍有可继续实现的工作，不满足blocked条件。


恢复补充：`c49fdf4`已提交833项安装证据、29模块身份与独立水汽端点测量。湿干设计审核明确保留REQUEST CHANGES：逐操作两库存float精确增量相等可能使正常耗尽无解，不能把普遍unsupported当完成。设计末尾主代理已要求选择实际补偿库存表示，或精确成对extent账本加独立、显式、逐步/全prefix有界存储舍入残差合同；数值相间修正、实际蒸发量与存储舍入三者分开。原δ的局部ULP及相对蒸发积分上限继续有效，不能只凭一般atol或扩大阈值验收。此为下一实现前须关闭的数值设计项，不影响已验证反应实现，也不使Goal无可推进工作。

低高水汽设计可独立实施：完整域须证明Cp>R、保留h锚与各高温接缝偏移、gas_u_error包含锚/积分/偏移数值预算；0.1748J/mol是模型差而非误差界。高温chemical未知不能被当成已证明不凝结。所有本回合运行测试已结束；设计review终态见research/REVIEW_WET_DRY_CONTINUATION_DESIGN.md。下一回合直接开始上述实现/针对性反例，不再重复833项或同一设计措辞。


## 最新水汽跨域与事件写回检查点

上一回合实际完成反应/来源/安装验证并提交，属于progress；本回合继续新增实际caloric/host/写回实现、反例修复与独立审核，属于progress。原§11未满足，Goal继续active，无须外部输入即可继续下一实现。

- `4ef76a2`：源门禁JoinedWaterVapor低293–500K保持原bridge，500以上按原NIST Cp从同一低h锚分段Fraction积分至6000K，保留500/1700 Cp跳、原h/偏移/sourceassets。低正理想项及高区间有理数证明Cv>0；低h全域误差仍显式条件声明，不将接缝差当误差证书。budget最大float的溢出由独立2RED修复。IdealGasPhase/mass、反应完整identity、WaterPhaseTransfer仅low_modelchemical相容和RigidStorage活动Joined实际数值预算门禁均接通。四条实际SolidFluidHeat ±100W/4s轨迹跨500/1700升降温，完整mol/U与独立系数积分终温检查通过；这不是湿耗尽或真实高温固相验证。
- `624d89c`：选择耗尽方案(b)的具体写回部件depletion_roundoff。独立成对±δ与实际汽浮点残差分账；局部液ULP/绝对/真实蒸发积分相对限和逐事件/全prefix水mol/H/O/Mkg预算；累计绝对残差不抵消，JSON恢复保留Fraction与原政策。部分正常事件无需逐位相等即可按事前预算继续，但未定位事件或切换模式。主代理非零Fraction输入下溢反例先RED后拒绝修复，最终16作者测试通过，独立旧15+新增单项分开保留；另120边界算术独立通过。
- 独立provider31项与host9+写回初15项均实际通过；新两份CODE_REVIEW_JOINED_WATER和CODE_REVIEW_DEPLETION_ROUNDOFF为限定组件APPROVE。旧设计review被迟到精简覆盖后，经原审核者确认恢复602ebdc的完整历史；原worker节点/第二事件澄清+2行保留，没有新造已通过门槛。
- 最终冻结非editable离线安装在/private/tmp无PYTHONPATH实际 **889 passed in136.85s，0失败/错误/跳过**，31个实际安装模块与源码一致。research/installed-sandbox-joined-water-tests.xml及installed-sandbox-joined-water-identity.json为最终证据。进程22155已exit0，所有代理本轮执行已结束，没有待轮询测试句柄。旧833项证据保留。

### 下一步直接实现完整事件主机

1. 不再重写同一设计或重复889项。在已选方案(b)上实现depletion_integration事件panel、显式existing_liquid/depleted_no_nucleation模式与完整结果/跨段账本，实际关闭湿→干连续积分缺项。普通RK中间Eulerstage限制仍真实存在，不能靠最大step数趋近耗尽。写回函数只处理panel后的δ与存储残差，不能自行授权事件、伪造正向蒸发积分、丢弃原face/reaction/U误差或重置prefix。实际host绑定H2O两列与原native水摩尔质量。
2. 预登记并执行恒定汇/时变汇独立耗尽时刻、粗细事件面的时间/状态差、共同物理时刻继续积分差、节点先后/其他事件、微小蒸发但液流主导、实水/固体/气体/液面/反应组合。每个fine段都受下一程序节点限制；节点两侧事件未分离不能强行推进。完整状态反解和每step/prefix mol/元素/M/U/面账本照常保留，数值修正与物理传质及存储舍入三者分开。
3. 高温dry chemical驱动力超原293–500K域时strict unknown/unsupported或明确记录的亚稳无成核研究分支，不把未计算当成不会凝结。Joined高温热量域不解除液相、固相或材料范围约束；真实湿干/烧结高温材料资格依然未完成。
4. 持续保留原Goal全范围：湿相变/液迁移/热气多格时空收敛、原泥成套动力学/计量/形成能、烧结连通性/几何、冷却力学、同域三机制公开留出预测、完整原污泥全周期、多代搜索与CLI/UI。不能把本次caloric接缝测试或数值写回部件当成完整模型。

## 最新实际湿→耗尽→干态继续检查点

本回合为progress，原Goal仍active，§11未完成。`89d5d26`实现显式existing_liquid/depleted_no_nucleation与strict/metastable研究分支；`7da961b`实现完整Rates耗尽panel、clock表示误差独立预算、实际干态共同时间续算和跨全部段的精确库存/能量账本。旧SSPRK2有限时间耗尽失败、clock表示残量超库存ULP以及相邻级实际同一terminal的反例均保留并有对应修复。

31项事件/clock/写回测试独立通过；非线性cubic探针证明局部event指标不能认证此前普通湿段误差，原普通容差失败及100倍更严普通容差对照均保存，不将local completed当完整ODE误差证书。

实际真实水provider+制造固体/载气/K/传热主机attempt03在86.82s、224评估、27个接受试算panel、0拒步完成；21保存状态，事件0.00028422061165952946s，终时0.03125s，程序节点保留。完整水量max残差1.15805e-22mol、全prefixU6.81945e-11J、逐stepU2.02577e-11J；独立G=1/15传热和干升温超反解区间断言通过。执行前后所有源码/fixturehash一致；独立reviewer另外只读重算JSON账本，未冒称重跑物性。attempt01/02各120s失败原样保留；第三次收紧terminal_window减少重复湿前段，精度门槛及资源上限不变。

首轮冻结安装917项出现3failed/914passed（230.46s）：默认None模式物化成单格tuple导致原有两格液面/反应wrapper组合失败。`3c65ee7`保留None声明、由interfaces按当前host生成默认模式；显式tuple仍严格长度检查，不自动复制dry。原3测试未改，12模式+原3失败节点独立15passed5.54s。首次失败XML原字节在installed-sandbox-depletion-tests.raw.zip，可读XML仅去行尾空白，normalization.json记录hash；曾因此git diff --cached --check非零，保留raw后重新检查exit0才提交。

最终冻结非editable离线安装已实际完成：/private/tmp运行、不设PYTHONPATH，**918 passed in234.43s，0失败/错误/跳过**，32个真实site-packages模块在执行后与源码再次hash匹配。最终证据research/installed-sandbox-depletion-final-tests.xml和installed-sandbox-depletion-identity.json。包括修复默认模式后的真实湿干host测试，未只跑旧失败节点来代替整体集成。所有本轮代理与测试进程均结束；最后测试session84474已exit0，不再轮询。上一轮889通过和本轮917的3失败证据都保留。

### 下一可执行物理工作

1. 在现真实事件积分器上补两格非同时耗尽、液水共享面和反应同时活动的全过程；现最早候选/第二事件歧义会明确unsupported，未证明通用多事件路径。对完整湿前段和事件后段分别做有独立参照的时空收敛；不得用已通过的单格低温制造轨迹代替一维砖分布场。
2. 衔接真实湿态低温到干态高温的相态适用反解括号；当前固定括号不能在仍有液水时跨过液EOS稳定/压力域。保留strict未知或显式metastable资格、同一K与来源，不能预置dry或抹去液域限制。
3. 原污泥成套反应/毛细输运/烧结/孔隙几何/力学证据与实现、三机制公开留出预测、全周期、多代搜索和CLI/UI全部仍为原合同必需项。来源参数不能由制造值升格，不因本次数值修复宣称模型全部完成。

## 多格事件与湿态到高温：当前回合

上一回合实际实现湿干事件、修复安装组合回归并完成918项冻结验证，属于progress。本回合`9194fd1`进一步实现明确分离的多格事件：共同时间遇第二耗尽候选时有界缩短、清空原比较重新细化，每个普通RKstage重查完整状态，两个事件实际进入制造解析轨迹，所有共享面与反应源一次推进。新5+旧31共36项独立通过2.09s；加速第二事件的原失败及中间100拒步失败保留。不是同时事件或任意刚性多事件求解器。

同提交新增显式dry反解括号数值政策：仅实际NL精确0使用，正液量沿原wet括号；原EOS域/形成能/预算均不放宽。9项独立测试1.57s通过，真实单格wet300K/dry502K完整解码及mixed选择/默认语义覆盖。单独解码两状态不等于连续湿→高温轨迹。

Root真实两格fixture、事前合同和runner在test_depletion_coupled_host.py及research/COUPLED_DEPLETION_PLAN.md、coupled_depletion_run.py，初始diagnostics通过。曾错误认为裸Dfixture0代表总flux0，实际混合物校正仍迁移fixture，已修正审计为完整示踪/质量外边界账本，原物理算子不变。首次真实积分已终止：coupled-depletion-attempt-01.json，360.97s/314eval/35接受试算panel，原360s预算耗尽、无已提交事件，源绑定一致；第二事件共同tc重选实际生效，但逐格液体携焓放大终端N误差，原U门槛未达到。第二次已事前登记收紧window与显式safe_fraction及基于成本的600s预算，物理输入/精度门槛全部保留。

wet→hot同主机600s/恒1000K炉温首轮也已真实终止：wet_to_hot_attempt01.json，179.88s、4523eval、526试算panel，one event于0.0002842209402078s成功接受并继续干态到198.0041396848s，但100拒步上限耗尽；尚未完成600s或>500K。独立partial账本重算通过，不当成功。原因是全干态仍每2s重新启动普通integrate，反复从maxstep2拒到约.47s而丢自适应步长历史；拟只在所有格明确dry时一次推进到下一程序节点，保留原误差/域/资源与maxstep。高温下一次保持原240s/100reject预算，不以增加拒步解决重启缺陷。独立干段参考仅条件于实际eventU/time，不认证event时间。所有这些仍是制造固体/动力学配真实水provider的数值验证，不授予原污泥材料资格。

## 两格耗尽与湿态到高温：实际通过检查点

上一提示词答复回合没有推进实现，判为no progress；本回合实际运行、保存新证据并提交代码，属于progress。Goal保持active，原§11全范围未完成。

- `fa88647`：统一可审计safe_inventory_fraction（默认.25、严格0<f<.5）与仅全显式dry时保持普通积分自适应历史；55项独立轻测试通过7.36s，XML已保存research/depletion-safe-dry-review.xml。默认fraction历史逐位一致只适用于单独fraction补丁，不能冒称组合改动保持旧干段网格。
- 两格attempt02实际completed，444.525s/494evaluations/58试算panels，42已提交steps；两真实事件0.00028837917551549386s和0.0010885050887795723s，完整推进至1/256s，保留1/512程序节点。完整湿相变、液共享面、反应、气热组合保持原物理参数和精度门槛，使用已事前登记.4 fraction/1/1048576 window/600s预算。独立JSON复算N残差8.2756816e-18mol、元素1.1232598e-17mol、质量1.5340836e-19kg、U6.6127672e-13J通过；82个运行源码/fixture/runner文件前后及审核时一致。原attempt01失败保留。CODE_REVIEW_COUPLED_DEPLETION.md说明：原K由绑定源码与运行断言核，JSON本身无operator快照；细化摘要不是未保存试探轨迹的独立复算或全时空收敛证书。
- wet_to_hot_attempt02实际completed，198.3825s/8953evaluations/1272试算panels，原240s/100reject门槛未改。真实湿初态经一事件耗尽后至600s，终温530.7349451167803K；独立条件干段参照530.7349459107604K，差小于原5e-4K门槛。max水量5.3932176e-22mol、逐库存prefix4.6652987e-22mol、U7.1303175e-10J；运行源hash一致。高温chemical仍明确unknown/metastable，无成核结论不升级。失败attempt01仍原样保存。
- Areias2025 Fig4 A/B共26读图点及像素/刻度/误差/许可来源已实际产出，非仓库cwd重现通过。独立来源/代码审查尚在执行，未将其准入收缩本构。下一变形—几何—机械功实现合同在research/DEFORMING_HOST_DESIGN.md：规定形变气体执行器是数值耦合验证入口，湿固体/自由烧结所需骨架应力与能量仍为必需后续，不缩减Goal。

### 当前唯一重测试进程与恢复动作

非editable冻结离线安装已完成，实际从/private/tmp、不设PYTHONPATH启动完整tests/sandbox，PTY session **78292** 仍在运行（最近工具返回带此session的进度，而非终态）。目标XML为research/installed-sandbox-multicell-hot-tests.xml。恢复时先轮询同一session；观察超时不重启。完成后读取真实XML，并逐模块核源码与实际site-packages身份；未完成前不得宣称新版本全套通过。两实际实验66952及97463均已exit0，不再轮询或重复运行。src/tests/runner冻结至全套终态。

之后完成来源数字化独立审核、保存整体测试/身份和阶段提交；继续可变几何与机械功、原污泥成套材料证据、烧结/连通性/冷却力学、三机制公开留出验证、全周期、多代搜索及CLI/UI。所有原Goal必需项保留。

### 本检查点最终核验与下一步

上面78292运行记录已终止：实际exit0，**954 passed in444.54s，0失败/错误/跳过**。新XML已由ElementTree读取计数；32个真实site-packages模块在测试后逐一核对源码hash一致，cwd=/private/tmp且无PYTHONPATH。证据为research/installed-sandbox-multicell-hot-tests.xml和installed-sandbox-multicell-hot-identity.json。不要再轮询或重启78292，也不要重复旧918项。冻结版本已包含本轮全部src/tests修复；尚未加入后述隔离motion候选。

`f3aabfc`保存两实际通过实验及原失败；`01c1d42`保存Areias26点独立审查通过的数字化证据。Areias独立检查25资产hash、26点原图与Decimal75角点/舍入一致；不授予材料准入。高温结果原独立预审者也已只读复核1259状态与81依赖、完整pair/storage/逐步及prefix，报告追加在CODE_REVIEW_WET_TO_HOT.md，未冒称再次运行EOS。

可变几何设计及独立审查已完成：DEFORMING_HOST_DESIGN.md/CODE_REVIEW_DEFORMING_HOST_DESIGN.md。审查发现同V但A×2/width÷2会破坏零变形等价，已补全部格数/面积/宽度/体积与参考构形绑定及明确算术容差/拒绝测试。设计最终hash652d5af0b356466ab5b426215e44638d8f849c71b412176a7e7d6d2928ff0e59。

下一工作已经分配给review_water_resume：仅在/private/tmp/brick-deformation-motion-candidate/准备C1运动学provider与独立测试候选，不动仓库src/tests，不做GasHeat refactor。恢复先检查代理实际状态和候选文件；取得独立代码审查后再应用。先完成统一V/A/d/Vdot入口，再接可审计规定形变气体功测试及湿固体真正机械储能/烧结闭合，不能停留在气腔并改称完整砖模型。其余原Goal必需项仍全部未豁免，Goal保持active。

## 规定几何与机械功实际接入

上一回合已实际运行与保存954项安装证据，属于progress。本回合新增代码、解析验证与独立审查，亦为progress；原Goal§11未完成，仍active。

- `bb3098c`：GasHeatEvaluation公开原有一次解码的T/p/source，__call__保持Rates。Root新3测试先缺API失败后44相关通过；独立审查从HEAD旧__call__保存黄金对照，非零共享热/流/反应/外边界四Rates逐位一致，新增冻结回归后独立30通过。不是仅新evaluate与新__call__自比。
- `1dca610`：PrescribedSlabMotion正式接入固定参考C1法/切伸长与当前V/A/d及完整Vdot；独立29轻测通过，应用后29再核。原负Fraction时间下溢放入域、0维输入异常、16/32/64格按width ULP误拒均有真实失败；按坐标加法/减法ULP传播修复局部一致性，非累计位置误差证书。完整隔离源码/测试/原始失败zip与verification已保存，构造逐knot/运行逐sample检查不冒全域float证明。
- 同提交DeformingGasHeat在同一当前几何及同次T/p上计算相对输运与−p*Vdot；只允许显式压力匹配气体执行器/制造输运网络。父thermo变更在replace之前拒绝；flow h不额外pQ；当前bulk用于反应；参考count/A/width/V完整匹配。14实际host测试4.87s通过，独立host+motion+gas诊断共47通过4.87s，并用同次测试hook确认三档每个实际step均为规定dt。
- 闭式绝热压缩/膨胀三档dt=1/128,1/256,1/512s，实际256/512/1024steps。最大T误差6.7844911e-4、1.6957182e-4、4.2387968e-5K，减半比4.000954/4.000471；最细P与等熵不变量相对误差7.8168645e-8，U解析误差9.3253496e-4J。原最细门槛不变，粗档结果没有冒称通过最细要求。各档stdout、XML及从XML抽取metrics一致，未重复运行补造指标。

当前冻结非editable离线全sandbox测试 **session1707** 已实际启动并返回进度，XML目标research/installed-sandbox-deforming-gas-tests.xml；尚未终态，不宣称新全套通过。恢复先轮询同一session，不重启；src/tests冻结。结束后解析真实XML与34个预期新安装模块（须实际计数）再保存身份。原954版本和两实际实验均已终止，不重跑。

下一物理工作由review_water_resume独立准备research/DEFORMING_SOLID_ENERGY_DESIGN.md，只读现湿固体整体U/几何并核2–3份原理主来源，定义总应力功、骨架/界面储能与thermalU分账，不把气体孔压乘bulk变化代替湿砖力学。仅文档/证据，不动冻结源码；完成后独立审核再实现。真实原污泥材料、自由烧结/孔道/冷却力学、公开三机制留出预测、完整周期、多代搜索和CLI/UI仍为原合同必需，不缩范围。

### 规定气腔分支最终冻结检查点

session1707已实际exit0：**1001 passed in448.58s，0失败/错误/跳过**。XML已实际解析；34个真实site-packages模块在测试后与源码再次hash匹配。cwd=/private/tmp、无PYTHONPATH，结果为research/installed-sandbox-deforming-gas-tests.xml与installed-sandbox-deforming-gas-identity.json。所有测试进程已终止，不再轮询1707/19915，也不重复旧954整套。当前源实现止于bb3098c/1dca610加上述验证，尚无skeleton_energy实现。

湿固体下一合同DEFORMING_SOLID_ENERGY_DESIGN.md已核读三主来源并给具体接口：Etotal=thermalU+温度独立骨架/界面内能；同势给应力，Wtot含储能率、耗散与真实孔体积功；初始固定Ns，反应体积/机械能导数后续仍必需。独立初审纠正耗散功率D与Rayleigh势Phi=D/2术语，并把湿恒温oracle限定为固定液汽库存，活跃相变不能据U恒定推T恒定。修订hash ef7c5795cd5c6e451b4cf97cac6ffd1f46ecf9fae3da434d099573547184a219；boundary_program正在完成最终来源/接口审查，恢复先读其实际状态/报告再实现。没有待运行EOS；不因文档预登记而宣称湿固体机械实现完成。

湿固体设计最终APPROVE已闭合：Root在热U推导中补齐总E已含的explicit_body_heat，最终设计hashbc8392df0f4d3921b10fc6207f0d6fa526038218545400516d0fee174477cb08；独立CODE_REVIEW_DEFORMING_SOLID_ENERGY.md实际核读绑定，保留原修订史。总/热能身份、target误差传播、accepted RK分项功账本仍为下一真实实现必需门槛。

review_water_resume已接新的隔离任务，仅/private/tmp/brick-skeleton-energy-candidate/准备skeleton_energy.py及独立测试/失败记录：明确制造的log-strain势、内部界面能、Rayleigh耗散、Piola和能量率及保守数值预算；不改repo src/tests、不做EOS/storage/integrationhook。恢复先检查代理与实际文件，完成后独立审查再应用。尚不能宣称该provider已经完成或通过；本版本完整安装证据仍仅1001项/34模块。

## 骨架、目标区间与普通RK分项功：实际完成检查点

本回合新增可执行源码与独立验证，属于progress，Goal仍active，原§11未完成。

- `skeleton_energy.py`：温度独立log-strain弹性/显式取向内部界面势，同势Piola与能量率；D与Rayleigh D/2区分。只准入显式制造参数。23测试通过0.08s；独立240项有理atanh对数级数核75个输出包络。原候选与失败历史zip保留；Root应用时误去sys import导致1failed22passed，application-failure.xml原样保存，恢复import后23通过。
- `solid_fluid_storage.py`：显式target_energy_error_bound_j向外传播，负tiny Fraction拒绝、正tiny不归零，默认零旧结果逐位兼容。新11加旧23共34测试通过0.69s，独立34通过0.66s，保存两个XML。尚非Etotal storage。
- `integration.py`：可选elastic/interface/dissipation/pore/body分项功，schema每次评价锁定，实际接受stage同权积分；每项quadrature roundoff和总量分解残差有理记录，累计绝对分解残差受既有能量绝对预算约束。独立44通过0.50s，旧HEAD nonlinear 123接受/3拒默认路径逐位一致。仅普通integrate；wet wrappers/耗尽panel尚未转发，净U自适应不证明抵消分项截断准确。

冻结非editable安装session46721已实际exit0：**1051 passed in446.61s，0失败/错误/跳过**。XML实际解析；35个真实site-packages模块逐一与源hash相同，cwd=/private/tmp，无PYTHONPATH。证据：research/installed-sandbox-skeleton-components-tests.xml和installed-sandbox-skeleton-components-identity.json。不要再轮询46721或重复原1001全套。

下一工作：review_water_resume在/private/tmp/brick-deforming-solid-storage-candidate/准备有明确TotalEnergyTarget与实际完整固体身份的点储能候选，9项dry轻测先通过，独立review_convergence_resume审核中；Root仅在完整suite终态后开放≤90s真实wet验证。尚未应用repo，不属于上述1051安装证据。boundary_program在/private/tmp/brick-depletion-components-candidate/追耗尽panel/wrapper分项功后续，不改repo。点储能完成仍需明确作用域的积分状态、实际湿机械host和独立轨迹验证；材料证据、自由烧结/孔道/冷却力学、三机制公开留出、全周期、多代实验及CLI/UI全部仍必需。

## 模型能量身份、点储能与耗尽分项的应用检查点

`41e5911`保存上一1051/35安装版。新ConservedState追加默认None不透明energy_model_identity，RK与inventory writeback保留，旧三热主机拒绝非None；新13项先RED后共73通过，独立73通过并实际比旧HEAD三个默认轨迹。DeformingSolidStorage完整固体provider绑定与显式TotalEnergyTarget、机械/几何/表示误差传播，独立11通过、应用后11通过；全部原wet大误差拒绝和新exact rational制造volume定义保存archive。后者不是实际原泥物性证据。

耗尽分项候选正式按原字节应用：terminal取实际Fraction(end-start)权重、全程schema/tag核查、跨普通/事件段累计绝对分解残差在整path commit前检查；两真实wrapper仅转发原cell components，不额外加heat。独立25通过，另实际时变分项经29拒步/1573observations完整越event至.2s，终端有理权重和prefix复核；dry schema变更保留19已commitsteps及原湿模式。Root应用再测38（含身份13）通过0.93s。README/原RED/log/manifest/两基线源码及输出均归档；旧None默认baseline实际重跑逐字节相同。

新完整冻结安装session89265仍运行，唯一恢复动作先poll同session；新src/tests冻结，不能把局部测试当新完整suite。终态后解析实际XML与真实site-packages逐文件身份，再保存版本验证/提交。下一新host隔离候选需同次total->thermal inverse供传热/输运/porework，保留完整误差/几何/source，尚未接实际时间推进或wet/depletionhost准入。原§11未完成，Goal持续active，本回合有实际实现/测试属于progress。

### 总储能/耗尽分项整包终态

session89265已实际exit0：**1089 passed in453.56s，0失败/错误/跳过**。XML实际解析，36个真实site-packages模块逐一与32965ce源码核对一致，cwd=/private/tmp，无PYTHONPATH。research/installed-sandbox-total-storage-tests.xml及installed-sandbox-total-storage-identity.json已保存。没有尚未观察终态的旧完整suite，不再轮询89265/46721。

下一host仍隔离，不在此1089证据中：私有thermal assembler复用、point current_storage与全能量scope候选正在审核。初等向压缩η0解析试验attempt05温度过2e-5K但pore功未过1e-6J，保留失败；64→128呈二阶趋势不等于门槛通过。事前登记下一512/1024/2048三档与实际网格/拒步统计，原门槛不动，只因已测成本扩资源wall20→90s且整个attempt≤150s。作者已收到安装终态后开跑通知。新current_storage曾插入中部破坏旧positional，独立审查指出后改尾追加并新增回归1pass；尚待最后代码/物理审查与应用。

## 规定形变总能量主机当前恢复点

本回合实际完成点储能、identity/depletion组件与干态机械主机，属于progress，Goal仍active。干态首轮pore失败保持；细化后512/1024/2048实际无拒步，finestpore7.2252e-7J过1e-6J。源码修复只涉及审核提出的current_storage尾追加和initializer严格输入，原physics/gate不变。独立13轻测及真实旧热/气/反应golden通过，Root应用13通过；完整archive/readme与3src应用精确比较已核。

新fullsuite唯一session75509正在运行（开始已返回6%进度），源码/tests冻结。完成后实际XML计数与37预期实际安装模块身份逐一核，不重旧1089套件。下一wet entropy oracle在/tmp独立推导，尚不运行湿EOS；未来用同Nl=1/Ng=.01/Ns2/300K与10%isotropic，独立water EOS entropy closure与主机energy积分比较，不能调用被测storage作参照。当前还没有此湿积分验证成果。

### 规定形变固体主机完整安装实际终态

源码fa3194b冻结安装session75509实际exit0：**1103 passed in523.90s，0失败/错误/跳过**，包含正式默认fine3档扫描。37个实际site-packages模块与源hash逐一相同，cwd=/private/tmp、无PYTHONPATH。实际XML和installed-sandbox-deforming-solid-identity.json已保存。当前没有待结束的旧完整suite。

独立湿熵参照已完成数学/代码审核和9轻测试，dry volume残差漏门槛先RED后修，没放宽gate。真实30s硬限两点probe仅2.0704s：初态p304469.313540Pa；lambda=.9，T300.186070144980K/p567435.655362327Pa，ΔS−4.01e-11J/K、ΔV−1.36e-20m3；halfxtol差T2.503e-10K/P4.899e-7Pa过原gate。154是公开water.state_tp调用次数，不是内部EOS求解次数。optional已测storage forward.1696s/inverse.8125s，使用oracleT初始化的roundtrip不冒实际trajectory。结果与完整source/assets/limits在/private/tmp/brick-wet-deformation-oracle。

按实测成本不盲跑2048步湿扫描或450s粗pilot。Root另事前登记30s硬限真实wet host前缀smoke：同物理motion/库存，只推进原曲线0→1/64s，cap1/128、≤4接受/4拒，原gate不动，失败保存；不能将此前缀升级成原完整10%轨迹通过。并行仅可做来源/无EOS准入设计与快速同EOS后端微探针，生产backend未改。
