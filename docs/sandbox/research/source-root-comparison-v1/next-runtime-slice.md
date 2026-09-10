# 下一最小运行片段：来源单格蒸发耗尽并真实继续干态

本次仅只读接口判断和已终态保存数据的标量分解。未执行 EOS、storage 构造、模型 check、求解器或测试；未改变原结果、政策或生产代码。当前原生共同正端点结果 SHA 为 `6aa52124fec977dfb39c65cac64538c87918fc8ed3cff82d3b3a5d5cd0474ae8`。本建议是原完整 Goal 的下一代码片段，不能替代其一维多格、原污泥反应、烧结冷却、公开三机制验证、来源应用与多代搜索要求。

## 应直接实现的运行行为

实现一个明确限定为 **N1、无跨面液流、唯一单调蒸发首根、一次事件** 的来源执行函数。输入实际 source adapter、正湿状态、精确起止时间和完整冻结政策；输出真实湿前段、终端账本、候选校正/模式、实际事件端点评价和至少一个时间增加的干态接受步。该函数负责一次有界事件片段，不再增加只有 comparison/proposal 的包装，也不复制整个自适应耗尽控制器。

执行链是：

1. 普通正湿前段仍调用 `integrate_exact`，必要时用已实现 `SourceApproachResult.trial.reference` 的真实末态继续；不能把 affine raw endpoint 代替已选择的 reference endpoint。用原步长、节点和整个调用的剩余资源。
2. 从真正求值的终端起点/合法中点构造 source panel。只在液体净消耗完全来自正蒸发、所有液面通量为零、所有气体竞争已排除时，绑定到现有蒸发 clock/writeback 算术。以实际面板积分和根证据建立 terminal state，不能把当前共同正端点直接归零。
3. 将候选状态传给 `ExactSourceColumn.with_depleted_cells(...,(0,))`，立即实际评价 dry 事件端点；再以候选 dry adapter 调用原 `integrate_exact` 到同一选定后续时刻。初始 dry Nl=0 是显式模式结果。这里不要调用仍要求全部初始库存严格正的 `SourcePrefixTrial`，也不要放松它的零库存保护。
4. 对独立终端/接近离散得到的完整“湿→事件→干”路径，比较真实事件端点以及同一 **事件后** 共同时刻的原时间、N/U/T/P 门槛，并从原始初态逐前缀审核普通账本与校正。先保存候选真实运行；全部数值门槛满足后才提交本次数值事件，失败保留候选而不改原可接受轨迹。

起步可用当前 N1 closed case 证明真实 dry 回调和时间推进；同一片段的有意义行为验收还需用现有 `ProgrammedSourceWetColumn` 的非零热边界，证明耗尽后真实 U/温度变化，并精确处理一个炉程节点。相间系数始终保留原非零值；不能用把系数设零、先造 dry 初态、仅评价 dry 单点来代替事件执行。

## 可直接复用的具体接口

| 责任 | 现有代码 | 接入边界 |
|---|---|---|
| 普通湿/干积分 | `exact_integration.integrate_exact`；`ExactSourceColumn.__call__/breakpoints` | N/U 与真实 kg 来源储能身份不变；传入全部精确节点 |
| 实际来源面板与终端库存/U | `build_source_panel`、`build_source_prefix`、`audit_source_prefixes` | 可使用末端 `numerical_boundary` 作为终端算术证据，不能改成已验证普通 trial；各分量/状态投影门槛全部保留 |
| 首根竞争 | `order_source_panel_roots`、`refine_first_root` | 原 4N 库存竞争和一个面板内排序/定位/修正的总细化预算；不能重置预算或重复求根冒充独立离散 |
| 蒸发根证据 | `ExactAffineSamples`、`ExactAffineEvidence`、`locate_exact_affine` 的已有算术 | 必须实际绑定三项液体速率、真实 gross evaporation、源/时间/库存及原政策；其单调和 dyadic-bin 合同不能用一般 source 根记录伪装。排序与兼容 clock 搜索应共用既有已耗轮数/余量；不能另给完整预算 |
| 保守微小校正 | `exact_affine_depletion.exact_depletion_writeback`、`DepletionRoundoffTotals` | 已接受 `ConservedState` 且不要求 mechanical_stretches；原 U 不变，只做有界液→汽成对数值校正、单列汽储存舍入。来源调用层仍须证明真实物理来源与面板一致 |
| 明确模式切换 | `ExactSourceColumn.with_depleted_cells` → `SourceWetColumn.with_depleted_cells` | 已要求原 wet 模式和精确零液体；operator identity 改变而 energy identity 保持。programmed wrapper 已支持同样切换 |
| 实际 dry 储能/相律 | `SourceWetStorage.evaluate/invert`、`RigidWaterGas` 的 `pure_gas_analytic_rounded`、`evaluate_wet_phase` | 零液体储能和无成核 dry 分支已经存在；相律仍查询真实平衡驱动，凝结驱动或未知域退出，不能静默忽略 |

旧 `execute_exact_terminal` 和 `integrate_exact_depletion` **不能直接调用**：前者要求 `ExactFreeWaterTransfer/WaterTransferEvaluation`，后者还要求真实机械伸长，比较/提交审核读取机械字段。`integrate_mixed_exact` 也严格限定 `WetPair`、两个 cell 和 mixed ledger/context。不要伪造 host、把固定干 kg 塞入 mol 数组或提供假 stretch 绕过这些边界。先完成上面的一个 source 事件运行函数；需要整段自适应事件编排时，再从既有 driver 提取实际共用的调度/资源骨架，保留旧入口并用适配操作接入，避免复制第二套 controller。

当前保存的 DepletionPolicy 含 `terminal_method='euler'`、无 ordered/nested 配置，它在前几阶段只用于门槛/根接近。新仿射终端执行必须明确声明相应运行方法；不能在旧冻结记录里偷偷换成 affine 或声称旧 mechanical ordered policy 已适配 source。新的运行配置应事前登记，原时间、N/U/T/P、校正及源误差门槛保持。

## 两个真正需要补的准入接口

**来源终端绑定和逐前缀校正审核。** 源终端 caller 应把实际 source 样本、共享积分、完整根竞争与现有蒸发 clock/writeback 联系起来；已有 writeback 只检查算术，并不证明来源。把校正加入从原始初态开始的 N/水/元素/质量账本，U 校正为零，舍入另列；不能在 mode change 或细路径起点重置累计预算。N1 无液面消除了 drainage 分配歧义；多格排水耗尽及同供体焓/干界面/再润湿仍是随后必需工作，不能把排水余量算成蒸发。

**来源 dry 完整温度区间压力界。** `enclose_source_inverse_pressure` 明确要求 Nl>0 且 liquid_pressure_pa=pressure_pa，不能拿它检查 dry 端点；仅把这个 guard 删除是错误的。dry 闭合已有 P=Ng RT/V。可为真实 source dry inverse 加一个严格绑定的分支，以实际 Ng/R、完整 `[T-eT,T+eT]`、原可用体积区间和舍入合同给出完整压力区间，再比较事件/干态共同端点。纯 `propagate_declared_pressure` 算术已支持 Nl=0，但其当前记录假设文字仍是 wet 液相；不要把该文字原样称为 dry 资格。共享数学可复用，dry 状态/资格绑定应明确。

## 当前 P 失败的实际原因及精度分配

仅解析两个已终态保存 JSON，未调用生产模块。精确 Fraction 分解脚本为 `pressure_budget_readonly.py`，完整结果见 `pressure-budget-readonly.json/log`。

| 已保存比较 | 名义 ΔP | 原报告 P 界 | 条件 P 界 | 可用体积贡献（两端） | fluid 原半径之和 | 完整 T 传播增量 |
|---|---:|---:|---:|---:|---:|---:|
| 上阶段 approach | 0 | 0.00222644981324 | 0.00238482373336 | 0.00202665158861 | 0.000199798224634 | 0.000158373920120 |
| 本阶段 common | 0 | 0.00273982704919 | 0.00274561991348 | 0.00202665251775 | 0.000713174531436 | 0.000005792864291 |

单位 Pa；原 P 门槛始终为 0.0001 Pa。本阶段体积贡献约 73.814%，T 传播仅 0.211%。即使假设 eT=0，原报告 P 界仍是门槛的约 27.4 倍。因此 **不存在仅靠更紧 inverse 就能达到本例原 P 门槛的分配**；新根时间比较通过也不改变这个结论。旧输出与拒绝必须保留。

一般分配应先计算 `B0=|ΔP_nominal|+rP_a+rP_b`，只有剩余 `BP=P_tol-B0>0` 时，才可事前分配 `L_a*eta_a+L_b*eta_b <= BP`，并要求每个真实逆解的 `(abs(RU)+epsilonU)/Cmin <= eta`。对应的温度/能量求解器容差只能收紧；还须先核对 epsilonU 和浮点分辨率的不可消除下限，不能承诺迭代更多一定可解。当前 common 的 BP<0，所以不应为了这个保存失败重跑更紧逆解。

要使原 P 比较有实际通过可能，最小下一证据选择是：

- 若新研究案例的虚拟设计几何能给出可核查、更紧的可用流体体积界，应从定义的精确几何/推导与浮点误差计算该界，并预登记为新案例。不得倒推一个恰好过关的误差值；也不得把数值几何误差冒充真实污泥体积不确定性，旧 1e-12 m3 结果不变。
- 若比较两端确实共享同一物理体积参数，可研究在 **同一个** 体积区间上对压力差作联合包络。其参数身份/相关性、全区间传播和其余独立 EOS/闭合误差都要证明并单列；不能因为名义 ΔP=0 就把两个体积半径直接抵消。新的更紧数学证据须预登记和独立核查，原保守报告仍保存，原 P 门槛不改。

这两项不是新增一层比较产品；应作为上述真实湿→干执行中事件/干态端点压力门槛的必要输入处理。

## 数值执行资格与材料资格，及最小验收

已有明确且自洽的制造几何、传输设置和声明数值误差包络，可以执行并接受 **条件数值湿→干运行**；无需等待真实材料适用性全部证明。新运行记录应明确自身的数值接受状态/条件，原 `source_certified=False`、`material_qualified=False` 和旧 comparison/pressure 的 `event_admitted=False` 保持原含义，不可把旧对象改标签。物理相变律/来源域检查与原数值门槛仍必须满足，不能用“仅数值”跳过它们。

本片段的完成证据应同时包括：实际正湿初值；由真实样本定位的唯一耗尽；原微小校正及每 prefix 水/元素/质量/U 合格；恰好一次模式变化；实际 dry 事件评价及之后至少一个接受步；带热边界时非零能量交换和有误差界的温度变化；独立终端路径在真实事件和事件后共同时刻的全部原门槛；取消/资源/凝结/气体先耗尽/修正超预算失败保留此前结果。先做便宜制造与独立解析验收，再按实测成本登记一次 native。当前 38 次来源求值已实测 107.148309 s，不能把更长事件路线无条件塞进旧预算或反复碰运气。

若压力等门槛仍不满足，完成候选执行和明确失败本身是代码进展，但不能报告本数值事件已准入；应针对已测得的主导误差解决。完整 Goal 保持 active，不因 N1 片段通过而删除后续全流程义务。
