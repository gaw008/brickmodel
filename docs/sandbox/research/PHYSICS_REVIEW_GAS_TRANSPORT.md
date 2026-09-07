# 气体输运模块独立物理、数值与代码审查

审查对象：`src/sludge_sandbox/gas_transport.py`、`tests/sandbox/test_gas_transport.py`、`GAS_TRANSPORT.md` 与 `data/sandbox/transport/`。本报告由独立审查子代理只读检查与执行，不修改被审代码；实现修正由模块负责人完成。这是软件/方程离散审查，不是外部专家认证或真实原污泥材料验证。

审查状态：`accepted_for_manufactured_operator_integration`。发现的一项 P1 已由实现负责人修正并通过独立重验，见末节；本次限定模块内未留存未关闭 P1/P2。科学状态仍为 `not_validated_for_raw_sludge`，不批准完整耦合过程或材料预测。

## 1. 发现：P1，中心扩散修正可从零库存格抽走物种

初始实现使用 `j_k = j_k_star - Y_face,k * sum(j_star)`，其中 `Y_face` 来自中心面组成。它满足零总扩散质量，但不是任意所接收的非负多组分输入下的保正离散。面两边至少一个单元的物种库存为零时，修正项仍可使该物种从空单元流出。单纯缩小时间步不能解决：右端项在零库存边界已经指向负域。

实际反例（纯 manufactured，不作为材料参数）：

```text
M_A=M_B=M_C=0.02 kg/mol; T_left=T_right=300 K; R=8 J/(mol K)
V_left=V_right=1 m3; area=1 m2; distance=1 m; weight=0.5
left inventory  = {A:0,   B:0.9, C:0.1} mol
right inventory = {A:0.1, B:0.1, C:0.8} mol
K=0 m2; kr=1; mu=1 Pa s
```

采用正的、对称的二元系数 `D_AB=0.01, D_AC=D_BC=1 m2/s`，在面摩尔分数 `(0.05,0.5,0.45)` 按缓存的 Cantera `getMixDiffCoeffs` 公式构造相应混合平均系数，而非把三个系数任意拼接：

```text
D_A=0.018830525272547076
D_B=0.09174311926605504
D_C=1.0
```

修复前实际输出：

```text
F_A=+0.02954137532846583 mol/s
F_B=+0.38763877397004937 mol/s
F_C=-0.4171801492985152 mol/s
sum(M_k*F_k)=2.168404344971009e-19 kg/s
dN_left,A/dt=-0.02954137532846583 mol/s
```

于是左格 A 从初始零库存出发，在 `dt=1e-3, 1e-9, 1e-15 s` 时分别得到 `-2.9541375e-5, -2.9541375e-11, -2.9541375e-17 mol`。这是半离散方向错误，不是“大时间步”的问题。63 个既有测试全部通过，但没有检验这一情景。

建议并独立核对的修正：将修正项视为修正质量漂移，`mass_correction=-sum(j_star)`，其组分用该漂移方向的供体 `Y_upwind`；原始 `j_star` 仍保留摩尔分数梯度。该选择是本项目的数值离散，不能称为 Cantera 连续式直接提供的保正算法。

```text
j_corrected,k = j_star,k + mass_correction * Y_correction_donor,k
donor = left  if mass_correction > 0
        right if mass_correction < 0
        none  otherwise
```

两个性质可以独立证明：

1. `sum(Y_donor)=1`，故 `sum(j_corrected)=sum(j_star)+mass_correction=0`，保持质量平均参考系。
2. 左格 `X_k=0` 时，非负 D 使 `j_star,k<=0`；漂移向右则左供体 `Y_k=0`，漂移向左则修正项 `<=0`，两者都不会从左空格移出物种。右格同理。原有 Darcy 组分上风具有同样的零库存边界性质。

此证明不保证正库存下任意大时间步可行，也不保证强梯度的误差已足够小。后续积分器仍须按所有邻面、反应联合设置步长；修正漂移的一阶数值扩散需要网格收敛验证。禁止用逐物种 clip 代替修正，它会改变零质量约束或共享交换。

## 2. 核读来源与量纲/参考系检查

核读了缓存的 Cantera `Diffusive Fluxes`、`GasTransport::getMixDiffCoeffs`、`IdealGasPhase` 压力/标准浓度定义，以及 MOOSE `Advection/eq:darcy`。这些是原项目维护者的方程/API 文档；它们不证明原污泥材料系数适用。注册表的 8 个来源/许可文件逐一重算 SHA-256 与字节数，全部与登记一致。

| 项目 | 结论及限制 |
|---|---|
| EOS | `N/V_gas` 为当前气相摩尔浓度，`p=sum(c)RT` 与 `rho=sum(c)Mbar` 一致；mol 与 kg/mol 没有混成 kmol |
| 载气 | 初始/边界状态和面流使用完整显式物种集合；缺一个映射键会拒绝。如果调用方在全部映射里同时删去载气，纯算子不能发现，需气氛/材料门禁 |
| 开放气相体积 | 正的 `gas_volume_m3` 由调用方传入；算子不负责扣除固体、液水、闭孔，不声称已验证孔隙几何 |
| 原始扩散 | `rho*(M_k/Mbar)*D_k*grad(X_k)` 的单位是 kg/(m2 s)，对应质量平均速度、摩尔分数梯度系数；不能换入 Mole/Mass 变体系数 |
| 扩散修正 | 目标是 `sum(M_k*F_diff,k)=0`，不是 `sum(F_diff,k)=0`；不额外强制等摩尔流是正确的。第 1 节的零库存问题已用共同修正漂移上风关闭 |
| Darcy | `K*kr/mu*grad(p)` 为 m/s 的表观体积流；再乘一次孔隙率会错误。气相相对渗透率显式，重力被明确省略 |
| Darcy 密度/组成 | 密度由插值面 p/T/X 的 EOS 计算，组成使用 Darcy 供体侧 Y；这是清楚声明的离散选择，质量通量恰等于 `A*rho_face*u_D`。强组分/温差下仍需收敛，不能称精确界面解 |
| 共享面 | 一次面对象提供全部物种 mol/s；左减右加可逐物种抵消，不只总质量抵消。该模块没有实际多格时间积分器 |
| 面/半格 | 非中点权重 `d_right/(d_left+d_right)` 的定义正确；右侧为已知真实界面时权重 0。膜未知状态、变系数半格阻力和非均匀材料界面须由上层求解，当前不能声称已实现 |

## 3. 归一化记录与能量连接检查

固定外库的分数和只允许 `1e-12` 相对舍入范围内修正；明显错误的比例被拒绝。构造器实际保留了原始不可变 `reservoir_input_mole_fractions`、原总和和最大绝对修正，测试也验证了原输入后续修改不能污染快照。插值面保留总和和最大修正两个诊断。它们目前位于返回对象；后续运行 artifact writer 仍须真实保存，不能仅因字段存在就宣称全程归一化账本已经交付。

气体算子不计算焓，这是符合模块边界的选择。当前面输出分别提供 `F_diff`, `F_adv`, `T_face`, `T_Darcy_donor` 和 `R`，允许耦合层计算：

```text
Q_material = sum(h_k(T_face)*F_diff,k)
             + sum(h_k(T_Darcy_donor)*F_adv,k)
```

必须涵盖所有气体并让两侧用同一个能量流；不能按物种净流正负重新决定整股流的温度。一个物种的扩散与 Darcy 项可以相反，先相加净流再统一取某一侧焓会改变能量模型。扩散修正漂移的供体只是数值组分选择，不能再叠加第二条 Darcy 能量通道。

两侧 R 和每种摩尔质量不一致会拒绝；算子允许 manufactured 的 R=8，实际证据模式应由统一热化学/来源门禁要求物理 R。该接口足以传递检查所需 R，但不能据此宣称完整气/液、反应、变形能量已经验证。

## 4. 实际测试与独立极限

实际定向运行：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_gas_transport.py -q
```

初审结果：`63 passed in 0.03s`。这套测试覆盖等压反扩散、同组分 Darcy、单物种等温压力平方解析极限、供体温度、库存与压力更新、关闭通道、非法数据和可查询的舍入修正；没有证明全 PDE 收敛或真实材料适用。

另运行不调用测试文件的独立脚本：用不同温度、不同分子量和不同组成两侧、非中点权重 0.2，验证交换方向翻转（翻转后权重为 0.8）、面积七倍、距离三倍、总扩散质量和 Darcy 总质量恒等关系：

```text
nonmidpoint_reversal_max_mol_s                 = 0
area_linear_max_mol_s                         = 6.776263578034403e-21
distance_inverse_max_mol_s                    = 1.6940658945086007e-21
diffusion_mass_residual_kg_s                  = 0
advective_mass_flow_minus_face_rho_u_kg_s      = 0
face_T                                       = 531 K
advective_donor_T                             = 355 K
```

5 个独立恒等检查全部通过，并确认扩散面温度与 Darcy 供体温度未被合并。这里的误差是浮点算术残差，不能当成实验误差。

零/非法数据方面：单个物种可为零，真空总量被拒绝；非正孔容、非正 T/R/M/mu/面积/距离、负 D/K/kr、kr>1、权重域外、非有限数值、布尔/字符串及派生溢出有拒绝路径。零全部 D 且 K=0 为精确关闭通道。零单物种 D 不是专属密封膜，因为质量参考系修正可能仍携带该物种，此限制已明确。

## 5. 本模块不能证明的范围

- 没有真实同材料域 D/K/kr 数据或实验对照；没有原泥预测的科学有效性结论。
- 没有干湿孔容演化、闭孔气体、有限库温度积分、反应和热量总账本。
- 没有膜界面状态求解、跨异质材料半格矩阵通量、时间积分/空间收敛。
- 压力扩散、Soret、Knudsen、滑移、非 Darcy 惯性、非理想气体、重力及拓扑变化均明确未实现；文档列出限制，但实际支持域门禁还需落实到运行前和运行中。
- 上风修正避免本反例并不消除模型形式误差，也不说明任意组独立 D 都可成为真实多组分物性。

## 6. 版本与修复后复验

初审快照：

```text
src/sludge_sandbox/gas_transport.py
  a893ee843d8f3756b13fa629261d5e30296603278c86d7e2f6c35a52373a2e70
tests/sandbox/test_gas_transport.py
  492d9cd68d71e36fbda9498fc0d77e1193cfb46b583156c5892a4a93a6e02c77
docs/sandbox/research/GAS_TRANSPORT.md
  a2e291f5948e33b6500d584268f734cc3933d0a48c19496139b98afe5001218a
```

已重新核读负责人修正的代码和新增测试。修正通过同一 `total_star` 生成所有物种的漂移通量，按其符号选左右供体，并保留 `diffusion_correction_velocity_m_s` 与 `diffusion_correction_donor`；没有改动库存、逐物种 clip 或再增加 Darcy 通量。说明文档已写明连续公式与一阶数值离散的区别、旧精确测试值改变的独立手算理由，以及网格误差限制。

复跑相同定向命令得到 **`79 passed in 0.03s`**。新增覆盖包含原反例及翻转、三物种左右零库存与有/无 Darcy 的组合、非中点交换反向、光滑组成的面流一阶收敛。光滑测试的独立连续值为 `(0.0152,0.0443,-0.0595) mol/s`，间距连续减半时最大误差 `.0081,.00405,.002025,.0010125`；由手算连续公式可以核实这些参照值。它仅证明该面算子的相应光滑极限，不替代整个时间相关 PDE 的收敛。

审查者独立重跑原 P1 反例，结果为：

```text
F_A=-0.0018830525272547079 mol/s
F_B=+0.6390341968158136 mol/s
F_C=-0.6371511442885591 mol/s
dN_left,A/dt=+0.0018830525272547079 mol/s
sum(M_k*F_diff,k)=-3.876022766635678e-18 kg/s
correction donor=left
```

再以固定随机种子 `40707` 构造 150 个独立 manufactured 情景（3 个物种 × 左右空库存 × 每组 25；改变分子量、温度、体积、D、K 和面权重），分别检查扩散、Darcy 与净流的空库存边界方向，共 **450 项均向非负域或为零**。全部情景同时检查扩散总质量，最大 `abs(sum(M*F_diff))/sum(abs(M*F_diff))=6.343803275607852e-15`。这些是有界软件反例搜索，不是实测材料分布、统计置信区间或穷尽证明；第 1 节的符号推导给出了对应输入域的边界理由。

最终核验快照（本报告只适用于这些内容及明确范围）：

```text
src/sludge_sandbox/gas_transport.py
  12cd37bca0c21d5ad4489389f5587d2191382f42e34b43e78d934a3e7a51346f
tests/sandbox/test_gas_transport.py
  c32c7c37bf6bec7bdb0e385f88ceb17b8c1c63902354954073877f8dbb96dfe8
docs/sandbox/research/GAS_TRANSPORT.md
  13d6774041500d6184b4b018a46f5b5c2b3b8a77112867d9ac4c7dc6423813d5
```

P1 关闭。可以把修正后的算子接入后续 manufactured 耦合验证；仍需共享能量流、正性时间步、全程质量/元素/能量、材料适用域和公开实验等更大范围的实际证据。初审中心修正版本不得继续用于包含零初始产物的耦合求解。
