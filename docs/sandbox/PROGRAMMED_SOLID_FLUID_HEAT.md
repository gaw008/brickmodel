# 显式固液气储能主机的动态炉气边界

实施前合同：ProgrammedSolidFluidHeat仅包SolidFluidHeat，不内置相变；WaterPhaseTransfer由另一模块显式外包。每trial调用base.evaluate一次保留整体storage inverse，以实际外格T/P/Vgas与BoundaryProgram完整reservoir组装gas面mol和同源供体h；用真实面积和末半格导热串联对流/辐射代数平衡，炉温不是表面温度或芯温。拒已有外reservoir/表面条件。结果保留base_evaluation及storage_states/storage_inverses/gas_states代理，暴露实际breakpoints_s。制造固体/几何/气体/输运/film门禁保持，程序虚拟设计不冒称实测。

预登记：制造单格固定固体/气体、传质关闭、零辐射、线性升温—保温—冷却程序真实integrate；节点与末端对独立线性ODE解析温度绝对1e-6K，外能量账本1e-7J。纯对流串联解析温度/热流分别1e-7K/1e-8W；含辐射独立scipy根1e-7K；开边界压力/组成改变时检查真实入/出流方向及供体h而非u，保留固/液零面通量。域外、重复边界、制造门禁、完整气体排序、不重复decode均测试。仅新增有意义的局部/集成验证，单运行预算90s。

最终接口公开 `base_model`（原SolidFluidHeat）、`transport`与`inventory_layout`代理、完整库存`species_order`和纯气`gas_species_order`，这两个顺序不能混用。`ProgrammedSolidFluidEvaluation.base_evaluation`保留原结果，三个storage/gas代理直接返回原tuple对象。每次trial不创建伪fluid状态，不将固体总U传旧fluid decoder；先完成一次整体base.evaluate，再叠加外面gas mol/h和向内表面热的负值，内部面及原reaction/cellpower数组保持原账本。WaterPhaseTransfer在外层作显式第三主机适配，属于其模块；本模块不另藏一套可选相变调用。

表面求解保留既有ProgrammedGasHeat已审核的半格对流/辐射单调根算法，局部函数按新主机的transport几何/导热系数取值。由于本轮不改既有模块，共享公式在新模块局部实现；对照解析与独立brentq验证，后续抽公共纯函数应另审而非绕类型调用旧主机方法。G=A*k/(dx/2)、H=A*h；无辐射时q=GH/(G+H)*(Tg−Tc)。k=0时进入cell的导热为零，外gas携入焓仍存在；h=emissivity=0时无外热。表面残差只是给定当次解码温度的数值代数闭合，不包含整体反解温度或物性误差。

外气体reservoir使用程序当时Tg/P/全部species摩尔组成，压力/气氛真实影响传输。外face供体焓来自与储能相同的gas_phases：入流用炉气Tg，出流用cellT，绝不以表面Ts或u替代；通量符号沿原face向外约定。完整程序排序必须与气体列匹配。程序只能连续分段，调用integrate时显式传`breakpoints_s=op.breakpoints_s(start,end)`，不自动发现节点、不支持同刻跃变或域外外推。

来源记录汇聚原整体储能/几何/transport、程序身份及film系数身份。制造探测逐一检查film、transport、solid物性、gas物性、geometry，虚拟程序或几何保持设计来源，不能据此声称材料准入。没有默认h、发射率或sigma；`material_qualified`始终false。原输运外reservoir或表面条件已存在就拒绝，防止重复边界。错误沿已有物性域/数值失败分类，时间超程序范围是DomainExit。

实际验证：测试先于新模块，首个收集因模块不存在失败；首版4项通过，真实积分测试发现测试调用误用了knot_times_s，修为既有breakpoints_s（同时账本读face_energy_j）。未修改积分器或物理门槛。5项通过0.65s后，增加k=0仍携带气焓、完整气体顺序/来源要求和真实气氛变化入流积分，总8项通过0.84s。恒温程序段、升温/降温段节点温度对独立解析解绝对1e-6K；另一条实际入流程序逐步气体库存与外面焓账本分别1e-12mol/1e-7J，实际压力随库存变化。单trial计数验证base只做一次完整inverse。

现阶段边界是施加给固定几何固液气中间态的虚拟/有据程序，不包含窑炉流场解、固体相变/反应/收缩、有效参数演变或成品性能。少量制造程序通过不代表真实窑炉参数或湿砖高温全程已经准入。
