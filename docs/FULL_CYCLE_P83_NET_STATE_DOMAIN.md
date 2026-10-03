# P83 原净状态、耗尽与共同氧域：静态结论

本轮完成源码与符号合同，找到了固定其余未知量的氧根论证缺口；没有实施求解器或做科学数值调用。当前不建议把局部 joint-BE 直接接入生产：共同炭域可能排除 q=0 左端，合法氧根还必须同时满足有机物净残差；原固定 8 次机械 Newton、有限对数图和完整离散 U/S 均未得到新方法资格。停止继续扩写宽泛理论阶段。唯一下一路线建议是回到原模型未完成的最终 cooling_hold 时间步比较，沿用 P80 未采用候选，取得受限的最终端点证据，并明确保留严格非负 FAIL。该建议仍未采用，不能据本报告启动计算，也不能用数值比较替代非负修复或整模型验收。

证据来自当前 53 个原生产文件、758 条完整根参数与 P82 完整合同及两条独立 AI 审查。只用 stdlib 读源/AST/现存 JSON 与书面代数；不重读、重解旧轨迹，不调用任何生产函数。所有部分读取文件按完整字节计入当前独立 64 MiB 容量账本。P82 审查不是新的人类批准。Git/Drive/实际恢复/历史容量另列。

## 同阶段独立 AI 审查：边界恒等式与停止条件

本页是父协调提供的独立 AI 纯符号审查合并，不是新的人类批准/额度；初始派发1次，审查补充1次，科学窗口与调用仍0。反馈到达时首个正常提交451db5232a556299849e749ab1aebf94b55e4b10已普通推送，但Drive与终态尚未交付；保留该首个后继与原回执，追加同阶段正常后继，最终仅做一次Drive增量，不改历史。

| 精确关系 | 必要前提与结论 |
| --- | --- |
| q_L=Q-c_n-u>0，c(q_L)=0 | 必须原完整r_d在此同态有定义且为0，才能省略r_d；0乘发散affinity不可直接代入。原char纯代理没有log c项，但其余气体/热力/机械域仍须有限有效。 |
| F_v(q_L)=h*r_a-c_n-u=-c_n-R_u-h*r_b | 三式使用同一个X(q_L)、同一个u/h与原r_a/r_b，属于符号恒等，不是数值评价。 |
| 若R_u=0且c_n>=0，则F_v(q_L)<=-c_n<=0 | 非负原r_b和h>0有效时条件成立。它要求辅助有机物闭合，不能据固定任意u证明该符号。 |
| 若c_n<0且R_u=0，则F_v(q_L)<=0还需h*r_b>=-c_n | 旧负库存不能无损正化；该不等式既未由原输入保证，也不使入步负态获得资格。 |
| q_L<=Q等价c_n+u>=0（正左端情形） | 否则库存区间已经空；下界0仍受原gas-log有限图限制。 |
| 有效共同切片上所有D_j非零且原helper域有效 | 8次有限Newton映射可连续；本轮没有证明它不连续或不收敛，也没检测新的奇异点。即使连续，输出不必F=0，其算法状态/根不等于精确机械平衡系统的状态/根。 |

因此前述“正左端无符号保证”精确针对固定u且未同时闭合R_u的标量论证；不是在已同时闭合R_u、非负c_n和合法同态率时仍否定条件边界号。真正未满足的是：没有源码/既有证据提供覆盖整个共同合法区间的同态辅助闭合u(q)、真实有限机械图及其余气热力相/输运的资格；不能把独立一维IVT扩为全耦合存在唯一。

在此停止BE正式修复推进，不继续展开标量括根或另一广泛理论阶段。下一仍仅建议回原模型未完成的最终cooling_hold时间证据；该候选未采用/未运行，严格负库存、完整U/S与数值/实材缺口保持。暂停BE不等于原模型合格。

## 原状态映射 X(u,v_net,chi)

逐格记原入步库存 o_n,c_n,q_n,z_n,w_n,N_n 分别为 organic,char,O2,CO2,H2O,N2，单位 mol；a,b,d 为 organic 氧化、organic 碳化、char 氧化的本步 mol 进度。u=a+b，v_net=a+d，a=lambda、b=u-lambda、d=v_net-lambda。这里 v_net 是进度，不能与原固体摩尔体积数组 v 混用。

原三通道给 o+=o_n-u、c+=c_n+u-v_net、q+=q_n-v_net、z+=z_n+v_net、w+=w_n+u、N+=N_n。加入其他原反应与输运时，J_g=原其他反应产气+原有符号输运增量，J_water=原液态水输运；三通道不改其他凝聚物。令 Q=q_n+J_O2、Z=z_n+J_CO2、W=w_n+J_H2O、N=N_n+J_N2，则 q+=Q-v_net、z+=Z+v_net、w+=W+u、N+=N。J 是其余共同未知量满足原方程后才得到的量，冻结 J 只是条件切片，不能把输运自由选择或宣称已消元。

当前根 gas.storage=solid.thermoelastic=1、kinetic_liquid=true、direct channel off、calcium mode0、carbonation factor1。沿 make_cycle 与构造源码得到 12 格、11 个场块、4 个气体块、7 个反应块：gas_offset=132、extent_offset=180、last=264、长度275。这是静态布局算术，不是新构造或旧 checkpoint 解码。历史原37数值 context 的一致性仅引用 P82 的 P81 身份证据，本轮不重构/复核其运行时数值。

| 原 native 字段/槽 | 物理量与单位 | 参考量、映射及净变量关系 | 角色 / 源码 |
| --- | --- | --- | --- |
| f0 | T [K] | T=Tr*f0；Tr=root reference.temperature | 独立温度未知；full_cycle_solid.py:345–350 |
| f1 | 液态 water [mol] | n_water=n_water,0 exp(-f1)；含蒸发/凝结和 J_water | chi 中其余物理未知；full_cycle.py:277–295 / gas.py:814–815 |
| f2 | kaolin/metakaolin [mol] | n_kaolin=n_kaolin,0 exp(-f2)，metakaolin 由原耗尽产品重建 | 其他反应进度未知；full_cycle.py:223–233,285–287 |
| f3 | calcium pool fraction [1] | 当前 n_calcite=Cpool*f3，n_lime=Cpool-n_calcite-n_OH | chi 中原 Ca 变量；不是当前的 calcite log；gas.py:172–194 |
| f4 | organic [mol] | o+=o_org,0 exp(-f4+)；正初始且 o+>0 时 f4+=log(o_org,0/(o_n-u)) | u 替代此物理未知的合法正域表示；full_cycle.py:285–295 |
| f5 | char [mol] | c+=sigma*f5+，sigma=md/M_char，f5+=(c_n+u-v_net)/sigma | 线性库存，允许精确零；full_cycle.py:232–233,288 |
| f6 | eta [1] | 原不可逆轴向应变；不是 thermoelastic 分支的 log pore | 独立力学内部未知；solid.py:345–370,419–447 |
| f7,f8 | 累计热/携能 [J] | 各格原积分乘 escale，dot=heat/escale、flow/escale | 诊断积分，不反馈三条率；gas.py:817–818 |
| f9 | portlandite [mol] | n_OH=sigma*f9 | chi 中原 OH 未知，Ca 余量约束保持；gas.py:174,819 |
| f10 | 液相 log-odds [1] | x=1/(1+exp(-f10))，原稳定分支等价实现，有限实数给 0<x<1 | 独立相内部未知，carrier=active*n_metakaolin；solid.py:75–84,101–177 |
| gas blocks O2/N2/H2O/CO2 | n_g [mol] | n_g=n_g,0 exp(l_g)；l_g+=log(n_g+/n_g,0)，必须四气体均正 | 原物理气体未知；O2/CO2/H2O 净更新仍须其余 J 约束；gas.py:239–242 |
| 7 个 reaction blocks | 累计 Xi_r [mol] | native slot*逐格 sigma；本步三槽分别增加 a,b,d | 原三通道记录不能只保存 u/v；不是反应供体；full_cycle.py:298–302 / gas.py:821 |
| last:last+4 / 后4槽 | 累计气体进/出 [mol] | native*nscale，原边界有符号流分别积算 | 诊断边界预算；gas.py:822–824 |
| y[-3] | 外压功 [J] | native*escale，dot=-P sum(Bdot)/escale | 原 signed work；gas.py:825 |
| y[-2],y[-1] | 产熵/交换熵 [J/K] | native*escale/Tr | 独立原积分记录；gas.py:826 |
| Vp,B,Es,cap,p_g,Pgas,stress,K | m3,m3,J,Pa,Pa,Pa,Pa,Pa | 由完整 f/ns/ng 经下述实际机械映射输出 | 不可作为互相独立的自由 chi |

chi 至少保留 T、water/kaolin/Ca/OH、eta、phase log-odds、其余反应/输运共同未知、原参考库存/体积/尺度、根物性、分支、绝对 t。原 silica 惰性库存也保留。原37 context 属性名称在 JSON 全列，并保留 initial_partition/phase0/liquid_reference/species/reactions/branch/layout；这些是参考与历史身份，不是可自由改的求根变量。原 times、temperature/gas knots 与 stages 用绝对时钟，不能把 t 重新设为0；gas.py:655–656,909–923、checkpoint.py:24–49、continue.py:51–70。三条局部化学率不直接含 t/tf/inlet，但输运、热交换及其反馈的完整事件含它们。

相同 (u,v_net) 不识别 lambda；相同完整物理终态 U/S 不识别通道。但原 native_y 的三个累计槽通常不同，不能称完整原状态相同。逐列 N_a=N_b+N_d、rank=2、null=(1,-1,-1)，同一完整状态的 delta_g_a=delta_g_b+delta_g_d 是计量恒等式；不能推出动力学非唯一或 Jacobian 必奇异。合法 X 与 h 给定后，原三条率指定 a=h*r_a、b=h*r_b、d=h*r_d。须同时满足 R_u=u-h(r_a+r_b)=0 与 R_v=v_net-h(r_a+r_d)=0；a=h*r_a 后 b=u-a、d=v_net-a 才是三通道闭合。

## 实際固定次数机械映射，不是假定平衡根

solid.py:345–370 的 z0=eta+beta_T(T)+beta_phase(f,ns)。每次 j=0,...,m-1，m=root numerics.mechanical_iterations=8：

Vp_j=Vp0 exp(z_j)，Es_j=Es0 exp(2z_j/3)，cap_j=(2/3)Es_j/Vp_j，Pgas_j=sum(ng)RT/Vp_j，B_j=ns·v+Vp_j。

常模量分支 F_j=K0[(B_j/B0-1)-thermal-eta]+prestress+P-Pgas_j+cap_j，D_j=K0 Vp_j/B0+Pgas_j-cap_j/3。当前 m_dry=2/phasecontrast=4/active=.3 使用 variable-modulus 分支：

K_j=K0[(ns·dry_v)/B_j/fdry0]^m_dry exp(-g C_phase)，eps_j=B_j/B0-1-beta_T-eta+initial_elastic_strain-beta_phase；stress_j=K_j eps_j+(B0/2)K_V eps_j²，tangent_j=K_j/B0+2K_V eps_j+(B0/2)K_VV eps_j²；F_j=stress_j+P-Pgas_j+cap_j，D_j=tangent_j Vp_j+Pgas_j-cap_j/3。z_{j+1}=z_j-F_j/D_j，最后只按 z_m 输出 Vp/B/Es/cap。详见 solid.py:380–417。

这是一串 8 次显式代数复合。源码没有在 unpack 中以残差容限迭代到 F=0，根参数也说明最终 force residual 另报。任何沿 q 的真实导数必须递推 z'_{j+1}=z'_j-(F'_j D_j-F_j D'_j)/D_j²（各导数含 z_j、组分等依赖）；未求导/未调用 Jacobian。只有另证 F=0 且平衡导数非零后，才能使用平衡隐函数 B'=-F_q/F_B；不能替换当前映射。D_j 非零、正有限 dry/bulk/pore、有限分支等是连续图域的必要条件，源码表达不给整个候选 q 区间的全局界或收敛证明。

固定 u/J/T/其他凝聚物时，q+z=Q+Z，w=W+u，N不变，所以气体总 mol 沿 q 切片恒定；变化仍通过 char=c_n+u-Q+q、凝聚体积、dry fraction、K 与机械复合影响 pore/pressure/骨架 mu。不能据气体总量固定就冻结孔体积或应力。

## 三条真实率、完整化学势与零边界

gas.py:652–681：mu=h(T,f)-T*s(T,f)，凝聚物再加 (Pgas-P-cap)*v+skeleton_mu，气体加 RT log(p_g/Pr)；water/kaolin 还用原 retention/binding 偏导。三条率直接读相关四凝聚/气体势，其中 H2O 是气体，因此 water-binding 的 water/kaolin 势本身不直接进入三通道 delta_g；它们仍通过其余反应/热输运影响完整 X。保留整段势构造，不加独立反应热。

delta_g_a=mu_CO2+mu_H2O-mu_organic-mu_O2；delta_g_b=mu_char+mu_H2O-mu_organic；delta_g_d=mu_CO2-mu_char-mu_O2。G(A)=-expm1(A) (A<0)，否则0，A=delta_g/(RT)。有限实态 G 属于[0,1]，在0连续但导数有拐点。原 k_a=A_a exp(-E_a/RT)G_a*(p_O2/p_ref)^m、k_b=A_b exp(-E_b/RT)G_b、k_d=A_d exp(-E_d/RT)G_d，r_a=k_a o、r_b=k_b o、r_d=k_d c。各参数都是原根 assumed：A_a=A_b=A_d=1e6/s，E_a=E_d=100000J/mol，E_b=110000J/mol，m=1，p_ref=20900Pa；完整 value/unit/range/source/status/note 在 JSON 引用，不创建新运行参数。

原 rate 实际依赖 T、organic/char donor、四气体（partial/总pressure）、所有影响 ns·v/dry volume 的凝聚物、eta、phase/carrier、原材料与参考量；p_O2=ng_O2 RT/Vp，condensed mu 的骨架项由 solid.py:407–417。A/E 相同不推出 k_a=k_b+k_d，affinity 的加法也不推出 G 或率相加。它们与原 transport/water/thermal/mechanical/phase 方程须使用同一个 X，而不能由净量只保留两个自由度。

| 边界 | 真实原式和可得结论 | 有效条件 / 不可扩大之处 |
| --- | --- | --- |
| 正初始 organic 耗尽 | o=o0 exp(-f4)，dot f4=(k_a+k_b)*1_{o0!=0}。o→0 等于 f4→+infinity；有限其他因素时 r_a,r_b→0 | exactzero 不在正初值有限图；有限时间耗尽没有新证明，其他势/机械域必须有限 |
| 初始 organic=0 | 原 initial!=0 mask 令 dot f4=0，o=0，r_a=r_b=0 | 保留原 f4 gauge，不计算 log(0/0)，不强设 log0=0 |
| char=0 | dot c=k_b o-k_d c；c=0 时 birth=k_b o≥0，oxidative loss=0 | char pure-proxy mu 没有 log c 项，机械等有效时有限；允许零出生。连续不变性是有解及有限合法域的条件结论，不是 BDF 非负证明 |
| negative incoming char | 同一线性式/净映射保留负号；若 birth=0，BE c+=c_n/(1+h k_d) 仍负 | 不能 clip/seed/abs 迁入正域、不能宣称无损恢复。旧 negative FAIL 保留 |
| O2→0+ | p_O2→0、mu_O2→-infinity；其他相关势有限时 delta_g_a,d→+infinity，G_a,d→0，且 m=1 氧因子→0，r_a,r_d→0 | 要 T 正且有界、Vp 正有界、donors/骨架和 CO2/H2O 等势有限；只给 oxidative rates 的单侧延拓，不是完整 native event 的 q=0 可调用状态 |
| exact O2=0 | gas log 需 -infinity，原 dng/ng 及 log(partial) 不能有限表示该点 | 原四气体 positive-initial log 图只覆盖严格正库存；不置 log0=0，不新增零边界分支 |

G 对有限 affinity 连续、局部 Lipschitz；相分支/变量模量/transport 同时有效才可能使完整切片连续。若 CO2/H2O、孔/机械也趋奇异，上述单变量极限不能沿用。原 complex-step Jacobian 只对原物理列和当时实部活动分支扰动（gas.py:891–901），不证明跨零、跨 active-set 的新 residual 导数；原 diagnostic 热/携能/extent 等列为0，不代表可丢账本。势导数图将 B 显式独立，只用于 fixed-volume 梯度；solid.py:601–644 明示该图虚扰动不重解机械。它与本轮物理 unpack 的 B 消去不同。

## 共同氧域及实际阻碍

为审查固定 chi 的候选，仅在固定 u,J,T、其余独立未知与原 branch/context 后令 q=q+、v_net=Q-q。u∈[0,o_n]，c(q)=c_n+u-Q+q，z(q)=Z+Q-q，w=W+u，N固定。

库存层的氧区间为 q_L=max(0,Q-c_n-u)，q_R=Q；Q≥0、c_n≥0、o_n≥0 且四气体、其他凝聚物/孔/T共同合法是前提。原有限图实际取 q>0、z(q)>0、w>0、N>0、正初始 organic 时 o_n-u>0；char可取0。若 Z<0，CO2还要求 q<Z+Q，可能切掉 q_R；其他有符号 J 使区间空或分裂也未排除。实际机械所有8个D及热力/输运的定义域还要逐点满足，不能只用 mol 非负当全域。

F_v(q)=q+h[r_a(X(q))+r_d(X(q))]-Q= -R_v。分类如下。

| 命题 | 分类及精确边界 |
| --- | --- |
| q_L 的 char 约束与 Q 上界 | 恒等成立，来自 c(q)≥0 与 v_net≥0；不是无条件完整图域 |
| q_R=Q 时 F_v=h(r_a+r_d)≥0 | 条件成立：q_R 是实际有效端，非负 donors、h>0、原有限非负 k；Z≤0 可排除右端 |
| q_L=0 时 lim F_v=-Q | 条件成立：Q>0，其他共同域可连续延拓至0，oxidative rates→0；exact0不在原有限log图 |
| q_L>0 时 c(q_L)=0、r_d=0 | 恒等库存关系与有限 rate 条件成立；此时 F_v(q_L)=h*r_a(X(q_L))-(c_n+u) |
| q_L>0 时左端 F_v≤0 | **具体阻碍**：原表达不给 h*r_a≤c_n+u；其符号未定。不能把不可行 q=0 的 -Q 当有效左端符号 |
| 若合法端之间连续且真正左右异号，则有内根 | 条件成立的一维 IVT（严格异号才保证内点；非严格可只有边界根）。前提尚未获整个原切片资格 |
| 当前 8 次 Newton 切片全区间连续且有界 | 尚未证明：中间 D_j 可为0/域失效，无来源给全区间非零界；不能替换已收敛平衡图 |
| F_v 全域单调或根唯一 | 尚未证明：char体积/骨架/孔反馈、CO2竞争/full G 拐点不定导数号；本轮无求根/差分/数值反例 |
| 一个有效 F_v 根完成联合三通道步骤 | **具体阻碍**：F_v=0 不要求 R_u=0，也不保证 a=h*r_a≤u；b=u-a 可负。只有联立 R_u 与其他共同方程才给闭合 |
| 计量 rank2 导致联合 Jacobian 必奇异/根非唯一 | 不成立的推论；lambda方向库存不变不移除三原动力学方程的单位项。非线性全局存在唯一仍未证明 |

这否定“每个固定 chi/u 均可用0与Q端点保证合法氧内根”的普遍论证；没有证明整个联合问题无解，也没有把当时 tiny negative 的具体内部成因归于单一率/阈值。即使选择恰能同时解 R_u/R_v 的局部条件，仍不能推出完整 heat/gas/eta/phase/其他反应输运联立存在唯一。

## 路线收束与物理验收边界

本轮在上述 char 左端与 R_u 闭合阻碍收束。暂不实施 joint-BE/Patankar/log-char/投影方案，也不提出另一广泛符号阶段。要实现将不得不改变旧 BDF/NDF1–5 的方法、零边界/状态图、通道累计和 Jacobian 版本，原负 checkpoint 不能 lossless迁入非负域，而且完整独立离散产熵 Ip 与 U/S 链未获证明；付出已超出这个局部合同能资格的范围。

唯一下一建议：正式再采用/核对 P80 已登记而未采用的最终 cooling_hold 时间步比较范围，使用原 refined cooling 实际端点继续原 cooling_hold，和已存 coarse 最终端点比较；不重算前缀、不是 sweep/24UQ/拟合。此处不重读候选文件、不创建执行接口或预算/窗口，不发 CLI、不自动采用。未来只比较已约定最终产品及原账本/时间差，保持 signed库存和严格非负FAIL，不能拿较小误差授模型全PASS；时间比较也不代替网格/连续峰温/材料资格。若未来证据仍失败，就如实保留误差界，而非重新进入多代搜索。

完整热力 targets 仍为 R_U=Delta U-Qext-Hboundary-Wext，Wext=-P sum(Delta B)；R_S=Delta S-Ie-Ip。Ip必须由原各耗散机制独立定义/积算，不能事后设 Ip=Delta S-Ie 得 R_S=0。单点 rate*delta_g≤0 不证明离散熵非负；反应/相变热仅按原共享 caloric/mechanical链计一次。原完整U/S、携气/液水焓熵、外压功、机械相与网格/连续温差资格保持未完成；fixed-volume potential chart与物理机械图的区别不是 PASS。

原名义干燥0.1358920787402553%>0.1%仍FAIL，d8bc6f1b的0.13505646%是另一历史版本；本轮没有工艺尝试。coarse/refined负char最小值分别-1.2646807323299508e-18与-8.581861576534481e-20mol、负格数5→6是P81/P82历史，不是新测量；严格nonnegative=false。CaO零预算relative=null/passed=false/undefined_zero_budget，Ca元素账本不能修复相门槛。P34/P40 peak、P44 grid、P45 float、P50撤回、P51序列化及既有资源FAIL都保留。最新最终time/grid/连续peak/三方案/反演资格未完成；旧24UQ固定3.75e-14m²不能覆盖新机制。

758完整参数=144 literature/614 assumed/0 measured不变，高温portlandite/calcite/H2O黏度超源域解析延拓、粉料到砖类比、相/动力学工程假设与synthetic拟合仍待实测；没有实材/生产资格。整模型完成=false。Git普通原分支后继与Drive一次必要小增量只授交付，metadata≠实际恢复，本轮恢复0，历史20GB/GitHub容量未解决。实际耗时、full budget、Git/Drive最终回执在本轮 final-delivery-state.json 分列；科学wall/CPU=null。
