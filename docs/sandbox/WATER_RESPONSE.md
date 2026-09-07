# 纯水局部温压响应导数

状态：先登记验证标准后已实现。新增接口返回已审核 `WaterState` 及同一 IAPWS 方程在该状态的局部导数，保留旧 API。局部敏感度不是整个压力括区的严格误差界，不自动证明机械闭合 U→T 的总误差。

## 事前登记的数值验证门槛

- EOS 热力学恒等式 `Cp-Cv=T v alpha²/kappa`：摩尔单位绝对残差 ≤ 1e-7 J/(mol K)。这是数值一致性门槛，不是物理不确定度。
- 独立中央差分：T 步长 0.01 K；P 步长 max(1 Pa, 1e-4 P)，只选择不跨相界/公开域边界的内点。
- dv/dT、dv/dP 相对差 ≤ 2e-5，分别另允许绝对 1e-13 m³/(mol K)、1e-17 m³/(mol Pa)；du/dP 相对差 ≤ 2e-4，另允许绝对 1e-8 J/(mol Pa)。绝对项用于接近零的导数，不隐藏相变或源域错误。
- 覆盖液水 (300 K,1e5 Pa)、(350 K,1e6 Pa)、(450 K,1e7 Pa)、(499 K,9e7 Pa)，蒸汽 (300 K,1e3 Pa)、(400 K,1e5 Pa)、(499 K,1e5 Pa)。有限差分每次重新调用已审核纯水状态接口，不复述待测导数公式。
- 错误域、非有限或错误 Helmholtz 导数、返回值不可变，以及原 78 项水测试均须实际运行。

## 已实现 API 与推导

```python
response = water.state_tp_response(300.0, 100000.0, phase='liquid')
state = response.state
```

返回 frozen `WaterResponse`，保留原 `WaterState` 原样及其 T/P/phase/reference/method 身份检查，没有改变旧状态字段或旧 API。`source_ids` 来自原状态；`method_id="derived_iapws95_local_tp_response_v1"`；`derivative_scope="local_state_sensitivity_not_interval_bound"`。

令 `delta=rho/rho_c`，`tau=T_c/T`，`D=1+2 delta ar_delta+delta² ar_deltadelta`。依据已缓存 IAPWS R6-95(2018) p11 Table3 的压力、焓和热容关系，直接从原生 Helmholtz 导数计算：

```text
alpha = (1+delta ar_delta-delta tau ar_deltatau)/(T D)
kappa = 1/(rho R95_specific T D)
v_molar = M95/rho
(dv/dT)_P = v alpha
(dv/dP)_T = -v kappa
(du/dP)_T = -T (dv/dT)_P - P (dv/dP)_T
Cp_molar-Cv_molar = T v alpha²/kappa
```

`thermal_expansion_k_inverse` 为 1/K，`isothermal_compressibility_pa_inverse` 为 1/Pa；`molar_dv_dt_m3_mol_k` 为 m³/(mol K)，`molar_dv_dp_m3_mol_pa` 为 m³/(mol Pa)，`molar_du_dp_j_mol_pa` 为 J/(mol Pa)。κ 直接用 SI 质量比气体常数计算，没有直接拿上游 1/MPa 值当 1/Pa。`cp_cv_identity_residual_j_mol_k` 使用事前登记的 1e-7 绝对门槛。

正机械稳定因子、κ、摩尔体积和负 dv/dP 的模均检查正性，所有返回导数与残差必须有限。α 不被任意强制为正，因为一般流体的热膨胀符号与机械稳定性是不同条件。没有读取已隔离的 u0/a0，也没有额外施加生成焓偏移；常数能量平移不会改变这里的导数。

新接口先完整调用已审核 `state_tp`，因此保持原来的来源门禁、293–500 K/100 MPa 上限、稳定液/汽分支、饱和点歧义、EOS 数值与 caloric 检查。域错仍为 `WaterDomainError`，错误返回身份或响应数值失败为 `WaterNumericalError`。纯水汽响应仍是纯流体状态响应，不是含载气混合物的偏摩尔响应。

## 实际执行

先登记上述门槛并建立 17 项测试，在新接口尚未实现时实际获得 **17 failed**（缺少 `state_tp_response` 的 AttributeError），然后实现。补充隔离新响应门禁的异常导数和错误返回身份测试后，运行：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_response.py tests/sandbox/test_water_properties.py -q
```

实际 **99 passed**：21 项新响应测试与原 78 项水测试。液水、蒸汽共 7 组有限差分均通过原先登记的门槛，未放宽。异常导数测试固定原先已验证的状态再破坏响应计算，避免仅通过旧 state 验收失败而没有检验新路径。独立 reviewer 后续给出绑定当前源码 hash 的审核记录。

## 对闭合储能反演的明确限制

`du/dP` 可以用于局部敏感度分析，不能直接用这个点值替代整个压力误差区间的 `sup |du/dP|`。没有提供压力区间导数界、IAPWS 数值误差证书或真实物性实验误差。温度反演若使用这些局部值给线性误差估计，必须标记为局部近似；严格区间保证或条件外给误差界由上层另行处理。

固定压力的 `du/dT=Cp-P dv/dT` 与 Cv 不同；沿刚性机械闭合路径还须加入 `(du/dP) dP/dT`。这里不改变已有储能层的压力路径定义，也不自动把局部响应升级成全闭合能量验证。
