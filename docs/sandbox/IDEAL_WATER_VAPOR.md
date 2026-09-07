# 固定混合气常数的理想水汽热量桥

`IdealWaterVapor(source_directory)` 内部调用已经通过来源门禁的 `load_water_properties`。调用者不能注入任意热量对象或自行选择 R；没有修改纯水适配器，也没有自动注册到现有 `Thermochemistry`。本部件提供与温度型 `CaloricSpecies` 同形的 h/u/Cp/Cv 接口，不声明含载气模型或原污泥材料已经获得验证。

## 明确的派生定义

底层已经将原 IAPWS 理想焓平移到 NIST 298.15 K 气相生成焓参考。本模块直接读取 `state.enthalpy_j_mol`，**不再次加 C_E**。

```text
h_bridge = h_95_ideal_aligned
Cp_bridge = Cp_95_ideal
u_bridge = h_bridge - R_mix T
Cv_bridge = Cp_bridge - R_mix
R_mix = 8.31446261815324 J/(mol K)
Delta_u = u_bridge - u_95_ideal_aligned = -(R_mix-R95_m) T
Delta_Cv = Cv_bridge - Cv_95_ideal = -(R_mix-R95_m)
```

R_mix 是当前 `data/sandbox/thermochemistry/nist_gases_v1.json` 登记的统一理想混合气常数，来源 ID 为 `nist-codata-2022`（`data/sandbox/thermochemistry/sources.json` 对应条目），推导为精确 Avogadro 常数与精确 Boltzmann 常数之积。`constant_source_ids` 与 `constant_derivation` 显式保留这条来源，`source_ids` 是水来源与该常数来源的合并；五个 `source_asset_sha256` 只表示实际验证的水资产，不声称它们另行验证了 CODATA 文档。其值不可作为拟合自由度。原水方程仍使用 `R95_m=8.314371357587`，不改系数。`Delta_Cv=-0.00009126056624… J/(mol K)`，293–500 K 内 |Delta_u| 约 0.02674–0.04563 J/mol。差值是公开记录的模型转换；它不是额外反应热、潜热或新的生成能调零。

分类为 `derived_from_evidence`，方法 ID：`derived_iapws95_ideal_water_fixed_r_bridge_v1`。参考对象、原始来源 ID、五个来源资产 SHA256、摩尔质量、温区和当前 R 都可读。`mixture_qualification="not_established"`。纯水饱和线、非理想 EOS、标准熵、化学势和相平衡接口均未提供。

## 使用及边界

```python
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
vapor = IdealWaterVapor('data/sandbox/water')
h = vapor.enthalpy_j_mol(300.0)
u = vapor.internal_energy_j_mol(300.0)
delta_u = vapor.internal_energy_difference_j_mol(300.0)
```

公开温区严格保持 293–500 K；未知目录、hash/运行时不符使用底层 `WaterSourceError`，域外温度为 `WaterDomainError`，底层数值失败仍为 `WaterNumericalError`。桥接对象身份或输出被破坏为 `IdealWaterVaporError`。返回结果必须有限，Cp/Cv 必须正；原生 h-u=R95_m T 与 Cp-Cv=R95_m 另有 1e-9 J/mol、1e-10 J/(mol K) 的数值残差检查。容差只处理浮点舍入。

冻结对象避免通常的字段修改，内部来源对象必须保持原参考身份。这个门禁不是恶意同进程 monkeypatch 的安全沙盒。原数据和常数来源批准不意味着任意混合气压力范围批准，不能用纯水总压调用本部件来模拟非理想混合物。高温接缝和统一化学势仍按 `MULTIPHASE_STORAGE_DESIGN.md` 单独实施。

## 实际验证记录

先创建测试并运行，缺模块时实际得到 `ModuleNotFoundError`；实现后：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_ideal_water_vapor.py -q
```

首版 **28 passed**。覆盖 293、298.15、373.15、500 K 的来源焓保持、生成焓锚、显式差值和 h/u/Cp/Cv 恒等式，四个内点的独立中央差分，来源缺失/错误对象、温区、不可变字段、拒绝自定义极端 R，以及非有限/非物理容量和错误参考输出。独立审查由主代理安排，本文不预先声称其通过。

主代理另执行 20 个纯水汽点（293、298.15、373.15、450、500 K，各取 0.01/0.1/0.5/0.9 倍饱和压）作为边界诊断：500 K、0.9 倍饱和压时以 R_mix 计算的 Z 约 0.88304，而 0.01 倍时约 0.99891。桥接 R 导致的小 Δu 不意味着真实气体偏差也小；这些纯水点不构成含载气混合物验证。该采样由主代理执行，非本模块新增实验。
