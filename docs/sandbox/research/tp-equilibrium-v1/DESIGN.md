# 最小 CHONS 气体–石墨 TP 平衡：数学与接口设计

2026-09-12；本文件是尚未实施/运行的设计。本设计工作未安装 Cantera、未改旧主机、未执行 EOS；ROOT 后续已单独建立 Cantera3.2.0 环境，见末段。**建议直接使用官方 Cantera 的多相 TP 平衡求解器，加一个小型输入/单位适配与独立结果检查层；不另写 Gibbs 最小化器。** 首次输出是真正依赖标准化学势的高温组成，但只在明示的元素池和候选相内成立，不是整份原污泥、反应时间或整砖模型。

## 1. 当前可复用边界与选型

已读 `src/sludge_sandbox/thermochemistry.py:22` 的 CaloricSpecies、ShomateSegment/Gas：只有 h/u/Cp/Cv，虽保留 A–H 系数，未给通用 s、混合化学势或组成平衡。`continuous_caloric.py:1` 明确只接连续 h/Cp、不提供熵；任意分段 h 偏移不能静默搬进平衡 G。`phase_storage.py:83` 的 PhasePoint 仅 T/P/u/h/v。`reactions.py:100` 的 SpeciesDefinition 可参考整数原子计数形式，但其 Arrhenius 网络是给定反应进度动力学，不能充作此平衡求解器。旧 IAPWS/NIST 水桥与热量反解本轮均不接入，避免把不同参考体系当成同一 G。

Cantera 已有 `Mixture.equilibrate('TP', solver='gibbs', ...)`，允许气相与固定组成凝聚相共存，不需反应速率文件。官方也明确多相求解器有失败或错误结果的已知情形，因此不把正常返回本身当接受；本设计保留独立元素、G/化学势与不同初猜检查。显式指定 `gibbs`，失败保存，禁止 `auto` 在后台切换算法。自行写最小化器还需补熵/标准态、边界/消失相、可行初猜和受限收敛；对当前小任务没有收益。官方依据：[Mixture 接口与限制](https://cantera.org/stable/python/thermo.html#cantera.Mixture)、[官方气体与石墨示例](https://cantera.org/stable/examples/python/thermo/adiabatic.html)；只复用其中构相方式，原例 HP 不用于本任务。

## 2. 明确的问题与候选相

输入温度 T∈[800,1200] K，压力 **100000 Pa**，不是 `ct.one_atm`；T/P 固定，不求绝热温度、不反推原泥 U/H。元素输入 `b={C,H,O,N,S}`，单位 **mol of atoms**，每键必须显式提供、非负有限、非 bool，至少一个正值。其他元素/电荷/矿物必须拒绝，不丢弃或归一化。首版实际算例用完整正 CHONS 池；纯碳且没有可承载的气相等退化请求可明确 `unsupported_degenerate_phase_pool`，不得强加 epsilon 气量。元素零值允许据整数原子矩阵排除结构上不可能出现的物种，原候选表与排除理由仍保留。

候选气体拟固定为 `H2,H2O,CO,CO2,CH4,O2,N2,NH3,HCN,NO,NO2,N2O,H2S,SO2,SO3,COS,CS2,S2`。来源代理已核 v3.2.0 这18个官方名称和800–1200 K覆盖，使用 COS，不能猜别名。唯一凝聚相为官方 `graphite.yaml` 的纯 `C(gr)`，不可误把字符串括号里的字母当气相标志。此名单固定；不自动加入文件内全部气体，也不静默删除某个不支持的物种。离子、自由基、其他烃/焦油、其他固碳形态、灰与矿物均不在这一限定模型，省略影响 unknown。候选集合是 `virtual_design_choice`，不是从 TG/DSC 数据证明“只有这些产物”。

只使用同一已冻结官方 v3.2.0 NASA7 气体数据和纯石墨文件的显式1bar派生语义分支（见§3），实际检查每个物种的元素、零电荷、各段 T 域、参考压力和热化学模型。必须单独检查石墨域；`Mixture.min_temp/max_temp` 不包含固定化学计量固相，不能替代逐相检查。理想气体与纯固定组成石墨是明确本构近似；石墨不是已验证污泥 char。源系数/出处由来源代理登记，本模块只校验该小包真实文件及使用物种，不再造通用来源框架。

在任一 T：

- A 为精确非负整数原子矩阵；n≥0，A n=b。
- 气体标准态使用 Cantera 在当前 T/P 的 `standard_gibbs_RT`；μ_i=g_i^std(T,P)+RT ln(n_i/N_g)。N_g=Σgas n_i。
- 纯石墨 μ_C=g_C(T,P)，活度1；压力影响按原固相常体积模型，不自行删掉。
- G(n)=Σgas n_i g_i^std + RT Σgas n_i ln(n_i/N_g)+n_C g_C；0 ln0 取解析0，不能用 epsilon 替代实际库存。

这是闭合元素池在热浴/给定压力环境下的组成极值；体积可变，不是刚性绝热单胞。给定 b 不等于给定真实初始分子组成。数值初猜的 H/G 只能作为求解诊断，不等于原泥热解热；本阶段只可报告最终限定混合物的 H/S/G，不能从中推断升温耗热、释放功率或真实污泥反应热。

## 3. 单位、标准态与可行初始化

公共 API/输出采用 mol、J/mol、J、Pa；Cantera MultiPhase 的物种/相库存实际单位为 **kmol**，μ 与 molar h/s/Cp 为 J/kmol 系。入口显式 n_kmol=n_mol/1000，读回 mol=1000*n_kmol；这不是把1 kmol误当1 mol的“只影响比例”操作。保留原 Fraction b、送入的 binary64 kmol 与读回量，A·(1000 n_kmol) 相对原 b 的带符号差在求解前先过元素门。避免仅设置 X 后丢掉绝对量；按固定全局物种顺序设置完整 `Mixture.species_moles` 数组，再实读回。参考：[MultiPhase 的 kmol 与 μ 单位](https://cantera.org/stable/cxx/d1/d4b/classCantera_1_1MultiPhase.html)。

**来源核查发现必须显式处理的差异。** 原 v3.2.0 `nasa_gas.yaml`/`graphite.yaml` 未写 reference-pressure，分发默认按101325 Pa解释；NASA TM4513 p1/p2 明确其表值已采用100000 Pa。来源代理实际查看 p33 H2S、p39 N2、p55 C(gr)，所列熵常数未发生把1bar换到1atm所需的变换；这些是已核的代表条目，不能宣称已逐原页比对全18物种。原件保留不动，首实现明确采用 **`NASA1993_1BAR_EXPLICIT_REFERENCE_V1`**：复制所选原 species 定义到新派生输入，在每个 gas 和 C(gr) 的 thermo 中显式写 `reference-pressure: 100000 Pa`，原14个 NASA7 系数、区间、组成都不改。此为纠正分发缺省语义的 `derived_from_evidence`，不是静默把用户 P 当源标准态，也不是修改 s 常数。派生记录列出原缺省101325、显式100000、NASA依据、实际条目复核范围及原/派生hash。加载后核每物种实际 reference_pressure=100000，不能只相信 JSON 标签。

原分发语义另记 `as_distributed_default_1atm`，不能与该分支混称同一模型。若将来选择等价的1atm参考表达，气体须作 s°(1atm)=s°(1bar)−R ln(101325/100000)；按当前常体积石墨模型，h°/g°增加 V_m(101325−100000)，熵不变。该替代表达本轮不实施、不在失败时切换。目标状态 P 仍100000 Pa。已经读取当前压力的 g^std 后，不再额外加 RT ln(P/p_ref)。NASA 系数共同提供 h、s、Cp，形成焓已在积分常数中，不再另加一份；不混入旧连续 h。TM4513历史 R=8.314510 J/(mol K)，实际计算记录 Cantera 的 R/1000 和原子量，不宣称维度量逐末位重现1993表。参考：[NASA TM4513 原报告](https://ntrs.nasa.gov/citations/19940013151)、[标准态与参考压力说明](https://cantera.org/stable/reference/thermo/species-thermo.html)。原报告和代表原页在 `source-admission/raw/nasa-tm4513.pdf`、`nasa-p2/p33/p39/p55.png`；手动原页核读由来源代理完成，本设计不重复声明自己核过原图。

本候选有 H2/O2/N2/S2+C(gr)，所以可用明确数值初猜：n_H2=b_H/2，n_O2=b_O/2，n_N2=b_N/2，n_S2=b_S/2，n_C=b_C，其他0。精确原子账先成立，再检查 kmol 投影，不需要另加 LP 或发明挥发分配。氧氢初猜不是模拟真实进料；它只是相同元素约束的一个数学可行点。

## 4. 最小公共结构与执行路径

建议独立新模块 `src/sludge_sandbox/tp_equilibrium.py`，不改现有 caloric/reaction/storage 接口。限三个小不可变记录：

```python
TPPool(temperature_k, pressure_pa, element_mol: tuple[Fraction,...],
       basis_id, classification, source_ids)
TPPolicy(solver='gibbs', rtol=1e-10, max_steps=1000, maximum_elapsed_s=10.)
TPResult(status, reason, request, requested_elements, seed, raw_final,
         checks, diagnostics, provider_identity, source_ids, elapsed_seconds)
solve_tp(pool, source_root, *, policy, seed_variant='element_basis') -> TPResult
```

可用性准入固定来源小包与名单；source_root 显式，不查“碰巧存在”的同名系统数据。先核原件与派生文件hash，再只准入固定18条gas与C(gr)；禁止动态 extensions、任意跨文件 species 导入或反应段。内部用 `Species.list_from_file(explicit_derived_1bar_path)` 选已核派生 Species，`Solution(thermo='ideal-gas', species=selected)`，另载原 graphite phase，再建新的 Mixture。每次调用新对象：Cantera 相对象是可变状态，不能共享给并行请求或返回给用户保存。所有结果只返回复制后的标量/数组/固定记录。设置实际 TP 和完整 n，保存初始实读快照；调用一次明确 solver，返回后立即保存最后实读量，之后再作时钟/接受检查。失败期间若读取部分状态又失败，保留先前完整快照和新的读取异常；不能伪称它是平衡结果。无需新 job 平台、恢复资格或 codec。

先用制造数据测试域/元素名/负库存、mol↔kmol、kmol投影拒绝、保存失败/部分结果，及下面的解析 G/原子算术。实现后才按冻结方案安装隔离依赖和执行真实来源计算；当前设计不执行。

## 5. 小型独立接受检查（本设计推导，非新优化器）

气相理想混合 G 的 Hessian 为 RT[diag(1/n_i)−11ᵀ/N_g]，对任意向量半正定；石墨项线性，元素约束线性。因此限定模型是凸问题，但浮点求解/多项式/省略相仍未得到区间误差证书。检查不是只看 G 降低：单纯 G_final≤G_seed 不能证明到达极小值。

对实际保存的 n，先逐项有限且 n≥0（负小数也不裁零），实算 A n−b；保存所有 trace 数量，不以打印阈值改变状态。当前 T/P 不许漂移；气/石墨均域内、读回实际原子/来源对应。对 n>0 的气体，独立用 log(n_i)−log(N_g) 重算 μ 和 G，避免后台 log(0) 截断冒充有限化学势。结构强制零不计算 log；其余零 trace 明示，使用下面全候选 partition 检查而非给它伪造 μ。

名义 KKT：对有数值分辨的活性物种拟合元素势 λ，使 μ_i≈a_i·λ；正石墨加入 μ_C=λ_C，消失石墨要求 μ_C−λ_C≥0。只做一次小矩阵 least-squares，不调整 n；active 的门如 1e−12·Σb 只用于诊断拟合、属于 numerical_policy，不把小物种设为0。秩不足时报 `unresolved_element_potential_diagnostic`，不得报KKT通过。

为覆盖未进入拟合的所有气体和零 trace，用同一 λ 实算 `logZ=logsumexp((a_i·λ−g_i^std)/(RT))`，石墨 d_C=(g_C−λ_C)/(RT)。令 B=Σ元素 b，δ=max(0,logZ,−d_C)；若 b_C=0 已结构排除石墨，则去掉 d_C 项。对限定模型所有可行 n，都有 G≥λ·b−RT·B·δ：气相贡献由 Gibbs 不等式下界 −RT·N_g·logZ 给出，石墨贡献 ≥−RT·n_C·δ，而 N_g+n_C≤B。由此报告**名义 G 下界差**，可在有 trace0 时仍检查所有候选；实现只需稳定 logsumexp 和求和，没有第二个组成优化器。比较使用实际读回的 b_out=A n 与原 b 的残差分列，不能把非零元素误差藏在下界里。全误差仍 unknown，不能称认证全局最优解。

预登记数字门（均 numerical_policy，可在未执行前独审；执行后不得事后放宽）：元素每行 |b_out−b_requested|≤1e−10 mol+1e−10|b_requested|；所有 n≥0；|ΔT|≤1e−8 K、|ΔP|≤1e−6 Pa；名义 gap/(RT·B)∈[−1e−10,1e−7]；已分辨活性行 |μ−Aᵀλ|/(RT)≤1e−7；G_final≤G_seed+1e−7 RTB。正/缺失石墨的带符号条件独立列出。G/μ门是已选模型的数值检查，不是系数物理误差或材料置信区间。

## 6. 一次有界真实接受计划（待来源冻结与实现审查）

独立虚拟元素池 **C=1, H=1.6, O=.6, N=.1, S=.01 mol原子**，classification=`virtual_design_choice`，不称1 kg污泥。指定 P=100000 Pa。一个串行受监督实验最多四次平衡调用：先1000 K元素基初猜；再1000 K同池第二初猜（把0.1 mol C +0.2 mol H2转为0.1 mol CH4，全部原子严格相同）；仅前两项过门后再800 K、1200 K元素基初猜。每次新建相；不复用已收敛结果作另一“独立”初猜。每调用 rtol1e−10/max_steps1000/10 s，实验driver40 s、外部监督50 s+清理5 s；这些是未实测数值资源选择，失败即停、无solver切换/重试/调整物种。按原监督保存stdout、异常、所有调用前后复制状态、source/版本与输入hash；当前不安装或运行。

1000 K两初猜最终每物种差≤1e−8 mol+1e−7·max(n_A,n_B)，G差≤1e−7 RTB；只作同根数值检查。四点分别执行所有原子/G/相/域门，逐点展示气组成、气相总mol和石墨mol，不预设“必有/必无焦炭”的结果、不拿期望图形作事后门。成功只证明所选TP/相集合的实际来源计算链可运行；不证明整个800–1200连续域误差、反应速率、挥发分回收或物料适配。

## 7. Cedrone 与后续耦合的明确接口边界

首验使用虚拟池即可推进真高温物性计算，不必等待完整污泥反应机理。如果后续取 Cedrone Table4 名义 CHONS 子系统，只能记录“选定打印元素比例的名义池”和其转换公式；不归一化完整表以填合计差，不把未知灰/水/矿物氧补为0，不声称已有1 kg真实污泥基准。可另选 `b_C=1 mol` 的相对尺度，明确这是新的比较尺度，不能回写成实测干污泥质量或热效应。

开放排气要有外流物种/元素携出与边界账，更新 b 后重新求TP可作为准静态极限；一次闭合 b 的 TP平衡不是出口气体的全程累计组成，也不是有载气连续流的稳态反应器。真正接回砖主机还要定义材料库存如何进入此池、灰/矿物/char候选、能量参考兼容、温度/压力与流量边界；本模块不凭空给这些缺项补反应热或动力学参数。

## 来源/实现交接现状

当前设计冻结候选与源准入方向已对齐；来源代理的 `source-admission/CANDIDATE.json` 与 `SELECTED_SOURCE_BLOCKS.txt` 固定实际18条记录/温域，`CHONS_INVENTORY.json` 仅为未准入全库盘点；`SOURCE_ADMISSION.md` 是已读来源结论，原文件与NASA报告在 `source-admission/raw/`。参考文件固定到 v3.2.0，许可是 BSD 式三条条件，不是 MIT。源标准态冲突已有明确可计算派生分支，不作为停止物理实现的借口。

ROOT 独立安装环境：`/private/tmp/sludge-tp-equilibrium-v1/runtime`，Python3.12.13、Cantera3.2.0、numpy2.5.2、ruamel-yaml0.19.1、typing-extensions4.16.0，实际 INSTALL01.log；旧低温环境不改。本设计作者未安装或调用它。下一具体工作是一个小 TP wrapper 与先行制造测试，随后在该独立环境按§6冻结后执行；不需要再写一轮全面规划或新hash框架。

合同§4输入分类：元素守恒/TP下G极小关系为 `physical_law_or_constant`；NASA7与理想气体/石墨状态关系为 `literature_constitutive_model`，不将整套编译热数据都称实测；显式1bar语义派生为 `derived_from_evidence`；元素池/候选集合/目标TP为 `virtual_design_choice`；求解器、单位投影门、活性诊断阈值与资源为 `numerical_policy`；作者人工回归为 `manufactured_test_fixture`；材料迁移、缺失相与尚未量化的热数据误差为 `unknown`。`SEED_ALGEBRA01.json` 仅实际复核两种初猜的精确 CHONS 元素相同，未导入Cantera或运行物性，不能作为高温组成验证。

接点与数据安全补充：来源代理已核 Cantera v3.2.0 `NasaPoly2.h` 的 `updateProperties`/`updatePropertiesTemp`：**T≤1000 K 使用低温段**，1000 K等号归低段，不可搬用本仓 NIST Shomate 的高段拥有规则。直接读取实际 Cantera 值时保留此行为；独立多项式算术验证也必须相同，保存接点两支差异，不自行连续化/平滑。这是软件分支约定，接点不是相变。
