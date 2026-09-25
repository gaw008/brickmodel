# 小孔分子流极限：有来源的物种、能量和熵关系

2026-09-25 UTC。现有开放反应单元曾经过约.056Pa的低压状态，虚拟输运系数不能据此获得真实适用性。本阶段单独实现理想气体通过无厚度小孔的无碰撞极限，先核验静态关系。**这不是既有整段高/低压循环的替换关系，也没有真实砖孔网络或Knudsen数资格。**

## 来源与适用前提

[MIT 2008 Lecture 29](https://ocw.mit.edu/courses/5-62-physical-chemistry-ii-spring-2008/7aef298bb5d8fe6cf383fb18664341e8_29_562ln08.pdf)讲义页1–2给出小孔不扰动库内平衡分布、分子穿孔时无碰撞的前提，以及出射粒子通量为数密度乘平均速率再除四的结果。PDF第3页已渲染目视核对：最上面两式的速度指数缺少分母2，后面的笛卡尔积分和末式包含2；最终通量与规范化Maxwell分布相符。模型采用规范化分布独立积分，不照抄不一致指数。

CO2/N2名义摩尔质量分别为.0440095/.0280134kg/mol，来自[NIST CO2](https://webbook.nist.gov/cgi/cbook.cgi?ID=C124389)和[NIST N2](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7727379)。气体Cp、生成焓和熵沿用[USGS1995](https://pubs.usgs.gov/bul/2131/report.pdf)已核记录及其历史R，温区298.15–1200K；这里没有替换热力学常数或声称这些名义值无物理误差。

两侧各自为理想平衡气体，内部自由度与平移速度独立，孔对速度不筛选且没有吸附/反应/壁碰撞。声明示例面积1e−12m²只是线性比例系数。没有来源支持的实际孔尺度、碰撞截面、壁面适应系数和曲折度，故不提供真实砖的通量或全压力范围插值。来源记录在`data/sandbox/research/effusive-gas-limit-v1/sources.json`。

## 从速度分布推导守恒通量

以下为本项目推导。物种i的单侧出射摩尔通量为

\[
j_i(T,p_i)=\frac{p_i}{\sqrt{2\pi M_iRT}},\qquad
\dot n_i=A(j_{i,L}-j_{i,R}).
\]

令x=v/√(2RT/M)。出射分布的速度权重为x³exp(−x²)，两个积分分别为∫x³exp(−x²)dx=1/2、∫x⁵exp(−x²)dx=1。出射平均平移动能因此为2RT，库内则为3RT/2。加上不受速度筛选的内部能，携带总摩尔能为

\[
e_i=h_i-\tfrac12RT=u_i+\tfrac12RT,
\qquad \dot U=A\sum_i(j_{i,L}e_{i,L}-j_{i,R}e_{i,R}).
\]

这里h含生成焓。出流能量不是连续介质流焓，也不能丢弃生成能只记显热。左右库直接用同一数值反号记账。没有额外补加pV流动功。

## 熵非负的条件证明

两库合计的熵率为

\[
\dot S=\sum_i\dot n_i(\mu_{i,L}/T_L-\mu_{i,R}/T_R)
+\dot U(1/T_R-1/T_L).
\]

利用理想气体化学势及d(g°/T)/dT=−h/T²，每一物种可改写为

\[
\begin{aligned}
\dot S_i/A={}&R(j_L-j_R)\ln(j_L/j_R)\\
&+j_L\int_{T_R}^{T_L}\frac{e_L-e(T)}{T^2}dT
+j_R\int_{T_R}^{T_L}\frac{e(T)-e_R}{T^2}dT.
\end{aligned}
\]

当e′=Cp−R/2>0时，三个项在任一温度方向都非负。不是根据几个正数样例推断全域第二定律。源Cp的区间极值由x=√T后的驻点多项式及端点求得：CO2最小Cp−R/2约32.96465J/(mol K)，N2约24.93792J/(mol K)，均为正；有限精度多项式根求解不是严格区间算术证明。

若温度不同，物种净流为零要求pL/√TL=pR/√TR，而非pL=pR。此时仍可有热量和熵交换，不能称完全热力学平衡。

## 实际完成的科学核查

`parameters.effusive_gas_limit.json`在计算前固定9组状态、积分精度和误差预算。`review_effusive_gas_limit.py`独立积分Maxwell速度/角度矩、源Cp和三项熵表达，核对两侧翻转、能量参考变换及熵不变；全部通过。最大熵分解差7.11e−15W/(m² K)，小于原1e−10预算。冷热相同状态得到零通量；不等温的物种通量平衡态得到正热流和熵率。

能量参考变换对每物种增加常数a、熵参考增加b时，净能流恰增加Σaᵢṅᵢ，熵率不变。带生成能的净能流可以为负，不应直接解释为热量从冷向热；所记录熵率明确包含物种化学势贡献。

实现为`src/sludge_sandbox/effusive_gas_face.py`；完整输入、源快照和各项残差见`static-review.json`。目前只有静态极限关系的核查，下一独立阶段是有限库存双气室过程与全程能量/熵积分。没有用本结果替代真实砖流动系数、材料留出验证或有限反应动力学。`material_qualified=false`，`training_eligible=false`；未新增或运行软件测试、未生成校验和。
