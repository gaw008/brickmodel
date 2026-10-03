# P81 原生残碳严格非负：源码、已存坐标与数值方法研究

本项完成静态推导和已保存数据的逐格映射，没有修改生产方程、状态坐标或数值方法，也没有启动任何生产计算。连续方程的非负不变性只能在下述条件下成立；当前 BDF 离散轨迹和已存负库存仍未通过严格非负验收。所有失败、带符号原值和旧资格保持，整个模型未完成。

## 实际原式与非负边界

实际使用的原源码位置如下；完整带行号节选另存本轮 source-excerpts.txt，AST 只解析、不执行函数。

| 内容 | 原文件与行号 |
|---|---|
| char 线性库存/净源、extent尺度 | `src/sludge_vme/models/full_cycle.py:277–302` |
| Ca/OH库存与char原样继承 | `src/sludge_vme/models/full_cycle_gas.py:172–194` |
| 完整 μ/affinity/Arrhenius/O2/供体 | `src/sludge_vme/models/full_cycle_gas.py:652–691` |
| 原反应熵与热流交换 | `src/sludge_vme/models/full_cycle_gas.py:707–715` |
| 初态/物理与账本导数/外压功 | `src/sludge_vme/models/full_cycle_gas.py:799–827` |
| 原 complex-step Jacobian | `src/sludge_vme/models/full_cycle_gas.py:891–901` |
| 骨架/力学域、共用能量 | `src/sludge_vme/models/full_cycle_solid.py:345–370,407–417,419–516` |
| P80实际BDF调用与保存端点 | `src/sludge_vme/models/full_cycle_cooling_refinement.py:112–128` |
| SciPy Newton、NDF、误差接受、多项式 | `.venv/lib/python3.12/site-packages/scipy/integrate/_ivp/bdf.py:36–69,244–254,352–412,456–485` |

当前名义储气分支的反应顺序是 evaporation、dehydroxylation、decarbonation、organic_oxidation、char_oxidation、organic_carbonization、lime_dehydration。只有第 4、5 号反应改变 char，系数分别为 −1、+1；direct 通道当前关闭，也不含 char。记每格残碳库存为 c、organic 为 o，定义 G(a)=−expm1(a) 当 a<0，否则 G(a)=0。实际方程为

\[
\dot c=P(y,t)-K(y,t)c,
\quad P=A_c e^{-E_c/(RT)}G(\Delta g_c/(RT))o,
\quad K=A_b e^{-E_b/(RT)}G(\Delta g_b/(RT))(p_{O2}/p_*)^m.
\]

这里 \(\Delta g_c=\mu_{char}+\mu_{H2O}-\mu_{organic}\)，\(\Delta g_b=\mu_{CO2}-\mu_{char}-\mu_{O2}\)。A/E、氧压参考与阶数均读取完整根记录；P 的单位 mol/s，K 的单位 1/s。没有用常系数理想衰减替代实际模型。完整 μ 使用共用 h(T)、s(T)，凝聚相再加 `(pressure-P-cap)*v` 和骨架化学势，气相再加 `RT*log(partial/Pr)`。温度、气体分压、孔体积、骨架/相演化与这些系数相互耦合。char/organic 的 Cp 斜率和参考焓熵也来自 assumed 根记录；没有另设反应焓或 equilibrium pressure。

对实数、有限、可容许的耦合状态，T>0、参考压力>0、pO2≥0、A≥0、o≥0 时，G≥0，P、K≥0。在 c=0 且 K 有限时，消耗项精确为零、生成项非负；生成与消耗可以在 c>0 时同时存在，净负导数可以是正常耗减。organic 两条损失共用原 log depletion；在原初值≥0及坐标有限时，o=initial_organic*exp(−field4)≥0，零 organic 初值保持精确零。名义 recipe.char=0.005 kg/kg，已存每格初始 char=0.007805540060113066 mol，原 f5=0.005；名义初值并非零。recipe.char 的声明范围含零，未来表示仍须支持精确零初值和从零生成，不能加 seed。

非负不变性还需要解存在、唯一、局部适当正则且全程留在上述有限物理域。沿真实耦合解，若 P≥0、K≥0 有限且可积，则

\[
c(t)=e^{-\int_{t_0}^t K(y(s),s)ds}
\left[c(t_0)+\int_{t_0}^t e^{\int_{t_0}^u K(y(s),s)ds}P(y(u),u)du\right]\ge0
\]

只对 c(t0)≥0 成立。G 的两侧连续、局部 Lipschitz，但在 affinity=0 导数有折点。char 自身没有 log(c) 或除以 c 的化学势奇点；这不证明完整模型全局正则。气体 log(partial)、力学固定 Newton 的分母、有效热容、孔域与其他相分支仍要求有限正域，源码/已存端点没有证明所有内部状态保持这些条件。当前 incoming P75 有负 char，已违反该定理的初值前提，不能由连续边界条件追认为已修复。

## 原生坐标、已存库存与符号分类

char 是线性独立坐标，`c_i = native_y[5*n+i] * chemical_scale`。当前保存的 n=12、chemical_scale=1.5611080120226133 mol，cell_chemical_scale 逐格相同；状态长 275、extent_offset=180。原 RHS 对 f5 写 `(rate@snu)[:,char]/chemical_scale`，对 reaction extents 写 `rate/cell_chemical_scale`。P81 只读取原 JSON，执行该一次乘法及必要原账本算术，没有调用 decoder、势或 RHS。完整 36 行 f5、scale、既有 char、乘积、signed 差、符号以及相应 extent 关系保存于 `runs/full-cycle/p81-char-nonnegativity-static/saved-coordinate-mapping.json/csv`，不入 Git。结果数字与极值见配套 JSON。

P75 hold incoming 负格为 1、3、5、8、11；P76 coarse cooling 为 1、5、6、7、10；P80 refined cooling 为 0、2、3、5、7、10。incoming→refined 的正到负是 0、2、7、10，负到负是 3、5，负到正是 1、8、11。incoming→coarse 正到负为 6、7、10。坐标乘积与已存解码库存逐格一致；正 scale 不改变符号，因此 char 的负值已在 f5 中，不是 CaO 库存减法重建产生的新负值。coarse min −1.2646807323299508e−18 mol、refined min −8.581861576534481e−20 mol，负格 5→6，严格判据 false 保持。比 atol 小并不等于非负。

另外只做既有线性不变量的带符号算术：`c_initial + xi_carbonization - xi_char_oxidation` 与 f5 库存比较，原 extents 以已存 cell_chemical_scale 转换，既有解码 extent 对照另列。这种大累计数相减在近零 char 处会有浮点消去；差值仅说明两种保存表达的浮点关系，不能唯一归因负 f5，更不能把相减结果用于覆盖原状态。原初始 numeric context 是已存元数据，P78 new_declared_initial_reference 不是原 P68 内存恢复，P81 没有新 initial 调用。

该 `coordinate − ((initial+carbonization)−oxidation)` 带符号差在 hold 为 −6.060255002911057e−17 至 +9.315009602477892e−17 mol，coarse 为 −6.928182707638273e−17 至 +1.2363540953800017e−16 mol，refined 为 −6.070929380647338e−17 至 +1.0063890170421261e−16 mol。已存 decoded reaction_extent_mol 是全域浮点和，并非每格数组；原生逐格求和减既有全域和，hold/coarse 两反应均为 0，refined carbonization 为 0、char_oxidation 为 +2.7755575615628914e−17 mol。原算术顺序差保留，不新增近零归一化判据或 PASS。

OH 同样为 field9*chemical_scale 的线性库存；Ca 的 fraction 状态及 lime/calcite 由 calcium_pool 减其他相重建，是另一类库存相减边界。char 结论不能推广为 Ca/OH 修复。本项不扩大到这些通道。

## 当前 BDF 与 complex-step 的实际限制

离线 SciPy 源码显示 BDF 采用 1–5 阶及 NDF 修正，预测由差分历史相加，Newton 执行 `y += dy`，收敛后用 `atol+rtol*abs(y_new)` 的误差范数决定接受，没有 char≥0 的数学约束。密集输出也是差分多项式。P80 原入口只保存 `t_eval=[end_s]`，没有保存每一步 order、history、Newton iterate 或插值路径。不能从两个端点唯一断定负值来自哪一个内部步骤。

普通固定步 BDF2 的代数式 `(3+2hK)c_next=4c_now-c_prev+2hP` 含负历史权重；即使历史值为正，也没有无条件非负保证。这只是说明多步格式的非负证明不能由连续式继承，不是对 SciPy variable-order/NDF 的逐步重现，也不是本次负值的确定成因。容差控制、账本守恒和半步残差下降均不提供离散非负定理。原 root atol=1e−7、rtol=1e−5、max_step=60s，以及独立 conditional 30s 保持，不调容差或门槛。

当前 Jacobian 对原 physical columns 用 `y.astype(complex)`、加 i*step 并取 RHS.imag/step；step 来自根 1e−24 和 state scale 1。对固定 active branch、有限正域内解析表达，char 的线性乘法没有 abs/clip 分支。affinity.real 判断和其他相分支不是跨切换点全局全纯函数，现有 complex-step 不自动证明折点 Jacobian 正确。新坐标必须推导其链式 Jacobian，并同时处理 active-branch 语义；abs、floor、裁剪或符号判断会破坏该解析延拓，不能直接塞入原路径。

严格 source 身份：根原 native source 清单 50；实际 P75/P76 51，P78 账本 producer 52，当前 P79/P80 producer 53。本轮全部 53 逐文件普通字节相同，原 758 完整参数、物理条件、37 项 context 和旧合同不变。任何未来状态布局修改都需新明确版本和来源身份。负 c 没有实数 log 或 square 非负表示的无损逆映射；不得 clip/abs/seed 后冒充原 checkpoint 原样续算。

## 元素、能量和熵约束

当前 CH2O→C+H2O、C+O2→CO2、CH2O+O2→CO2+H2O 三反应的 C/H/O 原子计量均精确平衡，νchar 与上式相同。生产核仍以同一 rate 向量产生 `dns=rate@snu`、`dng=rate@gnu` 和原反应累计 extent。char 改一条数值式却不给 organic/O2/CO2/H2O 同一 extent，会破坏元素与原账本。

共用内部能量使用 us=h−P*v、ug=h−RT；温度式有 `heat+flow−sum(us*dns)−sum(ug*dng)+cap*dvs` 及原骨架/相存储项，外压功累计槽为 −P*sum(db)/escale。反应熵为 `−sum(rate*dg/T)`。在非负供体及实际 affinity 限制下，单向两条 char 反应 rate≥0、dg≤0，所以其连续反应熵贡献非负；这是条件化方程结论，非所有时刻实测或离散 S 保证。负供体可能使 rate/熵符号逆转，本项没有重新计算 rates 确认实际发生。新方法需共用同一反应进度、完整 U/S 和机械/边界功，不能另加反应热，也不能因守恒账本低 0.1% 便授严格非负或热力学路径资格。

## 候选取舍及真正最小下一工作

| 候选 | 精确零与生成/消耗 | 本问题限制 |
|---|---|---|
| log(c/scale) | 有限 q 不能表示零；qdot=P/c−K 在零生成时奇异 | 当前名义初值正不解决一般零；负 checkpoint 无损迁移不可能，不能先预定采用 |
| c=scale*q² | 零可表示，但有限 qdot 在 q=0 给 cdot=0 | 正生成需 P/(2q)，零点奇异/逆映射分支不唯一；不解决生产边界 |
| log1p/移位指数 | 零可有有限坐标 | 仍需 q≥0，原 BDF 可跨界；新隐式正下限不能取代真零 |
| char 单独冻结 P/K 的解析或隐式更新 | P/K≥0 时可保持零与非负 | 冻结完全耦合 μ/T/gas 不是原方程的完整离散解；若不同步反应 extent 与热量便失去原计量 |
| 联合 reaction extent 的生产消耗格式 | 可能同时保持零供体、生成与损失以及同一计量进度 | 共享 organic 两供体竞争和 char 串联要联合求解；零 donor 比值须解析极限，不能 floor；元素一致不自动证明离散 U/S/二阶精度 |
| 积分因子 c=(c0+b)exp(−l) | bdot=exp(l)P、ldot=K 可在方程层保留零初值和生成 | 增一变量/布局，b 的离散非负仍需证明，累积 l 可溢出；不能拿两个新 BDF 坐标冒充已解决 |

下一最小方案是先形成**三条 organic/char 反应共用进度的非负离散合同与数学推导**，保持原完整 affinity、供体、元素、U/S、压力功及精确零，明确零 donor 极限、同时生成/消耗和 complex-step/Jacobian 所需变更。上述联合 extent 是优先研究候选，尚未证明可接入全部气热力耦合，不是已选定实现。此下一项只需现源码和本项保存映射，不需再跑原负 checkpoint、更多容差搜索或广 UQ。若无法给出非负/计量/热力学同时成立的合同，应明确哪个约束尚缺证据，不能假设新 log 必须可行。

未来真数值实现若被单独采用，必须从声明的可容许原生初态产生新轨迹；不能把 P75 负态改成正态并称原续接。至少需持久化真正接受步的 char/三反应 extent 和必要 U/S，而不是仅末端点，预算和独立一次 time/grid 必须事先登记。本项不分配这些窗口，不提出调用生产 evaluator 的专用 checker/test，也未新增 guard、重试或实现。P80 final cooling_hold 比较候选保持 proposal_not_adopted。

## 当前验收与交付

本项静态证据完整性、53 源码字节保持、758 根记录保持及 36 行原生/库存映射按实际结果登记；没有新物理数值 PASS。P78 八阶段端点账本及 P80 cooling 局部半步证据只按原范围保留，严格负库存、最终四指标 time/grid、连续峰值、最新三方案与反演缺口仍在。名义余水历史 0.1358920787402553%>0.1% 保持失败，CaO 零预算 relative=null/passed=false/undefined_zero_budget，旧 P34/P40/P44/P45/P50 撤回/P51及资源失败全部保持。参数 758=144 literature/614 assumed/0 measured，动力学、工艺、跨材料与高温外推不能当目标实材验证。

Git 普通后继/push、一次原 Drive 增量名称大小父目录、实际恢复和历史存储分别留收据：`runs/full-cycle/p81-char-nonnegativity-static/final-delivery-state.json`。元数据不等于字节恢复；本项恢复 0，压缩原件/唯一历史不删除，历史 20GB 目标及 GitHub 容量警告未解决。科学 wall/CPU 不适用；实际行政与研究墙钟由 preparation→report/final 的 UTC 差记录，不写成 0 秒科学成功。读取 JSON 的行政类型错误和输出截断另存 formal-administration，不影响原科学数据但不能抹去。
