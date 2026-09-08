# 一维多格自由形变与逐格机械交换功

`CurrentSolidStorage`接收完整法向伸长向量和共同切向伸长，在同一参考网格的当前几何上反解每格温压与总能量；它不调用单格自由速率。`FreeSolidSlab`随后用全部实际压力求共同机械闭合，并重用原`SolidFluidHeat._assemble_decoded`共享面算子。

对每格定义n_i、共同t、V0_i与V_i=V0_i*n_i*t²。当前制造骨架的恢复能和黏性Piola关系保持原定义。法向逐格平衡，切向只满足约化的合力/虚功平衡：

```
n_dot_i = n_i²/eta_i * [(p_i-pe)*t² - S_n_i]
t_dot = t² * sum(V0_i*((p_i-pe)*n_i*t-S_t_i)) / sum(V0_i*eta_i)
R_i = S_t_i + eta_i*t_dot/t² - (p_i-pe)*n_i*t
C_i = 2*V0_i*R_i*t_dot
E_dot_i = shared heat/enthalpy + body - pe*V_dot_i + C_i
```

C_i是相容约束传递的机械功，逐格一般不为零，全局抵消。它以`mechanical_constraint`独立进入实际RK分项账本和checkpoint，不能叫耗散热，也不能在总能量中再加入D或恢复能变化。共同t是假设的位移形式；异质砖侧面逐点自由牵引、三维剪切/边缘效应不在该约化模型的证明范围。

来源身份、真实固相provider、固定固体库存、完整参考面积/厚度/格次序和总能量作用域均在构造或阶段检查；任一格反解失败保留此前完整已提交状态。所有模型与传递系数仍显式制造，`material_qualified=False`。

实际验证见`research/free-slab-v1`：高精度瞬时率、单格/均匀分割/重编号一致性、非零约束零功、独立两格干态轨迹、局部缺功反例，以及真实水固定相态的两档短轨迹。后者有共享热流，但没有活动蒸发、液面迁移或气体面通量；不能升级为完整湿坯干燥或完整烧结周期。

可以从Python调用`FreeSolidSlab.state_from_temperatures`建立全能量状态，再调用`integration.integrate`；同时显式设置`stretch_absolute_tolerance`与`stretch_scale`。可重现的完整制造初始化见`tests/sandbox/test_free_solid_slab.py::host`，独立轨迹命令：

```
python -m pytest tests/sandbox/test_free_solid_slab_trajectory.py -q -s
python -m pytest tests/sandbox/test_free_solid_slab_wet.py -q -s
```

实际水测试必须安装已锁定的water依赖，并遵守测试的资源上限；这些测试命令不是生产原料仿真入口。当前新主机尚未准入WaterPhaseTransfer、固体反应或动态边界程序，下一阶段必须接入并验证；原Goal范围不变。
