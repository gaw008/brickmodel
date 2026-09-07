# 初始湿态到高温的独立主机验证（运行前登记）

冻结输入：同一 SolidFluidHeat 的初始库存顺序为 (solid,H2Ogas,H2Oliquid,tracer)，数值 (2,1e-8,1e-6,.001) mol，300 K。水采用 source-gated JoinedWaterVapor，低锚声明数值误差1e-3 J/mol、host gas u预算.002 J/mol，未称物性精度。固相为制造常Cp50 J/(mol K)、v1e-6 m³/mol；载气制造Cp30。原完整储能反解门槛1e-6 J/1e-6 K。流体温度envelope显式295..600K；wet括号295..310K，只有实际Nl=0选择dry295..600K，不改EOS域。压力范围沿原Joined夹具1e4..1e7 Pa，无液仍真实闭合压力。

边界：虚拟恒炉温1000K、0..600s；制造k=.1 W/(m K)、h=10 W/(m² K)、面积.01 m²、末格宽.01m，半格串联G=1/15 W/K；emissivity0。显式全气氛与总压保留，但kperm=0/D=0使全部气体输运关闭；不是用外部水补库存。K=1e-6 mol/(s Pa)全程不变，初始existing_liquid，事件器真实耗尽后模式切换。dry_policy显式metastable_no_nucleation；500K以上peq未知，绝不解释为实际不凝结或模型证明没有成核。

事前验收：必须完成600s、恰好一真实事件、初态Nl>0与终态Nl=0；K/同源provider/制造门禁不变，事件后保留完整U与气库存、固相和载气逐位不变。每状态总水误差≤1e-12mol、累计已表示面能量/功账本残差≤1e-7J；继承事件器时间1e-7s、公共时刻N1e-10mol/U1e-6J/T1e-5K/P1Pa比较及原roundoff合同，不放宽。最终T扣逆解界仍>500K，实际表面热流=(1000−T)/15误差≤1e-7W，最后化学诊断为condensation_drive_unknown。

独立参考：以实际已接受事件时刻和事件U作条件初值，使用原Shomate系数的独立Decimal Cp积分与已定义500K低水焓锚，反解事件T；低段Cp来自原独立IdealWaterVapor，高段直接原源系数，加入显式制造固/载气Cv。数值积分dt=15*Cclosed(T)/(1000−T)dT并跨500分段，独立求600s终温；候选终温绝对差≤5e-4K。它验证干段能量/热传递演化，**不独立认证耗尽时间**；耗尽时间仍为事件细化误差指标。不能用约531K估算代替运行结果。

成本政策：原普通rtol1e-7/Natol1e-12mol/Uatol1e-8J，initial1/1024s、maxstep2s，由误差控制自适应；最大20000试探panel/240s全运行预算。预算失败保存实际前缀，不以静默扩预算或降门槛声称完成。初始态测试可独立轻跑；完整600s运行等待root双格任务结束与独立预审。runner接受新输出路径，拒覆盖，保存全部轨迹、ledger、事件/roundoff/细化诊断与前后源/testhash；失败也保存。此案例未加入反应与液体空间通量，不能替代root的多格耦合验证。

运行前审核增补（未重跑积分）：要求 states/times/steps 长度一致、时间严格递增、每step端点对应保存times、event terminal_panel严格对象身份对应。逐液/汽列独立Fraction累计faceL−faceR+reaction，在实际terminal步单独加液−δ、汽+δ+实际storage roundoff；核成对等反、实际vapafter−before与record、signed/absolute/correction/eventcount总计及最终cumulative数组精确一致。每步/每prefix库存残差≤既有1e-12mol；逐步及前缀U对同一heat/work账本≤1e-7J。每状态水/O≤1e-12mol、H≤2e-12mol、质量≤1e-13kg；事件后每保存态Nl严格0。上述Fraction精确于已表示ledger字段，不恢复浮点stage舍入前数学值。原物理/数值门槛与运行预算不变。

零修正路径同样合法：若terminal恰好已表示Nl=0，event.correction可为None，此时要求corrections为空、roundoff总计全0、液汽累计相加0；仅非None时做成对/实际写回检查。不能以强制存在非零数值修正的测试拒绝合法事件。
