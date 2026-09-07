# 导热、边界热与物质焓交换

实现：`src/sludge_sandbox/exchanges.py`。这是单面交换模块，尚不是全砖能量求解器。所有材料导热、换热和发射率必须显式传入并由运行资格层验证来源；测试中的系数和边界为人工构造。

## 关系、来源与离散

- Fourier 导热采用相邻格中心到面的两段串联阻力：`Q=A(T_L−T_R)/(d_L/k_L+d_R/k_R)`。由各半格恒定热流的 Fourier 关系消去面温推导；无界面接触阻力是这里的明确近似。跨材料跳变不使用算术平均 k。零 k 表示显式绝热，不能由未知值默认为零。
- 表面对流热输入为 `A h(T_gas−T_surface)`；辐射热输入为 `A ε σ(T_rad⁴−T_surface⁴)`。`T_rad` 是视因子为 1 的等效黑体辐射环境温度，不能自动当作有限灰窑壁的实际温度。参与性气体、复杂视因子和半透明表面不由该简式覆盖。
- 物质焓率分别为 `Σ h_k(T_face) F_diff,k` 与 `Σ h_k(T_donor) F_adv,k`。有逆向扩散时，不能把净摩尔流一律乘一个上风焓。EOS 与热化学 R 不同会在接口拒绝。
- 内部同一面热率正向定义为左到右；组装器须对左右使用相反符号。外边界热正向定义为流入砖体，组装时需明确方向转换。没有在此额外加入反应热、潜热或压力功。

本次实际核读的公开关系说明：

1. [Cantera 3.2 Governing Equations for One-dimensional Flow](https://cantera.org/stable/reference/onedim/governing-equations.html)，Energy 与 Diffusive Fluxes：导热项和物种扩散焓项的约定。官方原始关系缓存见 `data/sandbox/transport/`；此处单面率是对声明离散的推导，不能把 Cantera 火焰模型称作砖模型验证。
2. [Team Fire Dynamics / BUW, Fire Simulation Lecture Notes §6.2 Heat Flux](https://firedynamics.github.io/LectureFireSimulation/content/modelling/06_heat_transfer/02_heat_transfer_example.html#heat-flux)，2026-09-07 读取网页的净热流、辐射与对流公式。一般入射辐射式在黑体环境 `q_inc=σT_rad⁴` 下化为本模块边界。只用于关系核对，没有导入讲义示例的材料数值。
3. [COMSOL 6.3 Surface-to-Ambient Radiation](https://doc.comsol.com/6.3/doc/com.comsol.help.heat/heat_ug_ht_features.09.088.html)，仅检索到文字说明；没有把搜索片段冒充逐页数值证据。

物种焓用 NIST 原系数及对应段温区，见 `THERMOCHEMISTRY_SOURCES.md`。返回的来源 ID 目前只代表实际声明的函数来源；运行时 registry/资产/材料域未完成，输出保留原 `provenance_status`。

## 验证范围

`test_exchanges.py` 覆盖半格串联阻力、换向、零 k、炉气与辐射温度不同、无效值，以及实际调用气体模块/热化学的分项焓接口。它们验证代数与接口，不是独立公开湿坯实验，也不能替代后续时间积分和全能量账本。
