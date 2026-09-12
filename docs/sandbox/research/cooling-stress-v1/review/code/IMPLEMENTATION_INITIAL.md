# 冷却算子初次实现审查：修复待复核

当前判定：**Block，待主数值问题修复后复核。** 审查源码为 `b46b96308d56537c0fdcad4f1734d68f998d813d8d12ce203191e053acffd865`，原字节保存在 `plate-before-cancellation-fix.py`。未运行正式研究轨迹或水 EOS。

[HIGH] 正热容的单格共同模式在回代时失准

File: `src/sludge_sandbox/cooling_thermoelastic_plate.py`，evaluate 的低秩回代段。

Issue: 合法输入 M=C=1、α=sqrt((1−1e−12)/600)、Tr=T=300 K、T域[299,300]、应变域[-0.1,0.1]、ReferenceSlab(0.02,0.01,1)、k=1、固定外温299 K。Ce=9.99866855977416e−13>0；单格矩阵必须严格退化为 C，正确 Tdot=−5000 K/s。实际返回 −5000.158116811015，相对错 3.162336e−5，且返回ė=−204.12414523182946，而 α·Tdot=−204.1306003236085。不应返回互不相容的同一阶段字段。

Fix: 用保持共同模式的稳定等价回代，并验证温度率与共同应变率相容；对确实无法保持所声明数值精度的域明确拒绝。可利用 D_i+c_i=C，将 m 写为逆 D 加权 q 均值除以 C，保留锚定差值以避免大共同项相消。不要求更改正式研究配置或增加研究积分。

证据：`SINGLE_CELL_CANCELLATION_RED.json`；`implementation-red.xml` 对应第一项失败。

[MEDIUM] 停用/零流外面的温度比仍参与熵计算

File: 同模块 evaluate 的边界熵产段。

Issue: α=k=0、绝热单格、Tr=T=1e−100 K、T域[5e−101,2e−100]、外温1e308 K、其余M=C=1与正常几何。状态及无流输出均可表示，却对 0*((T−Tb)/T) 求值得到 NaN 后拒绝。外边界已关闭，其未使用温度比不应影响该静止状态。

Fix: 明确零流面熵产为0，避免求值不相关温度比。此项为极端输入健壮性，当前正式制造试件不受影响。

证据：`ADIABATIC_UNUSED_BOUNDARY_RED.json`；`implementation-red.xml` 对应第二项失败。

独立短点测试合计 **2 failed / 8 passed，0.12 s**。其余通过项包括冻结 Fraction 点、三格稠密解及逐格能量/熵账本、α符号反转、负参考u/ψ、α=0/k=0/恒温和可变输入快照/冻结输出。三格实现采用 ReferenceSlab 的均匀参考网格；准备推导中的一般不等厚情形没有被冒称此接口已支持。

使用已核实的仓库 `.venv/bin/python`、`PYTHONPATH=src`；旧临时 venv 当前没有 NumPy/SciPy/pytest，因此没有沿用旧环境安装证据。ruff/mypy/pylint/black 仍不可用。作者42项测试只静态核读，未重复运行；root 保存其独立执行结果。

本报告保存初次发现，不是最终修复后结论。后续报告应保留此失败记录并绑定修复源码身份。
