# 固定kg来源湿态共同体积：最小数学桥接候选

本候选接续本轮92项保存预算核算，未创建证书、执行EOS或改变原N3失败。原热余量约1.333e-6Pa没有耗尽1e-4Pa预算，但以下前提仍须真实取得。

## 报告温度根比较

实际同一SourceWetStorage/同一恒定available-volume参数V，固定同kg、source caloric/gas/R身份。两端都Nl>0。令G_i(p,V)=Nl_i*v(T_i,p)+Ng_i*R*T_i/p−V，先比较各自报告温度T_i的真实条件闭合根p_i(V)。Ni使用实际库存的Fraction精确和，不能用已rounded fsum代替。

以B端在全部原V箱下的已证明报告温度根区间I_B为共同支点集合。A/B根联合包络I_J包含两端全部可能根及中间线段，仍在原液体稳定P域。对每个p∈I_B：
D(p)=G_A(p,V)−G_B(p,V)
 =Nl_A*v(T_A,p)−Nl_B*v(T_B,p)+R*(Ng_A*T_A−Ng_B*T_B)/p。
共同−V仅在已证明同一个参数时精确消去。独立volume误差若另有部分则须继续加区间，不能把全部eV默认为共同。

需要两个温度下整个I_B的液体v包络：若已证明dv/dp<=0，V_i_interval=[v_i(Phi)−error_i(Phi),v_i(Plo)+error_i(Plo)]，各端须正；否则要有更一般的全区间函数证据。由独立区间得到D范围，gas项按有符号常分子/I_B两端求min/max。未证明液体数值误差相关时，即使同provider/T也保留两端独立error，不把它们相消。

因为−∂G_A/∂p = −Nl_A*vP_A + Ng_A*R*T_A/p² >= c_A=Ng_A*R*T_A/(I_J.upper)²>0，若稳定单调在整个I_J成立，|p_A(V)−p_B(V)| <= max(abs(Dlo),abs(Dhi))/c_A。可以采用旧kernel更保守的min(Ng_A*T_A,Ng_B*T_B)*R/I_J.upper²；两者都须明确绑定whole-domain证据。用B作支点不需要凭空在某个任意P求根；I_B不能替换为两个报告P点或单一中点。

## 当前保存点不足的具体位置

旧记录各自在(T_i,P_i)的v及pressure bound，不能给v(T_A,I_B的两端)和v(T_B,I_B两端)完整误差，也没有仅从一个点获得全域|vP|上界。因此目前不能填写LiquidEndpoints：即便名义P/T两端相同，也不能把点v当全压力区间常量。现Nl*B是|uP|界，不是|vP|界，不能拿来构造v的Lipschitz常数。

下一实际有界证据可在预登记后对两个报告T、I_B两端取得最多四个真实v观测及其原数值误差；是否需四个由精确相同输入去重决定，重复输入不能计作独立验证。稳定vP<=0及误差有效域仍是来源条件证明/声明，而不是四个点自己证明。所有点/域/来源资产/参数身份应保存，实际EOS成本单独登记。本候选不启动这些求值。

## 保持同目标的温度与数值余量

1. 单体已有total eP（含原V和独立EOS/闭合误差）用于根包含/域/I_B/I_J，不能先减两份extra再宣称剩下是完整根区间。单体pressure source/check仍必须通过。
2. 联合报告温度根界之外保留原 L_A*eT_A+L_B*eT_B，其中L是原完整V/温度连续围栏的bootstrap有效界。湿态U依赖P，因此不重算或缩小eT里的Nl*B*extraV能量项；完整路径与压力单体域证明保持。
3. 实际fluid.pressure_error_bound_pa不是nominal下界。它若已包含到原根/液体误差中，可保守再次作为独立pressure余量添加，避免没有证明的相关抵消；这可能重复但不漏项。若追求更紧，则必须明确逐项证明哪些属于液体v包络、哪些属于算术闭合残差，不能以“同来源”删项。
4. 推荐沿干态新策略的严格原分解验证：重算global/extra/total要求实际相等，超额记录拒绝新入口而保留原单体有效性；取实际fluid值并另保留total有向求和投影。若允许surplus，必须明确归入独立余量而非共同V，不自动消去。
5. 新液体端点评价的误差、液体摩尔量乘积/体积组合、Ng求和、NgRT/p及闭合求和、残差→压力除法的机器余量要单列。Fraction积分/残差组合本身可精确，但输入观测与实际原闭合操作并非无限精度。干态eta_box公式不能原样覆盖wet液体体积项。需要新全支点/全T盒的前向舍入界或用原经过验证的独立pressure余量覆盖，并证明相同目标。无法证明就unresolved，不能仅因算术D很小而过门槛。

最终候选形式 B_joint_reported + independent_pressure_margin + L_A eT_A + L_B eT_B，所有项非负；旧独立P界原样旁列。默认joint-only，只有严格证明两种证书同目标才可min；原threshold1e-4不变。仅新明确opt-in策略可选择新界，旧event/conditional失败不覆盖。

## 最小代码复用

旧paired_pressure的物理dataclass要求solid_mol/bulk/J，固定kg来源不能提供假字段。可从certify_paired_pressure抽取纯Fraction末段：给已验证 residual_interval、joint_root_interval、positive_compliance_lower，计算reported根差上界、必要向上float投影及稳定序列化；旧入口以原物理组装调用，golden保持。也可抽取“有符号常数除正区间”小原语，旧新共用。

新SourceWetSharedPressure入口只负责真实SourceInversePressure两端、live shared available V、真实液体共同支点证据、完整域与原余量组装；干kg只在storage/energy identity内，不入mol根算术。纯kernel不接纳物理资格，调用层不恢复任意未知类型。第一实现可以输出新条件界/拒绝而不做新事件调度；接现有N格逐cell策略后仍要求所有格通过。
