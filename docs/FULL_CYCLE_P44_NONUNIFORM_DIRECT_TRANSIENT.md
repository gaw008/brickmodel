# P44 固定二次分区的三档动态验收

P44固定二次分区10s合成动态三档已实际完成（2026-10-02T00:43:57.565155+00:00）：3实例/3积分均rc0回收，实际8160RHS/30Jac、solver32.657392s/CPU含构造33.530160s、launcher35.137540s。原质量/元素/完整能量最坏1.5485576e-8，四gas预算最坏9.1030257e-6、初始库存归一最坏1.6446839e-4，均<原0.001；time/grid四指标全PASS，最大0.0091178763<原0.02。仍partial：3/9唯一CaO逐相无floor预算FAIL、3档严格OH/carbonate熵负值和原始负库存保留；direct累计extent网格相对基准差3.01853436%未获额外空间资格。原P40uniformmesh7.33335%失败不被新表示覆盖；原P34全周期30/81、名义干燥0.135892078740%>0.1%及wholefalse保持。541=144literature397assumed0measured，旧534完整保留，仅新增7运行政策，45源码与4764255冻结一致；名义mode0/direct未启用。新8阶段、三方案/反演/UQ/离线CLI未获新资格，synthetic不授实砖速率。

|档位|格数|实际RHS（含内部Jac）|Jac|solver秒|CaO预算相对残差|严格OH最小W/K|严格carbonate最小W/K|
|---|---:|---:|---:|---:|---:|---:|---:|
|baseline|12|2379|12|9.200441|1.23878205|-6.80391314e-33|-3.367617e-42|
|time_refined|12|2108|8|8.027536|1.15750529|-5.78546121e-33|-3.11774189e-42|
|mesh_refined|24|3673|10|15.429416|0.935672515|-4.68552568e-33|-1.55887095e-42|

|加密|指标|带符号 refined−baseline|原分母|相对变化|原2%结果|
|---|---|---:|---:|---:|---|
|time_refined|porosity|1.33091593e-10|0.19102396|6.96727223e-10|PASS|
|time_refined|residual_carbon_kg|4.33680869e-19|0.00292504616|1.48264624e-16|PASS|
|time_refined|shrinkage|5.74296166e-12|0.001|5.74296166e-09|PASS|
|time_refined|peak_temperature_difference_k|2.33611104e-07|1|2.33611104e-07|PASS|
|mesh_refined|porosity|-2.25732956e-07|0.191023734|1.18170109e-06|PASS|
|mesh_refined|residual_carbon_kg|-1.12757026e-17|0.00292504616|3.85488022e-15|PASS|
|mesh_refined|shrinkage|-1.83877837e-08|0.001|1.83877837e-05|PASS|
|mesh_refined|peak_temperature_difference_k|0.00911787627|1|0.00911787627|PASS|

三档仅改变固定initial_partition mode2、格数/时间设置；同P40物性、配方、L=1/s synthetic、气氛、面积、厚度、10s、源域和原阈值，指数2 assumed，不用P43给定温度/浓度局部field作y0。initial_state实际供给BDF，初始所有独立extent/累计账本为零；真实初始库存/元素/mass/U/S、参考faces/centers/bulk/md/chemical/cumulative原样保存。没有改供体、增热源、裁负或从相库存重建extent。

孔隙率沿用当前体积加权，收缩沿用1−最终/初始全域总体积，残碳全域和，峰温差为输出样本最大空间温差，新mode中心诊断用初始参考格中心。原峰温差floor1K未调；新几何4指标通过不追溯替换原P40uniformFAIL。独立directextent时间差9.31411725e-6、网格基准归一0.0301853436；不另设宽门槛或floor授空间资格。

CaO全域带符号残差分别2.09522070e-17/2.96800345e-17/2.38524478e-17mol，初始CaO含原始负值；预算/初始库存归一各自保存，0分母明确undefined。每格OH+xiH+xiD、Cc+xiC−xiD、CaO−xiH−xiC及总Ca独立不变量保留。whole与唯一stage为同实际区间，9唯一相预算/18重复行，不当独立复制。OH与carbonate严格符号FAIL不被普通守恒或旧roundoff物理容差覆盖；direct样本熵均正，非所有连续/Newton/complextrial态正性证明。

首actual solverentry 2026-10-02T00:36:47.603274UTC固定唯一截止00:51:47.603274UTC；3starts含失败额度已全用，0失败积分/第四次/延截止/独立RHS-Jac扫描/fit/UQ/恢复。构造前MRO、公有方法及direct包装实际计数：每例一个实例、三继承层构造体各一次，constructor phase p/phase/liquid回调分别保存；仅公有dispatch覆盖，不声称每个importedpurehelper都插桩。summary每例21 rates/direct；接受步/输出样本域审计无新RHS，T[290,350]K、各分压[0,200000]Pa、总压[1000,200000]Pa实际PASS。每例求解器自适应步/步帽命中数留存，time步帽.05而base/mesh.1，原rtol/atol不变。

运行前仅修正共享start收据原子替换/回收范围，0当时science；运行后独立审查发现指标定义文案和初值诊断需按体积统一，只更正这部分保存数据，已通过最终加密值不重评。必要数值汇总1510309B<2MiB，45冻结src/root/执行metadata另辨识，无完整原始场。代码/参数准备、独立审查、文档/Git/Drive工作流另记，不混作35.14s计算耗时。

实现/局部条件化动态四指标已获所述资格，严格逐相/分支及完整模型未完成。下一必要候选是近零相状态表示的守恒/能量/熵准入；无后续资源分配，不自动积分，不关机制替代失败。P43正常提交4764255及1063956B/Drive1BGeKUOgJZF5Pkuq2w4lZNfrJ3PQZWjP3 metadata实际收据已并入本次实质准备。P44正常Git及唯一增量按随后本地实际收据，不notes递归；无下载/解包/恢复，压缩原件/独有历史保留，历史20GB与GitHub容量警告未解决。
