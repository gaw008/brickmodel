# 实际验证报告：G0/G1 基础与G2有界模块

日期：2026-09-07 UTC；平台 macOS arm64，Python 3.12.13。本报告只有已实际运行的验证，不代表完整 Goal 验收。

## 保存原生输出与实际反解温区增量

[单点后验核验证据](research/water-saved-output-correspondence-v1/README.md)：预选最大反解温差端点step8/cell1，保持原T±epsilon。窄数值根盒严格包含失败保留；拓数值密度括区后1.638728秒完成局部分支连接，31次/16叶覆盖且独立Fraction复核通过。固定原生输出查询的数学EOS残差、正斜率根括区及宿主舍入给出1.62099e-20 m³/mol界，小于原1e-16声明，7独立pure与保存数据复算通过。它只验证该查询和条件性的实际T区间，不等于全部16端点、原生算法整体或真实材料误差认证。

## 混合单位完整耗尽与真实水局部分支研究

新增[混合单位控制器证据](research/mass-wet-exact-controller-v1/README.md)：源码77项77.65秒、实际安装77项76.75秒，94安装模块身份一致；独立7主测试+9负控。实际两格解析测试液体完成两个耗尽事件与干态尾，逐事件六门槛、独立ODE和原始前缀守恒通过。此结果不是原生水或原污泥全流程验证。

[真实水局部共存连接](research/water-coexistence-connection-v1/README.md)：固定原系数，预登记六盒原3通过/3未决，加权坐标范数后5通过/1未决，保持K图像/包含余量与严格阈值。指定300±1e-7K盒经31次区间导数、16正导数叶连接局部机械根，独立保存数据Fraction复算通过。没有验证整个温度域、实际inverse温度误差覆盖、全局相或原生浮点误差界；不据此开启生产wet压力准入。

## 取消与续算增量

`research/checkpoint-v1` 保存事前PLAN、50项安装测试、49模块前后核验及四个串行受监督原生运行。真实水制造湿态refinement1案例先取消1步，续算再取消到累计2步，CLI续算至4步完成；与独立不中断4步比较，全部N/E状态、账本及终态T/P逐位一致，原独立账本阈值通过。剩余步数/拒绝次数/积分wall按完整父历史扣减，累计积分26.8253s。两类负控证明分段分别通过的能量/功分项舍入误差不能在合并时重置原额度。仅验证此固定步长普通积分器案例，不主张通用自适应逐位续算、强杀恢复或原污泥全流程完成。

## 运行时来源图增量

`research/run-provenance-v1`：40项实际安装测试通过，48安装Python模块及目录原始字节匹配。19方程/38参数声明组成4个输出依赖入口，原始案例、目录、参数指针、AST代码行号和来源资产均绑定。CLI单例/重放均completed各2步（外部15.5579/15.5387s），数值/账本及来源图一致；沿用原独立账本阈值，CLI与Python压力查询一致。额外来源文件缺失不伪填数值，未知来源显式呈现；未将资产覆盖率冒充材料适用性或实验覆盖率。未改求解器，也未重跑旧全suite。

## 统一入口增量验证

`research/cli-delivery-v1` 保存25入口测试XML、非editable包47模块前后核验、实际CLI单例和重放、四量来源查询、两次独立账本审计及四格新构建初态验证。run/replay各2步、外部15.5208/15.4597s，状态/账本/初终态诊断数值完全一致（计时除外）；四格仅初始化与callback，4.0832s。没有重跑未修改的物理求解器1293全suite，也不将此前全suite直接算作新增入口的覆盖。代码审查修复非完成退出码、未登记重放文件、嵌套manifest遗漏、来源导航过度声明和初态检查未接入问题。完整来源依赖图、跨平台干净环境、检查点续算和全周期材料模型仍未完成。

## B2 历史修复

源提交：`0634e80b1fa4d69c195022f1c7ecd79a16110fe2`。

| 实际运行 | 结果 |
|---|---|
| `run_tests.py` 指定新输出目录 | 14单元测试；全部8类NUM门槛passed；绑定bound |
| focused实际积分数 | B2 30 + B1 4 = 34；没有漏掉单元测试内2次调用 |
| `run.py --suite frozen --verification ...` | 22情景integrated，全部passed_frozen_suite |
| 独立 `audit.py` | 322204 checks通过，固定门槛1e-6未变 |
| 最大反应暴露误差 | 6.917104489190251e-8 |
| focused资源 | 77.61s，peak RSS 41.52MiB |
| 22情景资源 | 15.92s，peak RSS 94.63MiB |

命令、实际源码/输入/结果和校验包见 `research/b2-bound-0634e80/summary.json` 与 `reproduction.tar.gz`。原失败根因与未绑定隔离复跑保留在 `B2_ROOT_CAUSE.md` 和原始目录；未冒充当前绑定运行。打包成功不等于整个离线包已做全部重新积分。

该结果只验证原B2固定孔隙、给定温度、synthetic域。不提供真实材料参数或完整湿砖能量验证。外部`time -l`曾受sandbox kern.clockrate限制，未把其非零退出隐藏成成功；上述耗时/RSS来自实际内部计量。

## 新内核模块

源码模块位于 `src/sludge_sandbox/`；相应测试位于 `tests/sandbox/`。

| 模块 | 实际覆盖与边界 |
|---|---|
| evidence / units / geometry | 56项：分类、未知、适用域、方程依据根、布尔/非有限输入、单位、共享面积/孔容；不是材料外部验证 |
| materials | 25项：干湿料账目、额外加水、原泥/SSA分组、独立分析类型、矿相身份声明与非法值 |
| thermochemistry | 41项：真实NIST原值、分段范围、cp/h/u关系、反解、多解/间隙/精度不足/溢出；原拟合未平滑改写 |
| gas_transport | 79项：全气体库存/EOS、压差反馈、质量平均修正/上风Darcy、零库存方向、一阶修正离散收敛、归一化诊断 |
| exchanges | 10项：半格导热、气温/辐射环境分离、实际物种焓耦合、R一致性、净流与分项一致、相反溢出拒绝 |

独立审查报告分别在 `research/CODE_REVIEW_*` 与 `PHYSICS_REVIEW_GAS_TRANSPORT.md`。首审问题和修复前失败均保留。气体中心修正曾破坏零库存不变域；改为修正漂移的上风组成后，另150场景/450分项方向检查通过，最大全扩散质量相对舍入6.34e-15。这个离散是一阶数值处理，尚无完整PDE时空误差声明。

NIST 的原文表值核对是移录/拟合函数验证，不能称独立现实实验验证。热化学审查还使用独立求积、Decimal能量及反例；全部范围见其报告。作者/代理审查不等于外部专家认证。

## 干净安装的实际检查

从空目录创建 `/private/tmp/brick-sandbox-g1-install-20260907`，以冻结锁文件、非editable、离线方式安装。未设置 `PYTHONPATH`，从 `/private/tmp` 运行仓库的sandbox测试，实际导入位置为该环境的 `site-packages/sludge_sandbox`。

```sh
UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache \
UV_PROJECT_ENVIRONMENT=/private/tmp/brick-sandbox-g1-install-20260907 \
uv sync --frozen --no-editable --extra dev --extra research --offline

env -u PYTHONPATH /private/tmp/brick-sandbox-g1-install-20260907/bin/python \
  -m pytest /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox -q \
  --junitxml=/Users/wanggaoying/Desktop/brickmodel-github/docs/sandbox/research/g1-installed-final-tests.xml
```

最终结果：**211 passed，0 failed，0 skipped**。首次非editable测试与最后类型注解同步后的测试分别保留，不覆盖首份证据。最终XML为 `g1-installed-final-tests.xml`；依赖/实际导入位置/首次pip离线解析失败说明在 `g1-installation.json`。冻结 `uv sync` 复用了已缓存锁定轮子；这不表示没有缓存的任意新机器可以不下载依赖。

这个检查只证明包安装、导入与上述模块测试。新CLI/UI、数据准备命令、全周期求解、搜索和恢复还没有通过安装流程，不把它计作完整 V12/U01–U04。

## 对现实的验证状态

已提取 Wang 2021 的12干燥条件/186图中实验符号读数；40/60°C拟合、50°C留出的计划已登记，但尚未执行内核预测对照。Nowicki和Mohajerani的参数/条件/语义问题仍隔离。三个机制组的独立预测对照、完整原污泥材料域与整砖耦合验证均未完成。

`software_status=implementation_in_progress`；`scientific_status=partial_sources_no_complete_raw_sludge_domain`；`deployment_status=offline_research_only`。本 Goal 保持 active。

## G2 当前完整模块安装复验

已审核模块在冻结的Python3.12.13环境中非editable安装，包含锁定的 `iapws==1.5.5` 水物性可选依赖。最终源码重装使用：

```sh
UV_CACHE_DIR=/private/tmp/brick-sandbox-uv-cache \
UV_PROJECT_ENVIRONMENT=/private/tmp/brick-sandbox-g2-install-20260907 \
uv sync --frozen --no-editable --extra dev --extra research --extra water --offline --reinstall-package sludge-vme
```

从 `/private/tmp` 执行该环境Python的 `-m pytest /Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox -q`，未设置PYTHONPATH。实际 **429 passed in 16.01s，0失败、0跳过**。13模块的实际导入位置和源码hash逐一与工作区一致；见 `research/g2-installed-final-tests.xml` 与 `research/g2-installed-final-identity.json`。早期314测试快照保留，最终证据没有覆盖旧结果。

| G2新增模块 | 实际覆盖 |
|---|---|
| reactions | 49测试，元素/摩尔质量独立配平、联合消耗与不可表征库存增量拒绝 |
| integration | 28测试，SSPRK2真实子步与不等半步误差估计、局部/前缀舍入、失败/取消/超时 |
| gas_heat_model | 26测试，刚性气相库存/U实际解码T/P并反馈传热/扩散/Darcy/物质焓 |
| conservation | 37测试，精确加权质量/元素、分格分步及前缀的库存/U账本；不代表热物性重建 |
| water_properties | 78测试，原始来源和安装源码门禁、同相参考偏移、Cp/Cv导数及有限性；未接混合气 |

全部上述模块有独立审核记录，修补前反例未删除。水模块另有66状态和独立导数有限差分核验，最大Cp/Cv误差分别2.68e-6/6.55e-7 J/(kg K)，门槛1e-5未放宽。官方33水表点是公式/软件核验，不是新的实验观测。

## 刚性气相导热时空收敛

`research/RIGID_HEAT_CONVERGENCE.md` 及对应JSON记录7个实际制造案例：空间N=8/16/32，对连续解析余弦模态误差阶为1.967057/1.991756；时间步0.1/0.05/0.025s，对离散解析模态阶为2.011998/2.005992。N32再减半时间步，变化为其空间误差的0.00313%，低于预登记1%污染限。预登记阶数范围1.8–2.2没有改变。

7例无拒步，系统U残差0，末态逐格账本残差最大3.89e-16 J；资源8.52s/40.625MiB。独立审核重算解析轨迹与Fraction账本，并验证真实失败注入出口为非零。源码和完整轨迹均有hash绑定；纯格式检查曾报告脚本末尾空行，详见GOAL_STATUS，不冒充全格式检查通过。

这组实验只证明刚性气相导热离散，不证明水迁移、形变或真实砖全周期收敛。CLI/UI、完整材料包和三机制组实验预测仍未验收。

## Baloi 2025候选证据

已核读出版商原文，保留同研究5组体积配比/烧后性质和Table3派生计算；4份资产hash与提取重跑一致，独立审核通过。N19/N20导热计算与印刷值差异保留，低温有效cp显式归类派生；没有将这些烧后数据移作湿坯/高温本构。该来源增加终态对照候选，不使完整原污泥材料域成立。

## 连续边界与显式理想水汽增量复验

`622d376` 增加连续边界程序及41测试：有真实integrate节点连接和独立分段热量解析检查；另独立1000极端浮点插值核验。`7d3aaca` 增加固定R理想水汽热量转换及28测试：独立2071温点的最大h-u残差1.46e-11 J/mol、转换差值残差4.71e-11 J/mol，du/dT-Cv最大4.23e-8 J/(mol K)。最终源码hash均已绑定独立审核。

加入两模块后再次按上述冻结/非editable/离线方式重装，并从/private/tmp执行全部sandbox测试，实际 **498 passed in 1.99s，0失败、0跳过**。15个site-packages模块与工作区逐一hash一致，XML及身份记录为 `research/g2-installed-boundary-vapor-tests.xml`、`research/g2-installed-boundary-vapor-identity.json`。这次耗时只记录当前缓存/环境下观察，不和旧16.01s运行解释为性能改进。

新边界只是连续输入及积分节点；动态气体库/对流辐射组装仍待完成。水汽模块未自动加入现有Shomate组装器，保留纯水R门禁，并显式标记混合物资格未建立。当前没有完成液/气相平衡、固液气储能反演或全湿砖应用验收。

## 动态外边界与给定压力储能增量

`a84f46e`：ProgrammedGasHeat在每个实际积分阶段更新外部完整气氛/总压，求末半格导热与对流/辐射串联的表面温度，再调用原面通量/物种焓账本。15测试通过，独立80组非线性表面根最大温差1.93e-9 K；另有反向压力出流供体焓手算与真实升降温积分验证。制造案例不赋予真实材料系数资格。

`23cee3d`：PhaseStorage提供各相显式固定压力的物种U/H/V求和，条件反演保存实际MonotonicPath及来源，不自动证明声明的连续单调区间。22测试通过。大生成能量化平台、相消、导数下界乘积下溢等实际失败保留后修补；裸Shomate段不能默认重标物种。独立真实液水/水汽三组往返最大T差4.37e-10 K、U残差6.80e-8 J；固定p导数遵循Cp−p dv/dT，不冒用Cv。

经当前冻结非editable离线重装，从/private/tmp运行最后全部sandbox测试，**535 passed in 2.94s，0失败、0跳过**。17个实际site-packages模块hash均与工作区一致，全部测试源码hash记录于 `research/g2-installed-programmed-storage-identity.json`；最终XML为 `research/g2-installed-programmed-storage-final-tests.xml`，较早同535项快照亦保留。没有宣称这就是CLI/UI或原污泥全周期安装验收。

本次审核曾误以为pytest显式abs未指定rel会放宽比较。读取当前pytest8.4.2源码及实际反例证明该判断错误，审核记录已更正；显式rel=0是可读性澄清，不是虚构的旧门槛缺陷。最初粗积分未通过原2e-6 K绝对门槛的实际失败仍保留，物理结果门槛没有放宽。

该535项检查点时，水/气孔体积与压力机械闭合仍未实现；后续增量见下。相变/液态迁移、固体实际材料热化学、烧结/应力及三个机制组的公开预测检查仍未完成。

## 刚性液水—气体闭合与连续热量模型增量

`e46321b`：固定流体腔体、固定库存和平界面条件下，联立IAPWS液水占积与理想混合气压力。17项测试及独立审核通过，包含液体受压收缩、无液分支、独立压力根与微量物种分压下溢回归。显式压力区间和体积/压力分辨率门槛保留。此处没有毛细或气液化学平衡。

连续热量模型保留原Shomate系数和温区，使用显式原焓锚点积分Cp并公开分段偏移。22项测试通过；独立80位Decimal核查120个点。真实GasHeatModel中制造气体从500 K跨600 K接缝至700 K，独立解析总热量5400 J，各状态和分步账本核对通过；接缝2.2 s由调用者显式提供，不代表自动事件检测。另有NIST O2在699.9/700/700.1 K的实际反解验证。

固定相库存的闭合路径推导 `Cclosed=Cp_total−T A²/B≥ΣCv>0` 已独立审核。直接IAPWS与独立压力求根的三状态中央差分最大偏差2.79e-7 J/K，小于预登记1e-4 J/K；这是导数恒等式核查，不是完整储能反演程序或砖坯实验。

冻结、非editable、离线重装后，从 `/private/tmp` 无PYTHONPATH执行全量sandbox测试，实际 **574 passed in 5.63s，零失败/跳过**。19个真实site-packages模块源码与工作区一致。原始产物 `research/installed-sandbox-574-20260907.xml` 和 `research/installed-sandbox-574-identity-20260907.json` 保存模块、测试、锁文件和XML身份。既有535项记录保留；未把测试数量当作现实准确率或全流程完成度。

## 闭合路径储能与实际热量积分

`94257d6`新增水局部响应与最终数值压力括区：21项新水导数+78项旧水+23项压力闭合组合通过，独立不同步长有限差分和三压力根核对通过；记录见两份独立审核报告。水局部导数和数值函数括区不自动构成EOS全区间误差界。

`315337a`的rigid_storage每温度试算重新求液水占积/气压，使用同一压力求物种U/H与闭合热容。条件反解保留显式数值envelope，正下界/上界有向算术以及源来源；端点符号不确定、粗压力预算和表示精度不足时拒绝。18测试实际通过18.48s，真实积分每次operator调用均执行实际反解。单格电加热反馈下库存逐值不变，U与积分功账本在1e-8 J绝对门槛内一致，终温与独立嵌套求根在1e-4 K内一致。源和范围见 `RIGID_STORAGE.md`，不作为原泥实验或固体/相变模型验证。

冻结非editable离线重装后，在/private/tmp无PYTHONPATH运行全部sandbox测试，实际 **619 passed in23.27s，0失败/跳过**。20个site-packages模块与工作区逐一hash一致。原始XML `research/installed-sandbox-closed-storage-tests.xml`，安装/测试/锁文件身份 `research/installed-sandbox-closed-storage-identity.json`；原574项检查点保留，两个既有模块的本轮扩展没有重写旧验证产物。

## 多格流体气热、连续相与原始TGA增量

`e24a560`：连续Cp派生相适配新增3测试，与原PhaseStorage合计25通过；独立43项相关测试通过。额外NIST O2跨700/2000 K接缝7点反解最大T偏差5.30e-11 K，零液高温哨兵确认不调用水物性；无IAPWS低高温自动拼接。

`b8ae2aa`的RigidFluidHeat独立16测试通过40.10s。两格实际积分每trial按实际库存/U重解P/T/气孔，液水mol不迁移，气体换格并反馈压力，内部共享面的mol/J及系统账本通过事前门槛。另有双气不同质量扩散、供体焓绝热排出、反向边界携入独立手算、半格Dirichlet热阻与域退出。独立发现同源水汽provider因私有后端对象身份误拒，经RED后按完整语义身份修补并复验。原完整反解误差/括区与条件资格保留。没有液迁移/相变或多格收敛结论。

`eacdad3`保留CC BY Ghodke2022单次原TGA，共11575记录；独立检查所有原列/SI转换、噪声回升保留、原件官方hash/size与许可。没有独立实验holdout，也没有把PDF拟合表或DTA µV当运行参数/反应热。首次派生CSV的CRLF导致暂存格式检查失败，停止提交后原版本归档，再仅改LF；字段逐值不变，重建与格式最终复验通过。

当前冻结非editable离线安装，在/private/tmp无PYTHONPATH实际全量 **638 passed in63.82s，0失败/跳过**；21个site-packages模块hash与工作区一致。产物 `research/installed-sandbox-fluid-heat-tests.xml` 与 `research/installed-sandbox-fluid-heat-identity.json`；原619项检查点保留，不将新增原TGA行数混算为测试或独立实验数。

## 化学势与相间迁移增量

`f92de4f`的36项化学势测试及独立审查通过；独立显式Table1八温点oracle预登记后运行，peq相对差最大2.59e-13，h差≤2.57e-9 J/mol、s差≤7.28e-12 J/(mol K)。该oracle不用候选模块或原_phi0计算参考理想项，液体仍共用来源门控EOS。对native真实饱和压的模型近似偏差完整保留（500K约−11.24%），未设置虚假的零偏差通过门槛。产物 `research/water_chemical_oracle.json`，首版输出另存，独立审核包含脚本核查。

`f8b5a86`的16项相变耦合测试独立通过61.11s。真实绝热蒸发/凝结积分均按预登记水库存1e-11mol、U误差1e-7J、方向性温变超过1e-4K验证；不重复添加潜热。有限库存超步拒绝并保留初态，零汽化学势不伪造有限值，无液界面缺成核模型时退出。系数和载气是制造值，闭合反演误差界仍有条件；这些测试不是实测干燥/完整熵轨迹/全周期砖验证。原XML为 `research/water-phase-transfer-tests.xml`。

全量冻结非editable离线安装验证最终 **690 passed in124.57s，0失败/错误/跳过**；从/private/tmp运行，无PYTHONPATH，23个真实安装模块hash与工作区一致。最终XML与源码/测试/锁文件身份分别为 `research/installed-sandbox-phase-transfer-tests.xml`、`research/installed-sandbox-phase-transfer-identity.json`。性能profile另列且没有实施后加速声明。

## 有界缓存、石英来源与单相固体

`3ed9aa1`缓存18项新增测试、相关181项独立通过。修复独立复现的底层求解器删除后异常类别回归，预热后故障检查仍有效。相同反解3对裸计时中位1.3000s/0.8261s，所有T/P/残差/括区/迭代数逐值一致；饱和非线性求解从205次降到5次，真实TP求解仍205次，命中EOS检查没有跳过。详见 `research/CLOSED_STORAGE_PERFORMANCE.md` 与原始JSON；不是全周期速度保证。

`77b4515`石英来源原HTML与有限事实独立核查，2温段16系数及76个格式舍入输出检查通过。原提取只检查3列的版本已归档，新增Gibbs列核验后通过；物理相变焓差和拟合Gibbs差没有归零。纯石英来源候选不提供密度、成分比例或砖材验证。

`12f6f06`单相固体29测试，与PhaseStorage旧测试共51项独立通过；50组独立驻点/导数检验通过，内能差分最大误差7.25e-9 J/(mol K)，低于预登记1e-6门槛。实际PhaseStorage求和与320K反解通过，仍是给定压力的条件反解；固体占积尚未接入rigid整体系统。制造误差预算曾小于精确p0*εv，保留原比较，显式增加制造预算余量后通过，未改变科学验证门槛。

冻结非editable离线全量安装验证：**737 passed in78.91s，0失败/错误/跳过**，24个实际安装模块与工作区hash一致。原XML `research/installed-sandbox-solid-cache-tests.xml`，身份 `research/installed-sandbox-solid-cache-identity.json`；旧690项记录保留。测试数量与运行速度均不表示三机制实验验证或完整材料域已经完成。


## 固液气整体储能、输运与蒸发耦合

`96d70dd`实现SolidFluidStorage：23项最终独立测试通过0.63s；固定bulk减去实际固体占积，每个trial在总U中包含固体并重解流体压力，体积误差在干支也传播。单独60位Decimal参考不调用候选求解器，三状态V/P/U/H/C、U反解、实际25W/10s积分均通过预登记门槛；71次operator执行真实整体反解，保存库存不变、各时刻U−U0−25t误差为0。零表示本次浮点比较结果，不表示没有模型误差。产物`research/solid_fluid_analytic_oracle.json`与`research/solid_fluid_candidate_check.json`绑定最终源a592373d。

`3f69e34`实现SolidFluidHeat与WaterPhaseTransfer显式双host支持。13新案例加16旧相变案例独立运行29项54.68s；在该次收集后强化的两个案例另运行2项17.37s，原XML与强化XML分别保存在`research/solid-fluid-heat-review.xml`和`research/solid-fluid-heat-strengthened-review.xml`，不混淆快照。制造固体/几何在wrapper的门禁遗漏已修复并独立复验。两种固体Cp下真实蒸发终温的条件误差区间严格分离，固体域退出单独隔离验证；不据此推定真实泥料动力学。

最终冻结非editable离线安装，从/private/tmp无PYTHONPATH运行全部sandbox测试：**773 passed in96.01s，0失败/错误/跳过**。26个实际site-packages模块与工作区源码逐个hash一致，最终强化测试均包含在此次全量执行中。XML与身份分别为`research/installed-sandbox-solid-fluid-tests.xml`、`research/installed-sandbox-solid-fluid-identity.json`。完整湿砖、动态收缩、公开三机制预测、多代搜索与界面验收仍未完成。


## 动态固液气边界与完整相变主机

ProgrammedSolidFluidHeat每trial仅调用一次实际固液气base.evaluate；完整动态气体库影响压力/组成驱动流及供体焓，半格导热与膜对流/辐射共同确定真实表面温度。8项新测试包含实际升温/保温/冷却、非线性辐射独立根、实际气氛入流及每步mol/J账本。WaterPhaseTransfer显式第三host另5测试包含真实外热+蒸发、完整诊断及breakpoints转发。独立最终兼容/组合32项通过68.29s，原XML为research/programmed-solid-final-review.xml；制造系数未升级为材料物性。

独立60位Decimal常C线性炉温对照，执行完整40s三段程序：首次十进制dt=.4/.2/.1出现节点极短余步和后续自适应增长，uniform=false，因此完整判定false；脚本/计划/实际轨迹原样保存在research/programmed-solid-decimal-step-first-run.zip。没有修改积分器或声称该时间步策略已被修复。随后在复跑前登记仅将步长改成二进制精确.5/.25/.125，原材料/边界/容差/比例门槛不变；最终三档确为uniform且零拒步。

三档最大轨迹温差为0.000520179、0.000127759、0.0000316464K，比例4.07158、4.03707，均满足原门槛。库存逐状态精确不变，最大每步能量账本误差2.85e-11J内、全前缀3.50e-10J内。最大条件温度反解界3.994e-9K，本线性极限下表面残差允许界的40s保守累计温度量级5.947e-11K，均远小于观察离散误差。产物research/programmed_solid_analytic_reference.json与programmed_solid_candidate_check.json包含全轨迹、逐面热量、实际次数/耗时和代码hash。公式与脚本由独立代理只读核查，实际运行由主代理执行，不混淆角色。

这证明一个有界惰性固体/干气模型在指定程序下的时间收敛，不证明液水空间迁移、全湿砖时空收敛、长期真实烧成、收缩或实验预测。动态湿相变案例仍是短时制造系数验证。


本轮最终冻结非editable离线安装，在/private/tmp且无PYTHONPATH执行全部sandbox：**786 passed in109.64s，0失败/错误/跳过**。27个真实site-packages模块与工作区hash一致；证据research/installed-sandbox-programmed-solid-tests.xml及installed-sandbox-programmed-solid-identity.json。此安装验证包含全部13项新增测试及最终wrapper，旧773项检查点保留。


## 液相共享mol/焓面及连续流离散对照

`7bd4a38`：独立20项液面测试0.04s及6项主机测试22.89s通过，XML为research/liquid-transport-review.xml和liquid-solid-host-review.xml。包含精确Fraction正反向供体v/h、零与非零下溢、关系域/连接/来源、仅液制造参数在两外层主机的隔离门禁，以及真实0.001s两格湿水逐前缀水/U/面账本。固体及封闭气体保持，名义压力随液库存反馈；名义T变化没有被宣称超过温度误差预算。pressure_interval_scope=fixed_decoded_temperature、full_inverse_direction_certified=false不变。

主代理另从已有MOOSE每相Darcy方程推导恒温可压缩稳态参考，使用共用真实纯水EOS与独立Gauss积分/brentq生成压力剖面，不调用候选face。300K、50→1MPa、制造λ=1e-14、A=.01m²/L=.1m参考摩尔流0.00274052205113mol/s；16/32积分相对差3.56e-16只是数值一致性检查，不是严格误差上界。参考2353次EOS调用、9.35s实际完成。

候选4/8/16/32区间最大相对流量误差0.002719757/0.001375341/0.000691605/0.000346795，细化比例1.97752/1.98862/1.99428，原门槛通过；反向供体焓及近等压保留名义流/未认证方向亦通过。预登记、两个独立脚本及全部节点/面结果在research/LIQUID_FACE_CONTINUUM_PLAN.md、liquid_face_continuum_reference.json和liquid_face_continuum_candidate.json。审核者只读核脚本、身份和重算误差；没有将其说成独立重跑整套参考。

该检查针对给定恒温压力剖面上的面离散，使用外部恒温约束，不宣称绝热稳态、完整湿砖空间收敛、EOS独立验证或真实泥料透水系数。来源标签的表即使有S依赖，也不自动得到材料资格。冻结制造和tabulated关系允许有源平台的语义明确区分。

最终冻结非editable离线安装，从/private/tmp无PYTHONPATH实际运行 **812 passed in134.01s，0失败/错误/跳过**；28个真实安装模块与工作区源码逐个hash一致。产物research/installed-sandbox-liquid-transport-tests.xml与installed-sandbox-liquid-transport-identity.json；旧786项记录保留。


## 固相反应与全库存热力学反馈

新增SolidReactionConfig的13项绑定测试及SolidFluidHeat反应主机8项测试由独立审核者实际复验，分别0.49s/2.42s通过。覆盖显式列/相/摩尔质量/共同参考/provider身份、零O2只停止氧化、有限氧闭合轨迹、正Ea两温度比、库存—占积—能量反馈、完整程序/液迁移/水相变diagnostics及制造门禁。审核发现的位置参数兼容与kinetic域分类问题均先有失败回归再修复。没有将旧gross-extent工具冒称成实际积分限步。

预登记的60位Decimal独立一阶Xsolid→Xgas极限固定总U，并由各相常Cp/形成能独立推导T、Vs/Vg与P。实际候选2s三档dt=1/16、1/32、1/64，最终attempt002为32/64/128均匀步且零拒步；最大Ns误差6.13022e-7、1.51459e-7、3.76428e-8mol，比例4.04745、4.02358。最细温度误差0.000352617K，压力1.56026Pa；总U与逐步/全前缀能量差均0，质量最大偏差5.421e-20kg。全部符合原计划门槛，未调宽比较条件。attempt001已通过但少报告字段，补拒步/求值次数与显式step能量字段后运行002；两次产物均保留。

原plan、独立reference与candidate代码、所有轨迹JSON/CSV在research/SOLID_REACTION_ANALYTIC_PLAN.md及solid_reaction_analytic_*。这验证固定bulk、常速一阶制造反应，不能解释为真实碳热解、刚性污泥反应网络、烧结变形或整砖外部验证。

最终冻结非editable离线安装，在/private/tmp无PYTHONPATH运行全部sandbox：**833 passed in136.56s，0失败/错误/跳过**。29个真实site-packages模块与工作区hash一致，证据research/installed-sandbox-solid-reactions-tests.xml及installed-sandbox-solid-reactions-identity.json。新增公开Areias2025记录只属核读来源候选，未数字化或执行预测对照，科学资格不因安装通过而提升。


## 低高温水汽衔接与耗尽写回部件

`4ef76a2`实现JoinedWaterVapor并接到IdealGasPhase/完整反应identity/WaterPhaseTransfer低分支/活动RigidStorage数值预算。原低293–500K调用保持，500以上从低h锚精确积分原NIST分段Cp，500/1700的Cp跳与h偏移原样可追查。低理想项正贡献和高Fraction区间提供Cv>0数学下界；不是来源物性误差或真实高压水汽资格。显式低温h误差声明仍条件有效，预算溢出两处独立RED后修复。独立provider31项0.31s、host9与写回初15共24项2.23s通过，原XML已保留。实际四条SolidFluidHeat轨迹分别跨500和1700K升/降温，水汽/固体库存不丢，终温对独立系数积分2e-5K、prefixU/work1e-7J门槛通过。

`624d89c`实现耗尽事件写回的方案(b)部件：精确成对数值相间修正与实际存储舍入分账，局部液ULP/绝对mol/正向蒸发相对限以及逐事件/全prefix水mol/H/O/Mkg预算；累计绝对残差不因正负抵消而取消。精确有理数累计器可JSON保存/恢复。初15项独立运行，主代理随后查到非零Fraction项下溢成0，先RED后两行拒绝修复，独立新增单项1passed/15deselected0.05s，最终作者16项0.06s；独立另120项相邻float有理数核查通过。写回不是事件定位器，没有关闭程序节点/模式切换/完整湿干积分缺项。

最终冻结非editable离线安装，从/private/tmp无PYTHONPATH实际 **889 passed in136.85s，0失败/错误/跳过**；31个真实安装模块与工作区hash一致。证据research/installed-sandbox-joined-water-tests.xml及installed-sandbox-joined-water-identity.json，旧833项证据保留。新增测试进入同一最终环境，不将独立初15项误记为最终16项全跑。

## 实际耗尽事件与干态继续

`89d5d26`新增显式界面模式；`7da961b`接通完整Rates终端panel、精确clock表示误差、成对数值修正及独立存储舍入、全段Fraction库存/能量账本。常/时变汇独立根、资源/取消、节点歧义和真终端细化等31轻量测试独立通过。初始相同terminal重复计pass的缺陷由先失败回归发现并修复。额外非线性cubic探针保留默认普通容差下外部误差门槛失败，证明局部事件差不是全轨迹误差证书；收紧普通容差的结果单独保留。

真实水provider、制造固体/载气/K的主机attempt03实际86.82s完成：21保存状态，液水从正库存于0.00028422061165952946s耗尽，再继续受炉温加热至0.03125s，实际程序节点保留，K不变。独立源/fixture前后hash一致。完整水量最大残差1.15805e-22mol，总U全prefix最大6.81945e-11J、单step最大2.02577e-11J；热输入0.075520921343J。H/O、摩尔质量、精确pair/storage累计、独立G(Tgas−Tcell)状态诊断与超出反解区间的干态温升检查通过。不是同一原污泥的物性/干燥实验验证。

attempt01/02的120s资源失败及源码绑定限制原样保留。attempt03收紧terminal_window以避免反复湿前段试算，所有比较门槛、common horizon和120s上限均不变。

首轮新冻结安装回归实际 **3 failed, 914 passed in230.46s**，XML `research/installed-sandbox-depletion-tests.xml`。失败均为默认界面None被物化成单格tuple，旧dataclasses.replace构建两格液迁移/反应主机时引发invalid_interface_modes；不能将31项局部通过当作整个版本通过。原测试与失败XML保留，后续修复另行验证。

`3c65ee7`修复默认None的主机替换语义，显式模式仍严格校验；12模式+原3失败组合独立15项通过。再次冻结非editable离线安装，在/private/tmp不设PYTHONPATH执行全部sandbox，实际 **918 passed in234.43s，0失败/错误/跳过**。这次包括最终默认模式修复后的真实湿干主机积分断言。32个实际安装模块在运行后再次逐一核对hash一致，最终XML和身份为research/installed-sandbox-depletion-final-tests.xml、installed-sandbox-depletion-identity.json。旧失败XML原字节保存为raw.zip，可读副本的行尾空白转换已单独登记。

## 两格耦合与连续湿态到高温

`9194fd1`加入分离多事件共同时间重选与显式相态反解括号；`fa88647`加入统一普通步库存比例及全显式干态的自适应历史保持。新比例/干态和既有事件测试共55项独立通过7.36s。原二次事件加速失败、干段反复重启导致100拒步失败及实际运行超时都保留。

两格真实水配制造反应/固相/输运的attempt02完成，444.525s、494评估、58接受试算panels、42已提交steps。两个事件0.0002883791755s与0.0010885050888s后继续至1/256s，程序节点1/512s保留。独立从保存的每步数据重算库存最大残差8.2756816e-18mol、元素1.1232598e-17mol、质量1.5340836e-19kg、U6.6127672e-13J；数值相间修正/实际存储舍入及全累计精确核对。来源绑定与验证限制见research/CODE_REVIEW_COUPLED_DEPLETION.md。初次360s失败与第二次已登记600s预算分别保存，未改物理输入和误差门槛。

wet_to_hot_attempt02完成600s模拟、实际198.3825s，8953评估/1272试算panels。终温530.7349451167803K，对以实际已接受事件U/time为条件的独立干段参照530.7349459107604K，差约7.94e-7K，小于事前5e-4K门槛；这不独立认证耗尽时间。max水量5.3932176e-22mol、单库存prefix4.6652987e-22mol、U7.1303175e-10J，运行前后源码一致。原240s/100拒步预算与全部误差门槛保持。高温chemical unknown的显式metastable分支不构成实际不凝结证明。

上述是软件/数值耦合验证，固体与动力学仍为制造值，不是原污泥材料验证或全时空收敛。当前版本完整冻结安装测试已启动；最终结果必须读取新XML后单独登记，不能沿用旧918项宣布通过。

最终安装结果已实际完成：**954 passed in444.54s，0失败/错误/跳过**，非editable离线锁定安装，cwd=/private/tmp、无PYTHONPATH。实际解析research/installed-sandbox-multicell-hot-tests.xml核计数，测试后32个真实安装模块逐一与源码hash一致；身份产物research/installed-sandbox-multicell-hot-identity.json。原918项及失败历史保留；本证据不包含尚在隔离目录准备的可变几何候选。

## 规定形变几何与气体机械功

`bb3098c`公开单次气体解码的诊断，独立从旧HEAD函数保存的非零流/热/反应/外边界黄金数据逐位相同。`1dca610`将C1参考运动与当前V/A/d、相对共享面和−p*完整Vdot机械功接入统一N/U步。运动模块独立29项通过，负非零时间下溢、普通16/32/64格坐标误拒及构造节点遗漏的原失败完整保留在candidate-history.zip。

独立host+motion+诊断47项通过4.87s。三档闭式绝热参照使用实际均匀dt=1/128、1/256、1/512s及256/512/1024步，独立临时hook在同次运行逐步核实，不只从步数猜测。最大T误差6.7844911e-4、1.6957182e-4、4.2387968e-5K；减半比4.000954/4.000471。最细相对P/等熵不变量7.8168645e-8、U解析误差9.3253496e-4J，满足原最细门槛。各步/前缀能量及库存、双格异压执行器功、切向形变、当前体积反应、流焓单计和域/资源失败均有实际断言。metrics来自原XML，未再运行补指标。

最终冻结非editable离线安装实际 **1001 passed in448.58s，0失败/错误/跳过**，从/private/tmp无PYTHONPATH执行。已解析research/installed-sandbox-deforming-gas-tests.xml，测试后34个真实安装模块与源码hash一致，见installed-sandbox-deforming-gas-identity.json。此为明确受控气体腔体的机械功验证，不是湿固体骨架储能、自由烧结或真实砖力学；原完整Goal仍未完成。

## 骨架/目标能量误差/普通RK分项功冻结验证

非editable离线安装后，从/private/tmp且无PYTHONPATH实际执行完整tests/sandbox：**1051 passed in446.61s**，实际XML计数0failure/error/skip；35个site-packages模块逐一匹配当前源码。详见research/installed-sandbox-skeleton-components-tests.xml及installed-sandbox-skeleton-components-identity.json。该结果不含仍在/tmp的DeformingSolidStorage候选。

独立局部证据：骨架23测试和75输出有理级数包络；target uncertainty新旧共34测试与旧HEAD反解一致；component work新旧44测试与旧HEAD 123接受/3拒完整默认路径一致。三份CODE_REVIEW及XML在research下。保留skeleton-energy-application-failure.xml（应用时漏sys import导致1fail）与候选history.zip。普通RK分项账本非耗尽panel支持，数值自测非原污泥实验验证，当前仍未完成湿机械整体耦合。

### 点储能与状态能量身份增量（未计入旧1051安装套件）

状态身份13新测试先实际RED（energy-state-identity-initial-red.xml），实现后新旧共73通过0.83s，独立73通过0.81s。独立从41e5911装载旧integration，比对惰性、含反应/面/分项功、domainexit三个场景，状态/时间/所有旧账本/计数逐字段相同，只排除wall和新增默认None字段。

点storage候选独立11通过2.18s，应用仅docstring和测试导入差异后11再通过2.18s。审核另在两个motion时刻用常Cp解析解检查目标误差1e-4J+机械2e-4J端点温度被返回区间包含。9资产hash与v=1/50000的二进制表示差核验通过；候选archive内原wet大误差失败和新独立制造输入定义均保留。原wet病例仍拒绝，新fixture不替代原病例可解证明。两CODE_REVIEW、XML与candidate-history.zip保存完整范围。

耗尽terminal与wrapper分项传播：候选独立25测试0.64s，应用38测试0.93s。独立时变组件实际拒步/终端权重、dry schema失败原prefix保留、旧None baseline重跑逐字节相同；详见CODE_REVIEW_DEPLETION_COMPONENT_WORK.md、depletion-components-applied-tests.xml及depletion-component-candidate-history.zip。新全sandbox安装测试session89265尚未终态，这些局部结果未宣称全套通过。

### 总储能增量完整安装最终结果

上述session89265已实际exit0，**1089 passed453.56s，0fail/error/skip**。36个实际site-packages模块与32965ce源码一致；XML实际计数及身份环境保存在installed-sandbox-total-storage-tests.xml、installed-sandbox-total-storage-identity.json。未将/tmp的新变形主机候选或其未通过的孔压功门槛算入通过范围。旧1051版本仍保留，不重复验证。

## 规定形变固体主机：实际解析与独立审核

已应用3源码，私有assembler与point current_storage保留同一次总/热反解。独立13轻测0.38s、Root应用13轻测0.41s；对真实旧HEAD evaluate的两格非零导热/气输运/固体反应比对所有Rates和反解诊断一致；额外机械targeterror原对象/误差保留。原错误temperature string接纳先RED后用旧_column修复，实际历史initializer对有效初值bits/tag相同。

首次isotropic attempt05实际1fail5pass，finest128温度过但pore功1.84969e-4J未过1e-6J。attempt06仅细化512/1024/2048并按实测成本改变wall20→90s/总150s，原物理/数值/比较gate不变，实际72.6178s完成。每档实际均匀、0reject；pore prefix误差1.1560369e-5→2.8900834e-6→7.2252057e-7J，fineT7.0783983e-8K、elastic4.3959833e-10J、interface1.6987324e-11J，原fine门槛全过。原coarse失败不删；正式测试固定fine而非隐藏env。

长扫描未被独立审者重复：审者核实际XML、指标和数学解析，另独立短测试/旧路径对照。扫描源只有运行后采集，README明确非前后hash测量；后续唯一initializer修复及正式测试配置与实际选择有独立AST/初值等价证据。完整候选、错误、源码快照、XML/metric和review归档research/deforming-solid-host-candidate-history.zip。实际历史.py测试fixture保持原字节；不把后续入口修复冒称已在旧扫描运行。新完整安装测试75509正在执行，尚未终态。

### 规定形变固体主机安装最终验证

session75509实际exit0：**1103 passed523.90s，0fail/error/skip**，包括正式默认的fine等向压缩扫描及initializer修复；37个实际site-packages模块与fa3194b源码逐一一致。实际XML已读取，环境/源码身份见installed-sandbox-deforming-solid-identity.json。此结果仍不含真实湿态主机时间积分、phase/depletion新host准入或材料验证。

## 湿态熵参照与实际短前缀失败

固定液/气/固库存、绝热、准静态、零耗散的独立熵参照已通过9项无EOS测试及独立极限核查。真实水初点和10%等向压缩端点的独立求根实际约2.07s完成；端点T=300.186070145K、p=567435.655362Pa，减半根容差差值通过预登记门槛。端点储能反解是roundtrip，不能当作时间积分验证。

随后真实DeformingSolidHeat在同一原1s/10%运动曲线仅积分0→1/64s；子进程实际14.067s、exit1，保存2个接受步、15次评估、0拒步。T差3.47747e-8K、p差3.36077e-5Pa达标；弹性/界面功差2.04029e-10/7.20113e-11J达标；**孔隙压力功差2.97406436e-6J超过原1e-6J，整体精度验证失败**。库存与总能量前缀账本通过不能抵消这个分项截断误差。未执行450s粗网格提案或完整湿态10%收敛扫描；原门槛保持。

## 可选水后端可行性范围

`research/water-backend-feasibility/`保存两液态点实际成功探测、原始失败、许可/资产清单、纠正报告和独立审查。它不修改默认生产EOS。原始flash计时与完整水适配器工作量不同，不能声称数百倍整机加速。独立审查指出协作式超时和固定结果文件遗留风险；未来运行需要独立监督进程及独占尝试目录。适配器设计未实现、未通过生产准入，物理域/来源/误差门槛不变。

## 当前孔隙模板与真实相变回调

显式边界/相变准入初7项无EOS独立通过，首次真实非零K回调在当前输运构造失败：参考孔体积大于压缩后bulk。保留失败后将点storage的流体模板绑定到同一次当前bulk减固定固体占积；原储能误差、正体积和来源门禁保持。新增回归独立9项通过0.38s。

修复后独占callback02使用已审查监督器实际1.387s、exit0、声明输入前后不变。T≈300K、液压29788.53656Pa、当前A=.009025m2、d=.0095m；原K=1e-7mol/(s Pa)。保存原生化学势后独立Decimal重组peq=3531.5200776812662Pa，回调值差约9.1e-13Pa；r=0.0003531222195294428mol/s，与独立式差约1.1e-19mol/s。液/汽源精确成对、固定固体/载气不变、无额外潜热、五类功完整、单次总逆解对象保持。

这次回调沿用其原fixture的1e-5J/1e-4K反解门槛，不与前述另一个1e-6J/K短前缀混为同一病例。原callback01失败、修复先RED和callback02分别保存；没有重写历史成功。只有单次真实相变耦合通过，不代表动态相变、湿态孔压功收敛或耗尽过程通过。

### 当前孔隙/相变接入完整安装验证

冻结ecfb3e9后重新非editable离线安装，从/private/tmp无PYTHONPATH实际运行全部sandbox测试：**1112 passed514.98s，0失败/错误/跳过**，session45600已exit0。实际XML计数已解析，37个真实site-packages模块逐一匹配当前源码；证据为`research/installed-sandbox-wet-admission-tests.xml`及`installed-sandbox-wet-admission-identity.json`。包括新9项回归和既有整套湿/干/事件测试，不把单次新湿回调扩大成变形耗尽验证。

## 原湿态短前缀的有界步长细化

完整安装测试结束后，独占refinement02仅将原短前缀initial/maxstep从1/128改为1/256s；原1s/10%运动、0→1/64s终点、四步上限、25s积分/30s外部资源上限及全部精度门槛保持。实际初始N/E/模型身份与保存的原失败逐字段精确相同。当前代码另含ecfb3e9孔隙上下文修复，不能将两次跨源码结果宣称为严格同源码收敛阶实验。

实际4接受步、29评估、0拒步，积分23.6644s、监督进程25.5696s/exit0，输入前后保持。原1e-6J分项门槛下：孔压功差7.35992551e-7J、弹性5.09988e-11J、界面1.80028e-11J，均通过；T差8.60501e-9K、p差1.19981e-5Pa分别通过原2e-5K/.2Pa。全部接受前缀账本、原液体u/s操作数、原始失败和新的结果均保留。

这关闭限定短前缀的此次精度门槛，不关闭完整10%湿态轨迹、多步长/空间收敛、活动相变或完整砖过程。6276是保存的公共water.state_tp调用数，不是内部EOS求解次数。未启动原450s提案或2048步全湿扫描。

## 活动相变与规定变形的安装验证（2b1d07f）

见 [实际证据与独立审查](research/heos-active-phase/README.md)。显式HEOS安装模块运行制造湿态非零相变回调及同初态K1e-7/K0两条短积分，原反应/能量/当前几何门槛通过；相变引起水汽库存和温度变化。每个接受前缀独立重算守恒，局部相变熵产生不等于全系统熵证书。

第一次步长减半完成，但更细运行触发原时间上限，停在浮点尾步前。三尺度比较尚未通过；无EOS案例复现额外2ULP尾步的7次评估成本。完整失败保留，不把短机制对照或自身细化当作公开材料实验验证。生产源码未改，本次没有重复全测试套件。

## 普通积分器时钟修正与最终安装回归

`research/integration-clock-correction/README.md` 保存完整先失败后修复链。最终v2实际冻结安装全套1124通过/0失败/0错误/0跳过，525.571s；真实XML及测试后41模块源码一致核查一并归档。此前v1全套1121通过/2失败没有被覆盖。

最终v2原活动相变三尺度实际2/4/8步到同一.51s终点，各次原25/30s预算不变；两最细N7.0089014535540536e-12mol、E6.984919309616089e-9J、T2.8339286473055836e-9K、P0.00020889274310320616Pa满足原门槛。全部接受前缀账本保存；这是步长一致性和软件回归证据，不能当作原污泥材料验证或独立全轨迹真值。

规定形变+活动相变+耗尽新组合实际失败，见 research/deforming-active-depletion/README.md。HEOS在299.9996124454831K的共存Newton八轮振荡，原1e-4Pa门槛未过；旧固定/短轨迹通过不覆盖此路径。独立密度半步探针通过原共存残差，仅支持研究阻尼策略，不是已应用修复或整段验证。原物理门槛不变，生产源码未改；完整材料域仍未准入。

## HEOS共存回溯修复与原组合耗尽复验

上述 research/deforming-active-depletion 的旧失败保留。新实现已应用有界回溯Newton，原物理/数值门槛未放宽；同一脚本和物理条件的安装组合轨迹实际完成14提交步/1耗尽事件并继续到0.5078125s。逐步和累计水/能量、五功分项及精确相修正/存储舍入经独立核算通过，详见 [修复证据](research/heos-coexistence-backtracking/README.md)。这是规定变形、制造固体/界面系数配真实水的限定集成验证。不能把旧失败改为通过，也不能扩大到自由烧结、完整湿坯变形轨迹或真实原污泥材料资格；全流程和外部机制验证缺项继续保留。

本版本冻结非editable完整安装套件实际1135通过/0失败/0错误/0跳过，517.635s，session85070 exit0。测试后41个实际安装模块再次与源码逐字节一致；XML与实际命令/依赖/模块身份在上述证据包。192相关套件、原生30点/7导数和制造组合轨迹是分别记录的验证，不将代码测试数量当作现实验证覆盖率。

## Areias2019 三批TG稀疏观测提取

`data/sandbox/research/areias2019/tg_digitization/`保留39事前目标中的35读数及4unknown。六轴分别校准，74个实际坐标区间及39列完整绿色足迹经独立核算，六张叠图/联系图实际查看，3原生图从原PDF独立重提取字节相同，6审阅图实际重现一致。转换器高精度有理数向内舍入边界经发现/修复/复审，4项针对性测试通过。它是有条件读图观测候选，不是§8三个机制组的模型预测验证，也不提升原污泥材料/训练资格。本轮不改物理内核，不重跑既有1135套件。

## 反应与规定变形 v1

显式人工组成机械储能与当前反应库存完成干态联合验证。原细化能量失败保存；新64/128步比较在原门槛通过。完整安装1165项通过（XML561.281 s），运行后42模块与源码一致。原始轨迹、独立标量参考、逐前缀账本、失败与审查见 [证据包](research/reacting-deformation-v1/README.md)。这是制造算例的数值验证，不是公开材料实验对照，也未覆盖湿态反应耗尽、自由烧结或全周期。

## 固体体积误差的局部压力界

7项新解析回归通过，旧源3项预期失败保留；48项相关回归通过。完整安装1172项通过，XML557.992s，前后42模块逐字节一致。原湿態输入复跑仅压力指标通过，事件库存仍未过且120s超时，不能称联合轨迹完成。原始失败、修正证明和独立审计见 [证据包](research/solid-pressure-bound-v1/README.md)。

## 耗尽普通湿态前缀与独立接近验证

新20独立数值/故障测试与旧相关测试合计55通过；完整非editable安装1192通过，零失败错误跳过，XML535.553s，前后42安装模块与源逐字节一致。默认旧策略保留。候选曾出现可变观测别名、重复诊断成本、最终接受前来源绑定缺口，均保留原字节/失败后修复；独立共同偏差拒绝及最后两次切换的来源故障实际检查通过。证据 research/depletion-spine-v1/。

实际v3联合轨迹仍失败：147评估18试算panel，6已接受步0事件；12观测/9普通panel复用不能证明整条轨迹已加速完成。独立175输入及全部接受前缀审计通过，与v2完全相同。受监督异常追踪复现同故障并捕捉到295K、53692.54782795906Pa液态TP迭代的双密度周期；295K是反解下边界，不是实际砖温。原动态压力门槛 min(1e-4,rho*1e-7) Pa 保留，尚未修正该TP故障。制造化学/规定形变不提供真实原污泥材料资格，公开三机制/留出及全周期仍未完成。


## HEOS TP 有界回溯数值修正（当前阶段）

原 v3 联合制造解在反解下界 295 K、53692.54782795906 Pa 的液态 TP 求解发生八步双密度循环。原公开接口单点可重复同一失败；295 K 不是已收敛砖温。独立六分数探针从同一原生种子出发，完整步残差 0.00010410800314275548 Pa 超出原动态门槛，半步残差 0.00005536824755836278 Pa 通过；其余四个短步亦通过原完整状态检查。原失败与探针均保留。

修正只作用于 TP Newton 的步长选择：最多八个接受状态，每步固定六个缩短比例，总计最多 43 次实际密度评估；要求原压力残差门槛通过或归一化残差严格下降。下降本身不能作为最终收敛，最终仍执行原动态 `min(1e-4, rho*1e-7)` Pa 门槛及完整状态检查。原始全步分支限制先于回溯检查，原物理数据、来源守卫、相分支及宿主反解容差保留。每个实际失败或拒绝的原生试算都记录。

控制测试最初的人工压力设定碰到原饱和歧义保护，14 失败/1 通过的原件保留；仅校正该测试域后，旧实现 5 预期失败/10 通过。审查后扩展为 19 项控制测试，与原 11 项共存回归合计 30 通过；这些脚本化响应不是物性证据。实际原生固定 3×3 温压网格旧实现 8 通过/中心 1 失败，新实现 9 通过，均保留 XML 和外部监督记录。这是数值回归，不是独立现实材料验证。

当前内核 SHA-256 `c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12`。来源注册、批准清单和包装器只同步对应实现指纹；42 个实际安装模块已与源码逐字节核对。当前完整安装套件尚待执行，旧提交的 1192 项通过不转移到本修正。联合 v4 保留 v3 五脚本字节、物理输入、事件门槛、120 s 内部/150 s 外部/500 panel 限额；新的初态 callback 已通过，轨迹结果另行记录。

联合 v4 实际终态：callback 外部 2.087812 s 通过；depletion0 外部 121.780958 s 失败，内部 `resource_limit:wall_time_limit`，120.127148 s、365 次评估、44 个试算 panel、6 个接受步、0 个事件。level 4/5 两次末端比较已通过原全部门槛（库存差分别 9.97847847712262e-11 和 3.797651082493303e-11 mol），但后续独立普通接近减半检查尚未完成，耗费 122 次评估/13 panel 后预算结束；不能把局部两次通过当作事件通过。第二条全轨迹细化未运行。当前完整安装回归 session9190 正在运行。

独立 v4 失败前缀审计确认：depletion 的 177 个输入及 callback 的 176 个输入在运行前后与当前文件一致；所有 6 个已接受步的 C 最大残差 1.2053617652607596e-16 mol、H 1.9190590211230242e-22 mol、O 9.595295105615121e-23 mol、总能量 1.7920981904939563e-11 J。各物种/能量累计账本及工作分项用独立 Fraction 算术逐步重算一致。物理数值与 v3 相同，能源模型来源身份随已审实现改变；不能称跨版本序列化状态字节相同。详见本阶段归档中的 `V4_WET_AUDIT.md`。

最终完整安装终态：session9190 exit0，实际 XML **1220 通过/0 失败/0 错误/0 跳过，539.545 s**；运行前后 42 个实际安装模块与源码逐字节一致。当前无活动测试/EOS。阶段证据共 74 项，已打包并逐项复读核对长度/SHA-256，见 [阶段归档](research/heos-tp-backtracking-v1/README.md)。原始失败 XML 字节保留在 ZIP；仅便于阅读的副本逐行去除末尾空白并补最终换行。v4 联合事件仍未通过，全 Goal 未完成。


## 仿射末端事件候选 NUM-AFFINE-TERMINAL-1

以 e9db77b 为基线新增24项独立时钟、14项积分/解析边界、21项来源/取消防护，共59项；连同40项旧相关回归实际99通过，XML34.213s。时钟使用实际binary64速率的精确Fraction多项式，根向下定位及逐项账本一致性单独验证。闭区间库存极小值与正向相变积分分别用抛物线/三角形面积解析例验证。源码与数值审查通过；安装43个实际模块与源码一致。

首批全程A误差约1.4e-10mol在新末端之前已存在，局部末端误差约4e-15mol；保持原外部1e-10门槛并提高普通自适应精度后通过。.005普通段步长另触发原程序节点unresolvable_stage_time，已记录未解决。非线性耗尽的独立三次方根对照首轮误差1.2141e-8s超出1e-9s；更严格普通精度1e-16mol又因不可表示增量拒绝；保留全部失败后，用可表示的1e-14mol绝对与1e-13相对精度通过原外部门槛。这些精度仅用于独立制造oracle，不修改v5原联合实验设置，不把局部事件相邻一致称为全程误差证明。

新的v5初态callback实际complete2.014814s；联合depletion0正在原120/150秒限额运行，未有轨迹通过或完整安装回归结论。

实际 v5 两条联合轨迹均通过：depletion0 外部89.429237s、内部87.845694s，260评估/31试算panel/14接受步；depletion1 外部87.095868s、内部85.501777s，303评估/36试算panel/16接受步。各有一个实际耗尽事件并在非零反应、保留1e-6mol/s/Pa界面系数条件下继续到.5078125s。两次末端细化及独立普通接近减半检查均通过；未改变原120s内部/150s外部/500panel或任何物理/源误差/验收门槛。整体步长对照实际passed：N差6.6579933840488215e-12mol，E差2.6106135919690132e-8J，T差2.604963356134249e-9K，P差3.9664882933720946e-7Pa，事件时间差0。对照不是独立湿态温度物性oracle，也不是空间收敛或现实实验验证。

当前完整安装回归session8135正在运行，旧1220项通过不转移到当前代码。全部代码/测试/安装和v5脚本冻结。

独立审计补充边界：两条整体cap运行至耗尽的实际接受网格相同，因为安全库存分数而非最大步长主导；整体减半实际改变干态续算（14→16个总接受步）。因此事件时差0不能作为跨cap事件收敛阶数的证据。每条运行内部独立接近路径确实使用不同湿态网格并通过原门槛，构成局部湿态检查；仍非全程空间或现实验证。

最终完整安装回归：session8135 terminal exit0；实际XML **1279通过/0失败/0错误/0跳过，585.898s**，运行前后43个实际导入模块与源码逐字节一致。当前无活动测试/EOS。两次v5结果与独立账本审计、完整控制失败历史统一归档至 `research/affine-terminal-v1/`。该阶段确认有界数值耦合及安装回归，完整Goal科学与使用验收仍未完成。

## 两格湿态反应与内部输运对照（2026-09-07）

生产源码和测试保持 `67730b2`；当前安装的 43 个模块逐字节匹配。此阶段新增实际集成实验和独立审计证据，未重新运行未改动源码的 1279 项完整套件；该完整套件的历史证据仍在 `research/affine-terminal-v1/`。

同一两格半板（参考长度 0.02 m、面积 0.01 m²），初温 300/301 K，规定变形、制造 A→B 反应及骨架，与有来源的纯水物性组合。coupled 使用 k=1 W/(m K)、水汽 D=1e-8 m²/s；control 关闭这两项，其他设置保持一致。无 Darcy 流、外面封闭。区间仅 0.5 至 0.5000152587890625 s，所有保存状态仍有液水。

| 轨迹 | 接受步 | 监督耗时 s | 最大逐格能量账本误差 J |
|---|---:|---:|---:|
| coupled coarse | 2 | 14.618526 | 1.70855e-11 |
| coupled fine | 4 | 28.018826 | 7.02360e-11 |
| control coarse | 2 | 15.727174 | 1.09750e-11 |
| control fine | 4 | 27.920138 | 2.55263e-11 |

四条轨迹均 completed，并通过逐接受步的 Fraction 独立库存、元素和能量账本重算；逐格物种误差最大 1.86379e-16 mol，原门槛未改。两次初态回调各 63 项独立代数检查通过：质量参考系扩散含载气修正，傅里叶与公共面温焓流组合一致，关闭输运时通量为零。代数容差是在首次 coupled pilot 后、control callback 和全部轨迹前冻结，不能称为首个 pilot 的预登记。

固定的四倍经验分辨判据下，细步耦合相对控制的两个单元温差分别 +1.4464243e-6 / -1.4464127e-6 K，门槛分别 9.89102e-7 / 9.68596e-7 K；局部能量差约 ±1.4496e-5 J，门槛 8.8e-7 J。两类指标均通过。水汽/液水库存差约 2e-15 mol，低于 8.8e-11 mol 门槛，保持未分辨；相变速率差仅记录观测，没有经证实的灵敏度区间，不宣布反馈显著。A/B 的 Ea=0，不能据此声称温度改变固体反应速率。

这仅为有限时间、制造材料系数下的经验数值分辨检查，不是连续方程误差证明、空间收敛或现实材料验证。两格域不同于旧单格 v5 域；后续必须保持物理域和广延量一致才可做网格比较。原 `.005` 普通程序节点失分辨率缺陷仍未修复。原污泥材料闭合、自由烧结/冷却、三个公开机制及留出验证、CLI/UI 和多代搜索继续未完成。

完整脚本、原始轨迹、逐步账本、来源/安装绑定、独立审查及四组比较见 `research/two-cell-wet-coupling-v1/`。

## 固定物理域两格至四格检查（2026-09-07）

证据见 `research/fixed-domain-spatial-v1/`。源码/测试仍为 `67730b2`，上一两格证据提交 `c62fb2f`；本阶段未改生产代码，也未重复该版本已有1279项完整安装回归。实际运行后43个安装模块仍与源码逐字节一致。

固定0.02 m半板及0.01 m²参考面，四格库存、微界面面积、相变系数、参考体积及绝对几何误差减半，q(N)的B权重加倍，q0和强度型系数不变。独立无EOS检查通过171项与6个错误权重负控。代码审查发现中间流体模板孔容未缩放会违反构造器的体积上界，已在运行前修复；原候选和修正理由完整保留，实际动态孔容仍按当前总体积减固体体积计算。

非均匀及均匀初态callback分别4.741476/4.654432 s完成，各144项独立气相/三内面代数检查通过。非均匀中央面傅里叶功率-1.90000000181 W，其余两个内部面为零；均匀三个内部面均零。保守父子N/E和同温forward能量广延性通过，两父单元forward能量差实际均为零。均匀检查仅初态，不是均匀时间轨迹验证。

四格两条短湿轨迹均completed：2步30.990010 s，4步55.240541 s。逐格账本容差随单元体积减半，整体容差不变；最大局部物种误差9.31892e-17 mol、能量误差1.90234e-11 J。保存全部前缀、内部通量及功分项并独立Fraction重算。4个监督进程均终态；每callback181、每wet182个输入均实际核对before/after/current一致。

用子单元库存与能量之和对比原父单元，在细时间步下能量网格差约±1.44955e-5 J；单独时间步减半差最大8.73115e-11 J。温度只作参考体积加权诊断平均，网格差分别+1.44639387e-6/-1.44640256e-6 K，时间cap差不超过5.79803e-12 K。初温为分段跳跃，细网格中央传递距离减半，初通量变大是离散关系的结果。空间影响不可忽略；两个网格、这一极短区间和时间cap诊断不能证明空间收敛，未设置人为网格PASS门槛。

本阶段为制造系数/规定变形配真实纯水物性的有限空间一致性检查。材料现实验证、全周期空间收敛、自由烧结冷却、公开三机制/留出、CLI/UI及多代搜索仍未完成。已保留的普通分段时间节点失分辨率另列下一优先修复调查，不能视为已修复。

## Ordinary 程序节点修复：完整安装验证完成

原版最小常量源算例已实际复现：`.005` cap、`.05`节点、`.06`终点，停止于 `.049999999999999996` 并报告 `unresolvable_stage_time`。失败前的质量/能量前缀通过；8项初始回归2失败6通过，原件保存。有限端点表示调整后8项通过，扩展14项通过；独立常量积分、库存限制反例、负/零时刻、窄cap、取消和当前精度affine事件均覆盖。相关102项测试实际通过（31.62s）。

原保留的粗精度 `.005` affine 文件原样复测为3通过2失败：两个节点/耗尽路径完成，但A误差1.82883264e-10/1.65367720e-10 mol仍超过原1e-10门槛。较粗rel1e-7结果未被改写为通过；当前既有rel1e-11配置的同cap事件回归通过原门槛。材料误差、局部数值控制和全局输出精度不可混为一谈。

实际非editable安装前后43模块与源码逐字节一致；完整回归session33496终态exit0，实际XML记录1293通过、零失败/错误/跳过，573.270s。冻结源码和测试摘要仍匹配。证据归档 `research/program-knot-v1/`，包括旧失败、当前粗精度残余失败及新验证。仅有数值修复和制造验证，没有新增原污泥材料准入。
