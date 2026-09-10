# SourceMassCaloric独立物理/来源实现审查

审查对象：`src/sludge_sandbox/source_mass_caloric.py`，SHA256 `1cd8b30654ccbb7163be731d01ef63e947c6748ad97bfc97b81136a7b42f66ad`。已读实现、对应测试及首次GREEN01.log。来源元数据SHA仍为`2f9caf23689092e548b2b3d7abf7c54d58d177569a7850b47c69df15e74295d6`；未重新搜索或改变来源。

**结论：在明确声明的固定组分、不可压缩且比容不随温度变化的近似下，纯干物point caloric实现未发现阻断性物理错误。** 这不是湿格主机、化学反应关闭路径或N格运输验证，不能据此宣称那些缺项已完成。

## 实现边界检查

- `ArlabosseMassCaloric.specific_internal_energy`实际调用原provider.delta_h，未重新拟合系数、外推、引入摩尔质量或形成焓。reference_temperature限定源域，u(T0)=0明确仅相对坐标。
- 材料component_id固定为Arlabosse原混合来料干物；FixedMassCaloricStorage的chemistry布局必须匹配该ID。不能把该关系直接绑定Nylen、Wang或char/ash身份。
- 固定质量参与identity，anchor参与identity。不同质量是另一storage对象，旧能量目标无法无声用于新identity；当前没有质量演化接口或反应通道。
- ReactionDisabled生成与明确布局相符的严格零化学源，不构造A/B或氧参考。其phase_transfer_included=False没有声称整个湿系统已关闭相变；当前纯干物storage没有液水/气体/EOS行为。
- `specific_volume_m3_kg=None`明确缺失体积，未用0替代。由此没有自动取得WetMixedStorage或原泥材料的完整准入。
- 点热容使用m*Cp(T)；minimum热容使用整个308.15–378.15K域的m*Cp(lower)，正斜率确保是真实数学下界，inverse用残差除以此下界。并未误用较热查询点Cp。
- 能量全程Fraction，numerical_energy_error_bound_j=0在“精确输入的已声明名义拟合多项式”意义成立；fit_error仍None、material_qualified=False，registry派生能量节点同时说明来源fit与本构近似误差未知。这个0不是实际材料误差为0。
- float按精确binary64转换，随后以Fraction传给原provider，避免provider最短十进制语义的隐式变化。用户需要精确源域端点时使用Decimal/Fraction；308.15的binary64值稍越下界因此拒绝，与显式策略一致。

## 实际独立复算

独立脚本`check_physics.py`在80位Decimal环境中直接从线性Cp系数构造积分与二次方程，**不调用被测forward来生成期望能量或真温度**。之后才调用被测实现进行比较。一次执行正常退出，日志PHYSICS_CHECK.log、结构结果PHYSICS_RESULT.json。

| 条件 | 独立参考 | 实际结果 |
|---|---|---|
| 0.2kg、40°C anchor、80°C | U=13051.2J | 精确相等 |
| 0.2kg、60°C anchor、80°C | U=6657.2J | 精确相等 |
| anchor能量差 | 6394J | 精确相等 |
| 全域C_min | 309.83J/K | 精确相等 |
| 80°C点C | 339.44J/K | 精确相等 |
| 独立正二次根 | 80°C，判别式2880487.84 | 两anchor均45次迭代恢复；真实误差在声明数值界内 |
| 旧anchor target送新anchor storage | 拒绝身份错配 | `target_identity_mismatch` |

两次反解真实温度误差均为`5/17592186044416 K`；声明界为`5971491630916565395/19177548118589468528599782916096 K`，严格覆盖真值，最终括号均包含353.15K。未知fit、未准入、未知volume也逐项断言。没有为了得到通过修改参数或公差。

## 明确未覆盖

没有实际WetMixedStorage组装、液气参考耦合、真实湿格ReactionDisabled路由、孔隙体积、面焓流、边界能量账、N格求解或公开实验预测。因此该成果的准确表述是“原来源比热已成为可反解、带来源与坐标身份的固定干物质量储能point适配器”；完整原泥主机仍需后续集成。代码类型/身份全面安全审查由另一独立审查者负责，本报告不替代它。
