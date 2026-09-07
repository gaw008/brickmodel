# 物理沙盒 Goal 进度

更新时间：2026-09-07 UTC。完整任务合同：[GOAL_BRICK_PHYSICS_SANDBOX.md](../GOAL_BRICK_PHYSICS_SANDBOX.md)。

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
