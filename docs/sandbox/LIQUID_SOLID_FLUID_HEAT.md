# 液水共享面接入的事前验收

本轮接入可选显式液相配置：同一整体decode后的实际液体T/P进入已来源门禁WaterProperties，取得摩尔体积/焓；共享面Ndot写layout液列、Ndot*h加入相同能量面。固体零输运，封闭气体的输运参数在验证中明确设零。未知材料mobility不默认，冻结mobility只作为制造fixture。

事前数值门槛：两格共享液面值与算子结果逐位一致，内部face重复累加误差abs≤1e-12 mol/s、1e-9W；实际积分每个accepted prefix水总mol误差≤1e-11mol、系统总U误差≤1e-6J，各格U变化与累积face ledger误差≤1e-6J；固体及封闭气体库存逐位不变。供体能量验证用同一真实T/P水属性但独立Ndot*h计算，不能以被测face公式自证。P/T反馈与原状态对照；如果对比小于数值反解预算不宣称可分辨效果。

组合ProgrammedSolidFluidHeat/WaterPhaseTransfer时保留完整evaluation链和程序节点，且液face诊断不能丢失。新制造液系数也必须触发外层测试授权。不添加外液库、毛细、干孔浸润或真实泥水关系。

## 实现合同

`SolidFluidHeat.liquid_transport` 默认None，保持既有无液面迁移行为；配置 `LiquidTransportConfig(relations,connections,allow_manufactured)` 要求每格一项SaturationMobilityTable、每个内部面一项LiquidConnection，长度/精确类型/显式制造门禁均检查。状态依赖路径为显式饱和度表，冻结参数必须 `relation_kind=frozen_manufactured`；方程来源不等于材料表准入。

每次evaluate只调用一次整体decode_inverse。饱和度使用实际 `Vliquid/(Vbulk−ΣNs vs)`，不是Vl/Vbulk。仅有液时调用相同水provider的 `state_tp(T,Pliq,phase='liquid')` 取得h/v，未再次闭合P或反解U。无液时传None h/v；显式disabled面可返回零诊断，未查询不存在的液态。活跃干面等具体域行为交液算子明确判断。

`SolidFluidHeatEvaluation.liquid_faces` 在既有默认字段之后增加，保留位置构造兼容。液面mol流填唯一layout.liquid_index，液面焓流与原gas enthalpy/conduction同面相加；没有额外pQ或相变热补偿。左右单元由积分器使用同一个面值异号记账。没有外液库，所以外层气氛reservoir不会生成边界液流。

所有relations/connections来源汇入host.source_ids；ProgrammedSolidFluidHeat和WaterPhaseTransfer必要制造门禁各补一个显式 `has_manufactured_liquid_transport` 条件。新增分类控制测试将其他合成记录的分类改为非制造以隔离门禁，并以仅移除液配置作为负对照；这是分类逻辑测试，未改变来源事实或声称该合成数值成为实材。

液压力界使用SolidFluidState在解码T处的pressure_error_bound_pa。诊断为 `liquid_pressure_interval_scope=fixed_decoded_temperature`、`full_inverse_liquid_direction_certified=false`，每格完整inverse及其temperature_error_bound_k仍在链内。没有把固定T压力界冒称含温度反解不确定性；不增加虚构全域dp/dT界。名义压力差驱动名义流，近等压不epsilon截断，面诊断可标固定T方向不可分辨。

## 实际验证记录

先写host测试，首次collect因LiquidTransportConfig不存在失败。接入面算子后命令 `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_liquid_solid_fluid_heat.py -q` 得4 passed in20.96s：真实供体h接线、两格湿水积分逐前缀水/U/面账本、仅液制造分类隔离、program+water完整diagnostic链与节点。

随后补single-decode与disabled干面不得查询liquid TP两项，定向 `-k 'decodes_once or disabled_dry'` 得2 passed /4 deselected in2.31s。原积分测试还增加名义T变化检查；这不宣称该小变化超过温度误差预算。最终6项和既有host/wrapper兼容由独立审核者统一串行复跑，本条不预报结果。

此测试积分为0.001s的明确制造两格水连接，保持固体及气体密闭；验证显示名义P反馈和全U重新解码，不能替代时间/空间收敛、毛细压/连通本构或公开材料留出预测。
