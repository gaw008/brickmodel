# V-B1：共同气体边界的限定验证

2026-09-21 UTC，固定复核已推送开发提交`da5774b`，见[验证合同](../../../GOAL_VB1_OPEN_GAS_REVIEW.md)。**共同气体边界的来源公式、保存算术及本批纯气体运行通过限定复核；湿砖整列实际运行和真实材料准确性仍未验证。** 开发代码未在本阶段修改。

## 实际执行及独立性

复用[D-B1的100步记录](../../../../data/sandbox/research/open-gas-boundary-v1/development-outward-medium.jsonl)，新执行以下四次离线入口；各次均为根参数声明的1秒，没有模型拟合或在线运行依赖。

| 参数条件 | 步数 | 最终T，K | 最终P，Pa | 保存记录 |
|---|---:|---:|---:|---|
| outward | 50 | 550.7248428810271 | 99417.86988983571 | [记录](../../../../data/sandbox/research/open-gas-boundary-review-v1/vb1-outward-coarse.jsonl) |
| outward | 100 | 550.7241610015626 | 99417.70333807691 | 原开发记录 |
| outward | 200 | 550.7239943326567 | 99417.66293060666 | [记录](../../../../data/sandbox/research/open-gas-boundary-review-v1/vb1-outward-fine.jsonl) |
| inward | 100 | 548.4335344852298 | 99309.72776000157 | [记录](../../../../data/sandbox/research/open-gas-boundary-review-v1/vb1-inward-medium.jsonl) |
| 初始同压同温 | 100 | 549.5736627621227 | 99368.90823937363 | [记录](../../../../data/sandbox/research/open-gas-boundary-review-v1/vb1-equal-medium.jsonl) |

共550接受步。独立后处理不导入模型模块，用新读来源系数和Decimal50计算通量/携焓/EOS，用Fraction解释保存的二进制浮点状态和有理数交换账。它是同一助手在独立Goal内的不同计算路径，不是第三方认证。首次后处理出现整数温度转float后与Decimal混用的TypeError，已仅修正后处理类型并重算；[尝试记录](../../../../data/sandbox/research/open-gas-boundary-review-v1/review.json)保留该失败，未改模型或轨迹。

## 来源、单位和物理定义

重新核读NIST的[O₂](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Mask=1&Type=JANAFG&Table=on)100–700K、[N₂](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7727379&Mask=1&Type=JANAFG&Table=on)500–2000K和[H₂O](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1&Type=JANAFG&Table=on)500–1700K实际使用段。24个A–H系数和三项生成焓基准与已存包一致；[独立读回](../../../../data/sandbox/research/open-gas-boundary-review-v1/source_readback.json)保存数字、温区和URL。Shomate显热为kJ/mol，转J/mol后加生成焓；理想气体`u=h−RT`，不是只用显热替代共同能量基准。

混合物扩散形式参照[Cantera原方程](https://www.cantera.org/stable/reference/onedim/governing-equations.html#diffusive-fluxes)，继承的修正漂移采用供体质量分数，不能把这个离散选择称为文献逐字给出的实现。Darcy体积速度与相对渗透率的定义见原[MOOSE离线来源](../../../../data/sandbox/transport/moose-governing-equations.md)Advection节。传递参数依旧是显式虚拟选择，公开定律不决定真实砖坯的这些数值。

独立推导使用`Nout=Ndiff+Nadv`；扩散与平流分别乘公共面温度和实际供体温度下的摩尔焓。将摩尔流mol/s乘J/mol得到W，总流能还加传导热。按照[开放控制体内能关系](https://www.cantera.org/stable/reference/reactors/controlreactor.html)，固定体积单元只累计`ΔU=−∫Eout dt`，不另加流动pV功或潜热。混合气体为理想近似，动能/重力及真实砖材迁移误差未获验证。

## 保存收支与独立复算

对每个接受步独立计算：

`r_k = n_new,k − n_old,k + dt*Nout,k − δn_projection,k`

`r_U = U_new − U_old + dt*Eout − δU_projection`

三组分各自`r_k=0`，因此按声明摩尔质量加权的总质量余差也为0；每步`r_U=0`。550步共2750个等式全部成立，其中总质量是组分等式的线性组合，不增加独立物理证据。各次累计收支也为0；这里扣除了明示浮点投影差，**不代表真实物理误差为零**。

| 独立比较量 | 全部保存节点最大绝对差 |
|---|---:|
| 不扣投影差的单步组分账 | 1.354×10⁻²⁰ mol |
| 不扣投影差的单步内能账 | 4.441×10⁻¹⁶ J |
| 重算净组分通量与程序 | 4.741×10⁻²⁰ mol/s |
| 原扩散流按摩尔质量加权后的净质量通量 | 3.460×10⁻²³ kg/s |
| 重算总功率与程序 | 1.848×10⁻¹⁵ W |
| 功率拆分的二进制舍入差 | 1.109×10⁻¹⁶ W |
| 重算理想气体压力与保存压力 | 4.458×10⁻¹¹ Pa |
| 重算物性内能与接受状态U | 7.221×10⁻¹² J |

完整值及每次方向、温压范围和累计量见[独立算术](../../../../data/sandbox/research/open-gas-boundary-review-v1/arithmetic_review.json)。压力/内能差是名义状态方程和反解残差，不是材料误差或时间截断误差。供体选择独立重算无不一致。

物理上可区分的行为已经出现：outward的100步中，Darcy平流前55个接受中点向外、后45个向内；整个过程O₂/N₂净流入而H₂O净流出。因此不能把案例名字当成全部组分或全程同向，也不能把“初始同压同温”当成全程无压力流动。

## 熵与时间分辨率的范围

以理想气体`μ_i=h_i−T s_i`和共同基准，独立计算保存中点的名义界面总熵产生：

`σ = Eout*(1/Tr−1/Tc) + ΣNout,i*(μi,c/Tc−μi,r/Tr)`。

标准压力在差式中消去；只读实际正分压节点。550个名义值均为正，最小约8.837×10⁻⁵ W/K，见[逐点记录](../../../../data/sandbox/research/open-gas-boundary-review-v1/pointwise_entropy.json)。这是本批节点的代数评价；没有完整区间误差界、有限步熵不等式或所有可能参数下的证明，不能授予完整第二定律认证。

同一outward条件50→100与100→200步的最终温差依次为0.0006818794645K、0.0001666689059K，差值比约4.091；压力差依次为0.1665517588Pa、0.04040747025Pa，比约4.122。支持该条件下接近二阶的描述性变化。O₂/N₂/H₂O和U的描述阶数分别约1.865/1.844/2.580/3.209，原差异保留，不强行归为同阶；供体切换和分量抵消使有限档估计不能替代全局误差界。未运行湿砖空间收敛或真正独立的连续精确轨迹对照。

## 湿列接线与阶段结论

静态核读确认：适配器替换末面、内部面和左侧闭合面保留；`_integrals`给全部气体分量积分；`_advance`对每个组分采用左右面差，只给H₂O加入相变量；U只采用共同面能量差；接受中点通量回到旧接受状态更新，预测步不重复累计。`OpenGasColumnLedger`保留相应预测/中点记录。没有发现本次接线的符号或漏载气问题。

这不是湿主机实际运行验收。旧湿态构造、state和provenance会调用SHA绑定，当前未执行；`equilibrium_transport`仍有固定载气前提，不能直接拿该边界替换后宣称局部平衡路径已通过。新`case_id`是声明标签，不能冒充内容认证。所有旧记录和失败保持原状。

**本阶段关闭共同边界本身的来源/保存算术及本批条件运行验证；完整材料/训练/D1仍未准入。** 下一独立开发应解决当前湿主机依赖SHA的执行路径，才能在用户约束内实际运行低温湿态接线，再做该路径验证；不能把本批高温纯气体示例当作湿砖干燥完成。本轮没有新增测试、SHA操作、运行时网络或物理代码修改。
