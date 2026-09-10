# 可实现合同：来源湿态同一available V条件压力比较

本合同取代上一候选中尚未证明的“直接保留名义fluid即足够”捷径。无EOS/积分或参数修改；仅固定原来源模型的数值合同。保留原eV、eT、B与1e-4Pa阈值，旧失败与证书不重写。

## 1. 比较目标及真正的原单体范围

定义 v*(T,p) 为原声明数值误差包络所围住的光滑稳定液体体积函数，满足全域 vP<=0、|uP|<=B、原热量/volume error声明。定义 p_i(T,V) 为精确方程
G_i(T,p,V)=Nl_i*v*(T,p)+Ng_i*R*T/p−V=0 的唯一根。
原SourceInversePressure 的conditional目标是此函数在原温度逆解箱和体积箱中的压力，不是任意未来求解器的任意停止输出；其 mechanical.final_numerical_pressure_bracket 仅是rounded forward function的数值括区，明确排除EOS error。不要将后者当物理根证书。

新joint仍覆盖两端上述条件根的差（同一V、各自完整温度箱），并额外保留独立报告压力/机器残差裕量。有限个观测不能证明v*稳定或真实污泥适用性，source_certified/material=false。不承诺任意重新运行求解器、不同容差、不同EOS的输出落在同一joint界。

## 2. 输入与实际对象准入

Actual端点A/B: 已检查SourceInversePressure，Nl>0、同gas_ids/R、固定kg/source caloric与energy identity，原T/P/eP/eT/envelope完整绑定。显式shared声明只允许 a.storage is b.storage is declaration.storage 且同一 volume对象；当前状态U与N允许不同，两个空间cell不因相同digest成为同参数。

严格重算wet_fluid_pressure_bounds的global/extra/total，保存字段必须逐值等于原生产结果；任意超额拒绝新入口、保留原单体证书。实际fluid.pressure_error_bound_pa绝不能替换为其较小nominal下界。总界projection=abs(F(total)−F(actualfluid)−exact_recomputed_extra)保留。

Ng=ΣFraction(each saved binary64 ni)，R为实际声明的Fraction(Rfloat)。Nhat=math.fsum(ni)及后续nRT只用于显式数值误差，不改变物理Ng。

## 3. 最多4实际液体观测与根存在证明

取两端原报告温度保守箱 [Pi−ePi,Pi+ePi] 的hull，向外取binary64得共同支持J=[Jlo,Jhi]；J必须在两端原机械/水/数值包络P域交集，两个报告T在同一原域。固定J后仅评价(TA,Jlo),(TA,Jhi),(TB,Jlo),(TB,Jhi)，最多4次；同实际water实例/精确T/P/phase输入才允许去重。不是4次构造；已有合法同输入观测可显式复用且不冒充新独立求值。

每点保留完整WaterState、actual input、backend/source assets、reference、T/P/phase、density/molar_mass、原declared v error、表示转换余量、成功/失败、调用序号。两端T精确不相等即不能合并。源/域不合法、计算失败或资源中断保留全部前缀，禁止更换J反复尝试直到过关。

原εv声明必须明确覆盖native返回的v_float=fl(mass/density)与v*之差；若原provider声明只覆盖另一量/另一路转换，应加有证明的转换舍入或拒绝。用 v_float±εv 建立各点v*包络。严格稳定vP<=0是全J声明/来源前提，而非4点推断；各Ti的全J v*区间可取[lower at Jhi, upper at Jlo]，要求正。

四点另做每端根存在符号（全部共同V）：
Nl_i*v_lower(Ti,Jlo)+Ng_i*R*Ti/Jlo−Vmax >=0；
Nl_i*v_upper(Ti,Jhi)+Ng_i*R*Ti/Jhi−Vmin <=0。
成立则连续、严格负导数给∀V存在唯一根且在J。失败unresolved，不将旧rounded bracket冒充此证明。非零温度续延须有严格域余量。

D和Γ都用完整J，不混用未观测I_B端点。J就是保守B根支点集合，也包含A/B根间整条线段。

## 4. 无伪造solid_mol的精确报告T根差

D(p)=NlA*v*(TA,p)−NlB*v*(TB,p)+R*(NgA*TA−NgB*TB)/p，p∈J。
共同V项消去。液体按两个完整v区间做差（未知数值误差相关性保持独立），gas项按有符号常分子/J两角点。得到Dinterval。
c_i=Ng_i*R*Ti/Jhi²，c=min(cA,cB)>0；因vP<=0，原单调方程mean-value theorem给所有共同V的报告温度根差 <=max(abs(Dinterval端点))/c。无solid mol、bulk、J机械Jacobian字段。

## 5. 全J机器残差Γ：不能用名义fluid自动替代

下面是明确可执行的保守体积残差界，不重新调用EOS。定义S(x)为向上可表binary64点处一个完整ULP，使用Fraction确定上取点；正值/有限/正常数范围，无法建立有限界则unresolved。完整ULP覆盖round-to-nearest，fsum另外用2S保守覆盖最后求和/可能double-rounding；所有下列量以Fraction相加。

对端i，原native液体计算是fl(fl(Nl*m)/rho_hat)，不是Nl乘已rounded摩尔体积。令 vStarMax=本端Jlo的v*上界，e=全J原εv（取有效统一声明，不从4点最大值推成全域）。
Wcap=2*(vStarMax+e)>0，rho_min=m/Wcap。
理由：全J fl(m/rho_hat)<=vStarMax+e，正常数rounding保证精确m/rho_hat<=2*该上界；不是新增材料参数。故精确m/rho_hat与v*误差 <=e+S(Wcap)。
A=Fraction(fl(Nl_float*m_float))；deltaA=abs(A−Nl*m)。
GL= Nl*(e+S(Wcap)) + deltaA/rho_min + S(abs(A)/rho_min)。
Lmax=abs(A)/rho_min+S(abs(A)/rho_min)。

NRT=Fraction(fl(fl(Nhat*Rfloat)*Tfloat))，deltaNRT=abs(NRT−Ng*R*T)。此精确差含Ng fsum及两乘法全部实际舍入，不以近似γ替代。
GG=deltaNRT/Jlo+S(abs(NRT)/Jlo)。
Gmax=abs(NRT)/Jlo+S(abs(NRT)/Jlo)。
GS=2*S(Lmax+Gmax+Vmax)。
Γ=GL+GG+GS。

于是全J、全部共享V，|Ghat_i(p,V)−G_i(Ti,p,V)|<=Γ，条件是原εv包络对全J native返回值有效且这里的实际算术操作序列一致。V是模型共同实参数；若未来机器输入把V再投影，额外|Vhat−V|须另加，不能默认为零。当前只需保存名义V0的实际运行以及数学共同V根，不承诺另一次不同V机器运行。

使用此Γ无需把vP幅度当已知：只用稳定单调+全域v误差给rho下界。若v*或native ratio不满足正正常域、端点reference mass不一致、源单位转换误差不清楚，拒绝而非编系数。

为覆盖当前原报告机器点与同V0条件根的联系，验证保存Pi∈J，重算其实际closure_diagnostics/residual，取
zeta_i=(abs(saved represented volume_residual)+Γ_i)/c_i。
根存在J及mean-value theorem说明当前机器Pi与报告T/V0条件根距离<=zeta_i。保留
η_i=actual_fluid_pressure_error_i + projection_i + zeta_i。
actualfluid或Γ可能重复，但独立全保留；任何削减需新证明。这样不依赖“nominal fluid在全J仍成立”的错误推断。Γ也不能代表任意停止误差：仅使用本次saved residual；未来运行必须携带其新实际残差。

## 6. 温度桥接必须从新已证起始箱继续

新根符号证明给报告T根在共同J，未必落在各自原Pi±ePi。故不能不加检查直接复用旧Li。
令r0_i=max(original ePi,abs(Pi−Jlo),abs(Jhi−Pi))，原nl/ng/R/B/T/eT/域不变，用纯propagate_declared_pressure从r0_i建立global和bootstrap续延。失败unresolved。Li_used=max(original Li,new Li)，保留原Li*eTi另列，新增热余量=(Li_used−original Li)*eTi>=0。
这一步无需EOS、无需改变eT，不从湿态U对V独立作错误论证。它在原光滑稳定/|uP|声明下把全部共同V的根续延到各自原完整T箱。所有global围栏严格域内且bootstrap包含检查沿原规则。

最终 B_joint = maxabs(Dinterval)/c +ηA+ηB +Li_used_A*eTA+Li_used_B*eTB，向上float仅用于展示，exact Fraction作为判据。旧 independent完整P界、旧gates和old event不动；新opt-in selected=joint-only，不跨不同余量目标取min。通过只意味着声明模型下新的条件数值压力比较，源/材料/液体方向资格不升级。

## 7. 最小接口和有限验收

数据对象：SharedWetVolume(live storage/volume与原内容绑定)；WetPairSupport(J选择输入与向外投影/域)；WetVolumeObservation(实际water/T/P/phase/state/ε及原始调用证据)最多4个；PairResult(每端v区间/符号界/Γ分项/zeta/actualfluid/projection、D/c、旧/新热余量、原旧界、新joint、status/理由、source=false)。

先固定support和待求点，再调用至多4次实际state_tp，结果只从这些冻结点构造；后续check被动重核，不重新EOS。可提取旧paired_pressure中的纯区间加减/有符号除法/残差除compliance，由旧入口保留原golden和input JSON字节；新source caller不创建假固体字段。

制造反例：①同值独立V对象拒绝；②同T同N但独立ε不消失；③负gas numerator与跨零D四角；④4点符合nominal但root signs失败；⑤vP观测负不构成全域证明；⑥total surplus拒绝；⑦新J比旧箱宽导致newL增加，旧L-only构造被拒绝/扩张；⑧near-cancellation全Γ仍非零；⑨rho或算术范围不normal拒绝；⑩一个wet格不通过不能由dry shared掩盖。

原N3热预算审计仅说明旧热余量未先耗尽阈值；本合同新增η/新L/液体区间可能仍使结果失败，不承诺通过。不改变原eV、门槛、材料或源误差设定。

正常数围栏补充（实现应检查）：不仅Wcap，还需 vStarMin>εv，并取Wfloor=(vStarMin−εv)/2>0。要求Wfloor、Wcap、m/Wcap、m/Wfloor及由此得到的液体乘除和gas除法的整段最大/最小幅度可在正有限binary64正常数内保守包住；失败unresolved。这样“全J正常范围”不是只凭四个点正常就推断。过于苛刻可拒绝小库存，不得静默改用未证明的subnormal公式。原物理根证明本身允许小数值，但新机器误差合同单独有限制。
