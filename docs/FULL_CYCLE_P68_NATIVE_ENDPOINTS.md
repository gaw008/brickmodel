# P68 真实 nominal 三阶段原生端点

P68 新批准的真实nominal三端点采集已完成：rc0/reaped，wall83.251448208s/CPU82.261245000s，科学全部2025102B/4194304B，唯一300s窗口关闭。1构造/1初态/3solve，实际RHS23568/Jac125，0加载/势/state_dynamics/summary/fit/UQ。758完整records未变，144literature/614assumed/0measured，原12格mode0Ca0/directoff与8knots保持。3原生y各275及50源/config/context真实保存；heating实际T671.012175–671.432721K，脱羟累计0.0031031435281507207mol，q=-73.788495至-73.788437，载体账本非零不等液相充分激活。未算新守恒/功率/加密/材料资格，criterionNA/wholefalse；后续同状态loader+1event15values仅独立提案未采用。详见docs/FULL_CYCLE_P68_NATIVE_ENDPOINTS.json/md。

|阶段|原生时间 s|实际单元温度范围 K|q 范围|nfev / njev / nlu|实际 RHS / Jac|
|---|---:|---|---|---|---|
|drying_ramp|14400.0|[366.72596019115304, 368.50655273249475]|[-73.78855450650516, -73.78855450650516]|712 / 9 / 85|2116 / 9|
|drying|86400.0|[383.15027420074745, 383.15033411143116]|[-73.78855450650516, -73.78855450650516]|2468 / 19 / 290|5432 / 19|
|heating|97200.0|[671.0121750418057, 671.4327211834061]|[-73.78849547165363, -73.78843722943397]|888 / 97 / 180|16020 / 97|

全部源50份、完整配置与reference context在共享checkpoint头；3完整y来自实际sol.y端点，账本原点连续且不由summary回拼。native length275、gas132:180、反应180:264、边界264:272、外压功272、熵273/274保存。参考nscale=4.650198977282131mol/escale=114147.47988818285J/Tr=298.15K；signed零值及微小负累计量保留。

保存状态、NumPyJSON写出已实际执行；加载与势/动态投影没有调用。报告仅归约已保存原生累计量，未解码库存、计算液相分数/新状态/热源/热力或守恒残差。实际局部heating温度低于700K来源上限仅限此端点，不能授between-point/全周期资格。

下一只提出相同heating检查点的正常src cwd `--checkpoint-dynamics`：1saved-config构造/0initial/1same-state nativeevent+15完整势值/0JacODEsummaryfitUQ，新独立120s/4MiB/64MiB，原8reserve+额外2MiB保持。完整argv/输入/原与暂存blob/源码冻结/报告/监督程序/一档案/self预算在JSON；未批准、未启动，不移用P68窗口。q仍很负，可能无法充分激活液相耦合，不承诺PASS。

原名义余水0.1358920787402553%>0.1%、CaO零预算relative=null/passed=false和全部旧失败保持；0measured/wholefalse。完整8阶段、受影响加密/三方案/反演与现实材料仍有缺口。P67历史proposal0不改写。

Git/Drive增量/实际恢复/历史20GB/GitHub容量分别判断，restore0；最终实际源、根、冻结、必要输入、原与暂存blob、唯一archive及末收据自身见 `runs/full-cycle/p68-nominal-heating-checkpoints/final-delivery-state.json`。
