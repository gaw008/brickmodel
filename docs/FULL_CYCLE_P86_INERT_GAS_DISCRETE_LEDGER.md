# P86 原 N2 库存与边界账本的离散兼容性

**结论：本条链未发现具体代码错接或通量漏项。** 连续 N2 库存与边界账本使用同一次 rates 的同一通量，精确算术下守恒。实际 SciPy BDF/NDF 在线性历史上更新 log 库存坐标，再以 exp 解码，方法没有自动满足物理库存与累计边界的离散链式恒等式。这是方法误差候选；已存端点不能识别实际总残差的唯一原因。此次只读源码、已存 JSON 和纯算术，生产调用、科学窗口均0，science wall/CPU=null，未新增生产源码、checker、solver、tests、fixture、SHA或科学状态。

## 1. 实际物种、尺度与同一次通量

FullCycle.__init__按根species原顺序取gas：O2/N2/H2O/CO2，N2为索引1。原7条reaction的N2计量系数全部0；其余全部物种的formula没有N，所以N元素总量为2*N2全域库存。可选direct反应是lime_dehydration减decarbonation，其N2列也为0；当前实际branch direct=false。不因inert标签代替这些实际核对。

gas_state原式 n[i,s]=initial_gas[i,s]*exp(x[i,s])，x是维数为1的原native log槽。initial_gas是构造后被strictloader恢复的固定库存参考，不是当前pore*P/(RT)，机械孔隙变化进入压力和通量，不能另给dn添加假想体积源。实际12格、4gas，gas_offset=132、extent_offset=180、last=264，总native y275；N2槽为144:156（0-based），in/out槽为265/269。原nscale=4.650198977282131 mol，initial_gas每格N2=7.559037075092483e-5 mol，37项numeric以及partition/phase0/liquidreference保持。

令phi_i为第i格右面的**向右**N2通量mol/s，左对称面phi_-1=0，右外面phi_(M-1)。transport一次生成molecular+Darcy的单一face数组：相邻两格共享同一数。历史pair分子分支的species成对交换和为0；wall-friction分支可以有非零总分子流，但每个species的内部空间面仍同号对象进一格、出另一格。不把两种抵消混为一谈。Darcy按velocity符号取donor，仍进入同一face数组。

rates原行695–696给 r_i=dn_i/dt=-phi_i+phi_(i-1)，reactionN2列0。精确算术求和为sum r_i=-phi_(M-1)。_rhs_event只调用一次rates，并取同一个result的dng/gas写x_dot；取同一个gas_flux[-1]写两个累计槽：

```
dx_i/dt = r_i/n_i                                  [1/s]
dB_in/dt  = max(-phi_(M-1),0)                       [mol/s]
dB_out/dt = max( phi_(M-1),0)                       [mol/s]
Q = B_in-B_out = nscale*(y_in-y_out)                [mol]
dQ/dt = -phi_(M-1) = sum_i r_i
d[sum_i initial_gas_i*exp(x_i)-Q]/dt = 0
```

这里只有一个开放空间外边界，两个是in/out累计槽；左面为对称闭边界。原实际代码对.real做方向选择，在真实状态上即上述符号拆分；它不是库存裁剪。连续公式须在有限、正n及原通量/状态有定义的域内使用，不能授所有Newton/复杂步或源越域资格。内部面分组相消与浮点加减/全域归约可有舍入差，不断言机器位级严格为0。

endpoint_inventory从同一native端点解码，gas逐格sum形成库存，全局原native累计槽*nscale形成B_in/B_out；interval_ledger对给定起止做signed差，不重新积分flux，也不再生成rate。P78真实阶段点、P80冷端点和P85保温端点参考同一原context；其新declared初始reference不恢复原P68未保存t0。

实际原模型是ThermoelasticFullCycle(FiniteGasFullCycle)。其full_cycle_solid.py345–351的unpack也用同一fixed initial_gas*exp(nativegas槽)；537–548的_rhs_event先调用上述super event，再仅写liquid_coordinate10槽（120:132），未覆盖gas132:180或boundary264后的槽，rates/gas_state/transport没有子类重写。这一实际继承分派已经纳入，未把未使用的父类路径冒充当前实现。

## 2. 实际本机 BDF/NDF 更新，不把轨迹当固定 BDF1

本机离线SciPy1.18.1 bdf.py的MAX_ORDER=5，实际order自动1–5，采用quasi-constant步长；改变步长/缩到t_bound/失败减步/变阶时change_D以R(factor)*R(1)变换完整D历史。原gamma_q=sum(j=1..q,1/j)，kappa=(0,-0.1850,-1/9,-0.0823,-0.0415,0)，alpha_q=(1-kappa_q)*gamma_q。q1–4有NDF修正，q5的kappa为0；不能只用后向Euler解释全部实际端点。

对某一实际接受步，在所有既定history重缩放后，记a=alpha_q，G_X=sum(j=1..q,gamma_j*D_j[X])，P_X=sum(j=0..q,D_j[X])，c=h/a。实际Newton系统为

```
X_new = P_X + d_X
d_X + G_X/a - (h/a)*F_X(t_new,X_new) = eps_X
a*(X_new-P_X) + G_X = h*F_X + a*eps_X
```

eps_X只是用于分析的**未测量**接受步代数残差，定义正号如上；不是新增程序值，也不是假定为0。Newton最多4次；以atol+rtol*abs(predictor)缩放的correction范数、迭代收敛率终止，之后error_const[q]*d接受步；不是验证上述非线性残差严格为0。实际代码先计算f、加correction再终止，可接受的末点f未必被另一次重新评估。实际y与独立累积d、LU解、history更新/重缩放还有浮点项。root1e-5/1e-7是native坐标容差，不能当物理mol残差直接上界。

对Q是上述两个线性累计槽按固定nscale组合，P_Q、G_Q亦是其相同组合（精确算术）。对N2各格，n_i^+=a_i*exp(x_i^+)且F_xi=r_i^+/n_i^+。same-event通量求和消去右边界后得到实际方法关系：

```
Q^+ = P_Q-G_Q/a
      + sum_i n_i^+*(x_i^+-P_xi+G_xi/a-eps_xi) + eps_Q

E_step = sum_i(n_i^+-n_i^old) - (Q^+-Q^old)
       = sum_i[n_i^+-n_i^old-n_i^+*(x_i^+-P_xi+G_xi/a)]
         -(P_Q-Q^old)+G_Q/a
         +sum_i n_i^+*eps_xi-eps_Q
         + floating/evaluation/reduction terms
```

这是对原NDF预测、alpha/gamma与各自**实际线性历史**的符号关系，不需构造或评估新的库存history。指数映射没有强制使右式为0；P_Q/G_Q与P_x/G_x在历史变换下不是彼此的指数像。startup D1=hF、变阶/重缩放和原不同分量历史也必须在内。没有假定原实际D都是固定等距过去节点的标准backward difference，也没有假定全轨迹的order、h或eps已保存。

也可只在符号上定义n_pred=a_i*exp(P_xi)、d_i=x_i^+-P_xi，实际corrector的非线性缺项更直接为：

```
sum(n_i^+-n_i^pred) - (Q^+-P_Q)
 = sum_i n_i^+*(1-exp(-d_i)-d_i-G_xi/a)
   +G_Q/a +sum_i n_i^+*eps_xi-eps_Q +floatingterms
1-exp(-d)-d = -d^2/2+d^3/6-...
```

n_pred未计算，不是原已存状态。此corrector局部bracket的符号或O(d^2)量级不能替代全部step缺项：相对old端点还包含predictor的物理库存不匹配及P_Q-Qold，G历史也同时进入；更不能把它的符号或阶次直接解释为本次全程残差。

为了给出一个明确的链式缺项，在另一个**限定情形**：纯BDF、已一致的固定步长q阶节点history、无NDF/startup修改，令LZ=sum(j=0..q,a_j Z_(m-j))，sum a_j=0，Lx=h*r/n_m，LQ=h*sum r。delta_ij=x_(i,m-j)-x_(i,m)，则

```
C_exp = sum_i [L(n_i)-n_(i,m)*L(x_i)]
      = sum_i n_(i,m)*sum_j a_j*(exp(delta_ij)-1-delta_ij)
      = sum_i n_(i,m)*sum_j a_j*(delta_ij^2/2+delta_ij^3/6+...)
L(sum n-Q) = C_exp + nonlinear-solve/rounding terms
```

没有在本阶段计算任何新exp/log或合成delta。此缺项不是恒等0；在光滑正域、相应q阶一致的history、受控步比及足够精确非线性求解条件下，其未除h形式可有O(h^(q+1))的局部截断量级，除h后O(h^q)。这不是对实际变阶NDF全部步骤的已测阶次或总误差界；实际对应关系是上面的P/G/a接受步公式。q1纯BE理想情况下E=n_new*(1-exp(-Delta x)-Delta x)<=0，但原NDF q1有kappa=-0.185，且含历史/迭代/舍入，不能把这一符号结论施加到P80/P85。

## 3. 已存端点证据及分母

配套JSON逐字保留P78粗cooling/cooling_hold、P80 refined cooling、P85 refined cooling_hold的N2完整账本、N元素账本及原分母。不是重做此前已通过的全账本算术复核。

| 区间 / 条件 | N2 signed残差 mol | N2预算relative | N元素relative |
|---|---:|---:|---:|
| cooling / 60s | +7.381019059896337e-7 | 3.6230526509609004e-4 | 5.086555604574911e-4 |
| cooling / 30s | +3.691999369993121e-7 | 1.8122555723350852e-4 | 2.5452827881964555e-4 |
| cooling_hold / 60s | -6.628582699765885e-8 | 2.9269919853570203e-5 | 7.30756955098542e-5 |
| cooling_hold / 30s after refined cooling | +2.97338059863754e-8 | 1.3129579546513433e-5 | 3.277953449515219e-5 |

N2预算分母=max(abs(N_start),abs(N_end),sum(abs(each signed reaction source)),abs(Delta B_in)+abs(Delta B_out))，单位mol，门槛0.001。N元素分母=max(P78新reference的N原子mol, 2*Delta B_in[N2])，单位mol_atoms。N2初始归一化分母为P78新reference N2=0.0009070844490110978 mol，只诊断，threshold=null、defined passed=null；不能混成独立PASS。零分母仍relative=null/passed=false/undefined_zero_budget。

粗/加密cooling的Delta B_out实际分别为-3.7176887788181387e-7和-1.3007064087070062e-6 mol，**原负增量保留**。连续B_out导数非负不保证高阶多步离散累计槽单调；这是独立的已存非单调迹象，不能抹为0，也不能据此断言物理外边界漏接。实际内部步/Newton residual/history未持久化，不能从末点重建或逐步分摊原因。

误差下降与保温残差翻号说明两种数值条件产生不同账本误差，不证明唯一成因、总阶次或误差全部来自exp链式项。char为另一条线性化学坐标链，本次N2方法结论不是char负库存成因；暂停BE/char理论保持暂停。

## 4. 单个下一数值范围建议和真实缺口

建议下一独立范围：**原sintering115200→126000s的一对60s/30s条件比较，补取得该热段原120s观测网格上的温差峰值证据**，而非重复两段冷却比较。使用P71实际reactions端点完整y275/source51/context37；P78中同起点库存与新reference用于两个新终点区间账本。P73已有coarse末点但未保存区间采样温差，因此峰值比较确实需要这个短热段的coarse配对，不重跑已存前缀或完整8阶段。

原peak定义不仅是max(T_cells)-min(T_cells)：是原rates.surface_T、原center_temperature(T)与全格T的合并span，再在原output_step=120s样本取max。10800s区间含起止共91点/方案，两方案共182个sample rates/center helper；不能把仅cell温差、仅末点或未保存历史当成原peak。即便未来完成，此为原**采样**峰值的该段时间敏感性，不是连续时间极值，也不是全程时间或空间PASS。

下一接口尚未存在：full_cycle_continue只t_eval=[end]且采用saved参数，positionalroot改max_step不能覆盖saved60s。需要先独立采用一个最小additive producer55和单独sintering_half_step policy30s声明；old54/strictloader不改，明确input51/output55及original/effective完整case。当前不实现、不运行，候选仅建议；不得借P86静态完成启动。

未来forecast：1job/worker/attempt内2strict loads/2logicalctors、0initial、2原BDF从同一实际起点独立60/30、2endpointdecode/completevalue/interval；已有start/reference不重求。原120s观测网格的182 public sample rates、182 center helper单列，不藏在endpoint值计数内；两个solve内部RHS/Jac及其他primitive次数未知，需实际记录。0summary/gradient/dynamics/projection/fit/UQ/搜索。只保留两完整终点、峰值witness和必要汇总，无全场入Git。

预算：P71输入真实1,376,881B，P78真实483,536B；P71完整config当前JSON序列化628,457B，未来两case/输出55源码/原context/峰值汇总都按实际copies计入。P73过去coarse单末点wall6.7131872079s，不能据此断言新30s+182rates或成对全过程在120s内。完整运行时间/峰值接口序列化尚未测量。建议未来独立300s firstlaunch→finalreap上限、四science文件总4MiB、full64MiB且原reserve29,360,128B不减；这些只是新候选policy上限，未采用，需根独立参数声明、接口完成后fresh全字节gate。缺口若不能满足则停报，不搜索、不借旧headroom、不无限理论。

## 5. 验收与交付边界

0生产科学调用，science wall/CPU=null；静态行政真实耗时在JSON/finalreceipt。原54源码、758完整records（144literature/614assumed/0measured）、原50历史sourcepaths、两冷段独立声明及全部物理/程序/context保持。原strictchar/refinedcarbon负号、drying0.1358920787402553%>0.1%、CaO零预算nullfalse、P45/资源/all历史FAIL、高温assumed、wholefalse全部保持。本次没有改变任何物理数值验收判定。

正常原branch后继及原Drive一次必要静态增量另final-delivery-state；metadata不等恢复，实际恢复0，压缩源保留。历史20GB/GitHub容量警告未解决，没有新历史aggregate扫描。一次行政species-list schema错误已留证并按实际schema纠正，0科学；没有自动审批拒绝。

另一次行政协调证据相对路径读取错误留证，随后按task-17准确路径读取。独立协调符号审查使用Q=out-in，相对本文Q=in-out符号相反、公式一致；其原文本全字节计入本轮。没有据协调意见新开科学或理论阶段。
