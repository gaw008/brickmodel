# 物理沙盒 Goal 进度

更新时间：2026-09-09 UTC。完整任务合同：[GOAL_BRICK_PHYSICS_SANDBOX.md](../GOAL_BRICK_PHYSICS_SANDBOX.md)。最新状态以当前恢复入口及其实际产物为准，较早段落保留当时状态。

## 当前恢复入口（后续详细历史保留）

c5ddeb1之后实际progress：同原湿态10ms pilot session9698 exit0/67.54s，34steps2events620eval74attempts，原prefix审计通过，globalmax2.509e-10J。真实保存dry终态profile77466 exit0/1.410s，两output和saved base_rates精确同；unprofiled.01719s，仅单位成本样本。四格一次initialWPT51175 exit0/1.790s，首两N/(-net)候选Fraction gap0，满足当前selector拒绝条件；未运行四格integrator/未证明真实同时事件。

按实测资源推进同湿态2格elapsed.625s：coarse79355 exit0/119.00s，349steps389attempt2825eval2events end1.125；fine80816 exit0/173.67s，669steps709attempt5065eval2events，同end。fine仅id/refinement1(ordinaryinitial/max半)/maxsteps1024事前资源预算改，其他physical/所有原gates/800s保持；原512不足640dry+events，不是accuracy放宽。两组原audit_prefix SHA287bc实际exit0，globalmax1.18122e-9/4.07154e-10J<2e-8。全部65运行源码身份一致，无活动EOS/测试，不再poll上述会话。

标准库比较已补独立审核指出的原audit实际SHA及完整case->policy绑定，原脚本/原已通过report也保留；新比较exit0、独立最终review通过。两mesh实际不同，原初态N/E/stretch相同而case关联identity不同明确记录；eventtime差exact0。终态max N1.3982e-10mol/E1.26136e-7J/stretch4.09054e-9/T1.30858e-8K/P9.87175e-4Pa，T/P低于点误差界，不宣称两级收敛阶或全时间误差证明。证据research/thermal-timescale-v1，说明THERMAL_TIMESCALE_STUDY.md，三可运行新case已保存。

下一具体实现合同research/thermal-timescale-v1/NEXT_GROUP_PLAN.md：初始tau相等不是root同刻，保原单事件默认；先纯解析affine多root区间/正库存/ordering/union证书，再完整group correction/全cell六gate/模式切换/共同panel账本及record/resume接入。没有timing-displacement或ordered分支界不能直接zero所有tie。4/8完整空间矩阵尚未准入，原15us空间FAIL保持。真实原污泥材料、三组公开机制留出、完整湿烧成冷却与最终使用验证仍必需，Goal active。


f619433之后实际实现progress：PressurePolicy显式endpoint策略及不可变trialledger，defaultNone公开encode/原二分数字序列保留；case可选strategy严格唯一值并真实转发。新dataclass身份改变不冒称旧model字节相同。源码66/安装66通过，65模块一致；独立审查通过。原始RED/中间测试失败保留。见PRESSURE_ENDPOINT_STRATEGY.md及research/pressure-endpoint-strategy-v1。

实际同accepted wetstate1点比较session30911已exit0：baseline.80005s、新.13375s，两格最终root38→3，T/P原界通过；同物理N/E/stretch显式新数值身份重绑不是旧checkpoint恢复。实际单次新case service session83456已exit0/67.896s监督（service67.69s），30steps2events592eval70panels24endpoint、原.50032终点通过，事件时刻与旧记录相同。原6组×6gate经独立核查；原audit_prefix.py SHA287bc逐prefix实际exit0：N5.58085e-16mol/E7.62952e-11J/stretch4.21229e-16、全局外压功max9.99274e-11J/C累积绝对2.13932e-20J均过原门槛。当前无活动EOS/测试，不再poll30911/83456。新case data/sandbox/cases/reacting-wet-free-paired-events-endpoint-root-v1.json SHA9d930a6c6d60cf328e5abe2e61dc6a5f9f0cf06d9453827b84d0f0b56e5746f4。

下一步按实际较长空间pilot设计推进可解析时长与适应步长，用真实取消/续算同时检验新policy服务生命周期；原15us空间FAIL保持，不能改D/k/初始库存阶跃或放宽norm/gate。后续设计已保存research/pressure-endpoint-strategy-v1/LONGER_SPATIAL_PLAN.md：先同湿初态2格到.51的10ms成本pilot，再决定.625s热尺度；10ms不是空间验证。4/8格同父子单元可能触发simultaneous_events_not_separated，须实证分离或联合事件处理，不能扰动初态/改gate。计划未执行。新策略全取消/续算/重放尚未实际复验，不用旧default证据替代。原污泥材料/三机制留出/全湿烧成冷却仍全部必需，Goal active。


87b5f78之后实际进展：原accepted wet state1有界host profile已完成。session80931 exit0/3.357s，build1.340s，两个显式evaluate .887659s(profiled)/.805864s(unprofiled)，选定输出逐字相同；runtime/父封存前后一致，仅run_service历史查询修复差异已明确绑定。8 thermalforwards、320 pressuretrials、328 nativeTP；两最终closure均38二分，宽7.2032e-6Pa。_transaction self.711s是剖析归因，不能拆C内部或当656独立TP；digest9次累计.00417s不支持hash主导。独立脚本/结果审核通过，完整证据research/host-profile-v1。无活动EOS/测试，不再poll80931。生产源码未修改，本轮是实测证据进展。

下一实际实现合同research/host-profile-v1/PRESSURE_ROOT_NEXT_PLAN.md：default旧bisection保持；显式新数值策略用端点液体体积生成候选，但每个候选必须真实EOS+sign验证，保原width/residual/单调/guard及trial预算，不足收缩回二分。先独立解析根/假位停滞/浮点/异常测试及review，再原wetstate两次40s实际probe；未实现，不声明加速或事件通过。后续仍需事件/续算/空间收敛原门槛复验，不以点加速代替完整Goal。

限定新来源检索实际核读Houdkova2007公开PDF，指出PRES2006 Elsäßer热物性原研究，但当前正文Cp只有定性、fig5/6为流变；未取得可准入Cp数据，不补未知值。核查research/source-lead-houdkova2007/REPORT.md；只有网页解析原文，未保存PDF字节，未声称PDFhash。原污泥完整参数、三组机制留出及全烧成冷却仍未完成。Goal active。


0c2191d 之后实际进度（2026-09-09 UTC）：修复 v2 resume preflight 的构造顺序；保留实际完整盒/来源/前缀审计。源码与冻结安装 43 项通过、65 模块一致。真实 service start/session48184 cancelled 7steps；resume/session99452 completed30steps/2events至原0.50032，原前缀和累计预算保持；replay/session19128 exit0，353.89s、30steps/2events/592eval，times/states/steps/events/corrections与resume逐项相同。三会话均终态，不再poll/重跑。325成员完整证据 research/paired-service-lifecycle-v1。

真实取消T来源查询曾 quantity_unavailable，失败保留。随后修复合法量无final_snapshot时保来源图、value/pointer null及明确原因，未知量仍拒绝。永久RED14fail→GREEN32pass，实际安装32pass/65模块一致，真实取消7查询通过、完整7查询逐项不变、原封存不变；research/partial-run-trace-v1。源码查询修复在生命周期运行之后，二者runtimeSHA不同，不冒称新源码已重跑native。独立代码审查均通过。当前无活动EOS/测试。

空间保存数据独立诊断通过原六封存输入、parent N/E映射及初态几何通量核算，支持内部初始阶跃尚未解析；原空间收敛FAIL保持。0.391µm是水扩散尺度，粗估热尺度12.35µm，均远小于最细2500µm网格；不能把估算当完整耦合定理。research/spatial-jump-diagnosis-v1 另附 PERFORMANCE_PLAN.md，仅设计、未运行profile。

下一可执行步骤：按该有界计划先测真实已接受wet state的最多2次host evaluate（40s监督、source/输入绑定、原误差门槛；串行且保留实际profile），用实测调用成本确定原空间问题可解析尺度/时长策略。并继续原污泥材料闭合、三组公开机制及留出验证、完整湿坯烧成冷却与气液联合耦合。现仅制造材料短湿轨迹/事件与软件生命周期进度，不是完整Goal验收。Goal active，全部原§11范围保持。


3e04fce之后实际progress：新增pressure_comparison完整typed策略/codec/双路径实际host及数据审计；depletion只在opt-in捕获当次total inverses，event/common全格比较、before/after guard与累计attempt/completed；event_record v2/旧v1兼容及source/state/observations/成本/续算审计；case显式v2假设避免sourcehash自引用，真实build派生box并beforeforward验证；service允许v2续算形状后仍严格audit。

独立审核关闭真实WaterState mass序列化错位与bool/string采样漏洞。冻结安装实际140pass8.67s、65模块与源码一致。真实helper两格probe session1078已exit0（3.18093s），8endpoint完成/最大条件界3.7403908677e-5Pa过原1e-4门槛，非event成功声明。文档PAIRED_EVENT_COMPARISON.md。

实际事件session87636已终态exit0：监督352.383s/积分348.660s，completed30steps/2events/592eval/70panels，24endpoint全部完成，到原0.50032。事件cell1在0.5002686445571594、cell0在0.5002848875613792；每event两successive+独立细化通过原六gate。原独立P界仍.005135/.002784Pa>1e-4，只有显式新共享族界（max5.17914e-9Pa）通过，旧failed不改。独立审核的audit_prefix.py实际exit0：所有prefix N5.58089e-16/E7.62853e-11/stretch3.84743e-16，全局E+peΔV−boundary−body max9.99128e-11J、C跨格累计绝对和1.29891e-20J过原2e-8；gross/2correction均独立重算。运行前后water/65源码一致且physicalinputs与旧case逐字段复原相同。无活动EOS/测试，不再poll87636/1078。证据research/paired-event-comparison-v1；新增可复现data/sandbox/cases/reacting-wet-free-paired-events-v1.json。

下一步为新case真实service run/replay/resume及来源/交互核验，以及继续原空间收敛缺口/真实原污泥证据及全烧成耦合；不能把制造300K短湿轨迹当全周期。现数值器可在显式共享误差族完成两耗尽事件；默认独立族旧失败仍成立。原Goal继续active，所有原§11未完成项不缩减。


上一Goal回合仅重述提示词，按no-progress处理。本回合恢复实际未提交模块并独立重算四个保存证书exit0，冻结125文件证据包，新增PAIRED_PRESSURE说明，属于progress；完整Goal仍active。

新增paired_pressure/paired_pressure_host及31项专属测试：明确新制造共享常数参数盒，只计算reported-T条件压力差；默认unavailable，保留原点误差。旧版源码/安装相关60项通过、64模块核对；两个两格真实端点探针分别3.2685/3.1109s，非零差3.6015990190e-5Pa、上界3.7279046258e-5/3.7405558044e-5Pa。没有接入事件接受，原failed保持。来源、全部输入、四证书、审核和旧64模块已封存research/paired-pressure-v1/evidence-before-identity-fix.zip及逐文件manifest。

最终identity修复已完成独立审查：last observer后复核thermal/chemical两implementation与捕获值，原RED1fail保留，15主机检查通过。非editable安装专属34项通过0.34s、64实际模块匹配；真实两格非零neighbor正常observer补验session28048已exit0，3.40284s探针/3.78762s监督，两个上界及全部端点与旧运行相同。无活动EOS/测试。27项修复/审查/新native/设计证据封存identity-fix-and-adoption.zip；旧125项包不覆盖。原audit只证保存算术及内容一致性，不独立重建所有host误差项/材料物性。

下一实施合同已冻结research/paired-pressure-v1/ADOPTION_PLAN.md：实际旧压力gate也是reported-T条件界，温度误差独立检查，因此不凭新增Ttube要求阻断；新共享常数误差族必须显式opt-in，default原公式/旧记录保持。需新增before-call取消/尝试计费、实际event/common全格inverse快照与两op绑定、记录/审计/续跑版本分支及新案例声明。未接入/未宣称事件通过。完整原污泥材料/三机制公开留出/全周期/空间收敛仍未完成。


9121200之后实际原生耗尽attempt01已终态：session90003 exit0但模型failed correction_exceeds_evaporation_fraction，499.457s服务/496.887s积分，13accepted steps/0events/751eval/90attempt。固定end0.50032未到，停于0.5002620305782048。level1–11仅P比较失败，~0.005135Pa点误差包络大于原1e-4Pa门槛；不加refinement或放宽gate重跑。独立每prefix N/E/stretch通过，全局pe功最大2.76765e-11J、C累计绝对抵消9.25615e-21J通过原2e-8目标。单点实际安装诊断session46463已终态2.306s，证明流体项与约2e-12m3体积包络均有贡献。全部失败/审查/账本见FREE_NATIVE_EVENT_FAILURE.md及research/free-native-events-v1。

下一数值修复为有证明的成对压力差包络，而非削减原物性误差。reacting_skeleton_provider在/private/tmp/brick-paired-pressure-design-v1准备共享单调闭合推导（仅设计、未应用、无EOS）；恢复先读其实际最终状态/设计再审核实现。当前无活动EOS/测试。Kim2008定向原文检索仍未取得合法全文，未准入Cp或材料。原完整Goal继续active，原污泥材料/三机制留出/全周期/空间收敛都未完成。


2026-09-08 free-event application实际检查点：新显式event case、事件记录严格审计、完整累计续算、run/replay/resume与事件来源目录已接入。源码100+6通过；冻结非editable安装后从/private/tmp无PYTHONPATH实际106通过5.77s，62真实安装模块与源码一致。真实water构造4项通过，但service事件生命周期使用analytic callback/builder替身，原生耦合短前缀2步19.188s通过且七trace无缺来源，但0个耗尽事件，尚未做真实耗尽event run/replay/resume。首轮监督脚本证据目录误传导致4来源缺项，原封包保留，正确目录重跑通过。已关闭系数内容绑定、删小额correction、观测/refinement严格类型审查缺口；原失败保留。详见FREE_EVENT_APPLICATION.md及research/free-event-application-v1。当前无活动EOS或测试；下一实际动作是事前登记有界原生耦合事件应用实验。空间收敛仍未成立、原污泥材料及全流程/三机制留出仍必需，Goal active。



80b5331后实际progress：free schema2/4/8准入（旧prescribed仍2/4）、catalog域和UI模型专属gridoptions；修复JSON8在旧select空值→0问题，未知/不支持值在写case前拒绝。8格N/E/9stretches/当前非零Bq/界面/父误差测试通过。源码61回归1.30s，安装61回归1.24s+11Node UI通过；61实际模块和catalog/assets前后匹配。

完整实际2/4/8×粗细时间矩阵已完成，新增5原生组、复用原2coarse；均2/4steps、15/29eval无拒步。4coarse32.52s、4fine53.14s、8coarse58.90s、2fine26.49s、8fine106.55s；27357/92902/10876/98307全终态，无活动EOS。逐prefix/封存/当前科学模块逐字比较审计通过；最后2fine/8fine为实际安装运行，不重旧成功组。

关键结论为不支持空间收敛：时间细化后的父格温差2→4为1.52254e-6K，4→8为3.04496e-6K，增长约一倍；大于可用时间+反解界10倍门槛。时间变化低于约8.24e-8K反解界，不能宣称其极小差是独立精度。完整证据research/free-spatial-study-v1，说明FREE_SPATIAL_STUDY.md，原科学/精度门槛未宽。

下一具体事件服务设计由reacting_skeleton_provider仅在/private/tmp/brick-free-event-service-design准备，需显式DepletionPolicy/校正/最终interfaces/全机械prefix与checkpoint累计预算，避免ordinary服务在液水耗尽后继续错误模式。初态Nliq/r约0.27–0.28ms仅量级估计非事件定位。原GNEST缺质量/产品caloric材料问题仍保留，不重做已拒绝审计冒进度。原污泥、三机制公开留出、全湿烧成冷却及完整空间验证仍未完成，Goal active。


7f3d24b后实际完成free case应用接入：独立严格schema/current储能+反应自由主机/全机械初态及快照、2/4格beta/V0/界面/父误差缩放；独立20方程7root目录，run/replay/resume/trace真实模型选择与自由锚点；UI逐格n/全局t分开、溯源完整向量。说明FREE_CASE_APPLICATION.md，证据research/free-case-app-v1。

真实水应用2steps15eval16.59s通过；独立逐prefix全物种9.89e-17mol/局部E2.33e-11J/全局外功1.46e-11J，反应/两格蒸发/水蒸气扩散/热/自由形变真实共同活动，7trace无缺来源。重放逐位相同；首次callback3取消零前缀的测试失败保留，按实际guard位置callback19后取消1step+续算成功、原prefix不变，合计19.33s。91971/12781/56117均已终态；无活动EOS，不重复成功native。

安装93计算服务测试通过；22localapp因沙盒socket错误，获准loopback重测22通过2.60s；8Node UI测试通过。61安装模块前后与源相同，2catalog+JS/HTML逐字相同；1848/13200均终态，未重复原生EOS。案例/目录/服务code-review与TS UI review通过。尚无本阶段浏览器渲染或空间轨迹收敛证据。

下一实际空间研究由program_knot_review仅在/private/tmp/brick-free-spatial-study准备：现free schema2/4，研究自由分支8格准入与原实际案例2/4/8的网格/时间细化、统一物理量比较和实测资源预算。未repo应用/未运行，恢复从实际PLAN继续。原污泥材料、三机制公开留出、完整湿坯烧成冷却和联合所有输运仍必需，Goal active；本回合属progress。


ae5bf54 后实际完成动态炉程自由主机接入：当前几何表面热交换、完整机械率/分项功、程序内容身份及受控非法修改错误保留前缀。原生水 attempt01 130.70s 完成，3/7步、22/50eval、两个节点精确命中；独立170源码hash及Fraction逐prefix审计通过，最大水1.86e-16mol/局部E1.75e-10J/含边界热全局E6.30e-11J。源码34dry+1native通过，安装42dry10.27s通过，61实际模块前后逐字匹配。37884/65002已exit0，无活动EOS；不重复native。全部原始失败/JSON/XML/审计与身份见research/programmed-free-slab-v1，说明PROGRAMMED_FREE_SLAB.md。仍为短时制造材料、无物质面流/反应/耗尽，不是完整烧成。

下一实际候选由reacting_skeleton_provider仅在/private/tmp/brick-free-case-integration-candidate构建独立free schema、CurrentSolidStorage/FreeSolidSlab反应主机、完整初态与真实快照和2/4格广延参数缩放；未repo应用/未EOS。program_knot_review只读设计free catalog及run/replay/resume/UI接入，路径/private/tmp/brick-free-app-seam。恢复读取真实候选/审查后继续，不能把应用设计当已实现。原污泥材料及三机制公开留出、全湿烧成冷却、空间收敛仍全部必需，Goal active。

d969905后实际progress：free_slab_rates显式reacting_manufactured精确当前qeta及共同t加权分母，FreeSolidSlab显式反应模式重绑当前reaction storages、当前Ns/总E/孔隙/温压/自由形变真实闭环，fixed模式守卫与身份保留。源码65项3.83s+独立轨迹1项5.16s通过，正式安装104项14.01s通过（31745已exit0），61实际模块前后逐字匹配。无活动EOS/测试。证据research/reacting-free-slab-v1，说明REACTING_FREE_SLAB.md。

独立305/306K干态A→B两格0.1s轨迹23/32steps通过全部原门槛和每prefixDOP853对照；E最大1.395e-6/7.266e-7J，stretch3.173e-8/1.652e-8，解析A/B1.574e-10/8.058e-11mol，外功8.026e-9/4.556e-9J。原300K边界越域零step、域内粗E4.326e-6失败完整保存，仅收紧内部控制，未宽源域/外部gate。两份独立审查通过。仍为制造材料、无湿/气物质面流，非真实原泥/全周期。

下一候选仅由reacting_skeleton_provider在/private/tmp/brick-programmed-free-slab-candidate隔离准备：ProgrammedSolidFluidHeat显式FreeSolidSlab准入、真实当前表面几何、保留mechanicalrates与外功、原程序断点/来源身份；机械Pe独立常数，不随气库压力静默改能量身份。设计/private/tmp/brick-programmed-free-slab-design/PLAN.md。未应用候选、未原生EOS。完整原Goal的动态烧成/冷却、气液联合/空间收敛、原污泥资料及三机制公开留出仍未完成，Goal active。

f1f1349后已实际接入CurrentSolidStorage显式reacting_manufactured模式：当前Ns→q储能/固体体积/孔隙/总E反解；默认fixed身份/数值保留。FreeSolidSlab提前明确拒reacting点，尚未扩自由速率。源码39项3.68s、安装62项3.84s通过（45446/99141已exit0），61实际模块逐字匹配；两份独立审查通过。原候选/RED/源码hash/安装XML保存research/reacting-current-point-v1，说明REACTING_CURRENT_STORAGE.md。无活动EOS/测试，当前阶段可提交。

下一候选由reacting_skeleton_provider仅在/private/tmp/brick-reacting-free-rates-candidate隔离准备：solve_free_slab_rates显式reacting模式，实际q(N)*eta与加权共同t分母，固定路径兼容/当前Ns与误差界；没有repo应用、没有host反应准入。恢复先查看候选与审查，不重跑旧439s事件。原三机制公开留出/原泥材料/全湿烧成冷却/空间收敛仍未完成，Goal active。

233bb8c后本阶段实际progress已完成：真实水两格mixed depletion运行439.44s/积分436.173s、305eval、19步、唯一cell0事件3.041741648e-5s，cell1仍湿且凝结。原两终端+独立不同网格六门槛通过。逐prefix水3.84e-16mol/局部E1.65e-10J/全局外功1.06e-10J，实际局部C约4.25e-6J且全局抵消。163源码hash在解冻前独立一致；session58808已exit0，无活动EOS。全部初末snapshot/失败/分支审计见FREE_SLAB_DEPLETION.md与research/free-slab-depletion-v1。

另新增独立dry gas/enthalpy/自由力学轨迹：16/32步对DOP853通过，原失败保留、外部gate未放宽；陈旧几何负对照可辨。正式安装61实际模块匹配，18相关气流/机械事件测试9.25s通过（99499已exit0），另候选installed5项3.57s。生产源码仍233bb8c，无重复7分钟原生EOS。下一已审候选仅在/private/tmp/brick-reacting-current-point-candidate：CurrentSolidStorage显式reacting_manufactured/currentNs/q储能与孔体积，4drypass，另FreeSlab固定模式提前拒reactingpoint的最小guard1pass；尚未应用repo。先核候选与两个审查再推进自由rates当前qeta、真实反应源与整体能量；完整原泥/边界/空间收敛/三机制留出仍必需，Goal active。

233bb8c后当前唯一native验证session58808：tests/sandbox/test_free_slab_depletion.py，两格cell0耗尽/cell1仍湿，600s积分/660s外层硬限，完整源测试冻结；初始真实callback已保存，尚未积分终态。原六门槛不变，补局部constraint非零、跨cell累计绝对和及初末数值界审计。最终snapshot保存先于断言。路径/private/tmp/brick-free-slab-depletion-v1；恢复先poll同58808，不重启、不并发EOS。无生产源码变化；此测试尚未提交/未通过声明。

另独立dry gas trajectory候选/private/tmp/brick-free-slab-gas-trajectory已审：16/32不同网格对独立DOP853通过；原失败与内部收紧记录保留，未放宽外部gate。尚未应用repo（native冻结中）。reacting当前点候选由reacting_skeleton_provider仅在/private/tmp/brick-reacting-current-point-candidate隔离准备。Goal仍active，完整原§11未完成。

从23be5b6完成多格真实水相间转移准入与当前几何Darcy独立测试，属于实际progress。WaterPhaseTransfer显式接纳FreeSolidSlab，保留真实来源/热化学桥及external_traction、mechanical_constraint、body。源码4真实测试44.25s通过：两档1/2步、8/15eval，蒸发与凝结共同活动，逐prefix水最大5.4063e-17mol、全局外功1.3595e-11J；独立Fraction审计162hash匹配。干态非零Darcy两个方向独立公式/负对照与相关35项通过。资料见FREE_SLAB_PHASE_TRANSFER.md及research/free-slab-phase-v1。

正式非editable安装已终态：97测试61.68s通过，XML零失败/错误/跳过；61实际site-packages模块测试前后逐字一致。session87831/43779已exit0，无活动EOS，不再轮询。骨架/输运/相间系数仍制造，尚非原泥材料或完整干燥。下一推进两格一格耗尽一格仍湿，原六门槛保留；候选在/private/tmp/brick-free-slab-depletion-design，未运行。完整固体反应/动态边界/空间收敛/真实原泥及三机制公开留出仍未完成，Goal active。

本回合从5c5f09a推进多格自由主机，属于实际progress：新增free_slab_rates/CurrentSolidStorage/FreeSolidSlab，全局共同t_dot、局部constraint功和同次当前温压/共享热流真正连接。主机源码b78efa42，瞬时率21bc4cb2，点储能4b94d58a。独立代码/数值审查通过；固体与力学/输运仍是制造参数，material_qualified=False。

实际干态两格独立DOP853对照通过：6/8steps，E误差1.605862e-6/6.980263e-7J，stretch误差3.928e-8/1.707e-8；漏局部constraint的负对照虽全局守恒仍过，局部E偏差.0810722J。真实水两档固定相态轨迹41.693s完成：1/2steps、8/15eval、13.126/24.586s，T终值299.9999889194692/300.99999007520626K；全prefix外功残差最大4.208e-11J。独立Fraction复算通过，全数据见research/free-slab-v1。没有蒸发或液/气物质面流，不能叫完整干燥或完整材料验证。

安装已终态：61真实site-packages模块逐字节匹配；150相关测试8.46s通过（session40608已exit0），之后仅补3项纯测试覆盖tdot零但R非零/正确物理重编号/第二cell反解失败保留prefix，installed3项0.54s通过。运行源码未改变；真实wet记录160源/测试hash在当时独立核查一致，后来2个测试文件只增3测试，有单独最终XML。当前无活动测试/EOS，不重复29920/40608。全部原失败/候选/审查/安装身份已归档，随本阶段本地提交保存。

下一直接工作：WaterPhaseTransfer显式准入FreeSolidSlab（保留真实水caloric/source gate与constraint组件），实际多格蒸发/耗尽、非零Darcy/液面迁移组合；之后组成相关自由骨架/固体反应与动态炉温。空间收敛、完整原污泥材料证据、三机制公开留出、全周期/应用入口仍全部必需。Goal active，原§11未满足。


本阶段全部运行已终态：源码真实自由液相耗尽1项178.373s通过，安装172相关轻测53.36s通过（session83000已exit0），58真实site-packages模块测试后再次逐字节匹配。research/mechanical-depletion-v1已保存完整原始产物。无活动测试/EOS，不重启旧61001/83000。独立原始结果复核已通过：152源/测试hash一致、19prefix Fraction审计通过，实际独立分支113eval与6项门槛已核。阶段提交后推进多格自由几何/反应/材料域。Goal仍active，原§11未满足。


自由机械液相耗尽真实attempt03已完成：177.721s/305eval/19已提交steps/1事件，终点1e-4s；两次终端比较与独立halved-controls全部通过，原精度门槛保留。事件3.0417417141788028e-5s，逐prefix外压功最大残差1.12965e-10J、水4.68239e-21mol。research/mechanical-depletion-v1保存全部原失败/JSON/XML/sourcehash与审查。session61001已exit0，无活动EOS，不再轮询。自由主机仍是固定固体单格制造骨架，不能称真实原泥全周期。

当前唯一安装轻测session83000，100s外层硬限；非editable实际58模块与源码逐字节一致，src/tests冻结。恢复先poll同handle，完成后核实际XML并复制installed-*证据，完成本阶段本地提交。新源码SHA c9139510，机械候选加干态共同端点修复；没有重复实际湿干EOS。下一工作需将自由几何/全能量/共享面接入一维多格并接固体反应，继续真实原泥材料证据及三机制公开留出验证。Goal原第11节仍未完成。


当前唯一实际EOS试验session61001：自由湿干attempt03，固定源码SHAc9139510应用机械耗尽+已审干态共同端点修复，36针对性测试10.55s通过。原attempt02失败来自tc-at再相加舍入到tc前驱float，不是机械守恒/材料失败。按106.9s192eval实测成本，attempt03资源上限180s/外层210s，原物理与精度门槛全部不变。恢复须先poll同session，不重启；src/tests冻结。输出/private/tmp/brick-free-mechanical-depletion-v1/attempt03.*；新版本尚未安装验证，Goal仍active。


机械耗尽生产候选已按审查SHA9d569f8696精确应用，13制造新例+11旧例+4host guard共28项6.18s通过；生产应用独立code-reviewer再次APPROVE。非机械旧guard改为缺机械尺度前置拒绝，未改物理参数。来源/原RED/中间失败在research/mechanical-depletion-v1。相关轻测session46325已exit0，168 passed in53.42s；未安装新版本。

真实自由湿干attempt01在积分前被actual水摩尔质量逐位匹配拒绝，正确改为从actual chemical.reference绑定后attempt02运行106.90s/192eval/23试算panels，返回numerical_failure:unresolvable_stage_time。首轮相邻终端细化6维全通过，但level2终端细化的dry续算时间分割失败，尚未进入独立halved-controls验证，因此没有事件提交，保留12湿态有效steps；不能冒称真实事件组合验证成功。原门槛/物理未改，全部JSON/XML/log/源hash与事前合同已保存。program_knot_review正在隔离只读诊断实际时钟边界及轻量复现，禁止跳过独立更细门槛。无活动EOS；测试84176已exit1。Goal仍active，原§11未完成。


普通自由液汽转移安装终态：session40338已exit0，80 passed in10.57s，XML实际零失败/错误/跳过；58实际site-packages模块与源码逐字节一致。源码与安装实际蒸发轨迹数值相同，证据research/free-phase-v1完整保存。无活动EOS，不再轮询40338；后面的运行中仅为历史。

下一机械耗尽候选现已冻结在/private/tmp/brick-mechanical-depletion-candidate/depletion_integration.py，SHA9d569f869666fceee92bd13c4a412ab8578391dbb48419b010a025cb347de43f，candidate.patch/PLAN/测试及RED/中间失败保留。作者13新noEOS5.62s、11旧0.35s通过；尚未Root应用/安装/真实wet验证。program_knot_review与mechanical_code_review已启动独立只读审查该候选；恢复先取实际审查结果及文件。不得把候选完成当repo准入，现repo仍明确拒机械耗尽。Goal active。

2026-09-08 UTC 普通自由相转移：WaterPhaseTransfer现显式接纳ClosedFreeSolidCell，真实当前TP/气体积计算液汽源，原热化学桥核查不变，外功和机械率逐项保留。顶层source_ids补入实际基础评价完整来源。源码4真实测试9.63s+76回归1.53s通过；实际.001s液水减少3.2293e-7mol、蒸汽等量增加，T299.999736919K/外功残差1.35e-11J，原预算和checkpoint通过。候选与RED/输出见FREE_PHASE_TRANSFER.md及research/free-phase-v1。源码冻结，安装58实际模块已逐字匹配；唯一活跃安装验证session40338，60s硬限，恢复须先poll该句柄确认终态。

下一机械耗尽候选reacting_skeleton_provider正在/private/tmp/brick-mechanical-depletion-candidate隔离实现（不改repo/不EOS）：frozen/affine终端推进mechanical state与ledger，event/common-time比较、全局原初态累计审计。候选RED4项被原guard拒绝；首轮候选2守卫通过、两terminal完成但独立exp(t)普通approach精度未过1e-8，保留失败并收紧内部数值预算、外部验证门槛不变。未审查/未应用，不能宣称耗尽机械已完成。Goal仍active，完整第11节未满足。

动态储能/自由单格安装终态：session28559已exit0，167 passed in26.70s，外层26.965s回收。XML实际解析零失败/错误/跳过，58个实际安装模块与源码逐字节一致。安装湿轨迹与源码温压/伸长/功残差相同，粗细耗时6.612/12.512s；下文进行中为历史，不再轮询28559。没有活动EOS。

下一只读/隔离候选reacting_skeleton_provider在/private/tmp/brick-free-phase-candidate准备：新动态点/ClosedFreeSolidCell接实际液汽相间转移，保持总E与相参考能，不伪造旧host类型或丢机械state；随后耗尽terminal panels真正推进机械量/账本。该候选不改repo/不安装/不EOS，不属于167已通过结果。恢复从实际代理/文件状态继续。原第11节仍未完成，Goal active。

2026-09-08 UTC 动态储能/自由单格阶段：已新增dynamic_solid_storage.py及free_solid_cell.py，当前(n,t,N,E)真实反解温压再求自由牵引率；不构造PrescribedSlabMotion。integration新增独立external_traction/body功schema，保留原schema；数值错误保留接受前缀。dry/source审查通过。源码163回归3.24s+3真实wetpoint3.08s通过；实际湿fixedphase自由轨迹0→.001s两档1/2步通过，T差5.5e-12K、stretch差1.8e-12、外功残差<6e-11J。原宽误差精度失败与资源失败均保留，详见DYNAMIC_SOLID_STORAGE.md及research/dynamic-solid-v1。

当前唯一活跃验证session28559：非editable安装已完成且58个site-packages模块实际与源码逐字相同；安装167相关测试含真实wet两档正运行，外层90s硬限。恢复先poll同句柄，未终态不得宣称安装通过/重启。源码和tests冻结，下一任务不得并行跑EOS。下一必需阶段是固定相host接相间水分转移/耗尽事件及源误差传播，然后多格相容、输运/反应/烧结冷却完整周期；本阶段短单格轨迹不是目标完成。Goal继续active。

机械状态安装验证终态：唯一session47407已exit0，284 passed in44.62s。实际XML解析零失败/错误/跳过，56个实际site-packages模块与源码逐字节相同。安装cwd=/private/tmp、无PYTHONPATH。不存在待运行本阶段测试，不再轮询47407；下文“进行中”仅保存当时状态。

机械core独立审查已实际读完整修改与测试，无阻断；checkpoint/service修复后code-reviewer复核APPROVE。下一点储能候选仅由reacting_skeleton_provider在/private/tmp/brick-dynamic-storage-candidate准备，不改repo、不安装、不跑EOS；恢复先读代理/候选实际文件。候选方向为不依赖PrescribedSlabMotion的单格DynamicSolidStorage，零速率恢复能→实际温压→自由率，完整几何/来源/误差身份保留；尚未应用，不属于284通过版。

2026-09-08 UTC 机械动态状态阶段：从 f7bfa7a 实际推进 integration.py 的显式 mechanical_stretches/rates、独立误差尺度、全RK阶段及拒步/取消事务和伸长求积账本；checkpoint 保存/逐位连接/原初态累计审计机械字段。旧固定/规定几何主机和未同步实现的耗尽路径明确拒绝机械状态，库存舍入回写保留字段。具体合同见 MECHANICAL_STATE.md。源码122核心/检查点/轨迹测试3.16s及162服务/搜索/旧事件测试31.70s通过。旧非机械基准16接受/1拒的原字段逐字一致，新字段均None。相关原始XML、RED和修复前缺import失败已保存在 research/mechanical-state-v1。非editable安装实际56模块匹配；安装同组验证进行中，恢复先检查下述终态记录/唯一session47407，不重复启动。

新的下一执行点：新增直接接受当前机械状态的点储能入口，不能构造预定motion代替动态状态。由(n,t,N)构造体积/孔体积，以Etotal减恢复能反解温压，然后调用自由牵引闭合，给总能量加入真实外压功；先验证单格干/湿轨迹，再实现耗尽事件、多格机械相容和CLI/UI场景。当前DOP853对照只是制造自由机械轨迹（0→0.1s，p0、pe0/100），并未做真实污泥或全湿烧制验证。Goal仍active，§11未完成。

2026-09-08 UTC：新增 free_skeleton_rates.py，实现制造固定固相单格的瞬时自由牵引双速率闭合。法向/横向分别求解，保留实际牵引与功率残差及数值误差证书，不截断越域速率、不追加重复耗散热。独立物理/Python 审查无阻断；源码39测试0.14s及非editable安装39测试0.12s通过，实际56个安装模块与源逐字节相同。证据见 research/free-skeleton-rates-v1。Olevsky 教程/镍粉压力辅助论文核读见 data/sandbox/research/free-sintering-source-v1；没有准入真实污泥参数，没有分发未确认许可的教程PDF/截图。

下一可执行步骤是把 (n,t,N,E) 纳入真实积分阶段和误差控制、拒步、域终止及 checkpoint，替换只能 prescribed motion 的机械状态来源，随后验证完整自由形变轨迹；多格还需共同切向伸长与空间力学相容。当前函数的孔压由调用者提供，并非 EOS 耦合或全周期模型。Goal 继续 active；原第11节尚未完成。材料与公开验证缺口继续保留。

Agar2018 Fig3已推进为实际可重放数据：原PDF第5页矢量导出，六运行各30标记，共180项保留path顺序索引/形状/颜色，排除图例与设定TGA虚线；全标记控制点包络和轴线宽度通过Fraction角点映射为时间/温度条件区间。6个30min末点包络越图域明确flag不截断。来源和脚本哈希见data/sandbox/research/agar2018-heat/figure3；尚不是仪器原始数组、实验不确定性或模型外部验证。墙/料温不同运行身份保持，alpha/Cp循环不能作为验证。下一材料工作继续取得独立热物性或边界依据，再预登记真正的预测/留出对照，不因有180点就准入完整材料。Goal active。

比热来源追查有实质新证据：取得德国国家图书馆Agar2018原PDF（10.1007/s11356-018-1463-y），依第9页CCBY4保留未改动source.pdf及哈希，root与独立审查目视第5页。Cp1950仍是Kim&Parker引用输入；式4用Cp和同一温度曲线反推alpha，因此alpha/Bi不能独立验证Cp。Fig3的六次温度标记是可提取的传热验证候选，墙温与料温不同运行、TGA虚线为设定，尚未数字化/拟合或准入。材料9.8%湿基预干颗粒，主反应器初有空气，TGA氮气不能移作边界。详见data/sandbox/research/agar2018-heat。Kim原文机构搜索未取得，PubMed验证页，不重复无变化请求。下一主线以独立热物性/边界证据打断Cp—alpha循环，并准备该实测温曲线的预登记提取与运行级留出；完整原泥/烧结冷却仍必需未完成，Goal active。

真实材料主线新增Liu2023审计（DOI10.1093/ce/zkac058）：出版社HTML及表1/2/6/脚注/参考文献32实际读取，下载哈希，不再分发全文。Decimal与独立Fraction发现daf元素和68.78%、显热分项比例4.15684%而刊载4.02%、可用能按脚注65.16564%而刊载73.56%；比热1.95借用Kim&Parker2008，不能当同批实测。原值、条件舍入和未知基准保留于data/sandbox/research/liu2023-energy。无材料准入或EOS/求解器修改。下一具体入口：核读原引文32 DOI10.1016/j.biortech.2007.01.056的材料、比热性质和温域，继续补原泥热量/产物闭合；审计不替代烧结冷却/全周期实现，Goal active。

多代搜索已完成首个实际增量：search.py冻结目标/约束/变量/策略及来源，确定性坐标邻居、父结果关系、越界省略、全部评估和停止原因；跨代与恢复共享尝试和活动wall预算。源码/非editable安装各132相关测试通过，55模块前后匹配。原生两代五次均completed/exit0/reaped，78.995392375s；独立账本五条通过，CLI/Python一致。入选300.375K案例温差0.6249899491094197K，单独refinement1四步复算差2.9558577807620168e-12K，原1e-5K门槛通过且账本通过；不是空间收敛或现实材料验证。证据research/search-v1，详情SEARCH.md。所有原生与测试句柄终态，无活动EOS。相关会议能源研究的官方文件读取失败记录在data/sandbox/research/gnest-related-energy-v1，摘要片段未准入；不能据来源不可访问断言物性不存在。下一主线回到真实原泥产物/热容参考能的材料闭合和自由烧结冷却证据：以明确材料身份定位可核读原始数据，不能继续以制造搜索/界面功能替代全周期和三个公开机制留出验收。Goal保持active。

敏感性设计首阶段已实际交付：sensitivity.py严格1..3因子全端点设计、五条物理输入路径与单位/分类白名单、失效分支因子拒绝、冻结设计/候选绑定及所有端点完整后的高低均值差/斜率；不把网格/步长/开关作为工艺变量。CLI sensitivity-prepare/analyze已实现。128源码/安装相关测试通过；最终安装128通过3.26s，54模块匹配。原生初温300/300.5K两候选均2接受步completed，累计32.878858667s，2进程exit0/reaped，两轨迹原独立账本通过。审查后仅补指标计算模块身份字段，最终重新分析原封存结果，16原指标独立重算、8组差/斜率和CLI/Python一致；不声称metadata变更后原生重跑。证据research/sensitivity-v1共240成员重开核验。方法见SENSITIVITY.md；只是制造案例的限定端点对比，概率不确定性/全局敏感性/多代搜索仍为必需未完成。所有本阶段句柄终态，无活动EOS/测试。下一可执行项：有冻结目标/约束、父代变化和总预算的多代搜索基础，维持真实材料准入阻断；科学主线继续补同材料可闭合反应/热容参考能及自由烧结冷却，不能以应用功能替代材料全周期/公开三机制留出验收。Goal保持active。

实验级中途续算已实际核验：基线33b5e3c同一安装53模块，refinement1单候选12s取消后1接受步→run_experiment实际resume完成4累计步；两原生作业reaped，退出1/0，2次累计wall34.994843417s，原前缀和父结果SHA严格保留。根代理read_run/read_experiment及原精确账本重复核验1+4前缀、Fraction预算和代码身份通过；未新增不中断对照，不宣称一般跨重启逐位一致。证据research/experiment-resume-v1，243成员重开SHA/字节核验，无活动EOS。补齐上一阶段实际中途续算，不改物理/运行时代码。

科学来源有新决定性证据：data/sandbox/research/gnest2021已逐页目视接受稿表3/4/5并找到出版版核对；R5/R6产物和分别0.070/0.090，对式11要求的0.12/0.14均差−0.050，超过最近舍入条件界0.008。出版表3同值；TG3高温干进料产物差0.0493，表5仅分析基准账目，不是完整矿物元素。Decimal与独立Fraction审计一致，页码13修正保留审查说明。来源只作为事实/拟合候选，未做归一化、未填未知产物或Cp/反应热；论文25°C热值平衡不能补齐各伪组分动态能量。该来源直接用作全周期成套材料包的路线被阻断，停止对同表反复尝试。下一可执行工作：推进实验设计/敏感性和有父代记录的搜索接口；并寻找可解释缺失产物/分析基准及成套热容参考能的独立同材料来源，保持材料身份不混用。原泥/自由烧结冷却/全周期/公开三机制与留出/多代搜索完整要求仍未完成，Goal保持active。

批量实验阶段完成首个实际增量：experiments.py共享已有job/run服务，冻结候选/来源/代码与预算，累计尝试和活动wall，锁定顺序执行，取消请求/队列继续/描述性比较及CLI已实现。99相关源码测试2.97s与非editable安装测试2.93s通过，53模块前后匹配；最终两候选coupled/control实际31.86395s完成，两个子进程exit0并reaped，原独立账本两条通过，CLI/Python状态和比较完全一致。证据research/experiment-batch-v1共452成员重开SHA/字节核验。原归档脚本路径替换错误导致账本glob空循环误报和两CLI错误，原始产物保留，最终verify_saved显式要求两轨迹并实际核验；未改变物理门槛。审查修复总预算超限仍完成、损坏journal异常、方程目录绑定及超限覆盖原失败原因。accepted-prefix仅新编排分支测试，已有checkpoint自身验证不等同本实验端到端取消续算；pid=null的supervisor_failed仍保守拒绝，说明见EXPERIMENTS.md。所有本阶段原生/测试句柄终态，无活动EOS。新公开来源审计data/sandbox/research/raw-sludge-closure-audit-v1找到Global NEST/Energies两个不同污泥研究，产物/热化学完整准入尚未建立，不合并材料或安装猜测参数。下一步：实验端到端取消/续算、资源耗时敏感性与多代候选接口，并对Global NEST同研究产物和热效应闭合做有界可行性核查。原泥材料、自由烧结/冷却、全周期、三公开机制留出和多代搜索全部仍属Goal必需未完成，保持active。

本地中文界面阶段已实际验证：local_app与安装assets调用同一case/job/trace服务，CLI ui仅监听127.0.0.1，Host/Origin/token/JSON大小/UUID路径/来源清单守卫和单工作线程/20任务上限已实现。101相关安装测试通过5.65s，52模块前后匹配；2项无损导出/异步绑定Node回归在源码和安装资产通过。实际浏览器编辑/非法材料拒绝/求解/重放/来源打开/温压端点/对比/焦点/取消/超时/续算已执行。7原生子进程均终态reaped：3条2步completed，立即取消0步，超时0步，refinement1取消1步→续算4累计步completed21.6468s。五接受轨迹独立原账本通过，run/replay数值与诊断完全一致。发现浏览器JSON重序列化舍入大整数后已改rawtext无损导出，最终页面完整报告与原结果/manifest完全相同；旧失败、下载事件未确认、晚到取消操作和截图时序问题均保留research/local-ui-v1。四测试服务器40104/23725/57004/76677均停止，无活动EOS/测试/界面服务。Ctrl-C仍在关闭后打印KeyboardInterrupt非零退出，未称修复；Blob下载未获平台确认，可复制报告实际通过。下一实际交付：同服务下有预算的实验定义/比较和证据准入，继续补原泥成套反应/自由烧结来源与全周期闭合；炉温界面编辑、完整材料/三公开机制留出/多代搜索仍为Goal必需未完成，保持active。

整进程监督阶段已实际验证：新增job_supervisor/job_child及CLI supervise、job-status、cancel-job，实际Popen句柄控制SIGINT宽限/SIGKILL回收；父目录范围继承flock、UUID取消请求、状态/日志/CPU和原生RSS观察均保存。79相关源码和安装测试通过，51安装模块前后逐字节匹配。实际制造湿态run/replay各2步completed，外部15.7283/15.7448s，保存数值/账本/初终态诊断完全一致；10秒实际CLI取消后10.8449s退出，1接受步保留；0.05工作+0.1宽限启动超时强杀/reaped，外部0.2698s。三条接受轨迹独立原账本审计通过，四原生进程均终态，无活动EOS/测试。证据research/job-supervisor-v1保留实验外层备用时限150与预登记10不一致的偏差及原脚本；产品内层时限实际执行，不宣称外层10已强制验证。汇总校验已补足状态/退出码断言，原版本保留。仍无父监督器死亡后的独立看门狗、内存硬上限或一般强杀恢复；RSS单位明确未归一化。下一实际交付：共享服务的轻量本地中文界面，呈现运行/取消/来源缺项；原泥材料闭合、自由烧结冷却、三公开机制/留出、多代搜索、完整周期仍为Goal必需未完成，保持active。

检查点续算阶段已实际验证：新增checkpoint原始初态/逐步/累计N/E与功分项舍入审计，以及共享Python/CLI resume。仅允许普通积分器已取消且有内部接受步的同输入/同实现记录；剩余步数、拒绝次数和积分wall按完整历史扣减，后缀先保存再审计并合并，重启不重置累计误差额度。50相关安装测试通过，49安装模块前后匹配。预登记真实水+制造反应/规定变形refinement1案例按1步取消→累计2步取消→累计4步完成，CLI末次续算15.6419s；与不中断4步27.0513s的所有保存N/E、账本、终态T/P完全一致，独立原账本审计通过；累计积分26.8253s。当前无活动EOS/测试，证据 research/checkpoint-v1。早期两次测试取消触发器在提交前取消导致3失败的原文件/XML保留，已根据实际8次初态/RK/接受态评估确定下一试探时取消，未改物理/数值门槛。下一实际交付：整个服务进程的资源监督与持久运行状态，再接中文界面（当前仍无强杀恢复、通用耗尽事件检查点或完整全周期应用）；真实原泥材料、自由烧结冷却、公开三机制/留出、多代搜索保持必需未完成，Goal active。

来源图阶段完成实际增量：以525142d为基线新增安装包内19方程/38参数/4输出目录与运行时DAG，实际解析案例指针、AST函数行号、来源JSON位置及缺项，保留非JSON位置的声明性质。严格元数据/分类、引用/环路/路径、目录及代码/来源绑定检查已审查。40入口/来源测试通过；48实际安装模块及目录字节匹配。新CLI单例/重放completed各2步，外部15.5579/15.5387s，数值和完整来源图一致；独立账本通过，CLI/Python压力查询一致，四量均可追到登记来源资产。原生运行全部终态，当前无活动EOS/测试。证据 research/run-provenance-v1；方程目录仅覆盖当前制造湿态模型，资产可读率不代表材料/物理参数/实验覆盖率。下一可执行步骤：为已接受前缀接入冻结输入/实现身份的检查点续算及整个运行的资源预算，随后接共享服务的中文界面；真实原污泥完整证据、自由烧结冷却、三公开机制/留出、多代搜索和完整周期仍保持必需未完成，Goal active。上一段“完整依赖图下一步”已在本制造模型声明范围内取得增量，不能扩大为全Goal来源完成。

统一入口阶段实际完成：独立安装的 verification_case/run_service/CLI 不再依赖 tests 或临时实验帮助函数。严格 JSON/rawSHA 制造案例与真实水来源分开；25 新入口测试通过，47 实际安装模块前后匹配。两格 CLI run/replay 均 completed（外部15.5208/15.4597s，各2接受步），全部数值结果/账本及初终态诊断一致，独立原账本审计通过；四格新父态守恒初始化+初态callback通过4.0832s，未运行本入口四格轨迹。初态温度重构门槛已真正接入run服务。审查阻断项已修复，证据 research/cli-delivery-v1，操作 docs/sandbox/CLI.md。当前无活动EOS/测试。下一可执行工作：把来源导航提升为结果量—完整方程—派生参数—原始证据位置的机器可检查依赖图，补齐运行预算/恢复和界面；材料研究继续保留真实原泥关键证据缺项。此入口只有制造验证模型，不能替代材料/自由烧结冷却/公开三机制和留出/多代搜索/全周期必需交付，Goal继续active。下文历史live句柄均已终态。

程序节点修复已完成完整验证：session33496终态exit0，XML1293通过/零失败错误跳过573.270s，前后43实际安装模块及冻结源码/tests字节一致。当前无活动EOS/测试。14新回归、102相关验证、原2失败6通过和旧粗精度affine残余2失败全部保留，归档research/program-knot-v1。仅修ordinary端点表示，未放宽中点/库存/能量门槛。下一实际交付按归档NEXT_DELIVERY_STEP：接通新沙盒统一案例加载、CLI/Python运行与结果来源查询，去掉运行对tests帮助函数的依赖；真实原污泥缺项必须结构化阻断，不能自动退到制造案例。完整材料证据、自由烧结冷却、三公开机制/留出、全周期界面/多代搜索仍为Goal必需未完成项。旧live句柄为历史已终态记录。

程序节点修复候选（c3abc7a后未提交）：已在旧源码复现.005步长停在.05前一个float（2失败6通过）；新ordinary端点函数仅在已知节点、32cap-ULP界及精确库存安全余量内合并前一完整panel，不跳时间/不改中点守卫。14新回归及102相关测试实际通过。旧rel1e-7的两个保留affine算例现可完成节点/事件，但A误差1.83e-10/1.65e-10仍超原1e-10门槛，失败与全轨迹保留；当前rel1e-11同.005回归通过，不能称旧配置全通过。审查在 /private/tmp/brick-program-knot-v1/；新源码已非editable安装、43实际模块字节匹配。当前唯一EOS/测试为完整安装回归session33496，XML目标 /private/tmp/brick-program-knot-v1/installed-full-tests.xml，先poll同句柄，不重启、不并发EOS；源码/tests/安装冻结。下一步终态XML/43模块后核、归档失败和新验证、阶段Git提交。完整Goal仍active；当前不得宣称完整suite/材料/全周期通过。

固定域4格阶段已完成实际验证：2初态callback各144项面代数检查通过，171项无EOS缩放和6负控通过；4格2/4步轨迹completed30.990010/55.240541s，局部账本门槛减半后仍通过，2/4网格保守比较已完成。空间T诊断差±1.4464e-6K，远大于时间cap差，空间收敛仍未证明。43实际安装模块/4监督输入before-after-current一致，无活动EOS/测试。归档 research/fixed-domain-spatial-v1；原中间孔容构造缺陷候选保留并已修正。下一优先动作按归档NEXT_NUMERICAL_PRIORITY复现/修复普通分段时间节点单ULP尾段问题，保留原失败与中点可表示性门槛；不是继续把极短跳跃场网格比较称为全周期完成。生产/测试仍67730b2。原污泥材料闭合、自由烧结冷却、三公开机制及留出、CLI/UI、多代搜索等完整Goal继续未完成。下文live句柄为已终态历史记录。

固定域4格运行检查点：修正中间流体模板体积构造后，冻结fixture66639ad9/PLAN1ad81a3b（原候选保存在preflight-original）。两初态callback84987/58680终态通过，gradient/uniform各144项独立面代数审计通过，初N/E保守继承及同温forward广延性通过。wet4 coarse session71600已completed30.990010s/2步，逐格账本通过；当前唯一EOS为fine session15156，先轮询同句柄，未通过不可执行网格比较。源码/安装/实验脚本冻结。下一步fine账本、保守2/4网格差异与时间cap分开比较、源身份复核及归档。该短跳跃初场两网格不证明收敛；完整Goal仍active。

固定域空间细化准备中：当前生产/测试仍 67730b2，上一阶段证据提交 c62fb2f。新实验 /private/tmp/brick-fixed-spatial-v1 保持0.02m半板，4格库存/微界面面积/相变系数减半、q权重倍增，初始N/E保守细分。独立无EOS缩放检查已实际通过171项及6个错误权重负控，证据 /private/tmp/brick-fixed-spatial-audit-v1/scaling-result.json。新脚本/初态来源界正在交叉审查；尚未运行新callback或4格轨迹，无活动EOS/测试。下一步完成审查后先初态callback，再固定两timecap轨迹与独立账本/保守网格比较；两个网格不能宣称空间收敛，完整材料/全周期Goal仍未完成。

两格阶段实际完成：4 条轨迹全部 completed（coupled 2/4 步，control 2/4 步），逐格/全域独立账本通过，四组固定判据比较完成。温度约 ±1.4464e-6 K 与能量效应分辨，水库存及相变速率效应未分辨。6 个监督进程均终态，无活动 EOS/测试；全部输入 before/after/current 一致（callback 各180、wet 各181），43 实际安装模块与源码一致。生产/测试仍 67730b2，本轮仅实验/审计及文档证据。归档目标 research/two-cell-wet-coupling-v1；下一步按其中 NEXT_SPATIAL_SCOPE 保持固定物理域与广延量做空间细化，不能简单复制 q(N) 权重。完整 Goal 的真实原泥材料、自由烧结冷却、三个公开机制/留出、CLI/UI 和多代搜索仍未完成。下文旧 live 句柄均为历史检查点，不得据此重启。

当前两格验证（生产仍67730b2，源码/测试未改）：新冻结实验 /private/tmp/brick-reacting-wet-two-cell-v1，2格300/301K、规定变形、A/B反应、活动相变及内部传热/质量修正扩散；制造系数与真实水来源分开。coupled/control freshcallback66328/61026均terminalcomplete2.467376/2.453034s，耦合内面非零/对照全零，43源码安装字节匹配。当前唯一EOS为wet-coupled-0 session25354，2步上限起始设置，内部120/外部150秒100panel。审计脚本 /private/tmp/brick-two-cell-audit-v1 保存逐格/全域精确账本及失败；完整4run两mode两cap尚未完成，不能宣称空间收敛或全砖完成。先poll25354终态和独立账本，再依次剩余三条，保持所有输入冻结。

最新阶段完成：affine_midpoint及不可变二次时钟已通过1279完整安装回归（session8135终态exit0，XML585.898s，零失败错误跳过），运行前后43模块字节一致。v5两条联合湿反应/规定变形/耗尽/干态延续及原N/E/T/P/时间对照通过；独立14/16步账本、相修正及每次182输入核查通过。跨cap湿态路径相同、只干态网格改变，不能把事件时差0解释为收敛阶数；每条内部不同湿态网格检查真实通过。当前无活动EOS/测试。证据归档 research/affine-terminal-v1/（含全部候选失败、审查、原v5结果、完整suite）。下一实际步骤见该归档 readable/affine-terminal/NEXT_COUPLED_SCOPE.md：用现有模块建立2格非均匀湿态反应/传热/传质及关闭输运对照，再固定域空间细化；.005普通程序节点失分辨率仍是独立未修bug。原污泥材料闭合、自由烧结冷却、三公开机制/留出、CLI/UI与多代搜索仍为必需未完成项，Goal active。

最新v5两条均完成并比较passed：18043/36073均terminalcomplete，内层87.845694/85.501777s，260/303eval、31/36panel、14/16接受步，各1耗尽事件。compare.py exit0，N6.65799e-12mol/E2.61061e-8J/T2.60496e-9K/P3.96649e-7Pa/time0，原gate全部通过。当前唯一EOS为完整安装回归session8135，XML /private/tmp/brick-affine-terminal-v1/installed-full-tests.xml；43模块运行前匹配。先轮询终态并核XML/运行后43模块，再归档所有控制失败/独立审计/v5证据并阶段提交。源码/tests/安装/脚本冻结；不能把v5或99目标测试代替完整suite及全Goal验收。

最新v5第一条已通过：session18043 terminalcomplete/child0/89.429237s，内层completed87.845694s260评估31panel、1实际耗尽事件(.5002854010435919s)、14接受步，到.5078125s；两次末端比较及独立减半检查均通过原门槛。当前唯一EOS第二轨迹session36073（depletion1），同原120/150预算。先轮询36073终态，若通过才compare.py；随后当前源码完整安装回归与43模块复核、归档阶段提交。第一条通过只属制造反应/规定变形/真实水物性的组合，非完整原泥全周期或材料现实验证。

当前候选（e9db77b后，未提交）：新增不可变affine_depletion_clock与可选affine_midpoint末端，同权积分全部物种/能量/分项；59新测试+40旧相关测试实际99pass34.213s。来源最终switch/common漏洞已故障注入后修复；非线性公开无关制造oracle通过，较粗普通路径误差与.005旧knot失败完整保留。已非editable安装43模块字节匹配；v5 freshcallback46178终态complete2.014814s。当前唯一EOS session18043，/private/tmp/brick-reacting-wet-v5/depletion0-attempt01；原120s内部150s外部500panel及全部物理/门槛，唯一改动terminal_method。源码/tests/安装/脚本冻结，先轮询该句柄真实终态；未通过不执行depletion1。当前源码完整suite尚未执行，旧1220不能转移。Goal仍active且完整材料/全周期任务未完成。

最新完成阶段：HEOS TP回溯修正完整安装回归 session9190 terminal exit0，1220通过/零失败错误跳过，XML539.545s；前后42实际导入模块与源码逐字节一致。当前无活动EOS/测试。原生九点旧8pass1fail/新9pass；v4通过旧TP失败点和两次末端比较，但必需独立减半检查在原120s预算耗尽，0事件，depletion1未运行。74项原始证据已归档并逐项复读核SHA/长度：research/heos-tp-backtracking-v1/，包含失败XML、原始候选、源码绑定、v4结果与独立审计。下一有限数值步骤见其中 readable/wet-v4/NEXT_NUMERICAL_STEP.md：研究二阶末端积分与真实事件时钟证据，保留全部门槛和独立检查，先解析/制造解验证再原联合实验；暂未实现。完整Goal仍active；原污泥材料闭合、自由烧结冷却、三公开机制/留出、全周期CLI/UI与多代搜索仍未完成。

当前最新终态：v4 callback session26272 complete/child0/2.087812s；depletion0 session10907 terminal failed/child1/121.780958s，内部resource_limit:wall_time_limit120.127148s、365评估44试算panel、6接受步、0事件。TP旧失败点已通过；level4/5两次末端比较均通过原门槛，但独立减半普通接近检查在13panel/122评估时耗尽预算，未提交事件；depletion1未运行。完整安装回归唯一活动session9190，XML /private/tmp/brick-heos-tp-backtracking-v1/installed-full-tests.xml，42模块运行前匹配，源码/测试/安装冻结。先轮询同句柄至终态、核XML及运行后身份，再归档全部失败/审查并本地阶段提交。Goal仍active，真实材料/全周期完整范围未完成。

当前未提交TP修正：六分数原生探针session54000 complete1.16260s，五短步原动态gate+完整snapshot通过；候选控制30通过，原生九点旧版8pass1fail、新版9pass（session64092 complete1.46507s，XML1.031s）。kernel已应用c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12；manifest5f9e39bf...、wrapper和source注册仅绑定hash同步，42实际安装模块匹配。证据 /private/tmp/brick-heos-tp-backtracking-v1 与 /private/tmp/brick-heos-tp-step-probe-v1。当前无活动EOS/测试。worker准备 /private/tmp/brick-reacting-wet-v4 原5脚本/物理/门槛/120s内部150s外部500panel；还未运行联合v4或当前源码完整套件，旧1192不能移到新源码。完成review后先v4，再完整安装回归。Goal仍active且完整材料/全周期范围未完成。

最新终态：1192完整安装测试通过（session11689/535.553s），42模块前后匹配；v3联合轨迹仍在level3 HEOS TP失败，0事件。诊断43826已terminal failed49.48452s，精确捕捉295K/53692.54782795906Pa的8次双密度周期；295K是反解下界、非实际砖温。独立公开接口单点92373已terminal failed1.18991s，复现相同heos_tp_not_converged；原动态min(1e-4,rho*1e-7)Pa门槛未改。当前无活动EOS/测试。全部本轮证据归档 research/depletion-spine-v1/（旧失败/审查/安装/原v3/异常捕捉/单点），下一TP修正设计见 TP_FAILURE_NUMERICAL_REVIEW.md；须先保留精确失败并预登记有界校正，不重复整条无诊断运行。完整Goal仍active，原污泥材料闭合、自由烧结冷却、三公开机制/留出、全周期CLI/UI与多代搜索仍未完成。

完整安装新终态：session11689 exit0，1192通过/零失败错误跳过，XML535.553s；前后42实际模块与源码逐字节一致。当前唯一EOS句柄为诊断session43826，目录 /private/tmp/brick-reacting-wet-v3-diagnostic/diagnostic-attempt01；已完成两份只读脚本审查，原120s内部/150s外部限额，异常追踪不改求解器/来源守卫且不增加EOS调用。原v3失败仍未解决；先poll43826至终态，再核实际失败TP/迭代及source证据，不能把捕捉成功称轨迹通过。

最新运行入口：v3 callback session39396已terminal complete/child0/2.09734s；depletion0 session45698已terminal failed/child1/47.38958s，内部45.76055s147评估18试算panel、6已接受步、0事件，原因为 liquid_property_solution:heos_tp_not_converged；复用12观测9普通panel。不能称新事件策略完成联合轨迹；第二全轨迹细化未运行。完整新安装回归唯一session11689正在运行，XML /private/tmp/brick-depletion-spine-v1/installed-full-tests.xml；源码/tests/安装冻结，轮询同句柄，不并行EOS。下一终态核XML和42实际模块后归档提交；v3独立账本审计与TP失败捕捉方案由只读代理准备。

当前新改动（未提交）：耗尽普通湿态接近策略已应用 src/sludge_sandbox/depletion_integration.py，新增20独立测试；实际55相关测试通过13.26s，候选最终SHAab465ad7a1da9d39787afd7dd2c6dfc24e680936e9a6c99593b345ddbc49135a。可变观测别名、重复计费和最终来源绑定漏检均保留失败后修复；最后20通过5.828s。重新非editable安装，42实际模块逐字节匹配。下一串行执行 /private/tmp/brick-reacting-wet-v3 的原物理/门槛/120s内部150s外部500panel联合实验；随后完整安装回归。证据准备 /private/tmp/brick-depletion-spine-v1。原1172完整证据仅属a4f968f，不能移到当前源码。Goal完整§11仍未完成。

最新终态：压力传播修正完整安装 **1172通过/零失败错误跳过，XML557.992s，session36717 exit0**；前后42模块实际导入与源码逐字节一致。当前无活动测试/EOS。代码/7解析回归/48相关回归、v2湿态实际仍超时、独立算术与完整来源身份已归档 research/solid-pressure-bound-v1/。下一算法预登记 NEXT_EVENT_PREREGISTRATION.md；暂未实现。CLI_UI_NEXT_SCOPE.md核实应用层仍缺真实sandbox入口/持久运行与结果溯源，旧synthetic CLI不能充当完成。完整Goal仍active；真实原污泥材料、自由烧结冷却、三公开机制/留出、全周期CLI/UI及多代实验仍为必需未完成项。

最新恢复入口：v2 depletion0 session87557已终态failed/child1/121.7245s，内层wall120.0288s325评估6接受步0事件。已完成的三次细化压力指标变为0.00607/0.00519/0.00492Pa，原压力门槛通过；库存最后仍6.1412e-10mol高于1e-10，因此不能宣布联合轨迹完成。v1/v2所有失败保留；下一机制需提高事件定位收敛效率，不能增加本次上限或删去事件库存比较。当前完整安装回归 **session36717正在运行**，XML /private/tmp/brick-solid-pressure-bound-v1/installed-full-tests.xml，cwd/private/tmp无PYTHONPATH；同目录installed-identity.json已记录运行状态。源码/测试/安装/脚本冻结，轮询同句柄，无其他活动EOS。尚未提交solid_fluid_storage.py与新test_solid_pressure_bound.py，完整suite过后核XML+42模块再归档提交。tg_code_review正在只读v2算术审计，python_backtracking_integration_review在写下一事件数值设计；记录在pressure-bound-v1临时目录。

最新运行入口（994adec之后，未提交数值改动）：solid_fluid_storage.py已在保留原全局包络/越域拒绝后，以该已证明区间上端收紧同一体积误差的压力传播，原流体误差及液体能量界一致保留。7新解析测试：旧实现3预期失败/4通过，新实现7通过；48相关回归通过，两份代码/Python审查批准。重新安装42模块逐字节一致。v2位于 /private/tmp/brick-reacting-wet-v2，沿用原脚本字节/物理参数/误差/资源/事件门槛；callback session1060已终态passed，depletion0 **session87557正在运行**（120s内部/150s外部）。冻结源码/测试/安装/脚本，轮询同句柄，不并发EOS。完整新安装suite尚未启动；之前1165通过不能转移到这次源码改动。新数值证据目录 /private/tmp/brick-solid-pressure-bound-v1/。

最新终态：湿态联合callback通过，depletion0 session48458已终态failed/child1/122.0877s，内部wall_time_limit120.2988s。六接受步322评估、无事件；守恒前缀通过，但试探压力门槛含约1.602Pa误差下限，原1Pa门槛不可靠细化跨越。完整失败及173输入核验已归档 research/reacting-wet-v1-failure/。当前无活动EOS/测试，第二轨迹未运行。下一实际实现：保留全局区间及旧越域拒绝，使用已证实局部压力上端收紧同一体积不确定性的传播；证明/预登记在归档中。worker正在 tests/sandbox/test_solid_pressure_bound.py 写无EOS解析回归，root尚未改生产源码；不要把新误差界当已验证。

最新运行入口：公开 Lu2026 补充材料六条 MS 多速率失重记录及逐页独立核对已提交7af6f8d，见 data/sandbox/research/lu2026/。正文官方链接拒绝下载，基准/制备/气氛组成未知保留，未准入运行。湿态联合实验 /private/tmp/brick-reacting-wet-v1 已预登记并完成两份交叉审查；修正的是监督退出状态与失败证据保存，不改物理门槛。callback session42799 已终态complete/child0，实际同时A→B与蒸发、当前反应储能绑定通过。depletion0 **session48458正在运行**，同目录depletion0-attempt01监督，原120s内部/150s外部上限；不要重启同run或并发EOS。当前求解器/安装/脚本/PLAN冻结。下一步轮询同句柄，核实际完整结果与终态；成功后按原计划第二步长运行及独立账本审计，失败则保留原因诊断。

本次实现与完整证据已提交 **69a14f4**。当前下一阶段由 reacting_skeleton_provider 在 /private/tmp/brick-reacting-wet-v1 准备湿态反应/耗尽预登记与脚本；python_backtracking_integration_review 与 tg_code_review 等待最终文件进行只读审查。尚未运行新 EOS/轨迹，原完整安装 session99225 已终态。下一次恢复先读三代理结果与该目录 PLAN/审查，不重复旧全suite；先受监督回调，再按预登记执行联合轨迹。

最新终态：反应—规定变形完整安装回归 session99225 exit0，实际1165通过/零失败错误跳过，XML561.281s；前后42安装模块逐字节一致。93相关测试、两阶段细化与旧能量失败、独立代码/算术审查已归档 research/reacting-deformation-v1/，原始ZIP逐条重开核验。当前无活动测试/EOS。下文“99225运行中”为旧检查点。下一实验准备于 /private/tmp/brick-reacting-wet-v1，构建反应+真实水相变+耗尽联合验证，尚未执行；先审查预登记与脚本再运行。真实污泥材料/自由烧结/全周期范围继续未完成。

最新恢复检查点（dfa30aa之后，未提交）：新增显式 manufactured 的组成依赖骨架储能 q(N) 与规定变形反应耦合，旧固定固体库存路径保留。实际源码及测试变更见 Git 工作区；尚不属于真实污泥材料准入或自由烧结。93 项相关测试通过，Python 与代码审查通过。原细化对能量差 4.7827488742768764e-6 J 超过原 1e-6 J 门槛，失败保留；新 64/128 步结果由独立账本审核确认 ΔN=2.943464569304943e-11 mol、ΔE=2.9892544262111187e-7 J、ΔT=2.927231435023714e-8 K、ΔP=2.3685191990807652e-5 Pa，原物理门槛通过。新细化仅把显式步数资源上限从 100 提至 160，其余门槛未放宽。证据在 /private/tmp/brick-reacting-deformation-v1/，旧失败与修正均须归档。

当前完整安装回归 session_id=99225 仍在运行，XML 目标 /private/tmp/brick-reacting-deformation-v1/installed-full-tests.xml；不要重新启动或并发运行 EOS。42 个实际安装模块已与源码逐字节核对，测试期间冻结源码、测试与安装。下一步轮询同一句柄至终态，核实实际 XML 和安装身份，归档轨迹/失败/独立审查后再提交。尚不能声称完整回归通过。完整目标继续 active；材料证据、自由烧结冷却、公开机制与留出验证、全周期 CLI/UI/多代搜索仍未完成。下文为旧检查点。

最新恢复检查点（18087a6之后）：Areias2019 Figures38–40已按冻结预登记实际点选39目标，35可辨/4unknown。Fig38的300/400与Fig39的300完整抗锯齿列足迹超±2；Fig39的400被品红遮挡，不换列/补值。数据及来源链、原像素RGB、独立看图/74区间核算、精确舍入修复、4测试、实际JSON/CSV重放与图像重提取/再现证据在 data/sandbox/research/areias2019/tg_digitization/。

中间Decimal舍入对1e-100量级偏移可向内，独立发现已改Fraction整数floor/ceil，原发现与最终复审均保存。35观测是条件坐标读图候选，不是实验置信区间、反应转化率或模型外部验证；N2单速率、基准/制样/产物未知不变，材料/训练/动力学准入false。原论文及六张审阅图保留ignored缓存，无新增再分发许可。

物理src与既有1135安装验证版本不变，本轮不重复全suite或EOS；当前无测试/EOS待轮询句柄。本轮已产生实际来源数据与可重放转换器，属于progress。TG数据与代码/独立审查已提交ef5216f。下一实现的只读代码事实已保存 research/REACTING_DEFORMATION_SCOPE.md：host构造、host库存与skeleton三层仍限制固定Ns；反应config必须重绑实际current_storages。现有热U已含Ns形成能，不能额外加反应热；总压力功与组成依赖机械储能的拟议分账仍须独立推导审核，不能直接删guard。下一具体动作：预登记并实现新的显式制造反应骨架接口，先不改旧固定Ns身份/拒绝；以干态A→B不同占积/形成能+规定压缩、独立标量温度参照和非一阶速率当前体积检查推进实际耦合。随后验证组成依赖机械储能及水/输运组合；自由烧结和真实材料本构不因制造例通过而准入。当前无活动子任务。完整材料域、自由烧结冷却、三公开机制与留出、全周期CLI/UI/多代搜索继续为Goal必需未完成项。Goal active。

本次数值修复及1135完整安装验证已本地提交 `4f4590b`。TG下一步预登记已保存 `research/areias2019-tg-preregistration/`：三图分别校准，六映射/中间刻度残差经独立Fraction核算，固定每图13个目标温度，尚未选择TG曲线点。下一动作按预登记选可辨绿色重量点、保留遮挡unknown、核条件像素包络并独立复读；不能从读图误差推断实验不确定性或反应参数。当前没有待轮询EOS/测试进程。

最新恢复检查点（ae38c70之后）：HEOS共存求解已应用有界回溯Newton，保留原dp≤1e-4Pa、dg≤1e-6J/kg、分支/稳定性/源身份和8个外层状态上限；每次至多6个半分试探，总计至多43对EOS状态。kernel SHA 88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93，manifest及固定包装摘要同步更新，11项数值控制回归已加入。独立代码/Python集成审查通过。

原精确失败温度及邻点：旧版11通过1失败，新版12通过；原30状态/7导数/17故障路由检查通过。冻结非editable安装后192项相关测试通过。**完整安装套件session85070已exit0：1135通过、0失败/错误/跳过，517.635s；测试后再次核41个实际site-packages模块与源字节一致。** 所有本轮EOS/测试句柄均终态，无待轮询进程。证据见 research/heos-coexistence-backtracking/。

原callback脚本/物理字段不变，新组合耗尽session70146 exit0/57.216599209s，14提交步/15状态/1事件到0.5078125s；原事件门槛和独立逐步/累计水能量与浮点修正账本通过。修正预算含原显式numerical_clock_inventory_residual，未放宽为任意容差。只保存的refinement指标已核门槛，不能从未保存的全部参考态独立重建T/P差。旧失败和不同版本保持分开，不迁移其验证身份。

本轮为数值修复和制造夹具耦合验证，不是自由烧结或真实原污泥全周期。下一来源动作：按三批TG各自刻度预登记稀疏数字化及读图误差，生成经独立复读的观测候选，不由单速率推断唯一动力学。下一实现须推进反应/空间输运/自由烧结冷却的实质缺项；原污泥材料闭合、三个公开机制及留出、全周期CLI/UI/多代搜索仍为Goal必需未完成项。Goal active。下文为历史检查点。

最新恢复检查点（2e16a70后）：规定形变/活动蒸发/耗尽组合已实际运行并揭示HEOS共存求解故障，证据 research/deforming-active-depletion/。单callback通过；耗尽attempt01 exit1/27.881735s、72评估、6提交步、0事件，heos_coexistence_not_converged，不能称耗尽通过。已提交前缀能量/水与5功精确分项检查通过。

真实末状态重启诊断exit0/6.0085565s，内部仍失败：chemical kernel在299.9996124454831K八轮密度更新振荡，dp略超1e-4Pa而dg已在1e-6J/kg内。两端点独立native probe复现，半步/四分之一步均过原dp/dg，实际exit0/1.149743s。未改kernel、未放宽门槛、未将调试exit0称物理成功。replay unused vapor的−Infinity是未初始化私有诊断，原件保留，不作物性。

**所有句柄6613/41736/24073/77192均终态，目前无活动测试/EOS进程。** 下一可执行动作：隔离实现有界回溯Newton，先以保存的精确失败温度和邻近点复现/验证原共存及Table3门槛，保持源/运行身份；通过相关数值/故障/安装检查后，重新原组合耗尽案例，保留旧失败。生产仍是9ba520d源码及1124安装回归证据，本轮没有新生产修改或完整suite。

TG原图提取可行性已核三原生图及8资产哈希，见 research/AREIAS2019_TG_EXTRACTION_FEASIBILITY.md；绿色重量可以有限读图，Figure40纵轴不同，三图分别校准；有界未发现仪器数组，不声称不存在。尚未数字化。来源与完整材料域、反应/输运/自由烧结冷却、三机制/留出、全周期CLI/UI/多代搜索仍为必需未完成项。Goal active，本轮是真实运行、故障定位与局部数值证据进展。

最新来源检查点（9ba520d之后）：已核读Areias2019 Tables16–22和热分析方法/批次对应。六组成表83条转录与原页逐项复核，独立Decimal保留Table20条件总和[91.66,92.31)%而不归一化。三批日期支持Tables17–19与Figures38–40的明确名义批次链接，见 data/sandbox/research/areias2019/batch-links.json；不证明同分样/共同质量基准，处理泥与Table21未强行匹配。

热值四项、氧弹/He等温TG-MS/N2升温TG-DSC/膨胀仪条件已机器记录。N2方法与300°C氧化解释、1050°C方法与1100°C结果文字冲突保留；没有据此拟合耗氧反应或自由烧结。源码未改，1124完整安装通过仍属于9ba520d的既有证据，本轮未重跑EOS或测试。

下一来源步骤：按三批明确身份核查Figures38–40坐标及原始数据可得性，建立带读图误差的TG观测候选，并保持单速率/机制不可唯一辨识限制。实现工作仍须完成湿态活动相变与变形/耗尽组合、空间输运、自由烧结冷却及全流程应用；来源核读不替代物理实现。当前无待轮询进程；Goal active，本轮有实际新证据与材料映射进展，未达到§11完成条件。

最新恢复检查点：最终 v2 普通积分器时钟修正已完成实际冻结安装验证：**1124 pass / 0 fail / 0 error / 0 skip，525.571 s，session83463 exit0**。测试后再次导入核对41个实际安装模块与源码逐字节一致。当前没有待轮询测试或EOS句柄。证据见 research/integration-clock-correction/；原v1完整1121pass/2fail、独立失败重现、修复与审查均保留。

最终v2用Fraction累加名义时间，拒步重锚，并保留原严格局部1ULP guard；实际RK与全部账本仍完整积分表示后的端点差。新增12项clock回归。原活动相变制造三尺度实际2/4/8步、15/29/57评估全部到.51s，原25/30s资源及两最细N/E/T/P门槛通过。不是完整湿变形、原污泥实验或全模型现实验证。

新增 data/sandbox/research/areias2019/：UENF官方论文的实验室15%石灰基准为采集污泥干质量；采前已有不明剂量加灰，不能把 lodo bruto 当作确证未经处理原泥。与2025筛分/制样不同，同批未证实，材料参数未准入。2025 Fig.4 已完成26点数字化的旧错误描述已更正，原始历史事实不覆盖。

下一步：核读2019自身三批采集泥与实验室处理泥的组成/热分析及样品映射，评估可闭合的材料域，不能迁移2025参数冒充同批；实现方向继续完整湿态活动相变/变形与耗尽组合及自由烧结，保留原门槛与实测成本控制。原污泥热化学/反应/输运/烧结/冷却本构、三个公开机制与独立留出、全周期CLI/UI和多代搜索仍为必需未完成项。Goal active，本轮为实际实现、验证和来源核读进展。下文是历史检查点，状态以本段为准。

运行中检查点（本轮尚未提交）：普通integrate已试行Fraction名义时钟、接受推进/拒绝重锚/断点同步，实际RK/账本仍端点差。先10clock7fail3pass，修改后38pass，另补第11常功测试后联合117pass。已安装这一v1（integration SHA a2afb84f开头），同原活动相变三尺度实际2/4/8步15/29/57eval，原25/30时间限制及两最细N/E/T/P门槛通过。结果 /private/tmp/brick-clock-fix/wet，源码/数值独立审查已通过。但它不是最终版本。

完整安装v1 suite **session61318已终态：1121pass/2fail，520.78s**，实际XML与身份保留在/private/tmp/brick-clock-fix。两项失败：test_depletion_components 的 terminal_and_all_normal_components_preserved 与 total_energy_binding_survives_terminal_and_normal_restart，原因unresolvable_stage_time。定向无EOS重现2fail，trace定位.15→.2名义.01在binary输入差下尚留1ULP；先前单ULP端点合并仍有必要。

上述v1完整suite期间源码/安装保持冻结，终态后已应用受审v2并加入第12个clock回归、重新安装。正在/private/tmp/brick-clock-final重新原三尺度，尚未完成最终完整suite。受审v2已在/private/tmp/brick-clock-fix/v2/sludge_sandbox/integration.py，SHA b3d3665b0dc73d372af4b88c1b3c17b4637288a271d66b9168d89b3682587524，仅在exact时钟后恢复原min(ulp(target),32ulp(step))局部guard，再同步target并完整积分。50目标测试/独立大origin短步拒绝/两个原fail通过，COMPATIBILITY_REVIEW.md已批准。/private/tmp/brick-clock-fix/test_local_endpoint.py是先失败的新增常3W端点回归，尚未并入生产tests。

下一步：等待61318真实终态并保存v1完整报告；应用受审v2、合入新增回归、冻结重装，重新原三尺度和全suite，核真实安装41模块、归档所有初失败/补正/审查并本地commit。此前goal缺项均保留；不可把v1三尺度通过或v2定向通过称最终全套已过。当前有实际实现/失败诊断/验证进展，Goal active。

最新检查点：2b1d07f生产源码未改，已用实际安装HEOS验证非零相变与规定变形，证据research/heos-active-phase。原callback独立Decimal/Fraction算术、当前几何/一次逆解/液汽精确±/无重复潜热通过，exit0/1.956s。明确layout[solid,H2O汽,H2O液,carrier]、初态[2,1e-8,1e-4,.001]为制造fixture。两条同初态/模型/运动/精度t.5→.51轨迹，K1e-7/K0，实际各2步15eval、外部7.998/7.930s，全部prefixN/E/总水与反应对称账本通过。活跃汽增3.4788077e-6mol、比K0末温低.0014410767K，满足预登记1e-4K；局部亲和力/熵产生可独立重算，不能称全系统熵或独立轨迹真值。

按预登记减半步长：fine .0025完成实际5步36eval/14.562s积分，含2.22e-16s尾步，所有prefix账本通过；finer .00125失败wall_time_limit25.052s/外26.543s、62eval8接受停.5099999999999998，未到同终点。未提高25/30上限，三尺度refinement_compare未执行，不能宣布三尺度通过。无EOS解析常库存复现同时间行为：8步cap在57eval停、10步cap实际64eval9步完成，尾步=2ulp(.51)。原失败/算术审核/源绑定全部保存，41安装模块与当前源字节匹配。

本轮所有句柄64204/78508/68872/83417/44702均终态。下一动作：为时间推进累加舍入尾步建立数值政策/回归并修复（仍须完整积分剩余区间并入账本，不能snap终态或放宽物理门槛），然后重跑同finer并完成三尺度比较。当前活动相变短积分已实现运行，但完整湿变形/耗尽、实际原污泥材料、空间输运/烧结冷却、三个公开机制及全周期CLI/UI/多代搜索仍为必需缺项。Goal active，本轮属于progress。

最新检查点：HEOS运行时检查优化已应用，证据 research/heos-runtime-optimization。阶段7仅runtime canonical重编码改rawSHA，构造双核验/前后读取/配置/锁/警告不变，30点7导数9故障stub通过；原湿前缀仍wall_limit/27eval3接受。阶段8另将原饱和try-body原样提取为私有锁内方法，公开饱和和温压各自完整事务，内部不重复，无缓存。原算术AST等价，17故障/公开路由stub和30点7导数通过；stage8原四步积分14.502s/29eval4接受0拒，所有原门槛通过，阶段7共同3步账本/4状态库存能量精确一致。旧失败均保留。

两源码与对应真实manifest/source摘要经独立审查后应用；源码身份改变不冒充旧结果。普通uv pip离线无法选缓存numpy失败后，uv sync --frozen --no-editable --inexact --extra dev --extra water --offline成功安装锁中numpy2.5.2并保留单独核查CP8.0.0。实际41site-packages模块与源码字节一致，水相关212tests/0fail/error/skip/1.486s，测试后再核41模块；本轮未重跑全1112。安装湿态runner仅tests helper在PYTHONPATH、无候选包，并assert所有sludge导入site-packages；原四步14.40582975s积分/18.59541429s外部，29eval4接受，T误差8.606e-9K/P1.1998e-5Pa/孔压功7.35993e-7J及全部Fraction账本/独立Python熵原门槛通过。独立审查已核实际源码/来源/安装/数值记录。

所有本轮工具句柄已终态，无EOS待轮询。下一动作：把显式HEOS接入原非零相变系数的规定变形callback及实际活动相变短积分，保留共同化学/能量/源身份、当前孔隙、单次逆解及耗尽门槛。不要把当前固定库存前缀称为活动蒸发或完整10%变形。仍需完整原污泥材料证据、干燥反应/供氧输运、自由烧结冷却、三公开机制/留出、全周期CLI/UI和多代搜索。Goal active，本轮有实际实现与验证progress。

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
