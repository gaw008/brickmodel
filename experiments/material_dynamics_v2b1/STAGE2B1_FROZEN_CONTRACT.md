# 材料设计 v2：第二阶段B1冻结合同

状态：Manager冻结的研究原型实施范围；不是生产配方、完整烧结世界模型、独立审核通过或工厂适用性批准。

## 1. 决策与非目标

首个可执行动态增量是“等温、固定几何/开孔率、C(s)+O2→CO2、有限供氧的1D反应—输运诊断器”。用无量纲参数隔离氧库存、内部输运、表面膜传递、反应负荷的影响；输出机制对照而非原污泥最佳配比。选择这个窄域是因为公开参数仍存在材料、气氛、单位与高温迁移缺口，不是声称已掌握完整污泥动力学。

明确延后：自由水/脱羟/热解/CO及其他挥发物、多组分DGM/压差流、非等温传热与反应热、变形/开闭孔、液相黏度、真实强度、黑心分类、排放合规、配方优化、窑车速度及生产控制。所有延后量输出not_modelled/unknown，不填零作为物理预测。等温意味着外部恒温约束，**不声称总能量闭合**，不额外显示假能量守恒通过。这里也不输出压力诊断。

第一阶段原型的作用：辨别“已消耗足够可氧化库存”与“缺氧暂时停反应”，以及同一假设材料在不同供氧/尺度阻力下的相对变化。不会用95%阈值冒充工厂燃尽或安全标准。

## 2. 空间、物种、参数约定

- 对称半板 ξ∈[0,1]，ξ=0为无通量芯部，ξ=1为外表面。固定截面积、均匀开孔率ε_o、半厚L。仅适用于两面对称供气的代表壁；不处理被封堵的单面、孔道不均匀气氛或整砖外形。
- C仅表示本模型明确声明的可氧化固体碳库存，**不是TG残渣、LOI或全部原污泥有机质**。只使用C/O元素域；N2为不参与反应的恒定背景，不建其他元素。
- O2和CO2使用同一个常数有效扩散系数。仅在等温、等摩尔C+O2→CO2交换的简化域成立；命名为approximate_equimolar_transport，不能称完整多组分输运或来源S02全模型复现。
- D_eff按总截面积定义，c按孔内体积定义。时间尺度 τ_D=ε_o L²/D_eff；无量纲τ=t/τ_D。不是L²/D_eff后又在PDE重复处理ε。
- u=c_O2/c_*，v=c_CO2/c_*，f=C_s/C_s0；c_*>0为参考O2孔浓度，C_s0为初始固体碳摩尔浓度（每总体积）。
- Γ=C_s0/(ε_o c_*)>0为初始碳与孔内参考氧的库存比。
- K=k τ_D≥0为本诊断闭合的无量纲反应速率参数。反应形式k C_s u是明确假设，不把k叫已识别本征常数。氧库存Damköhler组合ΓK为派生量，不独立重复优化。
- Bi=h_m L/D_eff≥0；h_m按总外表面积的气体膜传递速度定义。
- 有限外部库ρ=V_res/(ε_o A L)>0是分配给这个半板的储气体积比；它是封闭有限库，既无补气也无排放。
- 不提供默认的秒数或工厂材料参数转换。参数表只是文献候选索引，不自动喂入配置。物理量映射需要另外确认ε_o、D_eff、L及其联合材料/温区，不在本增量默默完成。

## 3. 冻结方程与边界

局部反应q=Γ K f u。1D场方程：

    ∂u/∂τ = ∂²u/∂ξ² − q
    ∂v/∂τ = ∂²v/∂ξ² + q
    ∂f/∂τ = −q/Γ = −K f u

芯部：∂ξu=∂ξv=0。

表面，向外为正：J_u=−∂ξu=Bi(u_s−u_ext)，J_v=−∂ξv=Bi(v_s−v_ext)。两种气体膜系数相同，不能任意打破本近似的等摩尔交换域。

三种边界模式：
1. infinite：u_ext=1,v_ext=0固定；外库无限，但膜传递有限，不称“有限氧总量”。
2. finite：积分du_res/dτ=J_u/ρ，dv_res/dτ=J_v/ρ；反向通量必须等量更新。初始u_res=1,v_res=0，不按每步重置外库。
3. sealed：J_u=J_v=0，无外库状态。

所有演示场初始u=1,v=0,f=1。无反应解析扩散测试可以使用u=0,v=1初场及显式Dirichlet极限，但该极限单独命名，不混进默认finite/infinite膜传递模型。

不可用“每步把负库存clip为0”维持守恒。采用保正/限制时间步或库存耗尽事件；数值问题明确失败，不将其当物理不可行。

## 4. 必须成立的预算与独立核验

- 等摩尔气体：局部u+v应保持初始常数（上述共同系数/一致边界域）；有限库u_res+v_res同理。
- 碳库存：C_body=∫(Γf+v)dξ；氧分子当量O_body=∫(u+v)dξ。有限库加ρv_res和ρ(u_res+v_res)。sealed/finite的总量守恒，infinite模式按实际净边界通量审计。
- 固体C摩尔消耗与CO2生成等量，O2消耗也等量；名义摩尔质量C=12、O2=32、CO2=44仅作这一简化计量检查，亦可由一致原子量生成。不得再增加独立总失重源。
- finite模式的纯计量上界：最大可燃尽分数≤min(1,(1+ρ)/Γ)；sealed模式≤min(1,1/Γ)。这是本模型初始库存下的上界，不是现实污泥合格界限。
- Audit必须从导出库存和边界通量重建预算，不读取solver给出的residual当真值；独立解析/半解析例子验证离散求解，不造新的大型hash/完整语义重放框架。
- 数值守恒采用相对初始非零库存和绝对尺度一致的固定容差，默认1e−6；配置中不得允许用户artifact无限放大容差。若达不到，修算法或诚实失败，不用模型不确定性掩盖数值误差。

## 5. 默认12个研究情景

所有参数是数值机制实验，不是测量值或文献拟合材料。共同默认K=1,Γ=2,Bi=1,mode=infinite,τ_end=20,n_cells=15；每行只覆盖下列变化：

- base：无覆盖。
- reaction_slow：K=0.1。
- reaction_fast：K=10。
- carbon_low：Γ=0.25。
- carbon_high：Γ=8。
- film_weak：Bi=0.1。
- film_strong：Bi=10。
- sealed：mode=sealed。
- finite_small：mode=finite,ρ=0.25。
- finite_medium：mode=finite,ρ=1。
- finite_large：mode=finite,ρ=10。
- no_reaction：K=0。

base/reaction_fast/finite_small另做7/15/31格和时间步收敛检查；不在12情景上无限扩展网格搜索。网格差异以剩余碳、芯部O2和事件时间为指标，事件未发生不可拿null当0计算误差。至少一组解析无反应扩散解、密闭充分供氧/缺氧计量极限、有限外库和无限外库差异必须实际跑出。

## 6. 诊断事件与诚实状态

输出平均和最大局部剩余碳f、芯/表u、CO2产生/净排出及体内/外库库存。采用95%/99%**数值诊断完成阈值**：平均剩余碳≤0.05/0.01时可记录平均完成时间，同时另记录最大局部剩余碳是否也达到阈值；不得仅用均值掩盖核心残碳。正文必须说明两阈值非生产标准。

`t_burn95/t_burn99`不得由瞬时速率变小触发。`t_gen`仅代表本模型CO2源，不能当全部原污泥气体；finite模式可反向交换，产气结束不代表净排出结束。`t_close`、压力、温度场、强度、窑速均固定not_modelled。

状态：reached_diagnostic_threshold / not_reached_by_horizon / oxygen_budget_limited / numerical_failure。氧库存上界足以排除阈值时可给oxygen_budget_limited；这也不是“材料物理不可能”。不输出validated_recipe或产品feasible。

## 7. 文件/API命名（实现者不得另选）

仅新增独立worktree内`experiments/material_dynamics_v2b1/`，CLI入口`run.py`，纯离线Python实现；可拆model.py/solver.py/audit.py/plots.py，不改既有核心solver/verifier或Stage1代码。

配置JSON：schema_version,scope,scenario_id,K,Gamma,Bi,boundary_mode,reservoir_ratio,n_cells,tau_end,diagnostic_thresholds。scope必须为dimensionless_reaction_transport_benchmark；拒绝缺失/负/NaN/Inf/未知字段/不一致boundary参数。sealed模式无reservoir；finite必须正ρ。阈值固定[0.95,0.99]，不与数值容差混用。

结果：summary.json（scope/status/全部假设/未建模量/时间与预算）、timeseries.csv（scenario_id,tau,u_core,u_surface,carbon_mean,carbon_max,co2_body,co2_generated,co2_net_out,u_res,v_res）、profiles.csv（scenario_id,tau,xi,u,v,f）、audit.json、两张浅色中文SVG（芯/表供氧与剩余碳轨迹；12情景诊断对照）、DIAGNOSTIC_REPORT.md、verification.json。表中不存在的外库值留空，不伪造0；完整文献候选CSV只读参考。

图表均写清“无量纲机制情景，非工厂配方/烧成时长预测”；不平滑虚构连续可行域。报告必须解释至少一个氧不足而反应近停、仍有碳残余的实际计算案例，并展示源库存/预算上界一致；另展示有充分氧时的对照。真实动态结果由实现者执行生成，本文没有预填任何模拟结果。

## 8. 验收与资源

- 固定量纲/归一化、C/O化学计量、边界符号、计量上界、保正、无反应/零通量、有限库不重置、burnout不误判、解析扩散、空间/时间收敛、配置拒绝、缺失事件、导出重算、实际12情景覆盖，均有focused tests及真实命令输出。
- 快反应/慢输运的梯度是待计算结果，不用预设图形冒充运行。修改一个导出库存或移除边界通量行时audit必须拒绝。
- 默认演示预算：单worker/单线程、总演示目标不超过180秒，超预算返回partial/timeout而不隐藏；峰值内存目标512MB以内。不运行旧full suite、不安装大型依赖。优先标准库保正有限体积；若需已有专用科学venv可只读使用，不改Hermes共享venv。
- 研究代码必须本地提交并接受独立Safety审核；不push/merge/publish，不创建OCI或收费资源，不调用付费API/Anthropic，不连接设备或生产控制。
- Stage1工作树与主仓库保持不变。新独立worktree为`/home/ubuntu/sludge-brick-dynamics-v2b1`，branch `research/material-dynamics-v2b1`，基线2620afe40faaf592fbb42b39e3a6a6a351009ad8。
- 独立Safety子卡同时依赖本实现与现有Stage1审核`t_c6aa7e5f`（其自身受OAuth前提约束）；实现可在隔离研究范围推进，但不能自我批准，不绕过审核。
- 完成时交付可复跑脚本、测试、输入情景、报告、原始轨迹、验证日志。**所有复验所需支持文件需进入本地commit或声明的压缩包；不能只写scratch路径然后被清理。**原始文献全文不作为聊天附件，保留来源及必要短引文/定位。

## 已创建的执行链

- 实现：`t_2c9cc3d9`，依赖已完成的证据研究`t_f456bbd3`。
- 独立审核：`t_c787a990`，同时依赖实现`t_2c9cc3d9`和既有Stage1审核`t_c6aa7e5f`。
- 现有OAuth/Stage1审批链保持不变；本合同存在不代表实现或审核已经完成。

## 9. 第二阶段A核验边界

Manager已读取四个永久附件并核对SHA256与参数表结构：102行=91 reported+2 derived+9 unknown；原7组检查脚本不在永久附件，scratch已清理，因此不声称Manager复跑过这7组。Manager另通过Europe PMC原始XML核对S02的0.011 cm²/s及O2拟合到500°C边界。[1] 从持久原文缓存核读了S09 Table5与S11制片/升温/保温方法。[2][3] reported参数不自动转成本合同默认值。

候选反应方程已做独立代数检查（contract-algebra-check.json），C/O/名义质量守恒为零残差；该检查不是动态模型运行或材料验证。B1完成和审核后再决定是否加入非等温、多步反应以及开闭孔/收缩；这些后续增量本合同未授权实现。

## Sources

[1] https://www.mdpi.com/1996-1944/14/17/4942
[2] https://www.mdpi.com/1996-1073/17/21/5382/htm
[3] https://orbit.dtu.dk/files/418782101/1-s2.0-S2214509525011854-main.pdf
