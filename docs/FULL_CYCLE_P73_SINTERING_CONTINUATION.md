# P73 原 sintering 单阶段续算实际结果

P73 原sintering独立续算真实完成：从P71 reactions115200s/y275至126000s，strict51load/ctor路径声明、0initial/1原BDFsolve、1新y275/source51端点，势/state_dynamics/summary/fitUQ0。rc0/reaped，wall6.713187208s/CPU6.480378000s，科学全部2006326B/4194304B，300s窗口关闭无重试；实际RHS1672/Jac8，nfev/njev/nlu=424/8/50。T1217.111809–1221.681264K，q-0.525843740–-0.351902963，signed推进57.239400269–60.096009625；已取得有意义后续相变坐标，但未独立计算fraction/phase功率/守恒。12格均越portlandite700K/calcite1200K caloric及H2Oviscosity1173.15K原源上界，沿旧assumed延拓不授source/material/continuous资格。758records原样、144literature614assumed0measured、criterionNA/wholefalse与全部旧失败保持。下一同端点1event15values仅登记未启动。详见docs/FULL_CYCLE_P73_SINTERING_CONTINUATION.json/md。

|项目|实际结果|
|---|---|
|区间 / s|115200 → 126000|
|端点温度 / K|[1217.1118086108925, 1221.6812642099712]|
|q 范围|[-0.5258437396857639, -0.35190296263572735]|
|q signed 变化|[57.23940026873696, 60.096009624832845]|
|BDF nfev/njev/nlu|[424, 8, 50]|
|实际 RHS/Jac|[1672, 8]|

普通 Research/src 模块入口只续原 sintering 一段。严格输入51source全部匹配，原y275和mechanical/referencecontext及所有累计原点保持；无initial_state、前段重算、seed、参数覆盖、环境注入、安装或新源码。P70历史intended标签保持，P73另外登记reactions→sintering；producer按实际saved stop_stage选择原下一段。

|反应|累计 mol|本段 signed增量 mol|
|---|---:|---:|
|evaporation|1.873408231465887|7.604188441867111e-07|
|dehydroxylation|0.30503219151407235|0.0|
|decarbonation|0.16860348357277524|0.0361913493442569|
|organic_oxidation|0.07780609464962564|0.0|
|char_oxidation|0.165730521556324|1.3134239977406887e-16|
|organic_carbonization|0.07206404083496713|0.0|
|lime_dehydration|-3.2750598845066403e-17|2.4773227163081625e-17|

原生四气体in/out、heat、carried、外压功和熵production/exchange槽只按原保存尺度归约，signed原始增量保留；这些是已有累计账本，不是新全库存/完整U/S残差验收。全部rawy与完整配置/源/context在runs；报告没有调用sigmoid/phasefraction、机械解码、独立势或额外科学算子。

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

端点域检查仅限实际保存12温度。portlandite caloric、calcite caloric、H2O黏度均12格越上界，保留原assumed数学延拓/no clipping，域内其他物种也不自动获目标材料资格。0measured，不扩direct synthetic290–350K，不授连续积分/Newton/complexstep源域。

q从原−60.6219..−57.5913推进到−0.52584..−0.35190，是真实原烧结状态；这使下一同事件phase与机械功率诊断有实际价值，但不承诺充分激活或独立热力学PASS。P73不追加fraction、potentials、state_dynamics或summary。下一候选strict51savedload/0initial/1event/15values、0JacODEsummaryfitUQ，独立120s/全科学4MiB/完整64MiB与原八reserve+2MiB，未采用未启动。

原名义干燥余水0.1358920787402553%>.1%、历史CaO零预算relative=null/passedfalse、P45/P34/P40/P44/P50撤回/P51/P58/P60/P61/P63与微小负库存保持。新端点/rc0不取代完整八阶段守恒、受影响时间/网格加密、三方案/反演或材料验收。

本次只7明确root/docs文件进入Git；正常后继push、原Drive一次增量、metadata读回、实际恢复0、历史20GB/GitHub容量分别列收据。全部必要文件与old/stagedblob、冻结、archive、最终self完整计数见runs/full-cycle/p73-native-sintering-continuation/final-delivery-state.json，末收据不递归commit或补包。
