# 局部平衡与慢输运衔接：有限设计

执行计划澄清：本文首版末段的`.05 s`为早期建议，尚未执行。ROOT随后按微小蒸气池时间尺度与已测单胞成本登记[NATIVE_PLAN01.md](NATIVE_PLAN01.md)，首次实际运行采用`1 s / 1步`。原数值与物性门不变，以下推导保持；不将早期建议当成第二个已运行工况。

**支持 ROOT 的证书区分。** 当前 `flash.finish` 返回的 `state` 已含最终 binary64 Nc/Nv 和原 Utarget；对这份实际状态调用既有固定组成 full-U inverse，确能取得**给定该组成/库存/U 条件下**的原 U/T/P 验收与温度反解界。必须保持整个原反解端点支持/压力门，不能偷换为 flash 的窄 T 括区；再在新 inverse.point 重算实际 aw·pure_peq−pv 和 μ 残差，按原 flash 容差验收。若新 T 下不通过，具名拒绝，不能覆写 T 或沿用旧 flash 点的残差。返回字段应并存 `fixed_composition_inverse` 与仍为 None 的 `equilibrium_composition_energy_error` / `certified_equilibrium_temperature_bound`；原 μ/log 和组成传播误差 unknown 不变。既有 state 水投影误差也不包含在这个条件温度界内。

**下一步数值风险补充。** 原给定组成 inverse 的 1e−6 K 门可能返回约 4e−7 K 温差，足以让重新计算的 μ 超过 flash 原 1e−5 J/mol 门；不能据此放宽 μ/peq。可显式选同算法、U1e−5 J、T1e−8 K、原 max100 的更紧数值策略，再实际重算两项化学残差；或把已计算 flash.point 作为给定组成候选，仍须核目标/状态/源一致性、原端点支持与 (|Ures|+Uerror)/minCv，并保留原压力门。已保存 Uerror≈7.2e−8 J、Cfloor≈16 J/K 只提示约 4.5e−9 K 的数值地板，不能保证每个新状态可达 1e−8 K。两路径均需后续独立测试和真实成本/残差验证；不得凭该点或局部 g_T 赋予整个平衡曲线温度证书。

**最小主机应推进守恒 Nt/U，再作平衡分配。** 直接“flash → phase=0 的 _advance 从 Nv 扣出口 → flash”仍受很短的 Nv/出口率限制，不能产生负 Nv 后靠 flash 修复。建议先将初态逐格 flash+固定组成反解/复核，单列零时刻初始化投影；以后每个宏步从已接受平衡态算现有 k/D/热浴/选择性汽口共享面，再精确更新

\[
 N_{t,i}^*=F(N_{c,i})+F(N_{v,i})+D_{L}-D_{R}+G_{L}-G_{R},\quad
 U_i^*=F(U_i)+\mathcal H_L-\mathcal H_R.
\]

D 是已有凝聚水面积分；G 是气体 H₂O 积分（内部气迁移继续禁用，外口为正出口 E）。外口同一次观察给 E 和 H=hv·E，热浴 Q 以 −Q 进入外面总能量；已有 nominal/readout 投影与分解残差照实记录，不能将单独舍入的 H 强称精确 hvE。内部共享导热与迁水携焓各算一次。拒绝 Nt*<0；不构造一个临时负 Nv 状态。

将精确 Nt*、不变载气及**一次投影**的 Utarget=fl(U*) 送入每格 flash，随后固定组成反解/复核。以 flash 的精确请求组成 x,n 定义

\[
 J_i=F(N_{c,i})+D_L-D_R-x_i,\quad
 x_i=F(N_{c,i})+D_L-D_R-J_i,\quad
 n_i=F(N_{v,i})+G_L-G_R+J_i.
\]

这是同一相重分配积分，非 Kph·h。可在所有 flash 成功后，用这些同一 J/面调用原 _advance 作唯一最终状态投影，要求所得状态逐字段等于 flash 返回状态；不能再从已投影 flash 状态重放 J。无局部相变 H、额外 latent 或刚性边界功。当前 Column 若必须保留相变系数字段，显式全零作为禁用标记，拒绝非零；该模式实际采用 flash，不运行旧有限率/BE 相变支路。

**账本与失败。** 仅最终采用的 flash 投影 δc、δv 计库存费 |δc|+|δv|，签名总水修正为 δc+δv；所有根试探的投影不累计到物理账。Utarget 投影 δU=F(fl(U*))−U* 计一次能量费；固定组成反解不改库存/U，不新增投影费。已有慢面 water/H/decomposition/heat 投影费用继续计入；此前已接受状态的累计水误差保留并加本步修正，不清零、不再次收费、不从新 Nt* 中扣回。全列检查 ΔΣNt=−ΣE+ΣδN、ΔΣU=ΣQ−ΣH+ΣδU。仅全部两格 flash/反解/化学复核/预算通过后提交一步；任一失败保留 partial trial，接受前缀不变。该保守平衡投影是新数值方法，仍需时间比较，不自称精确动力学。

**首例范围。** 两格沿原 md/V/A/宽度、Nc=(0,.06)、Nv=1e−6、T=(330,333)；dry 格载气 Na=.00034（沿已声明 O₂/N₂），wet 格 Na=.00032（沿 native02 的实际分量），热浴 333 K/G=.1、汽口 pe=0/Kv=1e−8 均为虚拟控制。先核两格零时刻 flash+给定组成反解，再预登记一个 .05 s 宏步及原资源/误差门；不能因原单胞名义根通过而假定其端点反解已通过。dry 格保留干压余量，wet 格给平衡蒸气留空间；Na=.00032 的 wet 格以后接近全干仍可能低于原 P 下界，故此例不授予全程资格。LTE、跨材料 D/k、几何与边界误差继续 unknown；全湿或最终干燥仍需真实载气交换边界，不能删水或扩域。

依据：当前 scratch `low_moisture_equilibrium.py:282/377`；正式 `low_moisture_fast_inverse.py:75/88`、`source_wet_column.py:575/611`、`controlled_vapor_column.py:134`。仅读源码与保存审查；无 EOS、实现、测试、网络或新误差框架。
