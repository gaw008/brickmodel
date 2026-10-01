# 全流程近似模型：离线使用与结果解释

P36有限来源准入及4固定局部核查完成（2026-10-01T19:44:21.845454+00:00）：湿表面机制准入，两主文宏观迁移率不直接准入。298.15K纯OH精确零CaO供体系数对照两旧率均0且directΔμ−57.92008kJ/mol；raw主机微小CaO/非零率保留，不称严格主机阻断。实际2.100607s、16本构调用、0RHS/Jac/积分/fit/UQ/恢复。440=141literature/299assumed/0measured，原434/科学核保持，未新增通道或默认A/E。原30/81、strictOH及0.135892078740%干燥失败保持，wholefalse。P37具显式迁移率输入局部能力仅候选；详见FULL_CYCLE_P36_DIRECT_CARBONATION_ADMISSION.md/.json。

P35有界零积分定位完成（2026-10-01T19:01:14.677712+00:00）：4固定RHS/Jacobian配对行和均0；432保存端点格揭示OH/extent偏离在最终投影前已存在，不能只归结为报告sum或CaO差值。3个calcite保温区间的小进度增量低于大累计量的binary64分辨率。未确认科学源码缺陷，源43保持，原427参数保持，仅新增7运行预算至434=141literature/293assumed/0measured。原30/81失败和严格OH耗散未资格、名义0.135892078740%干燥失败保持。P35诊断完成，P34及完整模型仍partial；无新周期/UQ/拟合/恢复，实际边界见FULL_CYCLE_P35_PHASE_LEDGER_DIAGNOSIS.md/.json。

P34实际交付（2026-10-01T18:23:07.469583+00:00）：科学提交f6694445已普通推送并确认远端；明确审阅的34源文件增量873,649B/35成员已上传，名称、大小、父目录读回一致，收据FULL_CYCLE_P34_DELIVERY.json。首份递归包被自动审批拒绝，保留原件且未重试该包；缩小替代范围经逐源审阅后上传成功。当前实现完成，原物理数值门槛通过；新增逐相30/81失败及严格OH耗散未获资格，P34仍partial，名义余水0.135892078740%工艺失败。0measured、新核比较/拟合/UQ未获资格。未下载、解包或字节恢复，小增量不宣称独立重放/完整恢复；历史独有Git/20GB/容量告警保持未通过。下一步为零积分近零坐标/台账定位，不新增积分。

P34实际结果（2026-10-01T18:00:13.462540+00:00）：显式CaO/水蒸气/portlandite可逆库存、同一μ/U/S/机械体积已接入；427参数=141literature/286assumed/0measured，原401条保持。三档787.9743s均完成，81普通/108气体0.05086556%/0.04510294%、四指标加密0.03755230%，新增OH/Ca池差0.002796151%，原门槛通过。但81逐相无floor相对预算30项未通过，近零分母最大相对1.514617812、绝对残差最大5.46438e−16mol；原失败及负库存/负OH支路熵保留，未改分母/阈值或裁切。P34扩展资格partial，名义余水0.135892078740%工艺失败、新核UQ及实材未获资格；完整项目不判PASS。详见FULL_CYCLE_P34_LIME_HYDROXIDE.md/.json；Git和小增量交付读取随后实际收据，停止恢复下载。以下为此前带时间记录。

P31–P33实际交付（2026-10-01T16:43:28.977544+00:00）：科学变更提交830a1b17已普通推送，远端分支一致；新小型增量1,869,103B/230成员已上传，名称、大小和父目录读回一致，云ID1yHSbl_b2CluKhrAyqGV2j5-6gWdJ8gIq，收据FULL_CYCLE_P31_P33_DELIVERY.json。按用户最新要求未下载、未做字节恢复或解包验证，原件保留。当前近似实现、物理数值、固定比较和最小CLI/Python恢复完成；名义余水0.135892074432%失败、0measured、新核UQ未获资格保持。历史/独有Git恢复、20GB和GitHub容量告警仍未通过；整体工程及全部项目不判PASS。后续说明提交及薄包读取独立实际收据，不预填成功。

当前模型更新（2026-10-01T16:29:23.484922+00:00）：P31四气体Maxwell–Stefan/Knudsen固壁摩擦、P32三既有固定方案、P33最小单参恢复及实际CLI/Python已完成。新核三档81普通/108气体预算最大0.07847497%/0.06963962%，规定四指标加密0.03468365%、附加压差0.30076853%，原0.1%/2%门槛通过。P33十次实际启动/完成，恢复误差0.022657712%<2%，约270.486s，根名义参数未改写。根401=132literature/269assumed/0measured。

当前约定八阶段近似实现及内部物理数值／固定比較／最低接口资格完成；名义余水0.135892074432%>0.1%工艺仍失败。非等温有限面／孔径代理、异材来源失配和产品精度仍未获得实材资格；新核未做UQ，P26仅5917历史，不扩样、不重跑。模型实现与内部核算不代表整个工程／实材／统计／项目交付全部PASS。

本次监督覆盖完整计算且均实际在预算内结束；超时停止路径未触发，原执行版保留，后续SIGKILL/finally修订仅解析未实测。Git/push及必要增量上传随后读实际收据。按用户最新要求，停止下载／恢复验证，只读回云名称／大小／父目录；不删除历史原件、不重新迁移、不建定时任务。详见P31/P32/P33报告和最终矩阵。以下带时间内容均为此前记录。


P31当前接续（2026-10-01T16:10:32.815226+00:00）：四气体耦合Maxwell–Stefan/Knudsen固壁摩擦已实现，旧pair beta闲置，Darcy及携焓／能量／熵各按原账本计一次。新三档81普通预算最大0.07847497%、108气体0.06963962%，规定四指标加密0.03468365%、附加压差0.30076853%，原门槛通过。根401=132literature/269assumed/0measured，非等温／有限面／孔径代理继续assumed。名义干燥0.135892074432%>0.1%仍失败，不搜索。

P32当前核两个既有固定方案已启动，P33原单参数两阶段合成恢复已登记尚未启动；旧P26分布/P29恢复不自动验证新核。不重跑UQ、不创建定时任务、不写长期memory或SHA。按用户最新要求停止全部下载／备份恢复验证，新小型上传只做元数据回读；历史原件、债务和失败保留。整个工程／实材／项目交付仍不判PASS。详见FULL_CYCLE_P31_WALL_FRICTION_RESULTS.md/.json和开发计划。下方“当前”均为此前带时间的历史记录。


D05环境云恢复新证据（2026-09-30 23:25:16 PDT）：用户正常Drive手动下载的42,904,062B归档，与已批准上传原件整包字节一致；两个Downloads副本均保留。新路径恢复4305文件/链接一致，隔离CLI/Python退出0，673模块及443动态镜像仅来自恢复目录或OS；12单元/8阶段/384根参数构造通过。实际恢复2026-09-30 23:18:24–23:18:45 PDT，21.841052s。云ID1ZvbCS-SVc3X1CQISYfHlnFeucpxjU1Ty；资格限当前macOS26.6.2 ARM64基础环境，详见FULL_CYCLE_D05_MANUAL_CLOUD_RECOVERY.json。

本次手动云副本恢复通过，原自动引用落盘HTTP403/0B失败仍保留且未重试，不声称自动路线已修复。原件、下载副本及旧失败证据均保留。科学核5917、P26物理24/24和工艺15/24、名义余水0.135819744246%失败、0measured保持；未新增积分/拟合/UQ/软件测试/SHA。完整历史、独有Git恢复、20GB和GitHub容量问题仍未通过；本项新增证据的Git/小包交付读取随后实际收据。以下为此前记录。

本轮模型交付读回（2026-09-30 22:33:39 PDT）：P26实际结果提交160f568c已普通推送，远端分支一致；新小型增量2,400,580B/131成员已核对名称、大小和父目录，且一次新鲜云取回后整包及全部成员逐字节一致。云ID1wRslg0RgOzeSeZvOaPBaqAsrzZ78ernS，收据FULL_CYCLE_P26_DELIVERY.json。近似模型实现和当前物理数值验收完成；工艺、实材、环境云恢复、历史/独有Git恢复及20GB不随本包通过。此交付说明的后继提交与薄包实际状态见p26-delivery-note-*收据，不预填。

当前P26终态（2026-09-30 22:30:07 PDT）：新明确批准的一次8配对×3批次结束，实际保存24/24结果，物理24/24、工艺15/24；批次1651.930406s，独立执行/统计/物理账本读回完成。648普通预算最大0.09578240%，864气体预算最大0.08458250%；原0.1%门槛保持。当前核5917与根384=131literature/253assumed/0measured不变，P24一次时间/网格验收保持，本批不重复加密/拟合。

约定单砖八阶段近似模型的已识别必要实现和当前物理数值/三方案分布/观测及最小合成恢复工作完成。八阶段/四跨项终态复核未发现另一项有依据且可独立实施的必要新机制；来源/材料未知不得虚构补齐。8draw经验分布不证明生产概率或稳健赢家，95%Wilson/0.9原门槛未认证不等于证明无赢家，不扩样。名义干燥0.135819744246%>0.1%、公开异材曲线失配、目标材料/产品代理待实测保持；整体工程与全部项目交付不判PASS。

环境42904062B归档上传及owner权限/名称/父目录/大小已通过，ID1ZvbCS-SVc3X1CQISYfHlnFeucpxjU1Ty；一次新鲜云引用落盘HTTP403/0B，云恢复未通过、已停止。D04历史路线未重试，20GB与GitHub容量警告未解决。P26本轮Git/Drive以随后实际交付收据为准。详见FULL_CYCLE_P26_CURRENT_UQ.md/.json、FULL_CYCLE_P26_CURRENT_ACCEPTANCE.json。以下为此前记录。

当前接续（2026-09-30 21:59:56 PDT）：人类已明确批准指定42,904,062B环境归档和一次新P26批次，旧“待答复”仅历史。环境归档一次上传成功，ID1ZvbCS-SVc3X1CQISYfHlnFeucpxjU1Ty，名称/大小/父目录/shared=false/owner权限读回通过；一次新鲜官方完整引用落盘HTTP403、0B，云恢复未通过，路线停止。D04历史拒绝路线未重访。

P26已实际开始UTC 2026-10-01T04:56:51.867703+00:00，硬截止UTC 2026-10-01T05:41:51.867703+00:00；监督PID99297，独占batch.lock，3并发/900s每例/2700s全局/0.25s轮询。根384参数与43个源码副本冻结，六科学文件与5917逐字节一致；原seed20260926的8配对×3设计保持，无运行中改核/原始场/补抽/扩样/重跑。实际状态读runs/full-cycle/p26-current-uq；本批产生最终结果前模型验收不预判通过。

以下为此前记录。

D05最新工程结果（2026-10-01T03:52:44.607988+00:00）：既有CPython/NumPy/SciPy及必要源码的42,904,062B平台快照已完成本地异路径恢复，4305文件/链接一致、CLI/Python隔离启动及12单元/8阶段/384参数构造通过，独立复核通过；首次遗漏units依赖失败保留。仅macOS26.6.2 ARM64基础环境启动资格，零新积分/拟合/UQ，不授予其他平台/可选依赖或完整计算资格。环境云上传一次被自动审批拒绝（认为未明确授权此具体二进制归档），未上传/未云恢复。详见FULL_CYCLE_D05_OFFLINE_RUNTIME.md/.json。

D04历史最新定位：三个独有Git对象已在post-delivery-001/002/003云分块清单中，无需重传；依赖闭包和云恢复未完成。最小历史44包正规Drive大文件下载失败，未返回本地路径；后续同下载页状态读取被自动审批拒绝，已停止。32MiB仅为特定工具上限，不能笼统声称所有路径受限。科学核5917、现有物理数值通过、名义干燥0.135819744%失败和0measured保持；P26待答复，全项目未判完成。以下为此前带时间记录。

最终范围与交付读回（2026-09-30 19:20:16 PDT）：八阶段及四项跨阶段均已独立核查，现行近似模型未发现另一项必需的新机制/积分/拟合；当前核探索性分布P26仍待原预算答复。D04另未完成：历史完整包依赖超过32MiB的90MB分块、独有Git对象与依赖闭包未获云恢复、可迁移离线环境未建立，不能概括为全项目仅剩UQ或旧403。当前f0a497bc结果已推送，新1,068,928字节/60成员包已实际云恢复；详见FULL_CYCLE_FINAL_SCOPE_REVIEW.json与FULL_CYCLE_P28_P29_DELIVERY.json。


当前状态（2026-09-30 19:14:43 PDT）：P29当前5917fcd核单参数干燥恢复及实际CLI/Python通过：10前向、265.504s，恢复误差0.022772%<2%；90普通/120气体预算最大0.001495%/0.000890%，独立读回通过。仅两阶段synthetic，根名义12000J/mol未改，不能替代名义干燥0.135819744%失败。

P30将现有基础物性归并为8组，来源/近似/待实测边界已登记，未找到支持新改核的未处理缺陷。仅澄清根历史文案；384=131literature/253assumed/0measured。科学核不变，P24三档物理数值、P25固定方案及映射资格保持。详见FULL_CYCLE_P29_CURRENT_RECOVERY.md/.json及FINAL_ACCEPTANCE.foundation_dependencies。

整个项目仍缺P26当前核探索性分布证据，第二24次尚未获答复，未启动。8draws即使全胜，其95% Wilson下界最多0.675592435<0.9，不能承诺肯定稳健赢家；不自动扩样或改门槛。目标材料/产品仍待实测，工艺/公开异材失配不改判。Git/Drive本次新增量以实际收据为准，历史恢复和20GB另列。以下为此前阶段记录。


当前P28状态（2026-09-30 19:01:56 PDT）：现有Septien六节点有效导热来源准入及18项湿基/干基换算、独立复核完成。六行均缺少与当前砖配对的温度/体积/相态/接触信息，未开展或判通过当前k定量验证；保留假设本构，零主机调用、积分、拟合、UQ。根382=131literature/251assumed/0measured，科学核5917fcd不变；P24/P25物理数值通过与名义余水0.135819744%失败保持。见FULL_CYCLE_P28_CONDUCTIVITY_ADMISSIBILITY.md/.json。

下一独立缺口是当前核P29最小单参数合成恢复，P18旧恢复仅为历史证据；P26第二UQ仍未启动。整个模型未判完成，实材/工艺/交付分列；P27两包已实际字节恢复，P28新增量另按收据交付。

以下为此前阶段记录。


当前P27状态（2026-09-30 18:46:46 PDT）：已完成N₂/CO₂原论文密度／单位／方法链核查，1新增来源、8原温度点、零积分／拟合／UQ。TN域内7点相对作者认可Table5高18.6281%–40.3006%，其数值更接近作者判不适用的Table7，但编纂原因未证实。当前核相对Table5全8点最大差3.34153%，不授予高温／孔尺度或直接实验精度，非水定律保持。完整原量、域标记及独立复核见FULL_CYCLE_P27_N2_CO2_SOURCE_CHAIN.md/.json。

根374=125 literature /249 assumed /0 measured；本项仅新增19审计条目和来源解释，旧355条与科学核5917fcd保持，P24/P25既有物理数值通过及名义余水0.135819744%失败不变。P26第二UQ未授权，但不是全项目停止理由；下一独立项是已有有效导热来源的可比性核查。整个模型仍未判完成，实材／工艺／交付分别登记。本项Git与Drive新增量以实际收据为准，P24/P25已恢复两包不重复。

以下为此前阶段记录。


当前状态（2026-09-30 18:19:44 PDT）：P24已完成来源水三对扩散接线，三档物理数值验收及独立复核通过；P25复用名义并完成两既有固定方案，独立结果读回通过。81项全程/分段质量、元素、完整能量最大0.07627288%，108项气体预算0.06777686%；规定四指标最大加密差0.13118595%，附加压差0.35051114%，均通过原门槛。P24墙钟454.739766750s，P25两例墙钟175.625240958s，无新拟合/UQ，无原始场。

根355项=110 literature /245 assumed /0 measured。N2/H2O、O2/H2O源表及H2O/CO2统一ABC已离线写入根参数；插值、逆压、有限水组成及孔尺度推广仍assumed。原水对factor闲置且D_ref仅影响非水三对，P21旧核d5fd9a2的24次分布不能授予本核资格；第二批UQ未获授权，当前分布/稳健性要求未完成，**整个开发目标仍未完成**。P18合成恢复也保持历史。

名义干燥余水0.135819744246%>0.1%，三档及原两方案都保留失败，不做第三次搜索。水黏度/Calcite热容域外外推、公开异材曲线失配、烧结/产品代理待实测单列；内部数值通过不等于工艺或材料通过。Git/Drive本次主增量已推送并实际字节恢复，收据见FULL_CYCLE_P24_P25_DELIVERY.json；全部历史、独有Git、离线环境恢复及20GB目标仍未完成。详见FULL_CYCLE_P24_SOURCE_DIFFUSION_RESULTS.md/.json、FULL_CYCLE_P25_FIXED_SCENARIOS.md/.json与FINAL_ACCEPTANCE.current_acceptance_matrix。

以下均为此前带时间的阶段记录；旧“当前”只适用于当时版本。


当前P22结果（2026-10-01T00:20:23.658067+00:00）：P22限定来源核查与独立复核完成：严格二元Fick语义明确，18点当前自由D相对缓存一级LJ来源模型的最大离散差为O2/N2 4.41252%、O2/CO2 2.51163%、N2/CO2 8.53378%。这是模型差异，非实验误差；当前缓存无直接二元实验点，H2O三对及>1200K来源覆盖未知。没有由此证明的接线/量纲错误，本项保持科学核d5fd9a2不变，零积分/拟合/UQ；P21不重跑，P20/P21已有验收只保留其原版本范围。P22完成不代表整个开发目标或全部本构来源缺口完成。

根323=86literature/237assumed/0measured，新增2条仅核查取点，原321条完整保持。名义干燥0.13602835%>0.1%、公开异材9活度/6热失配和目标实材待测不改判；旧已验收增量不重复恢复。详细语义、全18行、未知与后续候选/最小受影响验收见FULL_CYCLE_P22_BINARY_DIFFUSION.md/.json；本项新Git/Drive交付另以实际收据记录。

以下为此前阶段记录；其完成判断仅适用于当时已验范围。

当前最终状态（2026-09-30T23:55:36.990315+00:00）：P01–P21约定近似模型工作完成。P21唯一批准的8配对×3当前核批次已实际完成，物理24/24、工艺15/24；648项普通预算最坏0.08482890%、864项气体预算最坏0.07442392%。批次1675.375578s，24唯一状态和子进程回收完整，无补抽/扩样/重复批次。

当前物理核仍d5fd9a2，根321条=86literature/235assumed/0measured（四条新增仅运行预算）。P20三档物理及一次时间/网格加密保持通过；名义干燥0.13602835%>0.1%仍失败。三方案的小样本经验分布不证明真实生产概率，原Wilson95%/90%门槛下稳健赢家未证实，不等于证明不稳健。固定渗透率及来源系数组的范围/相关性仍未覆盖。

来源域外水黏度/Calcite热容外推、公开异材失配及目标材料/产品待测单列。P20当前同场映射/Python/CLI导入通过，P18合成恢复明确保持历史。模型实现与数值验收不等于工艺、实材或全部历史存储通过。P20小包666467字节/41成员已实际云字节恢复；P21最终交付另见实际收据，完整历史/独有Git/运行环境恢复及20GB仍未完成。

当前汇总见FULL_CYCLE_P21_CURRENT_UQ.md/.json、FULL_CYCLE_P21_CURRENT_ACCEPTANCE.json及FINAL_ACCEPTANCE.current_acceptance_matrix。下方运行中、pending和早期完成判断均为带时间的历史记录，当前判断以本段为准。

## 此前阶段与执行记录


当前P21接续（2026-09-30T23:25:11.054704+00:00）：协调会话已传递23:17UTC实际用户批准“允许”，批准唯一一次最终核8配对×3更新、45分钟总限、不保存大型原始场、不扩样。这条真实批准是当前执行依据，不再重复提问。根已登记三并发、900s/次、2700s整批及0.25s全局watchdog轮询预算，复用原25维取值和三方案，不改统计/工艺/物性、不扩样搜索。当前321参数=86literature/235assumed/0measured，其中新增4条仅运行编排。P20物理数值通过和名义干燥失败保持；P21实际结果产生前整体模型仍未完成。下方先前pending及授权解释均为历史，实际批准见runs/full-cycle/p21-current-uq/approval.json。


当前权威状态（2026-09-30T23:11:44.927781+00:00）：P19/P20已完成来源纯黏度改进及当前三档物理数值验收，**P21当前核三方案分布与排名稳健性仍未完成，整个模型不能判完成**。原8组配对×3=24次设计与禁止重启旧24批次存在授权冲突；前述预算决定仍待用户明确答复，尚未启动任何当前核UQ。

根现317参数：86 literature / 231 assumed / 0 measured。来源μ(T)及同温度Wilke已接入原共享Darcy通量，未新增储能或热源。81项质量/元素/完整能量最大残差0.05451679%，108项气体预算0.04842094%，四项要求最大加密差0.13112792%、附加压差0.36178638%，均通过原门槛；批次墙钟442.228086s，无重跑。名义干燥余水0.13602835%仍高于0.1%，工艺失败保留。

水黏度超过1173.15K推荐上限的面采样1198/1198/2398个，Calcite热容超过1200K亦保留assumed外推。数值负小库存/熵量未裁剪；目标材料及产品代理精度待实测。P20同场九类映射/Python前向与CLI导入通过；P18固定方案及合成恢复属于旧黏度核，不能自动升级为新核分布或拟合证据。详见FULL_CYCLE_P20_SOURCE_VISCOSITY_RESULTS.json/.md及FULL_CYCLE_P21_UQ_BUDGET.json/.md。

P18两个增量实际云字节恢复已由协调会话完成并读回收据；本次P19/P20增量尚按独立交付收据推进。全部历史/独有Git/离线环境恢复及20GB目标仍未完成。下方P01–P18“完成”结论均为历史阶段记录，当前判断以本段和FINAL_ACCEPTANCE.current_acceptance_matrix为准。

当前Python只存汇总入口见`runs/full-cycle/p20-source-viscosity/cycle-worker.py`；`report.viscosity_source_domains`列实际Darcy面温度的来源域统计。名义alpha1读取根公开μ0公式，alpha0仅原幂律显式对照。所有系数预存在根文件，前向不导入iapws或沙盒，不下载来源数据。已有CLI --compare将触发24个完整周期，P21预算未明确前不得据示例自行运行。以下旧次数属于各自历史核。


## P16–P18历史入口和运行证据

P16–P18版本当时完成了必要运行验证，详见FULL_CYCLE_CURRENT_MODEL.md；下方P06–P11的次数/版本为历史记录。当前根304条参数（70literature/234assumed/0measured），六种纯物质背景Cp使用根caloric_background的公开五项式，h/s、总容量与面携焓一致；report.caloric_source_domains记录采样温区及来源域外次数，域外延拓仍assumed。

最新实际离线CLI命令与exit0、10次真实前向收据在runs/full-cycle/p18-current/recovery/execution.json，必要摘要已纳入FULL_CYCLE_P18_CURRENT_VALIDATION.json。派生window.parameters.json只含drying_ramp+drying，根配置没有被拟合写回。九类观测已在P16同一当前轨迹上读取，非重新完成九条实测曲线校准。新名义干燥0.13602805%>0.1%，合成窗口通过不能改判。旧--compare的24次UQ及旧三参数/双参数恢复没有在新热容核上重启，其历史结果不自动验证新核全部假设。

只保存必要汇总的当前原方案Python调用示例及实际运行包装器在runs/full-cycle/p18-current/scenario-worker.py；最终报告含完整质量/元素/能量和四气体预算，无原始场。使用现有CLI前应按所选选项阅读下方输出行为。

P11已完成可运行与检查的接口及未来实测校准入口；这不是整个模型停止条件。当前按物理化学定律及公开论文/数据继续开发，缺少目标材料数据不阻塞独立验证；原名义干燥失败和真实预测限制见下文。P11实际完成58项纯数据回归、CLI负例和help启动验证；本次没有重新积分或拟合。

项目保留在 `/Users/wanggaoying/Research/brickmodel-github`。统一输入是根目录 `parameters.full_cycle.json`；采用明确的一维半厚度、假设材料和给定炉温/窑气外库。模型用于研究近似和条件化比较，材料适用性、强度/吸水/缺陷代理与现实对照待实测。

## 已有环境与入口

本轮实际读取的环境为 Python 3.12.13、NumPy 2.5.2、SciPy 1.18.1，与 pyproject.toml 的前向依赖一致。求解过程使用本地 Python/依赖/源代码，无在线 API、运行时下载、CDN 或远程字体。当前 .venv 的 Python 指向本机 uv 安装位置；代码备份不是完整可搬迁的 Python/依赖安装包。新离线主机需部署前备齐 pyproject.toml 声明的依赖与源码。D05现查发现 .venv 存在指向旧Desktop的editable项目元数据；当前源码入口显式加入Research/src，不依赖该旧路径。D05已建立本机平台快照并本地恢复启动；其云上传未通过，详见D05报告。

在项目根目录运行现有 CLI：

```sh
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-run
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-acceptance --acceptance
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-comparison --compare
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-calibration --synthetic-calibration
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-measured-fit --calibrate path/to/observations.json
```

以上是可选操作，不能为接续工作全部重跑。普通前向和 `--acceptance` 会按既有行为写 fields.json；本轮工作只保留汇总，采用下方 Python 入口在内存中消费原始场。原始场不得入 Git。不要覆盖已有运行目录。`--compare` 与 `--synthetic-calibration` 按既有入口只保存汇总和合成观测/派生参数。

退出状态须与结果一起读：普通前向和 `--compare` 的成功只表示各自物理核算通过；合成恢复的成功表示指定恢复条件通过；这些不要求名义干燥达标。`--acceptance` 还要求三档物理、一次时间/网格比较和工艺端点全部通过，原名义干燥失败将使总体结果为 false。退出码0不能单独证明整个模型或真实工艺完成。

## Python：只保留必要汇总

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'src'))
from sludge_vme.models.full_cycle import read_parameters, run_cycle, write_json

config = read_parameters('parameters.full_cycle.json')
report, fields = run_cycle(config)
write_json(Path('runs/full-cycle/your-run/summary.json'), report)
# 在内存中使用 fields 后释放；不将原始场写入 Git。
del fields
```

`read_parameters` 检查根参数条目、来源、单位、范围和身份。每个重要材料/工艺/数值参数均来自该文件；不使用环境变量注入。`changed(config, overrides)` 是已有显式派生工具，不改原配置；派生计算不能冒充名义结果。加密的分母尺度读取 `acceptance.floor.*`，不重新选择容差或放宽门槛。

`report['gas_ledger_endpoint_totals']` 保存当前配置窗口初始和每个阶段末端的全域孔气库存、累计净反应进度及边界进出。`report['gas_species_ledger']` 给出 O2/N2/H2O/CO2 的窗口总账与分段账。whole_cycle 键在截断配置中仅表示该配置窗口，读取 scope 一起判断，不把两段干燥写成八段全周期。

气体残差为末库存减初库存、减反应净源、减边界进入、加边界流出。预算归一化与相对全窗口初始库存归一化分别列示；后者不是通过判据。保留带符号净反应、近零负边界增量和原始残差。端点闭合不证明每个中间时刻或每个单元均闭合；不能替代原质量/元素/完整能量账本。

## 观测与反演

既有接口 `sludge_vme.inverse.full_cycle.map_observations(config, observations, report, fields)` 在同一解上映射观测，不重新积分；`predict` 会先求解一次；`fit` 接受指定参数和标记来源的数据；`joint_drying_synthetic_demo` 使用根预先声明的双参数/双通道干燥设计。

| kind | 单位 | 模型定义与解释 |
|---|---|---|
| tg | 1 | 凝聚质量/初始干质量，不等同纯水分 |
| dsc | W/kg | 有限孔气模式的净热边界功率/初始干质量，非仪器专属响应 |
| dilatometry | 1 | 厚度相对初始值的变化，包含当前热弹性与永久应变 |
| kiln | K | 根工艺给定炉温 |
| liquid_water | kg/kg | 全域液水质量/初始干质量，不含孔汽、矿物结合氢或额外虚构结合水库存 |
| surface_temperature | K | 模型外边界温度，区别于炉温和最外格中心温度 |
| absorption | kg/kg | 冷却产品吸水代理，待实测 |
| strength | Pa | 冷却产品强度代理，待实测 |
| defects | 1 | 冷却产品缺陷代理，待实测 |

曲线观测逐行使用 `kind`、`time_s`、`value`、`unit`、`scale`，产品观测不需要时刻。时间为当前窗口起点起的秒；时间插值采用既有线性插值。拟合数据集还必须提供 `measurement_kind`（synthetic 或 measured）、`source`、`fit_parameters`。`scale` 是残差归一化尺度，不自动等于测量标准差。

完整周期7类合成设计与2通道干燥设计是两个独立演示；干燥窗口不得使用冷却产品输出证明产品资格。无噪声同模型恢复只检验指定条件下参数恢复及接口；局部Jacobian秩不能证明全局唯一、抗噪或实材辨识。合成拟合仍为 assumed / synthetic_fitted，派生 fitted.parameters.json 不写回根名义值。

## 追溯与未通过项

最终运行、物理/数值验收、工艺失败、待实测、Git和备份分别见 `FULL_CYCLE_DEVELOPMENT_PLAN.md`、`FULL_CYCLE_REPORT.md` 以及最终验收矩阵。历史 d8bc6f1b 三档证据保留在 `FULL_CYCLE_PORE_GAS_RESULTS.json`；只有确认主机/根物理参数未变后，才可在原范围复用。

旧 UQ 的渗透率固定为3.75e-14 m²，最终比较继续固定该值以及已声明固定系数。新的比较不会覆盖所有271参数的范围，不能写成全面不确定性验证。原名义干燥余水0.13505646%高于0.1%门槛；关闭结合能、历史延时、合成真值或拟合结果不得替代此失败。历史两次广渗透率成本失败与干燥两次有界处理均不重启。

## 本轮已实际执行的入口

完整周期 `sludge_vme.cli.main` 的 `full-cycle --synthetic-calibration` 分支已返回0，实际22前向；随后 `joint_drying_synthetic_demo` Python入口实际17窗口前向，包装进程exit0。源入口 `.venv/bin/python examples/run_full_cycle.py --help` 也已返回0，仅用于启动验证。其余上列命令是已有可选操作，不声称本轮全部执行。

运行器、根参数快照、逐次执行记录位于 `runs/full-cycle/final-inverse-20260930/`，必要汇总见 `FULL_CYCLE_FINAL_INVERSE_READBACK.json`。原记录中的 `gas_ledger_present=False` 是运行器查错report层级，不能用于判定账本存在；账本本体及P01/P05证据以顶层 `report['gas_species_ledger']` 为准。

## 干燥判据的三个分母（P09澄清）

`example_endpoints.drying_remaining_fraction`取最湿单元在drying末的液水/同单元t=0初水。0.1%门槛不是干基0.1%；对应干基门槛为根门槛乘`material.water_dry_ratio`。当前0.13505646%剩余初水相当于约0.02025847%干基，仍高于原等效0.015%干基门槛，不因换单位改判。

恒温drying账本初水在drying_ramp末（当前14400s），冻结根`n_eq_over_n0`分母却是当前drying末的液水（86400s）。两者均不可直接当t=0初水分母；P09报告已统一到初水后比较。冻结根/单次细化/端点余额各有独立适用范围，详见FULL_CYCLE_P09_DRYING_ATTRIBUTION.md。

## 反演输出留存（P10）

既有CLI合成/标定命令和三个Python合成入口保持调用方式。完整合成的synthetic.observations.json新增truth_audit；两个窗口的truth_window_audit追加顶层气体账本与实际阶段范围。calibration.json保留原forward_*字段，并新增forward_gas_species_ledger及可用性诊断；窗口仍用forward_window_balance。

后续外部记录包装使用sludge_vme.inverse.full_cycle.forward_call_summary(report)，需要必要预算则使用forward_audit(report)；两者不积分。gas_ledger_status=present仅表示数据存在，missing对应明确诊断及审计中的null，不能据普通物理通过推断气体账本通过。缺少必需普通预算字段时直接报错。

runs/full-cycle/final-inverse-20260930/entrypoint.py和原39次记录为历史快照，保留错误字段，不作新运行维护入口。旧完整真值预算未保存且不可从摘要恢复；新版留存只作用于后续真实调用。详见FULL_CYCLE_P10_INVERSE_EVIDENCE.md。

## 未来实测数据的最小接入（P11）

填写起点见 [`examples/full_cycle_observations.template.json`](../examples/full_cycle_observations.template.json)，只包含 `liquid_water` 与 `surface_temperature` 两种观测的占位行。复制到新的数据文件后，按实际采样增加行。模板身份为 `template`，来源、值、时间、材料/配方/批次、几何及边界条件未知项均为 `null`，`fit_parameters` 为空；它不是实测数据，也不能直接传给准备或拟合入口。两种通道不保证任意参数组合可辨识。

根 `observation_contract.target` 当前未知不阻塞已有前向或合成计算。实测拟合前，需根据原始记录明确目标材料及条件，并在统一根配置与输入数据中如实声明；声明相符只表示准入条件相符，不证明材料有效性或实验真实。

1. 填写数据集 `source`、逐行 `source_id` / `source_locator`，以及身份与条件相容性的 `identity_source` / `compatibility_source`。真实原始实验才可用 `measurement_kind="measured"`、`source_kind="raw_experiment"`；论文表格或曲线数字化使用 `reference` 与 `paper_table` / `digitized_curve`，不能仅凭材料名称相似改称目标实测。
2. 从实验记录填写材料、配方、批次、几何、初态与边界程序。`conditions.configuration` 采用 `configured_conditions(config)` 返回的阶段列表与参数 value/unit 结构；该函数只是**配置快照**，不是实测条件或相容性证据。应逐项对照有来源的实验条件并处理差异，不能盲目复制快照制造匹配。不同批次、主干燥与后续调湿记录分别处理。
3. 每行据原记录填写测量方式 `acquisition`、阶段 `segment`、值、时间及来源。模板预列的量、位置、基准和单位是目标语义，不证明实验采用了该定义。两类主干燥观测需对应 `in_situ` / `main_drying`。`time` 包含数值、单位、原点、到过程起点的偏移秒数与来源；映射为 `time_s = elapsed_seconds + offset_to_process_start_s`。原点为 `process_start` 时偏移必须为零，不能凭猜测对齐。
4. 显式填写正的 `scale`、目标单位 `scale_unit` 与 `scale_source`。水分的目标单位是 kg/kg，表面温度是 K；即使原温度以 degC 输入，scale 仍按目标单位声明。scale 是残差归一化尺度，不自动解释为测量标准差 sigma，接口不替你传播不确定度。按研究问题选择根中有非零范围的 `fit_parameters`；已声明固定的几何、初态、配方和边界条件不能同时拟合。

水分的分母必须明确：模型 `liquid_water` 是液水/初始干质量。当前干基、湿基以及 MR 不能直接填入该值；当前干基或湿基转换需同源且有身份记录的当前干质量/初始干质量因子。MR 只接受明确的 `water_over_initial_water` 公式及有来源的初水/初始干质量分母，不能借用根名义初水，也不能猜测包含平衡水分扣除的 MR。百分数须依据原记录显式换成比例，接口不自动猜测。最小模板采用初始干基，不含这些可选转换项。

坯体内部温度不是 `surface_temperature` 的别名；炉温对应 `kiln`。烧后吸水率也不是干燥液水的别名：它对应独立 `absorption` 产品观测及烧后干质量基准，模型端仍为待实测代理。未知位置、干燥后的再调湿、称量方式与模型采集语义不符时，应保留差异，不能改标签制造符合。

填好记录后可先做纯数据准备。下例仅供后续使用，本轮未执行；`prepare_dataset` 不调用前向、优化或求根，积分次数为零：

```python
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'src'))
from sludge_vme.models.full_cycle import read_parameters
from sludge_vme.inverse.observations import prepare_dataset

config = read_parameters('parameters.full_cycle.json')
dataset = json.loads(Path('path/to/observations.json').read_text())
prepared = prepare_dataset(config, dataset, for_calibration=False)
print(prepared['admission'])  # 映射和声明问题；不是拟合成功或材料资格。
# 只有拟用于目标标定的完整记录才作以下准入检查；仍然零积分。
admitted = prepare_dataset(config, dataset, for_calibration=True)
```

`for_calibration=False` 可用于字段完整的文献 reference 映射，保留原行及转换说明；不能补齐未知测量值或修复来源缺失。文献 reference 不进入目标实测拟合。`for_calibration=True` 会检查身份、目标/输入条件、观测语义、窗口及拟合参数，失败直接报错。`fit` 及上方既有 CLI `--calibrate` 路径都会在优化和前向前调用该准入检查，用户不必靠手工预检查才能阻止不合格输入。准入通过后执行拟合才会发生新积分；本轮不执行该步骤。

输入已由 `prepare_dataset` 归一后也可传给 `fit`；二次准备始终重新读取 `mapping.original`，不会把转换后的初始干基当成新的实测原值而丢掉假设分母限制。要更正数据，应修改原始输入再准备。文献烘干参考质量另用 `basis="dry_reference_mass"` 和显式 `dry_reference_over_initial_dry`，不能悄悄等同当前或初始干质量。所有转换因子/MR分母必须带 `status`；要用于目标实测拟合，还须是 `measured`，并在因子的 `material` 中给出与数据集一致的 material_id/recipe_id/batch_id。非实测因子仍只能参考。

## P37 必填输入局部API（尚未接周期）

直接导入 `sludge_vme.models.direct_carbonation.DirectCarbonationMobility` 与 `direct_carbonation_sources`。mobility必填 `value_per_s/source/status/identity/applicability`；算子必填 `temperature_k/delta_mu_j_mol/portlandite_mol/calcite_mol/co2_pressure_pa/water_vapor_pressure_pa/gas_constant_j_mol_k/reference_pressure_pa/mobility/stoichiometry`。全部物理参数从统一根配置或明确带身份的调用数据读取；无A/E或砖速率默认。计量必须是OH−1/CO2−1/calcite+1/H2O+1且Δμ同方向完整净势。

实际离线Python调用证据是 `runs/full-cycle/p37-direct-carbonation-operator/probe.py` 与四份结果JSON。根 `public_reference_cases.direct_carbonation_operator` 及8个配套项只定义有限synthetic fixture；该脚本已经运行，后续使用不能自动重复耗用已登记4次预算。返回 `extent_rate_mol_s/species_sources_mol_s/entropy_production_w_k/mobility_contract/rate_law_identity`。瞬时导数不是累计ξ、全周期通道或CLI升级；不需外网及新增依赖。源码负库存保留，域外耗散未证明，不自动填来源或剪裁输出。当前全流程/材料/工艺未通过事项读P37报告。

## P38 来源 TG 双 DoC 的离线单记录API

从 `sludge_vme.inverse.source_tg` 导入 `map_saeki2026_tg`，显式传 `config=统一根配置` 和 `record=同源相质量记录`。根source_observation_contracts.saeki2026_tg及observation.saeki2026.molar_mass三项必需；不采用主机质量或隐藏默认。record字段见执行证据p38-source-tg四JSON的input，包含共同样品/时间/来源/分母、phase_separation与适用声明。两相value是已分峰归一相质量，unit明确g/g或kg/kg，denominator.basis=ignited_CH_CaO_reference，sample.basis=portlandite_powder，quantity=phase_mass_ratio。整砖总TG/initial_dry无法自动换算。

返回DoC_CH、DoC_Cc及signed差值，保留original_input与来源相对时间；该API不做峰积分、kinetics、主机调用或fit准入，9旧种类不变。完整source/reference原始输入可用于来源映射，但公式导出量不是目标直接实测；当前实际四条全synthetic。执行脚本已经完成唯一4调用，本说明不授权自动重复已用预算；后续新数据按其声明/独立预算处理。未实现CLI自动输入或整砖拟合，不把本项叫周期恢复。

## P39 显式条件主机通道

统一根名义配置没有direct_carbonation键，所以通道未启用。必须在make_cycle前给config['direct_carbonation']完整合同：mobility_parameter、identity、material、temperature_range_parameter、humidity_pressure_range_parameter、surface_basis。数值只取根parameters，L单位1/s且条目value/unit/range/source/status完整，域参数分别K/Pa。合同缺字段直接KeyError、单位不符ValueError；storage=0明确不支持。正CaPool及正T/R/Pr/L、非负供体/分压为当前理论域，不能据声明升为材料已测。

本轮可审阅合同在public_reference_cases.direct_carbonation_host.channel；仅synthetic_P39_host_coupling_only，不能作为名义砖体默认。调用者明确复制该合同仅用于有预算的条件核查。主机扩展active8反应/独立xi_d，保留旧7Arrhenius，reaction_fields/summary active_reactions含direct；使用相同U/S/volume、质量/元素/气体、水及熵，无新热源。gas/solid布局统一offset，不能在旧长度state上隐式添加通道。

本轮唯一4完整RHS已执行，脚本/输入/实际回调和signed结果在p39-direct-host，不授权重复旧四状态。真正周期summarize、CLI完整积分/加密/反演资格尚未更新；P40只为有界候选，未运行。P38来源TG映射继续独立，公式不识别L。
