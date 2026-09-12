# 受原域约束的单胞局部平衡 flash（设计，未运行）

**建议实施独立、有限预算的单胞闭合；不把旧固定库存反解直接嵌在全气→全液扫描中。** 固定载气各分量、总水 (N_t=N_c+N_v)、刚性可用体积 (V)、干质量与原完整 (U_*)，求分配和 T。瞬时相平衡是明确的 `virtual_design_choice`，时间尺度分离误差 unknown；不新造 Kph。先证明一个真实绑定单胞可计算，再讨论开放干燥。范围仍 T=325–338 K、完整 P 误差包络 90–110 kPa、(0\le W=MN_c/m_d\le j=.15)。本文仅读当前源码与 `physical-next.md`；无 EOS、网络、实现或准入成绩。

**1. 先构造有域内意义的库存括区。** 记 (x=N_c, n=N_v=N_t-x, N_a=\sum N_{carrier}, N_g=N_a+n, v=v_l(T,P))。原机械闭合等价于

\[
 P[V-xv(T,P)]=N_gRT,\quad V_g=V-xv>0,\quad
 D_P=V_g-Pxv_P>0,\quad P_x={Pv-RT\over D_P}.
\]

`rigid_water_gas.py:221` 已使用稳定液相 (v_P<0) 证明定组成压力根唯一；**它本身没有证明变组成时 P 单调**。若整个候选带另有 (Pv<RT)，才得 (P_x<0)。此条件在所讨论液水范围很宽裕，但应由实际液相响应/有界 v 验证，不当作无需检查的常数。此时可仅在允许压力边界读取液相 TP，反算

\[
 x(T,P)={(N_a+N_t)RT-PV\over RT-Pv(T,P)},\quad
 I_x(T)=[0,\min(N_t,m_dj/M)]\cap[x(T,P_+),x(T,P_-)].
\]

以原误差包络留**向内**余量选 (P_-,P_+)，或将上述名义端点向内修正直到实际 storage 的完整 P 区间通过；不能覆盖/放宽门。V 的既有误差也必须保留。端点只确定候选集合；每次实际 storage 解码仍须过原门。禁止先调用常达 MPa 的全气端点再把失败当正常根括区。若 (Pv<RT) 未得到保证，只可有界分区搜索并保留“预算内未找到括区”，不能声称物理解不存在。当前固定组成 inverse 要求整个原 T 区间均可解码，因此不适合强行处理只在部分 T 可行的 x。

**2. 平衡根与稳定性须基于同一个势。** 正 x,n 时用

\[
 g(T,x)=\mu_l(T,P)+\mu_{ex}(T,x)-\mu_v(T,p_v),\quad
 p_v=nRT/V_g,\qquad g=0\iff a_w p_{eq,pure}=p_v.
\]

`low_moisture_phase.py:84` 的实际 peq/pv 与 nominal 化学势另存残差，不将 exp/log 的舍入当物理不确定度。零端仅用解析符号：(N_t>0) 时 x→0 给 g→−∞，n→0 给 g→+∞；**只有端点属于可行域时该符号才能夹根**，不调用 ideal_vapor(0)。(N_t=0) 是保持干端 excess 的普通储能反解，无有限水 μ。域截断端点若 g≠0，只是受模型范围限制，不能宣称相平衡。

若存在消去液/气分体积后的共同 Helmholtz 势 A，满足 (g=A_x, U=A-TA_T)，在低 W 正库存内有

\[
 g_x={RT\over x}+RT\left({1\over n}-{1\over N_g}\right)
       +{(Pv-RT)^2\over P D_P}>0.
\]

因此每个可行连通 x 区间最多一个根；不是把来源 Fick Γ 单独当作全系统曲率。接点 j 取低侧导数；超出 j 拒绝。稳定平衡曲线的温度导数为

\[
 x'_{eq}=-g_T/g_x,\quad U_x|_{eq}=-Tg_T,\quad
 C_{eq}=C_{fixed}+Tg_T^2/g_x\ge C_{fixed}.
\]

**3. 现有接口尚不能无条件授予上述误差证书。** 结构上可构造共同 A：真实液体的 h/u/s 来自 IAPWS 势且只加共同能量常数；理想蒸气保持 h、令 u=h−RT，`water_chemical_potential.py:118` 的标准熵若满足 (s'_0=h'/T)，配合 −R ln(p/p₀) 与新 R 仍一致；干相固定质量可由其 cp 积分构造熵；低水 excess 正是 (m_d(h-Ts))。所以 native R 与混合 R 不同**不是自动的不一致结论**。但 storage 未返回完整 A/S，也未登记整体 (A_x=g, U_x=g-Tg_T) 的误差/导数证书，低 W log/activity 只有 nominal 读数。不能凭共享 reference ID 或数点正 Cp 宣布这些恒等式已在运行实现上有界成立。

最小先核项目：液相 (\mu_P=v, h=u+Pv)；蒸气 (s'_0=h'/T, u=h-RT)；同 Nt/V 机械路径上的 (U_x=g-Tg_T) 和固定 x 的 U_T；共同能量参考平移后同根不变。已核源码支持这些恒等式的解析结构；有界源数值差分只能作实现诊断，不能代替全域证明。若确认该结构并约束数值误差，可从**既有**干相 cp 下界与固定载气 cv 下界取统一

\[
 C_{floor}=m_d\min cp_d+\sum_{carrier}N_i\,cv_{i,min}>0.
\]

不能直接沿用某点包含当前 Nv 的 minCv 为整条平衡曲线下界；相分配会改变。原 U/T 门保留，但温度界必须含内层组成解误差：例如 ((|U-U_*|+\epsilon_U+\sup|U_x|\epsilon_x)/C_{floor}\)，或用有正确符号/误差包络的最终 T 根括区。当前 energy_error 只覆盖给定组成；不能漏掉 \(\epsilon_x\)。未得到这些条件时只返回 nominal candidate/未证温度界，不伪装成原 certified inverse 通过。

**4. 最小算法与验收。** 新 `flash(storage, chemical, Nt, carrier, Utarget, policy)`：外层有界 T 括根；每个 T 先建 (I_x(T))，再二分 g，复用 `storage.state/evaluate`、`chemical.equilibrium_at_liquid_tp` 与现有 low excess。只使用都含真实相平衡根的连通 T 子括区；中间遇域洞、无符号间隔、误差不可分辨、迭代/资源耗尽即具名失败并保存已完成试探。结果保存 T/x/机械括区、peq/pv/μ 残差、全 U/组成误差、源身份和调用数。第一阶段不增加列积分器框架。

原 Nt 用实际 float 的 Fraction 和保留；候选 (n=N_t-x) 精确构造，最终二库存投影误差单独计入原库存预算，不能独立舍入后静默丢水。保留完整 U*、干端 excess 常数与载气，无 Q/Hout/PdV/第二 latent 项。验证同 Nt/载气/V/U 的蒸发侧与凝结侧初态得到同根、重复 flash 不漂移、参考平移不改分配、域外全气端点被预筛、零/空括区/不收敛失败不污染输入；若完整 S 可一致重建，再核固定 U 的总熵不降。初次真实单胞通过仍不证明动力学快，也不能解决 full-wet 的固定载气压力矛盾；后续开放边界须真实交换组分并记录携焓。

定位：`arlabosse_low_moisture_storage.py:75`（完整 U）；`arlabosse_low_moisture.py:223`（低水势）；`rigid_storage.py:179` 与 `source_wet_storage.py:203`（固定组成容量/误差）；`ideal_water_vapor.py:95`（R/caloric bridge）；`water_chemical_potential.py:118–179`；`low_moisture_phase.py:84`。审查 storage SHA `7589525d415f7f9eaeb751c035aabdc12f130a11986bad42740b5022b8bb8c57`，chemical `2683bb786ad5e5b6648c02a3d5e9b9671f595820ab4a781e29808c3a95f80767`；其余以本次现行源码为设计依据，未冻结实现。
