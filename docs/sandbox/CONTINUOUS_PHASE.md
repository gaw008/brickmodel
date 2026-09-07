# 连续气体热量模型的相适配

IdealGasPhase新增显式接受ContinuousShomateGas全温区，segment_index必须None。原Shomate仍需显式单段；低温水汽桥保持原摩尔质量门禁。没有自动替换JSON参数包、补接IAPWS低温与高温模型或改变原焓锚点。

事前测试给出NIST O2在699.9/700/700.1 K的H/U/体积一致性，及制造Cp=30/40 J/(mol K)跨600 K的独立分段Cv积分。先运行取得2项缺接口失败、1项旧门禁通过；实现后新增3项与旧PhaseStorage22项共25通过（0.84 s）。实际RigidStorage零液高温反解分别跨到599.9/600/600.1/700 K，预先设定温度及能量门槛均1e-6（K/J），不调用域外液水。

来源/方法/常数ID沿用连续provider，manufactured分类继续保留并需下游测试模式。显式导入派生provider不代表数值envelope或砖材料参数已经获得准入。
