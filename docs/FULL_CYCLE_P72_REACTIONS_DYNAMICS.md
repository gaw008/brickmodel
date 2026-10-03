# P72 真实 reactions 端点势与原生变化率

P72 真实reactions115200s端点strict51load与同事件投影已完成：rc0/reaped，wall0.950378875s/CPU0.679432000s，科学全部1445502B/4194304B，120s窗口关闭。1load/ctor路径声明、0initial、实际1nativeRHS/rate/chart及15完整势，JacODEsummaryfitUQ0。Udot原生28.263728917584093W/投影28.26372891758409W/signed差-3.552713678800501e-15W；原Sdot=-0.000525131632333618W/K，投影对原全局signed差+4.336808689942018e-19W/K，派生Fdot差-7.105427357601002e-15W。CaO库存0.13241213422851839mol，实际phase功率3.6120133845024145e-25W仍极弱；qdot0.00498424–0.00660763/s。当前差未定位具体漏项，不证明浮点原因或独立PASS；下一价值在原sintering真实后续状态。758records未变/144literature614assumed0measured、OH700K越域assumed、旧失败与criterionNA/wholefalse保持。详见docs/FULL_CYCLE_P72_REACTIONS_DYNAMICS.json/md。

|量|原生全局|完整势投影全局|投影减原生 signed|
|---|---:|---:|---:|
|Udot / W|28.263728917584093|28.26372891758409|-3.552713678800501e-15|
|Sdot / W K⁻¹|-0.000525131632333618|-0.0005251316323336175|4.336808689942018e-19|
|派生 Fdot / W|19.56546608014372|19.565466080143715|-7.105427357601002e-15|

实际strict51source已消费，完整保存y275/config/referencecontext保持，0初态/ODE。现有RHS/完整值/helper计数实际记录，load/constructor为成功路径声明；低层未仪表化计数仍inferred。原执行记录boilerplate提solver/bundle仅历史文案，实际无solver，完整计数来自state-dynamics.json。

真实Vdot总量 2.7516227756605452e-11 m³/s，外压功 -2.7516227756605453e-06 W，Vp导数另存，不重复加压功。原全局S归约不变，逐格归约signed差 1.5178830414797062e-18 W/K；产熵 0.0007276155442689111、交换熵 -0.0012527471766025193 W/K，Sdot负值原样保留。F逐格Udot−T*Sdot−S*Tdot新派生，不借旧cache/meanT/第二EOS。

当前metakaolin=0.3050428640422212 mol，lime(CaO)=0.13241213422851839 mol；calcium chart方向Udot=22.997242827032874 W，为当前主要成分贡献。最低凝聚相库存 -2.179584804450866e-22 mol 保持signed，strict非负不授资格。现有CaO不为历史零预算改写null/false。

q范围 [-60.62185336451861, -57.591303231372684]，qdot范围 [0.004984239859100395, 0.006607625418110076] s⁻¹；原生phase功率 3.6120133845024145e-25 W，仍不足充分激活证据。q方向完整产品含耦合弹性/本构效应，不能与仅internalphase储存分项直接相减断言漏项。全部14×12梯度/速度/产品和原生分项、signed差完整保存。

单状态总体signed差目前没有暴露具体实现漏项；差小不是浮点归因证据，也不是独立热力学验收。无据不改原物理核或参数、不追旧阈值PASS。真正剩余模型缺口为充分phase状态、最新完整8stage守恒及受影响时间/网格加密、三方案/反演与材料资格。

下一具体范围为从原P71同一115200s/y275/source51检查点继续原sintering至126000s，炉温1073.15→1223.15K，原BDFrtol1e-5/atol1e-7/max60s及完整9knots不变。1strictload1ctor0initial1solve1endpoint，0势/summary/fit/UQ，独立300s/4MiB/64MiB并fresh内部采用/完整gate；不是重复当前诊断，不预测充分phase激活。完整argv/case/source/来源域/预算方案在JSON和runs/next-original-sintering-proposal.json。

实际当前12格温度都超过hydroxide源域700K；下一阶段还可能超calcite热容1200K及H2O黏度1173.15K上限。来源完整边界与原assumed解析外推保持，不授新高温/目标材料/连续域资格，不扩disabled direct与synthetic290–350K。原名义余水0.1358920787402553%>0.1%、CaOnullfalse和全部旧失败保持。

本轮7root/docs文件进入Git，raw场仅runs/原Drive必要一次增量。原八reserve+额外2MiB不减，最终完整预算含原/stagedblob、冻结、archive及末receipt自身见runs/full-cycle/p72-reactions-native-state-dynamics/final-delivery-state.json；实际restore0/20GB/GitHub容量另列。
