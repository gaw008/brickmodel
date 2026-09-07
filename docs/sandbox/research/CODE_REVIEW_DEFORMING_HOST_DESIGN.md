# Prescribed deforming host 设计独立审查

初审状态：REQUEST CHANGES（一个具体构造合同缺口；不是否定受控气腔物理路线）。只读设计、geometry、GasHeatModel、SolidFluidStorage、共享面与WORLD_SPEC，未调用EOS或改动源码/tests。本报告不将设计验证称实际实现完成，也未独立复查设计引用的NASA网页全文。

初审设计hash：`5b7fec2a62d5568032ae1222a0f683c12c58304eb6d78719aa744e57c69321ce`。
接口快照：geometry.py `384d35d67ed7aa043991d69e795169bafddb8e1466c1d1f0b072521c10a72312`；gas_heat_model.py `6019ac11662e8cb79ce75d0ed786c753cfe419904f74901eee750e45737cdbd9`；solid_fluid_storage.py `a592373dcc365ee121926eee2330ccad93b1d300822ab0eebcd7be2b1f45508c`。

## 必须补齐的具体合同

设计第三节目前只要求base reference gas volumes等于reference cell volumes，未明确同时检查base面面积和逐格宽度。这不足以保证第四个zero-deformation gate，也会改变系数对应的半格传输路径。

可直接构造反例：reference面积A0、宽度dX；合法旧GasHeatModel采用面积2A0、宽度dX/2、gas volume仍A0*dX。仅体积检查通过，但lambda=1时新host把面积/宽度改回A0/dX，即使机械功0，导热/扩散几何因子A/dx变为旧值1/4，因此Rates无法与旧host相同。

要求补充constructor对cell数、逐格width、共同face_area和fullgas volume全部与ReferenceSlab初始几何相容的校验；参考面/中心位置由该几何确定。若允许浮点容差，须事先明确其量纲/上限与zero-motion判据，不能用大相对容差吞掉几何变动；至少新增“same V but different A,width”拒绝回归。没有必要修改旧GasHeatModel对一般gas_volume≤bulk的支持，严格全气腔约束属于新wrapper。

## 已通过的物理与接口判断

- 本设计明确每格压力匹配的外部驱动腔体，而非把非均匀砖的孔压当整体外载。用实际N/U解码T、当前V得到p，再向同一Rates加−pVdot，压缩正功/膨胀负功符合该定义；不需要求动量仅限准静态理想执行机构假设。不能把这些执行机构在真实湿砖中不存在的能量，偷换成已证明可忽略。
- 共享物种焓运输包含流动功；相对于移动隔板的流量与−pVdot是两种不同贡献。设计明确不再添加同一流的pQ，也不以移动网格给库存额外加/减mol，因而没有流动功双计。现face_exchange没有lab速度输入，新增wrapper必须把固定系数的含义明确限定为隔板相对流的制造/理想网络关系，不能悄悄解释成真实自由气体运动。
- 几何公式同时含normal和公共tangential伸长；Vdot=A*dx_dot+A_dot*dx，不漏掉侧面膨缩。单个内部face只使用公共实际面积，当前两侧半格宽度进入同一交换，符合既有单面一次记账。不同cell压力下内部执行机构净功不强制抵消；只有共同p情况下，内部法向边界运动的功贡献才相消。
- 当前GasHeatModel本身已有真实N/U→T并生成GasState，但__call__仅返回Rates；提出的evaluate返回既已计算diagnostics、__call__委托rates是可实现的小兼容改动。必须先调用原base._check_state再创建瞬时view，以保留旧可变thermochemistry wrapper的signature防护，不能通过clone重置signature掩盖篡改。现body power确为0，故首版把整个cell_power字段保留给机械功有明确边界。
- 当前ReferenceSlab.deform返回数组虽writeable=False仍可重新置位；新snapshot需bytes-backed不可变副本，设计已明确。原geometry只检查volumes>0与有限值，没有充分拒绝face位置浮点合并；设计已将其作为新provider显式错误，不能假设旧工具自动完成。
- C1 smoothstep节点速度0适配现积分器同一节点无左右侧值的接口；只传breakpoints不能支持速度跳跃。每stage从原参考按绝对时间采样，避免逐步累积几何误差；几何数值范围检查与实际实验误差分开。
- 绝热constant-Cp oracle的T/V与P/V关系、闭合N不变、机械功符号、同体积返回、三档实际步长收敛门槛能抓主要功符号/几何错配。变量Cp不能沿用constant gamma；设计已明示。双格必须额外逐格和系统账本审计，因为全局能量守恒本身不能证明压力/供体焓正确。

## 对湿固体Goal的可复用性及未完成范围

这条路线可复用的是具有身份的MotionSnapshot（currentV/A/width与导数/共享面）、逐stage一致几何装配、已接受机械功账本和失效策略。它不是用气腔替代湿固体最终目标；设计第四/六节保留具体后续接口缺口，因此作为有界前置验证没有跑偏。

现SolidFluidStorage每次以当前固定bulk减Ns*vs计算available，并在冻结V下反解整体thermal U；原state.energy_scope明确不含strain/interface。要接真实湿固体，至少还需：当前bulk/闭孔/固相体积与可达孔隙的关系，真实骨架应力/运动合同，弹性/界面/黏性耗散的储能与热分配，以及随当前volume变化的压力/反解误差预算。固定V下Cclosed可用于该瞬时V的U→T反解，但不是沿V(t)轨迹的总dU/dT。

规定液气腔体的外功也不能只取−p*dVgas：液相本身体积随T/P变化，外部控制体积率与气孔率不是同一量。自由烧结更不能从dL/L0曲线直接推断三方向应变或J=lambda³，也不能把气孔压当完整骨架应力。Areias有限单向长度点仅为条件外部验证候选，不能提供未知机械能或动力学准入。以上是后续湿固体/自由烧结仍必须完成的范围，不作为本有界气腔slice已解决事项。

本设计获准实施前只需补齐上述几何reference合同；其余列项是设计已写明、实现必须保持的条件。没有发现需要改写整体方案的功/焓/共享面矛盾。

## 修订闭合

最终状态：APPROVE（设计准入到所限定的受控气腔实现与测试，不是已实现模型批准）。已实际重新读取最终设计，SHA256 `652d5af0b356466ab5b426215e44638d8f849c71b412176a7e7d6d2928ff0e59`。

第三节新增完整reference绑定：cellcount精确相等、面积/逐格宽度/逐格gas volume分别一致；只允许显式零相对容差与至多2*max(双方ULP)绝对舍入容差，并记录匹配政策/残差。第五节新增same-volume但A=2A0,width=dX/2拒绝回归以及count/孤立width/volume错配拒绝。该变更解决初审唯一阻断项，保留首审历史供追查。

实现时，接受2ULP几何舍入差不能再宣称任意这种输入下Rates逐位相同；完全相同参考输入应零形变等价，允许ULP差的输入应采用事前既有误差门槛并保留匹配残差。除此之外，不需改变设计的功/焓/共享面方案。原Goal的湿固体机械储能、自由烧结、裂纹/应力与材料来源准入仍未解决且必须继续完成。
