# P70 原生检查点单阶段续算静态接口

P70 原生单阶段续算生产模块已静态实现，未运行模型。旧50源码/loader普通文本与bytes保持，新增full_cycle_continue.py以已有strictload承接P68完整case/context/t/y并调用原SciPy BDF、native rhs/jac及绝对时间全9knots。输出配置/source有旧50+新producer51份，既有loader按51份严格匹配；不绕身份、不重复前三段、不回initial、不新物理。实际load/ctor/initial/RHS/Jac/ODE/potential/summary/predict/fit/UQ均0，仅新模块AST与源码静态读取。758完整records未变，144literature/614assumed/0measured，criterionNA/wholefalse。后续原reactions97200→115200s、炉温673.15→1073.15K、rtol1e-5/atol1e-7/maxstep60s、独立300s/4MiB/64MiB只登记提案；须新内部采用和freshgate再数值。700K hydroxide越域沿旧assumed continuation，不授source/materialPASS或承诺phase激活。详见docs/FULL_CYCLE_P70_NATIVE_CONTINUATION.json/md。

新增生产入口（cwd=Research/src）：`/Users/wanggaoying/Research/brickmodel-github/.venv/bin/python -B -m sludge_vme.models.full_cycle_continue /Users/wanggaoying/Research/brickmodel-github/parameters.full_cycle.json --checkpoint /Users/wanggaoying/Research/brickmodel-github/runs/full-cycle/p68-nominal-heating-checkpoints/native-checkpoints.json --out /Users/wanggaoying/Research/brickmodel-github/runs/full-cycle/p71-native-reactions-continuation`。Python接口为`continue_native_endpoint(parameters, checkpoint, out)`。本轮没有调用这两个入口。

现`integrate_until`会创建初态，故新模块直接调用该生产模块已导入的同一个SciPy solve_ivp，与相同model.rhs/jacobian及同套参数。载入器先完整核对旧50source，再构造一次并恢复保存context/scales/references。当前根仅提供行政producer合同；物理数值依旧使用bundle758records。累计槽原点、native气体logs及其initialgas尺度、q/eta/Ca/OH和机械reference不重构、不重置。

新端点source_paths为保存源码与本producer的有序并集51；完整ordinary source_text随端点保存，既有loader用该配置获取全部51文本并严格相等比较。输入50记录没有改写，旧loader没有修改，不能忽略新模块变化来加载输出。此接口是静态接线，未来51身份的实际load尚未执行。

拟继续原reactions一段，实际t97200→原t115200s，freshBDF历史但完整状态连续；只保新端点和原始输入origin，不采中间轨迹、不跑summary/势/反演。1load/1ctor/0initial/1solve；RHS/Jac/nfev/njev/nlu未知，未来实际记录，不能用估计顶替。窗口300s含JSON/reap，case/checkpoint/stdout/stderr全部4MiB；全必要input/source/blob/freezes/报告/行政/self/archive与原8reserve+2MiB共64MiB。失败回收关闭无重试。

|绝对时间 s|炉温 K|O2|N2|H2O|CO2|
|---:|---:|---:|---:|---:|---:|
|0.0|298.15|0.209|0.78|0.01|0.001|
|14400.0|383.15|0.209|0.775|0.015|0.001|
|86400.0|383.15|0.209|0.775|0.015|0.001|
|97200.0|673.15|0.1|0.78|0.1|0.02|
|115200.0|1073.15|0.04000000000000001|0.8|0.12|0.04|
|126000.0|1223.15|0.06|0.81|0.1|0.03|
|133200.0|1223.15|0.07999999999999999|0.8|0.09|0.03|
|154800.0|298.15|0.209|0.775|0.015|0.001|
|162000.0|298.15|0.209|0.775|0.015|0.001|

完整gas knots含原浮点0.04000000000000001/0.07999999999999999，未改成显示四舍五入值。插值复用原绝对时间函数和全部8段，无局部时间重基/新边界。

实际静态新模块AST已解析，50份source普通text与UTF-8 bytes相等，Git scoped diff空；没有导入模型，没有新增或运行测试/fixture/assert/probe/SHA。参数records全保持，本轮仅行政合同和报告变化。真实静态elapsed及preparation-to-report wall在JSON，不能称计算时长。

下一reactions炉温越700K hydroxide来源域；实际温度域尚未执行，沿原显式assumed解析外推，不调整方程掩盖负值、不扩direct290–350K。P69非零载体/q导数和极弱phase功率不证明充分耦合。原干燥余水0.1358920787402553%>0.1%、CaOnullfalse及旧失败保留，完整8stage物理/加密/比较反演与材料0measured仍未完成。

P70没有数值窗口或数值产物，后续routine有界研发沿人类持续授权另内部采用。Git/原Drive必要增量/实际恢复/历史容量分别判；restore0，不删除历史或独有数据。最终完整实际预算与交付见runs/full-cycle/p70-native-continuation-static/final-delivery-state.json。
