# 水平平界面分支的共享液相Darcy面

实施前合同：独立液体state带真实T/P/n/S及压力误差、同储能参考的v/h和来源；每侧在真实饱和度上查询有身份、出处、T/P/S域的分段线性k、krel_l、mu关系。`relation_kind=frozen_manufactured`仅制造测试；`tabulated_saturation_relation`显式状态查询与插值政策，可含平台或常数，不能因表值变化自动获得真实物性资格。无源参数保持unknown而非补默认。连通性另有显式身份/来源，可为虚拟设计假设，不能从湿库存推定。

面使用bulk面积与两半格距离，λ=k*krel_l/mu，Q=A ΔP/(dL/λL+dR/λR)，Ndot=Q/vdonor，Edot=Ndot*hdonor。Fraction表示输入的乘除/串联避免中间上溢，非零最终下溢拒绝，不用epsilon截流。disabled或任一零mobility明确零；活跃且非连通/未知连接/无液体退出。每side实际压力误差合并，方向区间跨0时仍保留名义流并标方向未认证，不伪造严格物理方向。冻结系数/单一供体密度为有限体积上风离散，不是精确可压缩稳态解。

预登记独立验证：k=(2,1)m²，krel=(.5,1)，mu=(2,1)Pa·s，半距=(2,3)m，面积4m²，压力(120,50)Pa给Q=40m³/s；供体v=2m³/mol、h=11J/mol给20mol/s、220W。反向改供体v=5/h=−7，Q=−40、N=−8、E=56，绝对1e-12。另验证零梯度/零mobility/disabled、无液/连通域、关系真实S插值、单位边界/制造门禁和极端浮点最终可表示vs下溢拒绝。有限事实来源身份/哈希只作可追踪声明，不代表独立材料准入。

实现API：`LiquidTransportState`、`SaturationMobilityTable`、`LiquidConnection`和`liquid_face_exchange`。面函数接两个state、两个relation、connection、实际bulk面积与两侧半格距离、manufactured opt-in，返回不可变`LiquidFaceExchange`。正Q/N为left→right；正/负供体依真实名义方向选一次，只产生一个共享mol/J值。液体负生成焓时，负摩尔流乘负h可得到正能量通量，不可再对能量符号取绝对值。

state元数据、provider方法/版本与资产哈希必须跨面一致；两侧T/P/库存不同合法。公开state可由调用者构造，其来源字段是绑定契约，不会凭标签替调用者验证EOS。真正主机必须从与储能相同的source-gated water provider于当前解码T/P取得v/h；本算子不拿气相温度/饱和液焓替换它。正库存需正饱和度与有限v/h；零库存必须S=0且v/h=None，禁止伪造干格液相状态。

表逐状态在有效S域内按Fraction线性插值有限非负k、0≤krel≤1、严格正mu，T/P也需在声明域内。S域不覆盖当前状态就退出；不外推、无默认残余饱和度。每次返回的mobility诊断含当前T/P/S、实际系数、关系ID/版本/分类/资产及插值方法。`frozen_manufactured`要求表各列常量且分类制造；`tabulated_saturation_relation`可来自文献/派生或制造，允许局部平台乃至有据常数，不把数值变化当作来源准入。全部仍`material_qualified=false`。它只是一个明确的受控状态依赖入口，不自动提供污泥本构、温度依赖黏度或毛细关系。

执行次序：先核对身份/门禁/几何，再对disabled给明确零；其余面先按两侧实际状态查询关系，任mobility为零即返回zero_mobility，可不要求干格的液体v/h；两侧均非零时要求显式connected且两格已有液相，之后才按名义ΔP选择供体。disconnected和unknown的活跃面是不同输入状态但都退出未支持的连接分支，不把它们伪装成零渗透率。外液体库/干孔浸润不在此接口内。

ΔP误差由所给两侧εP有向相加，`direction_qualification`区分conditional_direction_resolved与nominal_direction_not_certified；零名义差单列zero_nominal_pressure_difference，不能称物理流严格为零。`pressure_interval_scope=fixed_decoded_temperature`，`full_inverse_direction_certified=false`始终保留，因为当前εP并未包含温度反解误差到压力的传播。主机须保留原inverse温度误差链。差值与所有半格阻力/Q/N/h乘除按所表示输入Fraction计算；只有最终所需字段才舍入，非零最终不可表示会明确报LiquidTransportError，真正零k/krel/ΔP不算下溢。

结果保留液体完整源身份、connection身份、各side关系诊断及合并来源。方程形式依据已保存MOOSE Darcy及相焓输运快照，见`docs/sandbox/research/LIQUID_FACE_DESIGN.md`和独立审核；它不是这些系数数值的来源。液体流功已包含在h，额外pQ或潜热源会双计。

测试先于实现，首次因新模块不存在收集失败；首版9项通过0.03s，新增几何/来源/表域/平台/完整诊断/参考身份回归后20项通过0.05s。独立手算不使用面函数返回结果作真值，极端测试令中间mobility约1e600仍得到有限Q，并验证非零最终下溢不会称平衡。真实固液气host接入、共享账本积分及空间/时间收敛属于后续主机验证，不能由这20项面离散测试推出材料已验证。
