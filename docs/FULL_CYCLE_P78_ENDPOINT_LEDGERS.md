# P78 实际端点库存与完整有符号账本

P78 真实端点库存/账本完成：正常source-cwd CLI rc0/reaped，wall0.712672250s/CPU0.476645000s，四science文件1155171B/4194304B；1strictload/ctor/新detachedinitial、9decode/9completevalues，RHS/Jac/ODE/rates/grad/dynamics/summary/fitUQ0，唯一120s窗关闭0retry。8actualsaved y/time与原52source全保持，758records/144literature614assumed0measured原样。原8端点区间+新初始参考全程endpoint账本均低原0.1%；最接近门槛cooling N元素signed1.47620381198e-06molatoms/denom0.00290216784547，relative0.000508655560457（0.050865556%）；gasO2最高0.045102942%，U最高0.001458559%，S最高0.001016471%。P77行政AST false历史保留，正确目标归属三initialselfwrite0；未改loader/源。原P68initial未保存，新参考非历史恢复；后7actual差的原初始归一化依赖明示，ptp仅提供端点不授轨迹极值。8actual端点strictnegative保持/min-3.3795444690834975e-18mol，原干燥FAIL/高温assumed/加密三方案反演缺口保持，overallcriterionNA/wholefalse。下一仅cooling时间步敏感性静态候选未采用未启动，0追加科学。详见docs/FULL_CYCLE_P78_ENDPOINT_LEDGERS.json/md。

|状态|时间 s|完整质量 kg|原global U J|原global S J/K|严格非负|
|---|---:|---:|---:|---:|---|
|new_declared_initial_reference|0.0|0.25878344858031754|-3897260.8574435455|304.82489657017135|True|
|drying_ramp|14400.0|0.2543231508292204|-3803286.5203592824|357.79788560676394|False|
|drying|86400.0|0.22509502835873962|-3343906.05357126|227.69758374713842|False|
|heating|97200.0|0.21929916581473635|-3247943.358070013|346.5346608868541|False|
|reactions|115200.0|0.2025807953677922|-2900416.431764196|414.90385017423927|False|
|sintering|126000.0|0.20098451981134854|-2841748.303187521|445.1469339693935|False|
|hold|133200.0|0.20098441697774916|-2840380.1230539307|446.2659388216065|False|
|cooling|154800.0|0.20120097227605707|-3043807.078292989|163.18446955838147|False|
|cooling_hold|162000.0|0.20120942405983946|-3049625.685463363|144.76471130774382|False|

新增初始向量来自严格加载后的原保存上下文，只有它是新声明参考；八个求解器真实向量和时刻逐值保持。首区间和全程依赖该新参考，不能冒称P68初始字节恢复；后七段差为实际saved→saved，但质量/元素/gas初始分母仍依赖新参考。

|区间|mass相对|最大element相对|U相对|S相对|最大gas预算相对|端点局部门槛|
|---|---:|---:|---:|---:|---:|---|
|drying_ramp|6.938201449429777e-10|3.0951092656942395e-06|4.3498384041892e-08|6.793932736579988e-09|3.7916663835510146e-06|True|
|drying|6.977924914555852e-09|1.0429654613732823e-05|7.256907098333273e-08|2.3394913520748793e-08|6.205841317917786e-06|True|
|heating|2.3917212465371425e-08|0.00011336725179978408|6.85624737058834e-08|2.5685478846469464e-07|6.745565422612982e-05|True|
|reactions|1.5008773649440072e-06|0.00012174202661715136|1.1362459539560163e-05|1.0164708759786888e-05|0.00021206962539678428|True|
|sintering|1.2185329503269165e-09|2.3808185392652063e-05|1.9631123092708112e-08|1.4766727516657268e-08|3.4529501410965314e-05|True|
|hold|5.044889750051446e-11|7.724174748251796e-07|4.2987207272758694e-08|2.2732156215466483e-09|6.606361189519798e-06|True|
|cooling|1.0775131778885341e-07|0.0005086555604574911|1.4585590543803759e-05|7.999257258951632e-06|0.00045102941685340307|True|
|cooling_hold|9.491074315015845e-09|7.30756955098542e-05|7.1682049674850544e-06|9.721623841070245e-06|2.9461534528623452e-05|True|
|whole_declared_cycle_using_new_initial_reference|1.4190821451019381e-06|0.00017692442335288944|1.3608567052026213e-07|8.65651460796197e-06|0.00011856885527694521|True|

表中数值是dimensionless fraction，原门槛为0.001=0.1%；不是百分数本身。完整signed残差、各分母、实际根规则/单位/threshold和evidence_basis均在JSON。

全程signed质量残差 -3.6723497132823413e-07 kg；U 0.14382583183104525 J；S -0.0033141684625661583 J/K。U采用原global储能、减heat/carried/signed外压功，完整formation/phase/surface/binding/gas/elastic储能一次计入；S保留原global归约、分别换算生产/交换槽，另列原slot-sum次序差；F=sum_i(U_i−T_iS_i)。

原energy_scale=max(ptp heat+ptp carried+ptp work, saved escale)，但本次ptp只取提供端点，不是未保存轨迹极值。原mass[0]、元素max初始元素/本段signedin、gas预算及escale/Tr出处均保留。当前主要预算无零分母；undefined null/false分支未在这些主要行动态触发，不以此修复历史CaO零phase预算。

已有helper counters state_thermo/water_fractions/direct_skeleton/rawquartzphase/rawliquidorder均9、fixedvolumedecode0；ctor继承3entries/initial2entries/72Newton等仍为源码forecast，不是原语动态观测。科学窗口完成后只读JSON/原尺度字段与身份比对，没有modelimport、helper/势/RHS/ODE等追加调用。

P77 AST误分类只在新行政记录纠正：旧算法把本地y/state的索引内self读取当self写入，原False及错误targets留历史。正确剥离写目标value链，三initial的模型根self写入均0；原52源码/严格loader逐字节保持。

八实际端点仍有微小负凝聚库存；最小-3.3795444690834975e-18 mol，原始符号不裁剪。严格非负flags没有因闭合通过而转PASS，既有浮点库存预算在本轮未另算。原nominal余水0.1358920787402553%>.1%、0measured、三项热域assumed延拓及旧FAIL全部保持。

最突出剩余数值证据是cooling N/N2/O2闭合对时间步的敏感性。本轮全部局部闭合过原门槛，不据此修改物性或动力学。下一候选先静态建立root显式max_step30s（原60s）和独立producer，再单段原cooling比较真实P75hold起点与P78原cooling参考；不重跑前段或自动补全cooling_hold。新120s/全输出4MiB/完整64MiB必须fresh重新采用，本轮未启动。它也不能替代完整终态产品/峰值温差/grid验收。

|验收层|当前结果|
|---|---|
|正常CLI和完整9点输出|实际完成|
|八区间及全程端点质量/元素/U/S/gas|原门槛内；新初始参考/端点采样范围明确|
|严格非负|八实际端点False，保留原负值|
|连续source域/局部熵/轨迹极值|未取得本轮验收|
|最新时间/网格、三方案、反演|仍未完成|
|原工艺|干燥FAIL保留|
|材料实测|待实测，0 measured|
|整个模型|criterionNA/wholefalse|

正常七root/docs路径Git后继和普通push，原Drive一次必要小增量/名称大小父目录readback、actualrestore0。历史6raw输入本轮只读全bytes计入；增量保存新输出/源码/根/报告与输入身份，不代表六输入/独有Git/history20GB恢复验收。最终收据runs/full-cycle/p78-endpoint-ledger-acquisition/final-delivery-state.json，末receipt不递归提交补包。
