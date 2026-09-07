# 气体孔内状态与公共面输运

本模块是适用域受限的数值算子；当前完成 manufactured 验证，未批准任何真实原污泥的气体输运参数。代码为 `src/sludge_sandbox/gas_transport.py`，测试为 `tests/sandbox/test_gas_transport.py`。公式来源缓存及哈希见 `data/sandbox/transport/equation_sources.json`；软件文档不提供原泥砖的有效扩散、渗透或黏度关系。

## 已核读依据与实现选择

| 项目 | 依据及定位 | 本实现的选择或限制 |
|---|---|---|
| 理想气体 | [Cantera 3.2 IdealGasPhase](https://cantera.org/3.2/cxx/d7/dfa/classCantera_1_1IdealGasPhase.html)，standard concentration 与 pressure；缓存 `cantera-3.2-IdealGasPhase.h` 第 152–163、338–340 行 | 从实际物种库存、当前气体体积和温度计算压力；不要求等压，不推断载气 |
| 质量平均扩散修正 | [Cantera Diffusive Fluxes](https://cantera.org/3.2/reference/onedim/governing-equations.html#diffusive-fluxes)；缓存 governing-equations 第 73–91 行 | 保留连续方程的零总扩散**质量**通量修正；采用下文独立说明的一阶上风修正离散，不额外强制总摩尔扩散流为零 |
| 扩散系数定义 | [Cantera GasTransport 源文件](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/include/cantera/transport/GasTransport.h)，缓存第 56–75 行 | 输入对应 `getMixDiffCoeffs()` 的质量平均速度、摩尔分数梯度约定；不能用 `getMixDiffCoeffsMole()` 或 `getMixDiffCoeffsMass()` 替代 |
| Darcy | [MOOSE PorousFlow governing equations](https://mooseframework.inl.gov/releases/moose/2024-11-11/modules/porous_flow/governing_equations.html)，Advection / Eq. (4)；另缓存官方仓库读取时的 master 文档第 80–104 行 | 采用沿面的绝对渗透率 K、气相相对渗透率 kr 和黏度；本版本明确省略重力项 |
| 面离散 | 本项目的数值选择，不称文献原样实现 | p、T、X 按显式几何权重线性插值；ρ 由该面状态的 EOS 计算；Darcy 组成和焓采用其供体侧；扩散修正的 Y 按修正漂移自己的供体侧取值 |

Cantera 缓存保留 BSD 3-Clause 许可证。MOOSE 文档来自官方源码仓库，保留仓库 LGPL-2.1 许可证及版权文本；master 链接会变化，以此次字节哈希为准。缓存文件未经修改。实现依据公开方程独立编写，不导入这些源码。网页读取成功；Cantera 网页的直接下载及 MOOSE 发布网页的直接下载遇到 HTTP 403，已改用公开官方源码缓存，未绕过付费或身份认证。

## 输入与输出契约

`ideal_gas_state(inventories_mol, *, temperature_k, gas_volume_m3, molar_masses_kg_mol, gas_constant_j_mol_k)`：

- `inventories_mol` 为每物种实际 mol。若上层存的是 `mol/m3_reference_bulk`，先乘该单元参考体积。
- `gas_volume_m3` 是当前连通气体相体积。固体、液水和闭孔占据的体积须由统一几何模块扣除；不能把总砖体积直接传入。
- `M` 使用 kg/mol，`R` 使用 J/(mol·K)。Cantera 接口常用 kmol，引用数值必须做显式单位转换。R 必须与热化学模块一致。
- 所有实际物种，包括 N2、Ar 等载气，显式入账。一个物种当前不存在时也保留零值。输入映射必须与摩尔质量映射的物种集合相同。纯函数不能发现所有映射都同时遗漏的载气，该问题须由材料/气氛来源门禁检查。
- 返回不可变的浓度、摩尔分数、质量分数、平均摩尔质量、密度、压力和温度快照。各物种可以为零；总气体为零时组成未定义，会报错。

```text
c_k = N_k / V_gas                 [mol/m3_gas]
c_total = sum(c_k)
X_k = c_k / c_total
Mbar = sum(X_k M_k)
Y_k = X_k M_k / Mbar
rho = c_total Mbar                [kg/m3_gas]
p = c_total R T                  [Pa]
```

`ideal_gas_reservoir(*, pressure_pa, temperature_k, mole_fractions, molar_masses_kg_mol, gas_constant_j_mol_k)` 构造显式固定外库的强度状态。摩尔分数总和必须在 `rel_tol=1e-12` 内等于 1；仅这一级浮点误差允许归一化，不接受百分数、明显缺载气或任意缩放比例。返回状态保留 `reservoir_input_mole_fractions` 原始只读快照、`reservoir_input_fraction_sum` 原始总和和 `reservoir_max_abs_fraction_correction` 实际最大分数修正，供运行账本保存。普通孔内库存状态的这些诊断为 null。

有限外库应使用 `ideal_gas_state` 并持续积分其全部物种库存与能量，不能每步重置成固定 reservoir。外库是恒温系统时，其控温能量由调用方单列。

`face_exchange(left, right, *, area_m2, distance_m, face_left_weight, effective_diffusivities_m2_s, permeability_m2, relative_permeability, viscosity_pa_s)`：

- 单元或外库均可置于任意一侧。所有流率规定正号为左到右。
- `area_m2` 为当前共享整面面积；`distance_m=d_left+d_right` 是两状态点的当前距离。`face_left_weight=d_right/distance_m`，均匀内面为 0.5。对于直接给定界面状态的右侧外库，`d_right=0`、权重为 0，距离为单元中心到界面距离。有限膜阻力模型必须由上层另行解界面状态。
- D_eff 为每物种 m2/s，已按**总体截面积**有效化，必须适合上述摩尔分数梯度、质量平均参考系。K 为沿面的绝对渗透率 m2；kr 为显式气相相对渗透率 0–1；μ 为 Pa·s。这里不重复乘孔隙率或曲折度。
- 所有面系数均由外部提供。本模块不对相邻材料系数求平均、不推断孔喉。上层须在系数跳变/非均匀网格时处理半格阻力和通量连续性；多组分修正是耦合形式，不能仅将每个 D 算术平均后宣称验证了跨材料界面。
- 允许所有 D=0、K=0 或 kr=0 构造关闭相应通道的 manufactured 极限。仅将一个物种的 D 置零不一定使该物种的修正扩散流为零，不能把它解释为物种专用无渗透边界。

```text
q_face = w q_left + (1-w) q_right      # q is p, T or X
rho_face = p_face Mbar_face / (R T_face)
u_D = -(K kr / mu) (p_right-p_left)/distance
j_k_star = -rho_face (M_k/Mbar_face) D_eff_k (X_right,k-X_left,k)/distance
u_c = -sum(j_star) / rho_face
Y_c,k = Y_left,k if u_c>0 else Y_right,k if u_c<0
j_k = j_k_star - Y_c,k sum(j_star)     # zero correction if sum(j_star)=0
F_diff,k = area j_k / M_k
F_adv,k = area rho_face Y_donor,k u_D / M_k
F_net,k = F_diff,k + F_adv,k           # mol/s, + means left to right
```

`GasFaceExchange` 返回三组全物种流率、净流向、Darcy 表观速度、供体侧与供体温度、面温度/密度，以及 `face_input_fraction_sum`、`face_max_abs_fraction_correction` 的面插值归一化诊断。它同时携带 `gas_constant_j_mol_k`，便于耦合层拒绝 EOS 与热化学使用不同 R。Darcy 速度为零时其供体为 null。`diffusion_correction_velocity_m_s` 与 `diffusion_correction_donor` 单独记录扩散修正漂移；供体直接按 `-sum(j_star)` 符号选择，避免极端浮点下速度下溢成零丢失质量修正。分项方向由各分项的正负号给出；不同物种净流向可以相反。

调用方用同一个面对象执行 `dN_left/dt -= F_net`、`dN_right/dt += F_net`。不能分别从两侧重新计算同一个面，否则会失去严格的内部抵消。压力会在每次以新库存/新温度/新气体体积重建状态后改变，反过来改变 Darcy 流。

## 能量与时间积分边界

本模块不计算热源、热容、反应热或焓。调用方用统一热化学物种表计算：

```text
F_enthalpy = sum(h_k(T_face) F_diff,k) + sum(h_k(T_donor) F_adv,k)
```

两侧使用同一份焓通量并符号相反。氧气、惰性载气、水汽和所有气态产物均在此求和。不得再增加第二个气体冷却或反应热经验项。

扩散修正漂移属于 `F_diff` 内部的数值离散，仍使用共享的 `h_k(T_face)`；不得把它作为另一股 Darcy 流重复求焓，也不得用扩散修正供体温度替换真正 Darcy 供体的温度。

面函数返回瞬时导数，不保证任意步长保持库存正性。积分器必须以所有反应和相邻面联合决定可接受步长/耗尽事件，拒绝会导致负库存的步长。不得剪裁某一个面流以掩盖时间步错误。状态、体积、温度、质量、面积、距离、μ、系数的非法值、非有限值及派生溢出均报 `GasTransportError`；不隐藏 clip，不自动补气。

## 独立审查发现的 P1 与离散修正

第一版在修正项中使用面中心 Y。独立审查构造了正且对称的二元扩散系数反例：三个 manufactured 物种质量均 0.02 kg/mol，左库存 `(A,B,C)=(0,0.9,0.1)`、右库存 `(0.1,0.1,0.8)`，同为 T=300 K、Vgas=1 m3、R=8。取二元系数 `D_AB=.01`、`D_AC=D_BC=1`，在面组分 `(.05,.5,.45)` 按来源的 `getMixDiffCoeffs` 约定导出有效混合系数 `(.0188305253,.0917431193,1)`。面积和距离均 1，关闭 Darcy。

旧离散给 A 的净流率为 `+0.0295413753 mol/s`，意味着从 A=0 的左格继续抽出 A。减小任何正时间步都无法修复这一半离散域外导数。先添加原方向与左右反向两个回归测试，实际观察到 **2 failed**，再修正；没有用 clip、更改守恒容差或缩小步长掩盖。

现在把连续修正项解释为共享的修正质量漂移：令 `S=sum(j_star)`、`u_c=-S/rho_face`，以其上风组成计算 `j_corr,k=-S*Y_c,k`。这是一项明确的有限体积离散选择，与上述连续方程一致，但不声称与 Cantera 原程序的面离散相同。

- 总质量：`sum(j_diff)=S-S*sum(Y_c)=0`，保持浮点精度内的原守恒门槛。
- 零库存边界：若左侧 `N_k=0`，则 `X_left,k=Y_left,k=0`，因此 `j_star,k<=0`。当 `u_c>0` 时上风左侧 Y 为零，修正不会抽出 k；当 `u_c<0` 时修正向左，亦不会抽出 k。已有 Darcy 上风项同样朝非负库存域内部。右侧论证对称，且面积、分子量为正，不改变方向。
- 该证明约束半离散零库存边界，仍需合适的时间积分器和非负系数；它不保证任意有限时间步或未审查的反应项保正。

修正后的反例 A 流为 `-0.00188305253 mol/s`，其通量进入空格；没有丢弃或重新分配某一个物种的独立净流。输出额外记录修正漂移速度及供体以供追查。

上风修正只有一阶空间精度，会产生可量化的数值扩散。均匀光滑网格中，相对中心修正的一阶差项为 `-rho*abs(u_c)*(distance/2)*grad(Y_k)`；非均匀网格使用实际上风中心到面的距离。在 manufactured 光滑组分测试中，距离 `1,.5,.25,.125` 的最大摩尔流误差分别为 `.0081,.00405,.002025,.0010125`，相对于连续修正公式每次减半。这是收敛验证，不是材料参数拟合；后续整砖网格研究必须量化该误差。

原无氧二元反扩散测试中的精确值也随离散选择改变：手算 `j_star=(0,.016,-.012)`，`S=.004`，修正上风位于右侧且 `Y_right=(0,.4,.6)`，故修正后质量流为 `(0,.0144,-.0144)`，对应 `N2=.18`、`product=-.36 mol/s`。旧中心预期的 `1/6,-1/3` 被这个独立推导替换；零总扩散质量与全部物种守恒的断言未放宽。

## 适用性与待接入来源门禁

此模型假设气相连续、连通、低密度理想混合物、可用标量沿面 Darcy 渗透率，以及所给有效混合平均扩散系数在当前状态可用。它未实现重力、压力扩散、Soret、Knudsen、Klinkenberg 滑移、非 Darcy 惯性流、气体非理想性、热渗透、吸附、膜界面求解或断连孔拓扑切换；不存在对这些机制的默认“自动足够小”判定。

来源门禁至少须追查并验证：

1. 气氛和活跃反应的物种并集、实际载气、气态产物化学式与相态、质量/元素和热化学单位的一致性。
2. 同材料域的孔体积/连通性、液水占容、孔喉尺度和代表性体积依据。原料粒径 d50 不等于孔喉半径。
3. D_eff 的参考速度、梯度变量、截面基准、温度/压力/组成/含水/转化范围及孔隙/曲折度处理；K、kr、μ 的来源和适用范围。
4. 压差、温差、流速与孔喉尺度是否允许省略上述机制。若采用 DGM，应替换整个气体面输运算子；不能保留本模块 Darcy 并再次叠加 DGM 已包含的黏性贡献。
5. 边界库的成分、温度、压力、有限/无限定义和膜阻力；面系数与当前变形几何的同一步更新。

本次没有真实原泥砖的同材料 D_eff/K/kr 成套验证数据。不得将测试中的 R=8、虚构的分子量和传输系数作为 physical constants、literature 数据或材料参数；它们只检验算术与守恒。

## 验证记录

先写测试，在模块尚不存在时得到 `ModuleNotFoundError`；随后实现。定向命令：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_gas_transport.py -q
```

P1 修正后 **79 passed**。测试覆盖无氧等压反向扩散、零总扩散质量而非摩尔流、正对称二元 D 导出的空物种回归、三物种两侧零库存边界（有/无 Darcy）、非中点面反向交换、光滑组分一阶收敛、压差 Darcy 方向、单物种等温可压缩 Darcy 的压力平方解析解、外库反向供气和供体温度、全物种库存抵消与后续压力变化、当前气体体积压缩、显式非中点面插值、无梯度/关闭通道极限、输入快照不可变、可查询的微小归一化，以及无效输入/真空/溢出拒绝。这些属于程序验证；不能据此宣称真实整砖燃尽、热量、压力或材料输运已被独立实验验证。
