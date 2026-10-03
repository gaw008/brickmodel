# P88 原烧结段配对时间比较实际结果

P88 唯一原烧结段115200→126000s paired60/30实际运行完成，wall14.229181667s/CPU13.752422000s，四science3466865B/4194304B，300s窗closed/reaped/0retry/0postwindow科学。原55sources/758完整records/144literature614assumed0measured及37context保持；2strict51load/ctor/BDF/endpointdecodevalueinterval、182publicrates+182center实际完成，0initial/baseline/reference重求；coarse/refined原RHS1672/1856、Jac8/7与nfev424/764独立计，低层primitive仍sourceforecast未测。各91原120s完整cell/surface/center采样峰18.2667389391K均在共用起点，peakrelative0不证相同内段/continuouspeak；内段span signeddiff−0.0006413720864→+0.001029235586K。phi/carbon/条件shrink relative 2.156810623e-10/1.105255333e-18/2.331563675e-08低原strict.02，signedcarbon由负到正、shrink仍负不clip。两端点质量/元素/完整U/S/四gas低原.1%，最坏relativecoarse3.452950141e-05/refined7.606667307e-06。严格非负仍false，mincondensed -1.372439673e-20→-2.754455551e-17mol变更负，char最小也变负；不能称非负改善。原输入、actualsolver完整275维t0及signeddelta分存且均同一输入；source55/context共享、三个config各一次，P78newreference条件化与历史t0 null/unavailable分开。只局部sintering time/sampledpeak/endpointPASS，原drying.1358920787402553%>.1%、CaO nullfalse/P45/resources/全部FAIL/高温三源assumed/direct合成290–350K及wholefalse保留。下一仅原reactions97200→115200配对接口的最小静态通用化候选未采用，无追加科学。GitDrive/恢复0/容量另receipt。详见docs/FULL_CYCLE_P88_SINTERING_TIME_COMPARISON.md/json。

|指标|原60s|独立30s|绝对相对差|
|---|---:|---:|---:|
|porosity (1)|0.495137830122159|0.495137830015367|2.15681062e-10|
|residual_carbon_kg (kg)|-2.47777558045723e-26|8.57477774486079e-26|1.10525533e-18|
|shrinkage (1)|-0.00915537827295365|-0.00915537805949018|2.33156367e-08|
|peak_temperature_difference_k (K)|18.2667389390731|18.2667389390731|0|

峰值采用原格点、表面和中心三者max−min定义，单位K；不是cell-only。两次最高采样跨度位于115200s共用输入，零峰值差没有覆盖连续时间极值。已保存内部采样跨度差的signed范围作为无验收门槛诊断，不重新评价模型。

端点账本有signed原始增量、原预算及初始参考归一化；完整能量/熵沿用原host表达式及同一初始构成context，相变及反应只沿用原source，不另加热源。两个端点的累计范围不是连续路径最大值。旧P73端点不是新峰值基线，也未重算前缀。

孔隙率为bulk权重；残碳是organic+char元素C kg，负原值保留；负收缩表示该参考下端点膨胀。初始reference是P78新declared值，旧历史t0 unavailable/null保持。最小负库存与char负值无clip/seed/floor修复；全局碳变正不等局部非负。

原共同reactions输入已经char负6格/min−2.179584804450866e−22mol、portlandite负4格/min−9.349021574400408e−24mol。两新端点char负6/5格，最小−9.135592905202675e−24/−3.503660785213176e−23mol；全condensed最负来自portlandite。不能把所有负值归为本次新生，也不能宣称加密修复非负。保存span最大绝对差0.0010292355855199276K在sample1/115320s，signed refined−coarse为正；surface/center最大绝对采样差0.0006167816616198252/0.0007001377962296829K。这些是保存数组无新criterion的诊断，没有新增科学调用或全时程资格。

原source55/严格loader/CLI普通文本未改，root758完整记录一致。根文件保留原60s/rtol/atol与独立sintering30s，运行casefile与两solver实际设置匹配。完整input51普通文本是共享55字典的明确子集，原37context一次共享，原P71保存配置和两个有效配置各一次。精确inputt0和两个actualsolver完整t0直接保留，signed delta均为0，不从delta重建。没有91点全原生场进入Git。

后续仅一个未采用的静态接口候选：原reactions97200→115200区间的显式根合同选择/来源标签及独立halfstep声明。当前不读取或运行新的科学输入、不追加加密；后续数值预算需另完整声明。原前六段/全周期time/grid/三方案/反演/材料未完成，严格非负与干燥FAIL保持。

准备到本报告真实wall539.812266s；科学wall/CPU见实际窗口收据。四science文件和stdout/stderr完整保留；一次Git/Drive增量及完整终态预算在独立receipt，恢复0，历史20GB/GitHub容量仍未解决。
