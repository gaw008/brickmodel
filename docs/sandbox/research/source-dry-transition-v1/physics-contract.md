# 来源 N1 湿→干算术适配审查

只读现有 next-runtime-slice.md、source_net_panel.py、source_net_prefix.py、source_net_roots.py、exact_affine_depletion.py、rational_polynomial.py 和 depletion_roundoff.py。无 EOS，无生产修改。

1. 必须是实际 N1 原湿模式、固定干 kg、4 个流体槽 (liquid,O2,N2,H2O)，显式禁用化学；使用同一真实初态、同一两个实际求值、相同精确 start/interior/upper 和完整源绑定。面板已有 validator 保证化学零、phase=(-E,0,0,E)、face 映射及固定 kg；新 caller 必须另证这是合法实际求值路径，不能仅凭两个任意库存样本宣称真实终端。
2. ExactAffineSamples 的液体三项必须逐项是 (J_left,-J_right,-E)，不能先把三项相加再投影。本片段两面液流为精确零，故 (0,-0,-E)。gross evaporation 必须使用原实际 phase 的 E，不使用净排空。令 hm=interior-start，aE=(Em-E0)/hm，要求 min(E0,E0+aE*H)>0；仅检查两个样本 E>0 不够，若 upper 超过 interior，仿射外推可能转向。还须 p(H)<=0，全部气体首根严格晚于液体（或无根），初始所有 4 库存严格正。零初始、并列、切触、非单调、液体运输耗尽均不授本写回路线。
3. 源前缀相变积分只算一次 I=E0*h+(Em-E0)*h²/(2hm)，phase liquid=-float(I), vapor=+float(I)。旧三项 liquid float(-I) 必须逐字数值相同（IEEE 零的符号不改变 Fraction，但不能改率/误差）。源 raw liquid=float(F(N0)-F(float(I)))，与旧 reconstructed 完全一致。其余面气体/U仍来自 build_source_prefix，同一面一次投影、一次库存投影；不得只用旧三项拼出液体然后省略 source prefix 的全部分量/完整残差/焓分解门槛。U总面功为权威；没有额外潜热或写回能量。

## 根预算的最小复用

strict derivative<0 on [0,H] 时，非点 quadratic source root 的 branch 正是 [0,H]；既有 source 根每轮与 legacy refine_descending_bracket 完全同算术、同 midpoint==0 归 lower 约定。以已排序 chosen root 的 bracket/refinements 继续，用 source order 的 refinement_level 加后续实际轮数约束原 maximum_refinements（且<=256）。构造 ExactAffineEvidence 时 iterations 是原 H dyadic 深度，不是新增轮数。检查其原 time/correction/local ULP/fraction evaporation 门槛失败可继续，但只消耗剩余预算。不要从头调用 locate_exact_affine(maximum_refinements=remaining) 而丢掉旧层数；也不要调用完整预算两次。

例外：source 线性/精确端点 root 为 point，refinements=0，不能包装成旧 Evidence 的零宽 bracket。可从精确根 tau 及原 H 显式构造宽 H/2^k 的 canonical adjacent bin：非 dyadic 根按 floor(tau/width)；对 dyadic 内部根取 lower=tau；tau=H 则 lower=H-width。完整 bin 仍检查 lower>0、p(lower)>=0、p(upper)<=0。从已耗排序轮数起选层数，不给 point 路线额外完整预算；实际新增层数与原 dyadic 层数分别记录。若无法在剩余层数满足微小校正，明确 exhausted，不能改门槛。重建验证现有 evidence 不应当作新的求值/新科学证据。

## 全链账本：同一原始初态，不重置

每格每槽保留原积分器实际 represented face/local 增量；terminal 保留 source prefix 完整 exact integral、integral projection、state projection。对任意前缀：
R_N=N_current-N_initial-sum(face_left-face_right+local)-sum(writeback_actual_delta)。
每次 writeback 的 ideal delta=(-d,0,0,+d)，actual vapor=F(v_after)-F(v_before)=d+rho，实际液体=-d，rho 是 vapor storage roundoff；U写回严格0。模式转换仅 operator identity 改变，energy identity/kg不变，不产生库存项。dry普通段继续加入同一总账；不允许在 mode change / fine path 起点重新建零 totals。

逐前缀同时保留 represented residual 与 full-exact residual；后者还包含普通/terminal面投影误差，不能把误差项重复扣除。普通积分余额用原 IntegrationPolicy；写回事件单项/累计绝对 storage、correction 用原 DepletionRoundoffPolicy，两者不能互相替代。水总量 Rw=R_liquid+R_vapor；显式理想写回水变化0，实际水变化rho。元素 H=2Rw、O=Rw+2R_O2、N=2R_N2；固定固体元素在差额中抵消，不能声明未知固体绝对组成。流体质量差=water_M*Rw+O2_M*R_O2+N2_M*R_N2，M取已有实际来源物种元数据；原事件政策的 water_M仅用于原写回预算，不能借此虚构干物分子量。U账本含外边界能量，closed才可能全局0；每次写回前后U应逐位不变。

独立对照应分别审核：普通接受前缀；terminal raw；writeback 后（rho不能被漏掉）；实际 dry 事件评价；每个 dry 接受步。时间误差/两条实际路径原四门槛另判，守恒通过不证明真实耗尽时刻。真实凝结驱动退出不能由数值 dry 模式屏蔽。

## 已执行独立算术

check_arithmetic.py 最终 138 项断言通过，0.007294 s；只用 Fraction/标准库。覆盖常蒸发、加速/减速但全域正蒸发的 6 个 dyadic 层数、三项与共享 phase 积分投影一致、非点连续细化复用、线性/内部精确/上端点 canonical bins，以及采样正但上端转凝结、净零液流不代表无运输、排水伴凝结、汽储存 sub-ULP 丢量、跨段余额重置反例。

初版同样通过；人工复读发现一个 point-bin 检查意外引用上一循环的 hi，改为直接检查 width>0，已保留 check_arithmetic01.py、ARITHMETIC_RESULT01.json 和 ARITHMETIC01.log；最终 ARITHMETIC02.log/ARITHMETIC_RESULT.json。没有隐藏失败，没有变更模型或门槛。最终脚本 SHA256 c808024ea4ae809a22f02aaa91861a012b0c28d88ecf4535472b2f3d9dbc9ecf。
