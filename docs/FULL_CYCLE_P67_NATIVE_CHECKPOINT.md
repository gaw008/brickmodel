# P67 原生检查点接口与待采用的真实 heating 获取方案

本轮只完成静态生产接口；科学导入、构造、初态、unpack/rates/RHS/Jac/ODE/势/summary/fit/UQ全部0。三源AST语法解析完成，不代表动态运行或物理通过。旧750完整records未变，根758=144literature/614assumed/0measured；新增8项仅行政与未来提案。

生产CLI `--native-checkpoint` 使用完整当前nominal根，直接保存原solve_ivp端点完整y；`--checkpoint-dynamics FILE` 使用该文件的配置、源、t/y和机械参考，调用现有同事件动态与显式势投影。没有summary回拼或initial_state替代。普通full-cycle入口保持。

## 待采用的获取窗口

Research/src正常模块入口，`/Users/wanggaoying/Research/brickmodel-github/.venv/bin/python -B -m sludge_vme.cli full-cycle /Users/wanggaoying/Research/brickmodel-github/parameters.full_cycle.json --native-checkpoint --out /Users/wanggaoying/Research/brickmodel-github/runs/full-cycle/p68-nominal-heating-checkpoints`；参数/out在实际argv中均为绝对路径。1job/worker/attempt、1make_cycle/initial、3次真实solve_ivp；0state_dynamics/势/summary/predict/fit/UQ。当前未采用、未启动，P66窗口已关闭。

|阶段|累计端点 s|炉温端点 K|O2 / N2 / H2O / CO2 端点摩尔分率|本提案执行|
|---|---:|---:|---|---|
|drying_ramp|14400.0|383.15|0.209 / 0.775 / 0.015 / 0.001|是|
|drying|86400.0|383.15|0.209 / 0.775 / 0.015 / 0.001|是|
|heating|97200.0|673.15|0.1 / 0.78 / 0.1 / 0.02|是|
|reactions|115200.0|1073.15|0.04 / 0.8 / 0.12 / 0.04|否|
|sintering|126000.0|1223.15|0.06 / 0.81 / 0.1 / 0.03|否|
|hold|133200.0|1223.15|0.08 / 0.8 / 0.09 / 0.03|否|
|cooling|154800.0|298.15|0.209 / 0.775 / 0.015 / 0.001|否|
|cooling_hold|162000.0|298.15|0.209 / 0.775 / 0.015 / 0.001|否|

初始298.15K，原入口气氛及全部八段knots保留；炉温和气氛按原np.interp分段线性。12格/mode0/Ca0/directoff/time_scale1、配方与原开关保持，不能换P66的13格mode3/Ca1/directon。
BDF rtol1e-5、atol1e-7、max_step60s、complex-step1e-24、scale1全部沿原record；仅t_eval取每段原端点，不保存大轨迹。每段BDF历史重启，完整y与累计原点连续携带；0额外summary rates。
既有rhs_calls记录包含Jacobian里的RHS；新jacobian_calls记录生产调用，另保留实际sol.nfev/njev/nlu。当前156列/Jac只是源码推算，实际RHS/Jac数量未知。历史P34完整周期205.535595542s、7935nfev/324njev/58479RHS仅成本参考，不能冒充当前结果或承诺耗时。
新窗口建议300s launch→reap（含import/JSON），科学输出总4MiB，独立完整64MiB；失败/超时/超额关闭唯一窗口，无重试、续段、步长/参数搜索。case、共享完整source/config/context+3向量JSON、stdout/stderr全部按原文件字节计，不只选诊断字段。原八reserve27,262,976B不降，另留2,097,152B，合计29,360,128B；不能移用P66额度。

## 状态和上下文

nominal向量长275：字段[0,132)，四gas logs[132,180)，七逐格反应累计[180,264)，边界in[264,268)/out[268,272)，外压功272，熵production273/exchange274。热和携带能量为field7/8，全部保留signed与−0.0。反应还原乘cell_chemical_scale；边界乘nscale；热/work乘escale；熵逐项乘escale/Tr。

保存完整根records、所有8段程序、50源原文、源祖先版本、几何/初始inventory、b0/vp0/es0、反应与气体尺度、nscale/escale/Tr、初始prestress/elastic strain/dry fraction/quartz reference、phase0和liquid_reference。loader从saved config构造并恢复saved references，不调用initial_state；source原文不同明确报错，不混版本，不用SHA。完整layout/context表及实际源码身份说明在JSON。

## 物理适用范围与限制

历史P34 heating脱羟累计0.0031031435281507207mol说明获取方向，旧worker无完整y不能直接使用。heating673.15K可能产生非零metakaolin N，但远低1223.15K相代理参数、width40K、Ea180000J/mol，q/相力学功率可能极弱；非零载体不等于充分液相激活，不承诺PASS。

炉温低于portlandite700K热力来源上限，仍需之后检查实际单元T；完整caloric/viscosity/binary source域已列JSON。gas caloric298.15–2500K（CO2到2200），calcite到1200、lime到1800、OH到700；源外延续保持assumed。后五段不执行；峰温1223.15K会跨OH700/calcite1200/H2O稀气黏度1173.15K域。syntheticdirect290–350K通道原nominal absent，不扩到高温。

之后读取同一检查点作1native-event/15value动态投影仍只是独立候选，需按真实carrier、q与源域证据另行采用；本提案不自动执行。加载/NumPyJSON/完整端点动态读回尚未验证。

名义余水0.1358920787402553%>0.1%、CaO零预算nullfalse及所有旧物理/加密/资源/入口失败保持；0measured/wholefalse。Git、Drive元数据、实际恢复和历史20GB/GitHub容量分别判断，恢复0。

当前静态完整gate=37563636/67108864B；最终完整源/根/冻结/原与暂存blob/一档案/收据自身见 `runs/full-cycle/p67-native-checkpoint-static/final-delivery-state.json`。
