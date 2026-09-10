# 对root最终binary64设计的物理审查

root提出SourceWetStorage复用WetMixedState，factory只接受liquid/gases/U并固定solid mass；所有公开数值必须可无损表示为binary64，float按实际二进制数值，不能无损的Fraction/Decimal明确拒绝。该设计**可接受**：这是清晰的表示域约束，不是声称数学有理数1/5或十进制0.2在物理上不合法。应在错误与文档说明float(.2)的精确二进制质量和Fraction(1,5)不同，不能暗中相互替换。

固定drymass保存float，能量聚合时用Fraction(drymass)，source Cp收到Fraction(t)，保证与fluid实际温度一致。factory不暴露改变solid质量的参数，check拒绝外部dataclass replace更改质量。state仍携带绑定模型身份，旧anchor/volume/storage目标不得重用。

只允许显式ConstantTestFluidVolume且classification精确为manufactured，待真实同材料证据出现再增加新明确类型，比接纳可任意改标签的泛型source对象更严格。没有totalH、bulkvolume、solidvolume声明且material资格始终false，符合当前证据。

inverse沿用原湿质量储能的上下端能量余量、Fraction残差和全域导数下界，增加总能量float舍入与nl*|du/dp|*extraP，物理/数值上合理。factory已拒绝不可无损表示目标时，不需再把用户传入原exact值转换误差偷偷塞成0；如果后续放开该限制，则必须重新定义目标量化误差合同。

纯stock state复用不授予旧WetPair/exactstage准入。现阶段无真实材料体积、无N格面通量/事件/主机时间轨迹，均仍是原Goal缺项。

此前SOLID_ORACLE.json为独立精确m=1/5例，保留不覆盖。实际新host单例若用float .2，独立oracle改用其精确Fraction.from_float(.2)质量并明确记录，不按旧有理数期望硬套；这属于按公开表示合同选择输入，不是按结果调参。
