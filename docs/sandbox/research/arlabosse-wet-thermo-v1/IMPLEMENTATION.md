# 同源湿态热力学与能量反解

本阶段从da59890继续。实现、来源/代码审查和安装后的实际物性路径已完成；结果与复现证据见[验收报告](REPORT.md)。本模块仍是有来源的条件探索模型，完整Goal继续执行。

新增模型把Arlabosse2005同一表征污泥的干基Cp、湿基Cp加和近似、95°C水活度与总解吸热连接为共同的焓/自由能关系。模型误差、实验误差及标准态桥接误差仍未知。原离散接口和原始观测不变；W=0.5/0.6的原热量仍是null，新模型在这些位置的热量来自明确的线性插值。

固定液体机械压力为1bar，研究域35–95°C、W=0.15–0.8kg水/kg干物。它是声明的非反应研究域，没有被湿样实验完整验证。液体和理想水汽使用已有共享水参考；输出的平衡分压来自该模型，不能称为原生精确饱和压或实测污泥压力。

理论与单位见[设计审查](THERMODYNAMIC_DESIGN_REVIEW.md)。水的偏比化学势以J/kg水表示，转换到既有J/mol接口时使用同一水摩尔质量。干物h/s在参考温度的零点是参考选择，不能理解为零形成焓或实测绝对熵。过量热容为零属于作者Cp加和式所采用的近似。

## 使用

来源原件及固定科学依赖齐全后，从Python调用：

```python
from sludge_sandbox.arlabosse_wet_thermo import ArlabosseWetThermodynamics

model = ArlabosseWetThermodynamics(repository_root, water_directory)
state = model.evaluate(350.0, 0.3)
heat = model.isothermal_drying_heat(368.15, 0.75, 0.25, dry_mass_kg=0.1)
# target_j为该共同参考下的总焓；必须同时给出已知干质量与含水率。
inverse = model.inverse_enthalpy(target_j, dry_mass_kg=0.1, moisture=0.25)
```

CLI共用同一实现，温度和总焓目标二选一：

```sh
python -m sludge_sandbox arlabosse-wet --assets-root /absolute/repository --water-data /absolute/water --moisture 0.3 --temperature-k 350 --trace
python -m sludge_sandbox arlabosse-wet --assets-root /absolute/repository --water-data /absolute/water --moisture 0.25 --enthalpy-j TARGET_J --dry-mass-kg 0.1 --trace
```

TARGET_J必须取自这一模型声明参考下的实际能量目标；不能随意填入另一焓零点下的数值。每项返回保留来源、模型定义、读图包络、未量化误差及资格状态。读图包络不包含插值/温度延拓/标准态模型误差，不是总置信区间。焓反解的温度括号、残差和明确的端点浮点余量只表示数值策略。

实际路径以0.1kg干物从60°C、W=.75开始，按供热加到95°C，等温去水至W=.25，再按撤热冷却至50°C。每段用供热和带符号的蒸气携焓更新总焓，再反解温度。全程能量残差约1.52×10⁻⁷J，小于预登记1×10⁻⁵J；去水热120379.365079J，与原有理数热节点积分一致。总解吸热已含汽化部分，重复计潜热的负对照违反原账本门槛。温度和含水路径是受控研究条件，没有时间轴。

该模型不预测干燥时间、孔容、输运、压力反馈、化学反应或烧结。完整材料/全周期Goal仍未完成。
