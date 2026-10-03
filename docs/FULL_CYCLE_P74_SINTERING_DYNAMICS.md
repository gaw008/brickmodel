# P74 真实烧结端点同事件势与机械变化率

P74 真实sintering126000s strict51load与同事件势功率完成：rc0/reaped，wall0.950319375s/CPU0.679611000s，科学全部1442851B/4194304B，120s唯一窗口关闭。1load/ctor路径声明、0initial、实际1nativeRHS/rate/chart与15完整值，JacODEsummaryfitUQ0。原生phase储能0.356702602691W/熵0.000296048798703W/K，phase_eigenstrain_sum1.67659607635e-06/s/phase_modulus_sum-231587.726914Pa/s；真实Vdot-2.80385376731e-11m3/s/外压功2.80385376731e-06W。Udot投影减原生signed4.440892098500626e-16, Sdot原归约差0.0,派生Fdot差0.0。实际phase/机械分项已观测，不等全interval或独立PASS；不同q/phase分区不直接相减认漏项。758records全保持/144literature614assumed0measured，三项源越域assumed、负库存/旧失败/criterionNA/wholefalse保持。下一原soak仅登记未启动。详见docs/FULL_CYCLE_P74_SINTERING_DYNAMICS.json/md。

|量|原生全局|完整势投影全局|投影减原生 signed|
|---|---:|---:|---:|
|Udot / W|3.698330834913184|3.6983308349131843|4.440892098500626e-16|
|Sdot / W K⁻¹|0.0030351812533557284|0.0030351812533557284|0.0|
|派生 Fdot / W|-6.190932949893052|-6.190932949893052|0.0|

输入为P73完整真实126000s/y275/saved_config/referencecontext和严格51source。实际只有1共享nativeRHS/rate/chart与1projection、15完整势值baseline1+14方向，0initial/Jac/ODE/summary/predictfitUQ。既有helper实际次数保存；load/ctor是成功路径声明，未instrument底层只能source-inferred。全部51科学源码与758完整参数record保持。

|原生机械 / 相变分项|12格原始值之和|
|---|---:|
|elastic_storage_rate_w|-1.5424277285077065e-06|
|phase_storage_rate_w|0.35670260269067355|
|elastic_entropy_rate_w_k|-1.3502769693761596e-11|
|phase_entropy_rate_w_k|0.00029604879870288105|
|elastic_free_energy_rate_w|1.6518717555144887e-08|
|total_modulus_rate_pa_s|-228518.54633022577|
|total_inelastic_eigenstrain_rate_per_s|-3.876191585070125e-06|
|permanent_strain_rate_per_s|-5.552787661424755e-06|
|phase_eigenstrain_rate_per_s|1.6765960763546302e-06|
|phase_modulus_rate_pa_s|-231587.72691434197|
|dry_volume_rate_m3_s|2.873440887148482e-22|

真实bulk Vdot=-2.8038537673079733e-11 m³/s，Vp_dot=-2.8037609025731993e-11 m³/s，外压功=2.803853767307973e-06 W。本点收缩Vdot负，外压功正，原方向保持；没有第二热源或重复加压功。

q范围[-0.5258437396857639, -0.35190296263572735]、qdot范围[0.0005139761381496926, 0.0005711796844431627] /s；完整q方向产品U/S/派生F={'Udot_w': 0.3565315126542064, 'Sdot_w_k': 0.00029590715595940466, 'Fdot_w': -0.00409795161958969}。q方向包含耦合弹性与本构效应；它与native内部phase-only分项不是同一分区，不能直接相减认定漏项。完整14×12梯度/速度/产品、原生机械和volume分项在raw bundle保存。

原全局S归约顺序保持；逐格减原归约signed差=0.0 W/K。原生production=1.4264706096550559e-05、exchange=0.003020916547259178 W/K。Fdot为本事件逐格Udot−T*Sdot−S*Tdot新派生，同EOS/sharedprimitives，非独立cache/meanT/第二EOS。signed零或小差不建立独立热力学或浮点归因PASS，criterion_not_applicable。

实际最低凝聚相库存=-1.3724396733326604e-20 mol，char合计=-2.062973499011078e-24 mol，portlandite合计=-1.384323705536526e-20 mol，全signed保留。严格非负仍未建立；新CaO库存不为历史零预算relative=null/passed=false改判。

|类别 / 物种|原来源温度范围 K|端点低于 / 高于格数|
|---|---|---|
|caloric/O2|[298.15, 2500.0]|0 / 0|
|caloric/N2|[298.15, 2500.0]|0 / 0|
|caloric/H2O|[298.15, 2500]|0 / 0|
|caloric/CO2|[298.15, 2200.0]|0 / 0|
|caloric/calcite|[298.15, 1200.0]|0 / 12|
|caloric/lime|[298.15, 1800.0]|0 / 0|
|caloric/portlandite|[298.15, 700.0]|0 / 12|
|viscosity/N2|[120.0, 1700.0]|0 / 0|
|viscosity/O2|[120.0, 1700.0]|0 / 0|
|viscosity/CO2|[100, 2000]|0 / 0|
|viscosity/H2O|[273.16, 1173.15]|0 / 12|

实际1217.11–1221.68K端点12格均超过portlandite caloric700K、calcite caloric1200K及H2Oviscosity1173.15K。原assumed解析/数学延拓身份保持，不clip、不扩source/material/continuous-time或direct synthetic290–350K资格；域内其他物种也未实材验证。0measured。

本点已实际观察非微弱phase储能与非零phase机械率，整体signed U/S/派生F未暴露具体漏项。没有证据支持改物理核或参数。下一有价值范围为从原P73完整sintering检查点继续原高温保持一段（配置阶段名 hold）；按原全9knots/物理/BDF容差maxstep不变，取得剩余原stage状态以推进完整周期，而不重复本点投影或追小数差。独立300s/全科学4MiB/完整64MiB、1loadctor0initial1solve1endpoint与原8reserve+2MiB，仅登记未启动。完整argv/原case/interval/边界/域/预算在next-original-soak-proposal.json。

最新完整8stage质量/元素/完整U/S、受影响dt/grid各一次、三方案/反演及材料资格仍缺。原名义余水0.1358920787402553%>.1%、历史CaO零预算、P45/P34/P40/P44/P50撤回/P51/P58/P60/P61/P63与全部资源失败保持，不借旧UQ或synthetic验证新机制。

一次行政saved-JSON检查误读projection.global发生KeyError，未import/调用模型；随后读取正确existing projection.projected字段，原错误收据保存，科学没有重试或追加。

七本轮root/docs文件进入正常Git后继；rawy/dy/full14x12/nativecell/source/config/context只在runs和一次原Drive必要增量。metadata不是实际恢复0，历史20GB/GitHub容量未解决；最终全部必要source/root/input/freezes/oldstagedblob/archive/末receipt自身见runs/full-cycle/p74-sintering-native-state-dynamics/final-delivery-state.json，末receipt不递归commit/补包。
