# P71 原生 reactions 单阶段续算结果

P71 独立原reactions续算已真实完成：从P68实际97200s/y275续至115200s，0initial/1savedload构造声明/1BDFsolve，新y275与51source/config/context保存，0summary/势/state_dynamics/fit/UQ。rc0/reaped，wall35.968494625s/CPU35.703364000s，科学全部2006055B/4194304B，300s窗口关闭无重试；实际RHS9701/Jac56、nfev965/njev56/nlu157。温度1049.684203–1066.635128K，q=-60.621853至-57.591303，脱羟累计0.30503219151407235mol/新增0.30192904798592163mol，脱碳新增0.13241213422851836mol。q仍很负，未算液相/耦合功率；12endpoint均越700K hydroxide来源上限，旧assumed解析延拓不授domain/materialPASS。758records全保持、144literature/614assumed/0measured，原失败与criterionNA/wholefalse保持。详见docs/FULL_CYCLE_P71_REACTIONS_ENDPOINT.json/md。

|项目|实际保存结果|
|---|---|
|原生区间 / s|97200 → 115200，完整原y275输入、sol.y末端y275|
|端点温度 / K|[1049.6842033375572, 1066.6351278239797]|
|q 范围|[-60.62185336451861, -57.591303231372684]|
|q signed变化|[13.16658386491536, 16.19719224028095]|
|BDF nfev/njev/nlu|965 / 56 / 157|
|实际 RHS/Jac|9701 / 56|

原入口只续原reactions一段，模型rhs/jac/BDF、全部9knots绝对时间插值和原758参数保留，不重跑前三段。实际rawresumeorigin逐值等于P68保存heating输入；初始机械/referencecontext和累计账本原点不重置。输入strict50实际载入，输出51完整source普通文本等于launchfreeze，新51输出的动态load尚未调用。

|反应|累计 mol|本段 signed增量 mol|
|---|---:|---:|
|evaporation|1.873407471047043|7.254383893406356e-05|
|dehydroxylation|0.30503219151407235|0.30192904798592163|
|decarbonation|0.13241213422851836|0.13241213422851836|
|organic_oxidation|0.07780609464962564|8.204233359949311e-09|
|char_oxidation|0.1657305215563239|9.355534910847189e-05|
|organic_carbonization|0.07206404083496713|2.917273355861838e-09|
|lime_dehydration|-5.752382600814803e-17|-5.78901031401062e-17|

所有原始负值、signed累积与微小反向lime_dehydration保持，不裁剪。累计heat/carried/pressurework/entropy生产交换及四气体进出都在JSON列出cumulative和本段signed差；它们是原生槽归约，不是新库存/守恒残差验收。

实际端点12格温度均高于portlandite源域700K上限，保留该来源完整[298.15,700]及原assumed解析延拓政策。其他源域边界原值在JSON；端点内范围不意味着全积分内部点/连续域有效。目标实材0measured，没有新增文献或来源有效性PASS。

脱羟载体账本已明显非零，脱碳/氧化、完整气体与机械状态仍来自原物理核；q增加13.1666–16.1972却仍很负，没有调用sigmoid/phasefraction/potential或功率进行补测，不能判断充分液相激活。原名义余水0.1358920787402553%>0.1%、CaO零预算nullfalse及所有旧失败保持，完整8阶段与受影响dt/grid加密/比较/反演仍未完成。

下一只登记同一真实reactions端点的strict51load+1sameevent+15values：正常Research/src旧CLI --checkpoint-dynamics，0initial/Jac/ODE/summary/fitUQ，新独立120s/4MiB/64MiB，原8reserve+2MiB不減。它将检验新增producer身份的实际载入及1049–1066K演化状态U/S/派生F与真实Vdot，并保持700K越域assumed与弱phase限制；criterionNA不借旧阈值授PASS。本P71没有追加调用。

本轮仅7明确root/docs路径进入Git，rawfields/config/context/source在runs与一次原Drive必要增量。Git/metadata/恢复/历史20GB/GitHub容量分列，restore0；最终所有实际source/root/input/freezes/原及stagedblob/archive/末receipt自身见runs/full-cycle/p71-native-reactions-continuation/final-delivery-state.json。
