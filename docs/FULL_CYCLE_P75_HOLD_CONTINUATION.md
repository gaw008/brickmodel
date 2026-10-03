# P75 原 hold 单阶段续算实际结果

P75 原hold126000→133200s已真实续算完成：先保留P74两处错误P73reactions路径历史并静态纠正为真实P73sintering完整输入，不建alias、不用P71、不重建初态。strict51load/ctor路径声明、0initial/1原BDFsolve/1新y275/source51端点，势/state_dynamics/summary/fitUQ0。rc0/reaped，wall2.149399333s/CPU1.935516000s，科学全部2006371B/4194304B，300s唯一窗口关闭无科学重试；实际RHS422/Jac1，nfev/njev/nlu=266/1/28。T1223.149979234–1223.149995956K，q-0.000141480844976–-0.00013509899223。758完整records与51科学源全保持，144literature614assumed0measured；三项来源越域assumed、旧失败/criterionNA/wholefalse保持。预算flat-schema读取失败与重复行政调用留证，科学0后显式简化再freshgate。下一原cooling+cooling_hold两段单独候选未启动。详见docs/FULL_CYCLE_P75_HOLD_CONTINUATION.json/md。

|项目|实际结果|
|---|---|
|区间 / s|126000 → 133200|
|端点温度 / K|[1223.1499792338384, 1223.1499959555679]|
|q 范围|[-0.00014148084497644928, -0.00013509899223012911]|
|q signed变化|[0.3517678636434972, 0.5257022588407875]|
|BDF nfev/njev/nlu|[266, 1, 28]|
|实际 RHS/Jac|[422, 1]|

原P74候选的argv checkpoint与input_checkpoint误写p73-native-reactions-continuation，P75只改这两字段；原候选全文proposal0历史保持，纠正候选其他JSON字段不变并与协调正式候选相同。真正P73输入为p73-native-sintering-continuation/native-checkpoints.json，共1377152B、sintering126000s/nativey275/source51/referencecontext；不存在错误目录alias/复制或P71替代。原ordinary strict51loader实际成功消费，输出51source文本匹配冻结。

前置预算文件改为扁平八项结构，旧行政读取gate两次KeyError，prepare因manifest不存在在Research写入前停止；三次行政失败、科学0/Research写入0留证。显式读取P75flat表，extra2MiB使用原P74同一预留record，完整新预算独立测量，不借旧PASS/剩余额度。

|反应|累计 mol|本段 signed增量 mol|
|---|---:|---:|
|evaporation|1.8734083917132087|1.6024732166651476e-07|
|dehydroxylation|0.30503219151407235|0.0|
|decarbonation|0.16860348357277524|0.0|
|organic_oxidation|0.07780609464962564|0.0|
|char_oxidation|0.165730521556324|2.708090716991111e-18|
|organic_carbonization|0.07206404083496713|0.0|
|lime_dehydration|-3.314378176073889e-17|-3.931829156724912e-19|

四气体in/out与heat/carried/exterior-pressurework/entropy-production/exchange按原native槽和保存尺度sum/signed差归约。完整rawy与context配置都保持；这是原生账本读出，不是新库存或完整U/S残差验收。不调用端点势/dynamics/summary或其他科学解码；原始微小负值保留，strict非负未资格。

|类别 / 物种|来源温度范围 K|端点低于 / 高于格数|
|---|---|---|
|caloric/O2|[298.15, 2500.0]|0 / 0|
|caloric/N2|[298.15, 2500.0]|0 / 0|
|caloric/H2O|[298.15, 2500]|0 / 0|
|caloric/CO2|[298.15, 2200.0]|0 / 0|
|caloric/calcite|[298.15, 1200.0]|0 / 12|
|caloric/lime|[298.15, 1800.0]|0 / 0|
|caloric/portlandite|[298.15, 700.0]|0 / 12|
|viscosity/N2|[120.0, 1700.0]|0 / 0|
|viscosity/O2|[120.0, 1700.0]|0 / 0|
|viscosity/CO2|[100, 2000]|0 / 0|
|viscosity/H2O|[273.16, 1173.15]|0 / 12|

实际12格均越portlanditecaloric700K/calcitecaloric1200K/H2Oviscosity1173.15K，沿原assumed数学延拓/no clipping。域内其他物种未自动实材验证；0measured，不扩direct290–350K，不授连续积分/Newton/complexstep源域。

P74已有实际phase/机械点证据，P75不机械重复投影。当前原hold端点已保存，下一有意义范围为原cooling133200→154800及cooling_hold154800→162000两段顺序采集，第二段严格读真实第一段输出，0initial/无参考原点重置。仅登记单独1logicaljob/worker/attempt、2正常CLI child/2loadctor/2solve/2endpoint、一个总300s deadline和全部8科学文件合计4MiB、完整64MiB与原八reserve+extra2MiB；尚未采用或执行。原producer两flag仍按旧schemafalse，真实stage coverage与完整守恒验收分开；不根据最后endpoint造fullcyclePASS。

原名义余水0.1358920787402553%>.1%、CaO零预算nullfalse、P45/P34/P40/P44/P50撤回/P51/P58/P60/P61/P63、旧资源FAIL及全部负库存保留。剩余冷却端点、最新完整8stage质量/元素/U/S、受影响时间/网格加密、三方案/反演与实材资格仍未完成。

本次七明确root/docs文件正常Git后继/普通push，原Drive一次必要增量；actual_restore0/历史20GB与GitHub容量分别判断。全部原/纠正候选、路径纠正、admin失败、科学输入/输出/source/freezes/oldstagedblob/报告/admin/archive/末self按完整文件计入最终收据，末receipt不递归commit/补包。
