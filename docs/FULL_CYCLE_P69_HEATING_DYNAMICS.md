# P69 保存升温端点的原生能量与熵变化率

P69 已用真实P68 heating原生端点t97200s完成唯一saved-state导出：rc0/reaped，wall1.661012708s/CPU0.715526000s，科学全部1438584B/4194304B，120s窗口已关闭。1load/1构造声明、0initial、实际1nativeRHS/rate/chart、15完整势值，Jac/ODE/summary/fit/UQ0；source50普通文本匹配，758完整records不改，144literature/614assumed/0measured。原生与投影Udot均2.0827150877870784W、Sdot均0.001825961403377241W/K；U对外部signed差4.440892098500626e-16W，派生Fdot差3.3306690738754696e-16W。实际metakaolin非零、qdot非零，但phase总功率8.347174595727095e-39W，仍不授充分液相/全周期资格。criterionNA/wholefalse；原干燥/物理/资源失败保持。详见docs/FULL_CYCLE_P69_HEATING_DYNAMICS.json/md。

|量|原生值|完整势投影值|投影减原生 signed|
|---|---:|---:|---:|
|Udot / W|2.0827150877870784|2.0827150877870784|0.0|
|Sdot / W K⁻¹|0.001825961403377241|0.001825961403377241|0.0|
|派生 Fdot / W|-0.917072926349323|-0.9170729263493227|3.3306690738754696e-16|

原外部heat/flow/pressurework总量 2.082715087787078 W。实际Vdot总量 7.66808021861669e-12 m³/s，外压功 -7.66808021861669e-07 W；Vp导数另存，未重复加压功。原全局S归约保持，逐格归约差 0.0 W/K；产熵 0.0006462634381677042、交换熵 0.0011796979652095372 W/K，原identity signed差 -4.336808689942018e-19 W/K。

Udot逐项完整总量：{"caloric_temperature": 1.3117444417144197, "condensed_composition_including_binding_partials": 0.7683298728590873, "gas_composition": 0.002639399407811473, "pore_surface": 1.9529443870961104e-06, "elastic": -5.791386272985662e-07, "internal_phase": 8.347174595727095e-39}.

真实metakaolin库存 0.0031031435917963737 mol；q范围 [-73.78849547165363, -73.78843722943397]、qdot范围 [4.053401741306101e-08, 4.1384407963495136e-08] s⁻¹，q方向投影Udot总量 8.343666017651459e-39 W。这已覆盖非零载体和非零q导数，但原生phase功率只有 8.347174595727095e-39 W，不能判为充分激活或烧结耦合完成。原始微小负portlandite及反应率保持，不裁剪。

F逐格采用Udot−T*Sdot−S*Tdot；未借旧独立F缓存、平均温度或第二EOS。全部14×12梯度/速度/乘积及rawy/dy/分项/signed差保存在state-dynamics.json。公共RHS/value/helper计数实际记录，底层未仪表化调用不称实测。导出使用保存配置/机械reference context；当前根文件仅登记新授权，不替换保存状态。

该一次状态诊断criterion_not_applicable，不沿用P45/P50或累计账本阈值。没有新全程/分段质量元素能量验收，没有时间/网格加密。实际温度约671K只限定此端点，未验证内部积分点/连续source域。参数0measured，目标材料与产品性能待实测。

名义余水0.1358920787402553%>0.1%、CaO零预算null/false、旧守恒/加密/资源失败和wholefalse保持；不会用本端点差小替代。新科学余量0。后续登记静态原生续算接口：另加项目模块，保持现50source载入文本及原生origin；未来独立窗口才继续原reactions一段，不重算前3段，也不承诺phase激活。后续常规有界研发沿用人类持续授权，无重复许可问题。

行政路径修正、一次只读KeyError和坐标print误标签均在JSON留证，不是模型重试；raw输出不变。本轮Git仅7明确root/docs路径，raw场不上Git。Git/Drive增量元数据/实际恢复/历史20GB与GitHub容量分别判断，restore0；最终完整预算见runs/full-cycle/p69-heating-native-state-dynamics/final-delivery-state.json。
