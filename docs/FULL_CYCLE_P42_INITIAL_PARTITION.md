# P42 固定初始有限体积分区与逐格尺度契约

P42固定二次初始有限体积分区/逐格尺度原语已实现（2026-10-01T22:54:23.640845+00:00），准入partial/FAIL：实际一科学job、四fixture，64算术行63通过/1 uniform旧标量extent兼容FAIL，CPU0.010810083s、首监督0.263625s、子进程回收/首预算内。两修复启动gate均在改源/子进程前停止，原120s截止不延，0第二sciencejob；工作流收尾151.717013s，额度关闭。其后仅静态简化uniform恒宽L/N，修正版未执行且A*(L/N)与旧(A*L)/N运算顺序仍有舍入边界，不预判通过。旧44主机/506条保持，新原语未接主机，0物理算子/积分/fit/UQ/恢复；根514=144literature370assumed0measured，P40mesh/phase/strict、P34旧30/81、名义0.135892078740%失败及wholefalse保持。

## 实际代码与执行

新增 `models/initial_finite_volume.py` 和 `scripts/verify_initial_partition_invariants.py`。分区、每格质量/chemical/retention尺度、独立extent编解码、嵌套广延量相加及共享面守恒是可复用小型接口；完整主机没有连接该分区，名义uniform和direct未启用状态不变。当前原语有静态修正，首次执行源在 `primitive-attempt1.py`，分析脚本与执行版一致。首结果只支持首版对应行，不授予修正版资格。

唯一job从2026-10-01T22:45:50.974739UTC开始，deadline22:47:50.974739UTC；PID33918退出1，22:45:51.237040UTC回收。分析0.010810083s、进程0.260405875s、监督至回收0.263624583s。后来两次修复启动门槛分别要求剩余>60s、>30s，均在源修改/子进程前AssertionError；没有第二科学作业。后者条件改变也未让实际执行继续，失败如实保留。原截止已到，不再改变predicate/创建新deadline/换ID重跑。关闭记录距start151.717013s，与首预算内回收分列；P42仍[ ]。

首64行中63通过，只有uniform12.old_scalar_extent_encoding失败。原uniform宽度0.0012499999999999976–0.0012500000000000011m，来自浮点face相减。关闭后仅静态改为恒L/N，未执行：A*(L/N)与旧(A*L)/N及独立face/center计算的舍入顺序仍不同，不能宣称兼容恢复。复合非法输入仅证明cells=0被首前置条件拒绝，其余非法分支未单独验证。

## 解析分区与每格尺度

固定参考坐标从对称面0到表面L，x_j=L[1−(1−j/N)^2]，N仅12/24；指数2在根事前冻结为assumed数值设计。Δx_j=L[2(N−j)−1]/N²（j=0…N−1），严格正，ΣΔx=L，ΣV=A L。x_2j^(2N)=x_j^N；每相邻两个子格的宽度不同，但其总宽为父格宽。quadratic12/24最外格分别约0.104166667/0.026041667mm，不增加格数、不搜索指数。

每格V0_i=AΔx_i、md_i=ρdry V0_i、c_i=md_i/Mchar，retention_i=q md_i/Mwater（位点等效量，不增加物质）；初始n_i,s=ρ_s V0_i。均匀密度的n/V、md/V、c/V、retention/V、孔气nRT/Vp与混合浓度比应不随分区改变。相同浓度/温度下μ不变是解析条件，job只检查其给定密度比，不调用完整μ。

使用P40保存初态总库存/气体/phi/T和独立终态extent总量形成给定均匀化合成密度；这不是重模拟P40空间场。独立extent是保存进度输入，未从物种库存重构。给定率为extent密度/原10s，仅用于轴代数，不称实际kinetics；已是mol/s的rate不能再乘V或A。

extent_mol为(n,nr)，flat coordinate=(extent_mol/c[:,None]).T.ravel()；反算reshape(nr,n).T*c[:,None]。同理dcoordinate/dt=rate/c。父子独立extent、库存、质量、J、J/K直接相加；T、μ、压力不能作为广延量直接相加，体积加权T也不是热能。

## 内部面、量纲和受限耗散

dn_i/dt=S_i+F_(i−1/2)−F_(i+1/2)，共享内面等量反号，Σdn=ΣS+Fin−Fout。源若以mol/m³/s定义才乘V；本主机给定反应率已mol/s。内部中心距=Δx_i/2+Δx_(i+1)/2，外距=Δx_last/2；面积在flux中一次。

给定人工正对角迁移率g，单位mol²/(J·m·s)，F=(A/d)g(μL−μR)为mol/s；内部σ=ΣF·(μL−μR)/T≥0，W/K。给定k>0，Q=A(TL−TR)/(ΔxL/2k+ΔxR/2k)为W，Q(1/TR−1/TL)≥0。实际job只核查这些合成内部面和全域signed流量相消；外边界进入储量账本，但外库熵未核验。正对角证明不代替当前MS/Darcy正耦合、非等温移动孔气或瞬态能量验收。

一般有限体积储量/体积源及共享面积/中心距原则参见[NIST FiPy](https://pages.nist.gov/fipy/en/stable/numerical/discret.html)。仅为离散原理来源，不新增FiPy依赖，不证明二次剖分最优、砖材迁移率或当前耦合收敛。

## 同一自由能下的广延缩放与未覆盖项

同均匀物态、固定微观孔径的条件下，物种U/S与相能随n相加；surface es0=3γVp0/r，r是原材料孔径而非宏观格宽，随V0缩放。retention自由能的位点与水库存同缩放，局部μ强度量保持；干固体/石英参考分数同理。

每格F_el=V0_i K_i ε_i²/2，S_el=V0_i K_i β'_i ε_i，U_el=F_el+T_i S_el。K_V/K_D、carrier-birth组成导数的逆体积因子与V0相消，形成J/mol势；有效热容J/K、power W与db/dpore为广延量，dT/应变率为强度量。局部db=dpore+dns·v，机械熵ΣV0_i(force_i)ηdot_i/T_i，phase松弛保留本格active carrier权重。所有量必须由同一势导出，不另加反应或相变热。

以上是源码逐项尺度推导，条件依赖原本构的同密度、同温度、同strain/carrier状态。没有调用完整U/S/化学势/表面/弹性/机械算子，也未执行实际host/Jac，故不是完整主机热力学准入PASS。

## 后续主机真实依赖

| 源码 | 必要语义 |
|---|---|
| full_cycle.py:160–190 | b0/md/initial与反应、char+organic conversion scale逐格；不再取cell0；总A L与dry mass保持 |
| :231–245,352,367；gas:163,757–776 | char/OH同尺度；extent先按格轴归一化再转置展平；reaction scale二维 |
| gas:89–116,143–144,514,732 | scalar retention参数控制全局开关；sites/calcium_pool逐格；追加反应列不能无轴append |
| base:318,332,397,412,439；gas:715,960,1073,1100 | sweep按格轴；全域md.sum、余水Σratio_i md_i；中心温度9/8公式含uniform坐标假设，后续参考/当前坐标必须明确 |
| gas:1140–1141 | 冻结库存分辨率预算逐格或明确最大格；不默改尺度/范围、扩大direct预算或物理阈值 |
| gas:239–240,274–275,452–500,669–674；base:287–303 | 局部宽/半格串联输运和热导已有；面物性算术平均并非完整非均匀阻力加权证明 |
| solid:48–58,150–177,235–247,316–327,345–497,516–524 | 初始fractions/phase carrier/porous mechanic/fullU/S derivatives使用本格V0，保持同势、量纲、广延/强度关系 |

此表是明确三份继承链的源码核查，补充rg查找其他模块没有同一尺度变量用途，不把选择部分AST当全覆盖。原44主机逐字节相等收据独立保存，不能由job里说明性constant字段推断。

## 当前准入、失败与下一依赖

已执行支持首版二次嵌套、给定库存/独立extent/尺度归并、axis roundtrip、signed共享面与内部合成耗散；原uniform兼容FAIL及当前静态修正未执行均保留。完整主机非均匀接入仍阻塞，不能以解析关系代替约定fixture复核；本项额度关闭，不换任务ID刷截止。

下一项若复核修正后的受影响uniform契约，需要明确新的资源决定；其余physics/thermo准入及继承层变更也未获证。当前没有独立且已准入、可直接接入主机的空间变更；无数据不作为停研发原因。历史工艺、原P40 mesh7.33335%、phase/strict和P34旧30/81失败保持；新三方案/反演/UQ/八阶段/实材未获资格。

Git正常后继/push与明确Drive小增量读回单列实际随后收据；0恢复下载/解包/SHA/新增测试/长期memory/自动任务。保护原件/独有历史，20GB/完整历史备份/GitHub容量告警仍未通过。
