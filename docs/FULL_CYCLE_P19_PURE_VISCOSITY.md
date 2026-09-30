# P19 当前纯气体黏度来源核查

24个固定物种—温度状态中复用6个已有独立点、新增18点，零积分/拟合/求根。当前旧统一幂律相对纯气零密度关联式的采样最大绝对差：N2 2.675368%、O2 5.244310%、CO2 15.461950%、H2O 42.238290%。这些是离散来源比较，不能称连续温域误差界、实验精度或孔尺度输运误差。没有新增经验合格阈值。

N2/O2复用Lemmon2004 Eq2及已有源算术，CO2复用2017 Eq4及1.0055来源系数，水使用本地iapws1.5.5的R12-08 Eq11、rho=0。μPa·s与mPa·s转换分列，均比较Pa·s。水1223.15K高于1173.15K推荐上限；高温稀气外推虽然被官方描述为物理合理，仍不得继承域内精度。IAPWS95热力学33/33没有被冒充黏度验证。

接入四种来源曲线有物理依据：当前模型本已采用低密度体相Wilke假设，各物种温度依赖可直接引用已知纯气关系，省去任意共同指数/固定倍率。需在同一面温Θ计算mu_i和随温度变化的Phi_ij；不能只替换黏度值而保留旧常量Phi。实现须支持NumPy复数以保留complex-step Jacobian，不直接使用scalar math沙盒函数。

这只改善体相纯物性依据，不解决滑移、Knudsen、真实孔径/渗透率、混合气误差或材料验证。源压力定义是rho趋零，不是混合气总压、饱和蒸气或纯水密度替代。

第一次wheel直接zip导入在0个状态前NotADirectoryError，真实工具耗时0.504427s；原包临时解压后一次修正调用exit0，科学记录0.105257s、工具0.419851s；没有第三次尝试。只读独立复核通过。证据同名JSON与runs/full-cycle/p19-pure-viscosity/。

来源：[Lemmon2004官方全文](https://trc.nist.gov/refprop/FAQ/NAO.PDF)、[CO2 2017 NIST目录](https://www.nist.gov/publications/reference-correlation-viscosity-carbon-dioxide)、[IAPWS R12-08](https://iapws.org/technical-guidance/release/viscosity.download)。定向访问，未重新开展全面文献检索。
