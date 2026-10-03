# P87 烧结段配对采样峰值比较接口

独立 producer55 已实现，当前只完成静态代码、来源及序列化审查。生产模块没有 import 或运行，没有新物理数值结果。全模型验收仍未完成。

未来两条原始烧结段从同一 P71 实际 reactions 115200s、275维原生状态、12格和37项构成上下文开始，分别以原60s与独立声明30s传给原 BDF，到126000s。各91个原120s绝对采样点；格点、原 rates 表面和原中心辅助函数的温差 max−min 后取采样最大值，单位K。此处不能确认连续峰值。P73只保存端点，未保存峰值采样，因此新的60s基线是必要的短段计算。

sample0采用原输入；每条计算实际返回的完整275维t0向量单独保留，另存 signed solver_t0−input。原输入保存在共享 resume_origin。实际返回值不由delta加回重建。两条新端点完整原生状态及库存/势值/区间账本保存；不保存全部91点完整原生场，不将轨迹放入Git。

原54份生产源码普通字节一致，strictloader/CLI和历史50路径不改；完整原758项参数一致（144literature、614assumed、0measured），原60s/rtol1e−5/atol1e−7及既有cooling和hold条件保持。新增政策在根文件声明 units/range/source/status，独立 sintering_half_step 为assumed policy，不是材料测量。

|未来完成路径|次数与范围|
|---|---|
|严格input51读取/逻辑构造|各2；无initial、reset或历史参考重求|
|原BDF/新端点decode/completevalue/interval|各2|
|公开sample rates/中心辅助函数|各182；没有182个势值评估|
|采样decode固定机械Newton|每个8次，共1456次源码预测；不是独立实测|
|内部RHS/Jac与nfev/njev/nlu|当前未知；将来用原计数器分别保存|

完整sample rates每次 elastic_response=8解码+1骨架化学势+1孔隙力学=10，共1820；thermal_strain12、phase_eigenstrain13、phase_reference_volume12、quartz phase15、polynomial15、quartz_thermo3、liquid_order30、liquid_phase3、liquid_contrast9、liquid_equilibrium5，均有源分支次数表。thermo逻辑2（cell+furnace），各MRO三层合计6entry；source_caloric_integrals6；water_fractions/retention_sites各4、retention/binding各2。机械Newton8和表面Newton6分列（1456、1092），额外力学路线没有额外机械Newton循环。中心helper每次纯插值，内部decode/thermo/Newton0。以上均sourceforecast/unmeasured，BDF内部Newton/RHS/Jac仍未知。

67个实际MRO方法的完整call-site、条件与循环源码图在配套JSON；包括thermo继承、矿物/气体热容、quartz/liquid、孔摩擦/黏度/水通量、表面固定Newton、孔隙力学/相松弛等。这些是源码预测，低层primitive未仪器化，不能伪记0。额外public RHS、dynamics、projection、gradient、summary、fit/UQ为0。两端点势值路径与采样 rates 分开。

原P78相同起点库存及新declared初始reference仅读取，用于原分母与条件收缩。质量、元素、完整U/S及四gas沿用原端点账本，带符号原始增量保留；能量范围为两端点累计范围，不能当连续路径极值。孔隙率按bulk体积权重；残碳为organic+char的元素C kg；收缩用共同新reference。旧历史t0收缩 unavailable/null 不恢复。四产品原floor与strict<2%保持，非负库存独立判断。

实际当前输入配置/source/context序列化及保守numeric/schema/log分配给出四科学文件估算 **3,965,444B/4,194,304B**，余量 **228,860B**。共享case文件静态布局2,466,206B；完整55源dictionary一次719,525B，原上下文一次。两effective configs及原保存config存入同一casefile，输出显式引用；完整input51为完整55普通文本字典的明确子集，未删必要来源。输出比较schema不是原strictloader的直接checkpoint输入。新实际输出和两solve+182rates耗时均未测。

未来单次配对候选已具备生产入口，但未动态验证/未数值采用：工作目录为项目src，用既有 ../.venv/bin/python -m sludge_vme.models.full_cycle_sintering_time_comparison ../parameters.full_cycle.json --out ../runs/full-cycle/future-sintering-time-comparison；候选JSON保存绝对argv及cwd，不设置PYTHONPATH、不安装。独立300s从firstlaunch到finalreap包含import/read/sample/JSON，是policy上限而非保证。case-parameters.json、sintering-time-comparison.json、stdout.log、stderr.log合计4MiB，完整必要字节+不减29,360,128B reserves须64MiB；开始前另做fresh完整gate。失败关闭/reap且0retry，不搜索步长、容差、seed或clip。

保留名义干燥0.1358920787402553%>0.1%、负char/负signed残碳、CaO零预算relative=null/passed=false、P45及全部资源失败；高温外推assumed，direct合成290–350K范围不扩，材料实测0。局部sintering sampledpeak/endpoints不授全前六段、全周期时间/网格、三方案、反演或材料PASS。

静态开发及行政到本记录真实wall **1057.585492s**；sciencewall/CPU=null。Git/Drive增量、metadata和实际恢复另存receipt；当前恢复0，历史20GB及GitHub容量警告未解决。

变更路径：新producer55、根parameters、P87 MD/JSON、spec/report/plan/GOAL_STATUS、final acceptance matrix，共9项。证据目录 runs/full-cycle/p87-sintering-time-interface-static。下一步是单个已完整提出但未采用的配对数值候选，当前不启动。
