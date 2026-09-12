# 对称自由平板热弹性算子

这个增量计算温度和热应力的双向反馈。它的几何是大平板内部的对称半厚度截面：各层共享面内应变、面内零合力，大面法向应力为零。有限砖边缘、弯曲和真实烧结残余应变尚未纳入。

全部参数由调用者显式给出，目前只接受 `manufactured` 分类以验证方程和数值；不能用已有砖的冷态总收缩代替可逆热膨胀系数。`material_qualified` 始终为 `False`。方程与参数角色见[推导](../cooling-stress-next-v1/NEXT.md)和[事前登记](PREREGISTRATION.md)。

```python
from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
from sludge_sandbox.geometry import ReferenceSlab

plate = CoolingThermoelasticPlate(
    reference=ReferenceSlab(half_thickness_m=0.02, reference_area_m2=0.01, cells=2),
    biaxial_modulus_pa=1e9,
    linear_expansion_per_k=1e-4,
    stress_free_heat_capacity_j_m3_k=1e5,
    reference_temperature_k=300.0,
    conductivity_w_m_k=1.0,
    temperature_bounds_k=(290.0, 310.0),
    strain_bounds=(-0.01, 0.01),
    outer_temperature_k=300.0,
    outer_boundary="fixed_temperature",
    coefficient_classification="manufactured",
    mechanical_regime="symmetric_free_plane_stress",
)
stage = plate.evaluate([304.0, 301.0])  # 中面侧格、外表面侧格，单位 K
print(stage.temperature_rates_k_s)
print([p.stress_pa for p in stage.points])
print(stage.cell_mechanical_power_w)
```

`evaluate` 在同一阶段计算应变、应力、内能、熵以及联立的温度速率；这些都是半板量。共享内面热流正向为从中面向外，外热 `external_heat_in_w` 正向为流入半板。`fixed_temperature` 指外表面本身固定温度，只有末格半厚度的热阻，没有对流膜或假想外格。`adiabatic` 显式选择外表面绝热。

内能包含热弹熵的影响，不能把弹性 Helmholtz 自由能直接重复加进旧的热内能。每格满足 `V*udot=Q+Pmech`；局部机械功可以非零，半板总机械功为零。温度不是旧 `ConservedState.internal_energy_j` 的替代字段，本算子尚未接入那个总能量状态服务。

正固定应变热容是物理域条件，还不足以保证任意极端参数都能用浮点数可靠求解。实现检查返回温度速率的共同分量和逐行热方程残差；精度不足时会报 `unresolved_thermal_rate_*` 并停止，不能把这个结果当成已完成的冷却阶段。这项算术检查不表示材料不确定度或实验误差。

研究脚本 [run_validation.py](run_validation.py) 以 K 为主状态，用同一次积分累计 J 和 J/K 的辅助账。正式两条路径由 [supervise.py](supervise.py) 各施加 10 秒外部总期限，实际结果和误差以本目录报告为准。不要把这里的研究调用当成已实现的全周期 CLI 或中文界面入口。

本增量不输出厚度收缩、强度、开裂概率或产品合格判断。现实使用仍需同材料刚度、可逆热膨胀、热容、应力松弛和相变资料，以及适用的机械边界与独立实验验证。
