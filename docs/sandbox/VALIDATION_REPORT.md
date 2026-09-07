# 实际验证报告：G0/G1 基础与G2有界模块

日期：2026-09-07 UTC；平台 macOS arm64，Python 3.12.13。本报告只有已实际运行的验证，不代表完整 Goal 验收。

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
