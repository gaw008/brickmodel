# P77 离线端点账本接口：静态实施结果

P77 仅静态实施完成：新增独立离线endpoint-ledger exporter及根合同，原51model/strictloader源码逐字节不变，实际应用文件52；758records原样/144literature614assumed0measured，原候选/P65/P67历史notes保持。只stdAST/源码/现存JSON，productionimport/load/ctor/initial/decode/potential/RHS/Jac/ODE/rates/summary/fitUQ实际全部0，无--help/入口执行。initial_state不写self参考，单strictloader先ctor再恢复37numeric+partition/phase0/liquidreference，新initialy独立且不覆盖8actualsaved参考。未来1load/ctor/initial、9decode/9completevalues可保持原公用数，但ctor继承3entries/initial2entries和decode72Newton等另列sourceforecast，非实际计数。外压功原dy[-3]=-Psum(db)/escale，U残差减signedwork；原globalU/S与逐格F、完整storage只一次、signed质量元素gas反应能熵、原分母/zero nullfalse明确。首段/全程依赖新declared初始reference，后7interval真实saved差与该初始归一化分别标识，非P68初态恢复。六真实input合计8282699B；未来真实CLI/120s4MiB64MiB仅proposal0未采用未启动。静态不授physical/process/material/runtimePASS，旧FAIL/wholefalse保持。详见docs/FULL_CYCLE_P77_ENDPOINT_LEDGER_INTERFACE.json/md。

新增生产接口将读取六个明确文件、严格加载最终端点一次，并用保存的原配置与全部参考上下文处理八个真实端点。根 native_checkpoint.source_paths 不增加新生产输出器；旧50/51源身份保持，新文件作为独立输出来源记录。

|项|静态结论|
|---|---|
|原51源码与严格loader|逐字节保持|
|原758物理参数|不变，0measured|
|initial_state|创建独立y，不写任何self/reference；不需第二构造器|
|正确次序|严格source检查 → 1ctor → 恢复37numeric与partition/phase0/liquidreference → 新initialy独立 → 8真实savedy分别求值|
|初始证据|新同源declared reference，不是P68历史初态恢复|
|保存端点证据|后七区间差均实际saved→actualsaved；质量/元素/初始gas分母仍注明新reference依赖|
|生产入口验证|未导入、未运行；AST语法通过|
|本轮科学调用|全部0|

完整U/S直接复用现有 potential_values 的 native_reduction_U_j/native_reduction_S_j_k 原归约。形成能、石英/矩阵相、凝聚/孔气、表面、绑定/混合、弹性已经计入，不追加反应或相变热。F采用sum_i(U_i−T_iS_i)。

质量kg、元素mol atoms、gas/反应mol、heat/carried/exteriorwork J、production/exchange J/K。原RHS外压功槽是−P·Vdot，故能量残差为ΔU−Δheat−Δcarried−Δwork；另列Δwork+PΔbulk诊断，不为它借新判据。熵采用原global S与分别换算的生产/交换槽，另保留原slot-sum浮点次序的残差差异。

|分母|实际沿用规则及来源|
|---|---|
|质量|新真实初始reference的完整固/气mass[0]|
|元素|每元素max(initial元素库存, signed本段boundary_in·gas原子矩阵)|
|能量|原max(ptp heat+ptp carried+ptp work, savedcontext escale)，仅对本接口提供的端点样本取范围|
|熵|原savedcontext escale/Tr，沿用根acceptance.entropy_relative|
|gas预算|max(abs起/终库存, 每反应signed源绝对和, abs signed in+abs signed out)|
|gas初始参考|新reference的初始该gas mol，仅诊断，不设独立PASS|

零实际分母为relative=null/undefined_zero_budget/passed=false，未把原元素np.divide零分支的0输出搬作PASS；没有新增floor/epsilon。质量、元素、U/gas沿用acceptance.balance_relative；原escale是已有初始容量尺度，不是新增可调下限。端点范围不等于未保存中途最大残差，所有signed负库存和负账本差保留。

|未来入口层|公用入口数|继承内部source forecast|
|---|---:|---|
|strict load/ctor|1/1|构造器继承3entries，quartz phase2/liquid phase1等；无decode/value|
|initial|1|Thermoelastic+FiniteGas两entries，1新向量/1equilibriumlogodds；self参考写0/decode/value0|
|native decode|9|9unpack/chart，72固定Newton/elasticresponse，thermalstrain/phaseeigen81等|
|complete value|9|state_thermo9/thermo继承27/caloricintegrals18/quartzpolynomial45/liquidphase18等|
|其余科学入口|0|RHS/Jac/ODE/rates/gradient/instantprojection/state_dynamics/summary/fitUQ0|

以上均为源码分支推导，未独立观测原语计数。本轮没有任何科学窗口；原候选9decode/9value预算不含构造和initial内部，现已分别列明，原公用数不必增加。

未来正常source-cwd CLI：

    /Users/wanggaoying/Research/brickmodel-github/.venv/bin/python -B -m sludge_vme.models.full_cycle_endpoint_ledgers /Users/wanggaoying/Research/brickmodel-github/parameters.full_cycle.json --out /Users/wanggaoying/Research/brickmodel-github/runs/full-cycle/p78-endpoint-ledger-acquisition

六输入完整尺寸见JSON，总8282699B。未来四科学文件为case-parameters.json/endpoint-ledgers.json/stdout/stderr，合计4MiB、launch到finalreap120s；新完整64MiB预算重新纳入全部52源码/离线依赖/root/六输入/blob/freeze/报告/admin/archive/finalself及原八reserve+2MiB，不能借P77 PASS。未来尚未采用，任何计数、输出大小或数值PASS尚未取得。

原P65/P67参数note、P76候选原文与全部旧FAIL保留。0 measured、原名义干燥FAIL、高温三项assumed延拓、latest时间/网格加密/三方案/反演和整体模型未完成保持。两处行政格式派发错误已留证，不算科学执行或重试。

本轮只八条源码/root/docs路径正常提交推送，原Drive一次静态增量metadata，actualrestore0。旧六rawinputs本轮只读且全bytes计入预算，不重复整批上传；其历史完整备份验收不因此补齐。实际末收据见runs/full-cycle/p77-static-endpoint-ledger/final-delivery-state.json。
