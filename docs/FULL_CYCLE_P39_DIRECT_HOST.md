# P39 条件化直接碳酸化主机通道

UTC 2026-10-01T21:10:07.930204+00:00。已将P37显式迁移率算子接入有限孔隙气体/热弹性主机，完成本轮四个真实完整RHS状态核查。P39限定实施完成，完整模型及新通道全周期物理数值验收未完成。根469=144literature/325assumed/0measured，旧460完整条目保持；新增6运行项、独立synthetic L和2域数组。根名义direct_carbonation键缺省为未启用，绝无默认砖体L或A/E。

## 实际主机接线

调用make_cycle之前提供完整config['direct_carbonation']。必需mobility_parameter、identity、material、temperature_range_parameter、humidity_pressure_range_parameter、surface_basis；参数必须在统一根parameters且value/unit/range/source/status完整，L单位1/s。主机从条目读取value/source/status，从合同读取身份及材料/T/湿度/表面域；缺字段KeyError、错单位ValueError由现接口暴露。gas.storage=0明确不支持该通道，不静默忽略。正CaPool为线性钙坐标前提，本轮不是零钙材料资格。调用域声明不等于实材证明。

主机先按原七反应构造A/E/reactants/hazard/depletion_loss，后增active第八direct ν=νhydroxide−νdecarbonation。固相calcite+1/portlandite−1，气体H2O+1/CO2−1，CaO净0。Δμ直接取当前完整μ与ν的积，包含同一热容/相、压力/毛细/骨架、气体分压；水结合项对direct计量为零。算子rate尾列进入统一dns/dng，在机械/温度/储能/熵计算之前加入一次；不分解再添加旧h/c、不另加反应热，不把算子返回熵再加一次。

calcite用全部净源/CaPool；OH用全部净源/chemical_scale。direct或原正carbonation_factor选择线性calcite坐标，允许零calcite生成；二者均无时旧log路径。OH+ξh+ξd及calcite+ξc−ξd可独立诊断；ξd是第八累计进度槽，不由库存反算。Solid额外phase块仍统一移动gas/extent/last，原边界in/out、压力功/熵槽随last正确移动。独立extent只作为输出账本，不反馈RHS；旧7动力学参数未添假A/E。

reaction_fields及totals输出第八extent，active反应定义传给whole/eightstage gas、freewater及dryingwater helper；报告输出active_reactions和完整条件合同。未对旧根reaction list append。原库存数值分辨率预算仍仅用旧七项及原参数，未以新增extent扩大验收bound。关闭direct时calcite旧浮点表达式保持；仍有新direct=None和报告字段，未声称整个输出字节不变或动态兼容重新通过。

## 本轮实际证据

四状态沿P36根物理输入重新构造受影响主机，但没有重跑P36旧两rate或P37孤立标量。每状态完整12单元、1rates/1direct回调，全部实际负Δμ；没有人工逆向或平衡输入。每状态liquid_coordinate_rate实际调用2次、其他被登记的thermo/skeleton/transport/water/heat/mechanical/relaxation各1次，完整回调计数见JSON。总4RHS/4direct回调/48direct格，非4局部节点。

| 状态 | cell0 r (mol/s) | cell0 Δμ (J/mol) | cell0 direct熵 (W/K) | 结果 |
|---|---:|---:|---:|---|
| pure_portlandite_humid | 1.37395294e-05 | -57920.08 | 0.00266910831 | 通过局部接线 |
| pure_calcite_humid | 0 | -57920.0744 | 0 | 通过局部接线 |
| mixed_high_CO2_low_H2O | 9.89832827e-05 | -66351.5119 | 0.0220281417 | 通过局部接线 |
| mixed_low_CO2_high_H2O | 3.29944276e-06 | -53478.395 | 0.000591812521 | 通过局部接线 |

监督UTC2026-10-01T21:04:38.867178+00:00起，唯一硬截止2026-10-01T21:06:38.867178+00:00；实际2.079101042s，四child退出0并回收，无重试/超时/未知失败，0积分/Jac扫/fit/UQ/恢复，2MiB事前上限、实际当时1,215,044B。timeout停止路径本次未触发。登记至报告561.670s包括实现/阅读/审阅/文档，不叫积分时间。

所选状态νr/source/CaO0/Ca与OH坐标/独立进度/气体log坐标/孔体积和机械参数传递局部恒等最大相对1.75254187e-14<根1e−11；direct熵非负。共享主机瞬时熵identity最大绝对1.33226763e-15W/K，原始signed值保留。采用同一RHS导数构造差值的气体/水helper输出含direct+H2O/−CO2；其helper判定仅代数接线，非时间演化端点、独立flux积分或完整能量PASS，部分导数替代库存可非物理。没有调用summarize增加RHS/本构求值，真正八阶段端点动态汇总仍待轨迹。 嵌套helper继承solver-integrated字符串在P39不适用，以本段为准；三伪CO2端值约−1.5843e−4/−1.1160e−3/−2.1889e−5mol均非轨迹库存。host熵identity仅保存、未进入local_pass判据；源项/extent恒等同源，不授独立能量或熵验收。

正向/零OH证据不能升级P37合成逆向/A0为真实主机证据；A0一般不光滑，complexstep沿real branch，仅保持原约定，未做Jac资格。适用域只是298.15K根synthetic L诊断，无湿膜、界面面积、产品层或源实验/实砖宏观率。

## 未通过与可审阅下一步

P34旧普通81/气体108/四指标加密仍仅原f6694445证据，不能自动赋予本轮条件核。旧逐相30/81失败、strictOH未资格、名义干燥0.1358920787402553%>0.1%及负值/近零分母保持，原两次工艺尝试不再搜索。0measured，新核固定比较/反演/UQ资格未取得，wholefalse。

P40仅候选：事前冻结覆盖所选轨迹的显式L/域和Ca库存，受影响baseline一次、time/grid各加密一次共最多3积分；候选同一固定synthetic短瞬态：12格基准/12格仅time/24格仅mesh，每次300s、唯一总900s、单并发、2MiB、问题最多2次，无fit/UQ/恢复/额外Jac扫，原门槛和根分母尺度保持。独立OH/Calcite/direct路径、4gas、元素/质量/完整能量、strict熵必须保留有符号失败。实际积分将产生内部RHS/Jac回调，需真实计数，不借四调用重新标记。P39未登记P40运行参数或启动该批，不能以关通道/换工艺/延时对照代替原失败。

正常后继Git/push与明确小增量Drive名称/大小/父目录metadata另读实际收据。停止下载/解包/恢复，保存全部压缩原件和独有历史；metadata不是恢复，完整历史/20GB/GitHub容量告警未解决。

P40候选初始化前提：必须使实际动态y0、声明初始固相/总Ca/气体/phase coordinate与独立extent零点一致，账本initial/reference直接取实际y0。不得仅覆盖P39单点Ca分数就把原名义initial当动态起点；ξdirect仍独立积分，不从库存构造。现温域[298.15,298.15]K不能准入自热轨迹，若新synthetic动态域需事前根assumed登记，不能升为实砖/来源实验或八阶段资格。关闭direct的calcite表达式已恢复旧−rate，但并未因此给当前源码动态兼容PASS。
