# 显式逐格液界面模式

实施前合同：interface_modes=None默认全existing_liquid，保持旧活跃K零液退出。新模式depleted_no_nucleation仅允许实际Nl=0，K/来源不改，base完整主机继续evaluate与保留逆解；仅本界面交换源为0，不把它称平衡。dry_policy=strict默认，原chemical域内假想界面计算有凝结需求则拒绝；无法查询（包括高温）则unknown/unsupported。metastable_no_nucleation是显式研究选择，可在其余活动物性域内继续，记录诊断且不虚构实际液μ/peq。数值/来源错误不被改为unknown吞掉。

预登记：默认wet低温真实换相与无液旧拒绝；显式dry低温亚饱和正常、超饱和strict拒绝/亚稳保留零源；Joined水汽高于500K的真实solid/fluid主机strict unknown拒绝、亚稳实际升温积分保留水汽与总U账本1e-7J。base液面/反应净生产液体则unsupported再出现；invalid模式/错误长度/非零液切换/变更K检查。仅模式测试，不能称液耗尽事件已实现。

实现 API：构造器保留默认 None 声明，`interfaces` 按当前主机格数生成全 existing 元组；显式 modes 则冻结为 tuple 并严格检查格数；`interfaces`、`liquid_index`、`water_vapor_index` 是公开只读属性。`with_depleted_cells(state, cell_indices)` 仅验证状态形状、索引唯一/范围与所选液库存严格等于 0，返回 replace 后的新对象，不改原对象或任何库存。这是调用者显式授权的模式切换，**不认证耗尽事件位置、积分精度或实际液界面消失机制**。事件定位积分仍由独立模块实现。

干态保留一次真实 base evaluate 及其全部储能、液面、反应、程序诊断；本界面源严格为 0，原面通量、反应源、功账本不改。用 Fraction 对已表示的左面流减右面流加反应净源求和，正净液源退出 `dry_interface_liquid_reappearance_unsupported`。这仅检查净再出现，不保证识别同时生成和消耗、净值相消的全部微观液过程；负净源仍交原库存正性合同，绝不截流或裁剪。

假想平界面筛选取真实解码温度与当前气体**总压**作为假想液压（干态实际 liquid_pressure 是 None），忽略曲率/污泥活度/成核。`hypothetical_equilibrium` 单独保存该假设计算；实际 `equilibrium`、实际液驱动 μ、熵产均为 None。strict 仅按名义 pv 与 peq 比较，不是包含逆解误差的严格不凝结证明。若原水化学域不支持查询，strict 退出 unknown，metastable 显式记录 `metastable_no_nucleation_condensation_drive_unknown`；可查询且过饱和时，前者退出凝结 unsupported，后者记录 supersaturated。数值、来源与身份失败不会变成可忽略 unknown。显式 dry 即便 K=0 也保留同源和策略检查；默认 existing 且 K=0 的旧 disabled 行为不变。所有模式仍 material_qualified=false。

验证历史：事前 9 项先因缺失 API 全部 RED；首版实际 7 过 2 失败，暴露干态实际液压 None 不可直接用于假想筛选，随后明确采用上述总压假设，9 项通过（1.55 s）。追加不可变、数值错误传播与 K=0 严格策略验证后共 11 项；没有放宽原门槛。高温试验是预先无液、显式不成核的单格制造固相/真实 Joined 水汽升温，不代表湿态耗尽事件或完整湿砖周期已完成。

兼容回归修补：全安装发现默认模式提前物化为单格 tuple，导致旧 dataclasses.replace 更换双格主机时拒绝。新增专门测试先实际 RED（1 failed，0.39 s），随后保留 None 的默认声明语义。显式 existing/dry/mixed 元组仍不自动扩容，事件切换生成的完整元组同样严格。这一修补不修改原有三个失败测试或模式物理政策。
