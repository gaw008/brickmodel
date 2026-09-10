# SourceWetStorage：独立物理接入契约

基线HEAD caf7777；只读现有mass_wet_storage、rigid_storage、source_mass_caloric及既有水液汽桥/源元数据。没有新论文搜索、没有改repo。目标是复用现有水气实际EOS的源干物湿点储能，不是独立重建PDE，也不是完整材料模型验收。

## 必须保持的状态与参考语义

- 固定来源材料：Arlabosse原混合来料干物及其35–105°C热容域。干物质量m>0固定进入storage identity；新state不能允许无声改solid。若m精确为Fraction(1,5)，不要经float(.2)回读再比较而丢掉固定质量语义。可让state省略可变固体字段、只携带绑定m的身份；否则应保留精确m。
- 化学策略精确为ReactionDisabled，solid_ids仅真实Arlabosse ID，gas_ids有序为O2,N2,H2O。返回零固体/化学气体生成与零反应功率；不构造ReferenceSolution/A/B。允许state携带液水和气体库存不等于已有相变时间推进。
- 固体`u_s(T0)=0`是来源域内的相对能量坐标。固定m、不反应时它可与水/气原有共同NIST对齐能基同时存在，无需把solid anchor强制设298.15K。液水与水蒸气的reference、source资产、实际backend、摩尔质量与R必须保持同一来源桥；仅靠相同species名称不足。
- 纯水相变若以后改变nl/ng，U由现有各相内能直接计算。不得再额外加一次L*dn或“反应热”。当前storage只定义给定库存的点及逆解，不解决相变动力学、吸附/结合水或窑炉反应。

## 容积：只有明确契约，不能用假密度补足

输入为恒定可用流体体积Vp（不含骨架），有正值、单位、误差、适用域及证据分类。当前可以明确manufactured情景用于数值接入检验，且必须有显式允许与material_qualified=False。若允许source-backed体积，须有完整原文数值/单位/试样材料与制样/孔隙定义/误差/来源资产，不能只填source_ids或一个confidence标签。尚无同Arlabosse材料真实体积来源时，不自动提升材料准入。

湿bulk density不是干骨架比容；实验球直径也不确定内部流体空间。不能把Nylen材料球体积拿来补Arlabosse来源。给定Vp足以求水+气压力和总U，但不提供Vbulk或固体体积，因此**不得从fluid.enthalpy+solidU冒称total enthalpy**。推荐新point不提供总H，或者显式None；fluid.enthalpy保留原含义。若以后提供真实Vbulk，才能另行定义并审查U+pVbulk。

机械方程仍为`nl*v_l(T,p)+ng*R*T/p=Vp`。nl可为0，所有库存非负；ng=sum gas>0是现有气体顺应性和热容下界的前提，纯液体封闭点不在这条现有数值契约中。

## 总能量、热容与误差公式

令原RigidStorage结果为Uf,Cf,Cf_min,epsUf,epsP，来源干物比内能为us(T)=delta_h(T0,T)。

`U*=Fraction(Uf)+m*us(T)`，`Uout=float(U*)`。

`Cpoint=Cf+m*Cp(T)`；`Cmin=down(Cf_min+m*min_[Tlo,Thi]Cp)`。正斜率源关系的minimum取整个主机逆解域下端，不能使用查询点Cp冒充。Cf是现有水气沿机械闭合的热容，不能改为简单nl*Cp_l+sum ng*Cp_g；该差别包含压力反馈。

`epsUtotal=up(epsUf+abs(F(Uout)−U*)+nl*B_du_dp*epsP_extra)`。

如果Vp的输入精确值转float，体积总误差还须含转换差。额外volume误差通过机械压力导数下界传播：`|dF/dp| >= ng*R*T/Pmax²`；先用原全域Pmax获得全局包含区间，完整区间须仍在允许压力域，才可用已证明较小Pupper改进局部epsP_extra。nl*B_du_dp项不能漏；没有体积误差时不得人为添加制造偏差。

source_mass_caloric的名义干物能量是精确Fraction；物理fit/不可压缩近似误差仍unknown，不能加入一个0后宣称已覆盖。原water declared envelope仍只是有条件数值契约，实际点验证不能把声明自动提升成全域证书。

## 温度和逆解接口

储能各部分必须使用同一个实际温度。若fluid接受binary64，先确定共同`t=float(input)`，检查其精确F(t)在source域，再给solid传F(t)。不能fluid用float(t)而solid用原exact Decimal(t)却声称完全同点。域端点需注意308.15 binary64略低于精确来源下界；可选内缩的显式主机域，如320–340K，不得隐式剪裁。

能量target采用明确的表示语义。若接受Fraction/Decimal后转float，应保留并传播转换差，或明确API把转换后的binary64作为目标；不可无声把原精确目标当成同一个数。支持负固体相对U及负总U，因为形成能/参考零点可使这些值为负；正性只要求热容和库存。

逆解必须绑定同一storage/固定m/anchor/volume/来源/数值策略，要求完整温度括号位于各provider共同域。数值残差加聚合误差除以全域Cmin给温度上界；不满足能量和温度两门槛、端点符号不确定或超域时拒绝，不能以float残差恰为0伪成功。

## 后续独立真实水单例的预定范围

root代码就绪后单例检查，禁止长轨迹。建议状态T=330.125K、m=1/5kg、T0=313.15K、nl=.2mol、气体(O2=.01,N2=.03,H2O=.001)mol、恒定可用流体体积.001m³，主机温度域320–340K、压力括号50–500kPa。体积和库存明确数值情景而非来源材料实测。实际参数以root固定实例为准，变更须先记录原因而不是按残差调节。

独立脚本将用真实水provider与单独压力根求解/气体逐项能量聚合，比较源湿点U/压力/点热容和误差，不把调用新host生成的值当oracle。源码未完成前未运行此水实例；已先完成独立Fraction干物项，保存SOLID_ORACLE.json。外部单例墙钟建议45s，失败/超时保留记录且不盲目扩大预算。实际复核不覆盖材料物性、N格、相变事件或全域水误差证明。
