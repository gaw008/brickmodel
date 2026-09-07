# 固定总体积内的显式固液气储能

预登记实现合同：每次完整固体库存 Ns 重算 Vs=ΣNs vs、available=bulk−Vs，调用既有流体 forward 在本次腔体解 P(T)。总U为流体U加ΣNs us，总Cclosed及Cmin增加对应固体热容和已认证下界。反解必须对整个U重复实际forward，不用旧fluid inverse替代。全部固体keys显式含零；无气相/无正可用体积保持域退出，不添加epsilon气体。

误差合同：固体体积及bulk声明误差和相减浮点误差进入机械压力预算，包括无液体解析气相分支；以全压力域气体体积导数下界NgRT/Phi²保守传播，液体存在时还增加Nl sup|du/dP| εP。固体u声明误差已含p0v参考误差，再计浮点总和分辨率；资格仍是声明全域界的条件结论，不是严格真实材料证书。

预登记测试：无液单气常Cp固体的独立解析压力/U/C/Cmin及温度反解（温度绝对1e-6K、能量1e-6J）；恒功真实integrate保存状态总体U账本1e-8J且终温解析1e-6K。液水±体积扰动以独立scipy压力根和水EOS能量参考检查所报P/U误差覆盖；不以本模块自算反解作oracle。另测试完整keys/过占积/无气/制造门禁/来源参考/数值误差预算退出，零固体回归。每个真实积分运行预算90s。

实现接口为 `SolidFluidStorage(fluid_template, solid_phases, bulk_volume_m3, bulk_volume_error_m3, geometry_source_ids, geometry_id, geometry_version, geometry_classification, allow_manufactured)`（仅关键字构造）。完整固体keys与各provider物种ID一致，允许不同相使用同一物种名但必须匹配摩尔质量。`evaluate_at_temperature(T, liquid_mol, gas_mol, solid_mol)` 返回 `SolidFluidState`；`temperature_from_energy(target, liquid, gas, solid, temperature_bracket_k, policy)` 返回完整整体反解。几何、热量、数值误差的制造分类仍需显式门禁。原fluid_template的available是模板值，不覆盖此模型的bulk−固体占积。

结果保留原 `fluid_state` 及其机械/误差合同、实际 `mechanical`、活动固体 `solid_points`、含全部零库存键的 `solid_inventory_mol`、Vs/available、总体U/H、局部Cclosed/全域条件Cmin、体积/压力/能量误差及来源。映射不可变。若某solid库存零不查询该相温度域，因此零水或零固相不会无故阻止其他活动相，但正气相要求沿用原机械模型。

有向运算以所表示输入的Fraction体积总和与available为基础。固体体积误差不能仅当作一次初始修正：每次库存改变后重新计算，甚至无液体时仍纳入压力误差。固体u误差包含p0v的参考贡献，与可用体积传播中的同一体积误差相关；此处保守累加，没有利用相关性降低预算。旧fluid误差先保留，再加入固体/几何带来的额外压力和液体内能误差。压力区间必须完整落在模型压力域内；不能以名义点合法替代完整区间合法。

整体inverse每试探重新解温度对应压力；局部Cclosed只用于受保护Newton试探，验收由全域声明下界、带方向的能量区间及向外取整的温度区间决定。初始端点方向不确定明确拒绝；预算超限或方向不可分辨报数值合同错误，不通过缩小声明误差自动补救。`SolidFluidStorageError`继承RigidStorageError；固体provider自己的物性域错误保留SolidPhaseError，主机需据温/压域消息映射DomainExit，不能把预算超限当作物性域退出。

本轮实际记录：先登记测试，首次因模块不存在收集失败；首版测试发现fixture固体映射键与真实species_id不符，已修正fixture而非放宽身份校验；另发现1e-4十进制期望与实际binary64 bulk−Vs相差一ULP，改用独立Fraction表示输入的精确期望，没有放宽温度/能量门槛。负库存初版抛基类RigidStorageError，已归类到新的SolidFluidStorageError。11项通过0.60s后增加库存反馈/身份/完整域错误回归，20项通过0.62s；最终扩展和独立审核见审核报告。

本模块尚未包含固体相变/化学反应、收缩、弹性/界面储能或应力功，也没有推导导热、渗透率、材料矿物含量。固定外bulk条件下U包含固体，不能再对外气体h通量重复加Pv。真实湿砖主机接入与各传输通量测试另由相应模块完成；此处恒功真实integrate证明的是新整体储能每试探确实被使用。

几何分类另允许 `virtual_design_choice`：用于沙盒明确设定的控制体尺寸，与实测或文献物性区别保存，仍必须有 geometry_id、geometry_version 和 geometry_source_ids。此分类仅对几何开放，不扩展到固体热容、体积物性或误差合同，也不改变 `material_qualified=false`。制造几何仍按精确类别 `manufactured_test_fixture` 触发门禁，虚拟几何不会绕过制造材料的原有门禁。新增针对性测试先在旧实现因 invalid_geometry_classification 失败，随后加入几何类别，保留原必需身份及制造检查。
