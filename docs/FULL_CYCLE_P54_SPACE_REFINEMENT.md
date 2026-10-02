# P54 保存参考分区：一次13→26格空间比较

P54独立一次13→26格保存分区空间比较已真实保存并闭窗（2026-10-02T18:08:35.597727+00:00）。仅读复用P53真实13格/.05s/10s结果，不复制整份或重跑；原14faces形成13区间逐段二分至27faces26格，原面保留偶数索引，area/halfthickness与物理/298.15K/Ca1/direct通道/BDF/rtol/atol/max_step.05/output.5保持。新初态仅native model生成，不插值/rebin/seed/clip/y0覆盖。实际17:58:45.450309至17:59:03.467780UTC（洛杉矶10:58），监督18.017544333s/childCPU17.791956s，rc0回收/未超时；1job/worker/attempt/constructor/原solve_ivp，4106RHS含10Jac，另21summary rates，constructor内部1原分区primitive、0额外producer。唯一900s截止18:13:45.450309UTC未重置，初必要输入/冻结源/输出2032140B<3145728B。原四空间指标按max(abs(refined26),原floor)<原.02全部通过，最坏5.288244252e-03（0.528824425%）；收缩与峰温差使用原.001/1K，raw无floor分别.0195746832/.0182206191仅描述，directextent变化也无新阈值/资格。质量/元素/完整U最坏1.469543941e-08、四gas最坏8.515348875e-06、native累计熵3.001470368e-09<原.001；Cc/OH通过、CaO零预算null/passfalse整体相不PASS。strict仅21保存点，独立完整signedS累计分解/势导数未资格；几何signed成对/全局舍入差保留，无几何容差PASS。根634=144literature490assumed0measured，旧624完整records/P49/P51/P52/P53live合同/科学核/名义12格mode0Ca0sampling0directoff不改。P45/P34/P40/P44旧FAIL、P50两项错误初态PASS撤销、P51输出失败及名义余水.135892078740%>.1%保留，0新名义尝试。只授本固定空间对的四指标，不授fine26时间/一般空间全状态/八阶段/三方案反演UQ/完整CLI/whole模型；GitDrive恢复历史容量另列，不分配P55。

本轮复用原 `scripts/run_saved_reference_transient.py` 和实际冻结47文件，0科学源码更改。根新增10完整policy/assumed记录（7预算、subdivisions2、cells26、faces27），原624完整记录保持，根名义及原P49/P51/P52/P53live合同不改。先原P53已保存物理/.05case、最后应用26格/27面完整记录，不经过后续baseline12或P4913格覆盖。actualconstructor按mode3原primitive初始化几何并原生生成初态，继承三个构造入口是同一实例；没有新geometryproducer、旧状态插值/rebin或y0覆盖。初始温度/配方/气氛/直接通道/Ca1/BDF/rtol/atol/.05s/.5s输出保持。

| 原四指标 | P53 13格真实基准 | P54 26格细化 | signed细化−基准 | 实際分母 | 原相对差 | 无floor描述比值 |
|---|---|---|---|---|---|---|
| porosity | 0.19102385845251507 | 0.19102370804559643 | -1.5040691864198763e-07 | 0.19102370804559643 (细化绝对值) | 7.873730448e-07 | 7.873730448e-07 |
| residual_carbon_kg | 0.002925046159935924 | 0.0029250461599359145 | -9.540979117872439e-18 | 0.0029250461599359145 (细化绝对值) | 3.261821727e-15 | 3.261821727e-15 |
| shrinkage | -6.1600452361254554e-07 | -6.2830336289287914e-07 | -1.2298839280333596e-08 | 0.001 (原floor) | 1.229883928e-05 | 1.957468320e-02 |
| peak_temperature_difference_k | 0.28494581583328227 | 0.29023406008485608 | +0.0052882442515738148 | 1 (原floor) | 5.288244252e-03 | 1.822061908e-02 |

四项按原 `abs(refined26−coarse13)/max(abs(refined26),原floor)<.02` 通过；收缩floor.001、峰温floor1K，raw signed值保留。末列只描述，不设额外PASS阈值；零raw参考时null，原正floor指标定义保持。负收缩是小幅膨胀而非裁剪至0。direct extent基准0.00031506923678606755mol、细化0.00032132673514362591mol，signed差+6.2574983575583638e-06mol，raw比值1.947394248e-02；没有给反应进度或全状态新增准确性资格。

实际原14面在27面偶数索引差全0；signed子格对体积和−原父体积仅第6对为-1.6940658945086007e-21m3，其余0。按独立native数组math.fsum totals的全域差-2.7105054312137611e-20m3；已形成signed pair residuals再fsum为-1.6940658945086007e-21m3。两种浮点顺序分别披露，没有容差或几何PASS；原几何/宽度/面积以及本轮输入生成算术和native读回在两份geometry receipt中保留。

质量/元素/完整U相对残差6.235802642e-10/6.513742283e-09/1.469543941e-08、四gas最坏8.515348875e-06、native累计熵3.001470368e-09符合原.001；逐cell相残差先形成再global、原预算/初始inventory/extent尺度和signed源/边界保持。Cc/OH逐相通过；CaO预算/初末/源/残差0、relative=null/passfalse，三相整体不PASS。原生热/气体/水/携能/分项熵来自同次production summary，0postrun本构/C采样；strict非负只覆盖21实际保存时刻，不覆盖连续域/BDFknots/Newton/complextrials。

原累计熵残差摘要已持久，但完整独立signed Sstorage/Sproduction/Sexchange累计序列仍未保存，不能摘要重建或用额外算子补资格；共享缓存rate identity不能替代独立势微分。旧schema的P51/saved13cell是历史格式名，actualidentity/geometry/solver.cells明确P54/26。identity的13facesintervals指原13格、14面形成13区间。冻结declared_not_started为启动前状态，当前live/actualreceipt为closed。原scope全模型描述不扩大单一direct_transient0..10s，whole/onlystage不是独立重复。比较首版继承P52criterion/stdouttime标签已纯元数据纠正为实际P53空间基准，原报告与实际执行源保留，0数字重算。

P53只授原13格时间4metrics，本P54只授同10s/.05下13vs26空间4metrics；不能授fine26时间/一般空间收敛/全状态/八阶段/三方案/反演UQ/完整模型CLI。P45旧净UFAIL、P34/P40/P44失败、P50错误初Ca两PASS撤销、P51无持久numericresult的serializationfailed原样保留，不据本次结果改核或重做P45。历史名义water.135892078740%>.1%，0新尝试；0实测/no targetbrickL，whole_project_complete=false。

真实启动17:58:45.450309UTC、回收17:59:03.467780UTC，18.017544333s/CPU17.791956s、rc0/回收/未超时；1实例/ODE、4106真实RHS含10Jac、另21summaryrates，constructor内部1原partitionprimitive，0独立算子/producer/重试。唯一截止18:13:45.450309UTC，初必要输入/源/输出2032140B<3MiB；比较与行政收尾字节最终另测。声明至本记录684.107s行政时间单列。

11明确路径正常Git/push/remote、一次原Drive目录必要增量实际结果见 `runs/full-cycle/p54-saved-reference-space-refinement-final-delivery-state.json`，metadata不是byte恢复或owneraccess，原件保留。历史/独有Git/20GB/GitHub容量未解决。下一项建议仅补26格时间资格：复用本P54基准、同10s/.05→.025一次前向，若另分配预计1job/worker/attempt/constructor/ODE、900s/3MiB、必要输出约2.4MiB；它尚未登记预算或执行，不能自动P55/第二空间档。
