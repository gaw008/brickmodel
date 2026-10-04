# P95：CaO／OH 坐标与累计反应进度静态复核

P95 已定位相域和线性闭合缺口，尚未修复。只使用源码／AST 和保存 JSON 的基本算术；生产调用、ODE、新测试、参数修改均为 0。

当前 MRO 为 ThermoelasticFullCycle → FiniteGasFullCycle → FullCycle。Gas.condensed_state（172–184 行）在实际 mode0 分支取 c=Q*x、h=S*z、l=Q-c-h；Q 是保存钙池，x 是 field3，z 是 field9。物理域要求 0≤x≤1 且 0≤S*z≤Q*(1-x)。钙池恒等式 c+h+l=Q 本身不能保证相库存非负。

P94 的真实 14400 s 输入和两个 86400 s 新端点中，所有 12 格 x 都精确为 1，z 均非零。因此在精确二进制有理数和原 binary64 运算下均有 l=-h，每格至少一相为负。这种偏离已经存在于续算输入，并非仅在新端点出现；不能称为本轮制造的失败或把它当可忽略噪声。

实际 direct 关闭。脱碳源为 c_dot=-r_C、l_dot=r_C；脱水源为 h_dot=-r_H、l_dot=r_H。_rhs_event（808–827 行）分别更新 OH 坐标与 signed extent；reaction_fields（FullCycle 298–302 行）及 endpoint_inventory（41 行）用 cell_chemical_scale 映射反应进度，不使用初始 OH 为零的 legacy extent_scale。因此精确连续关系是 c+xi_C=c0、h+xi_H=h0、l-xi_C-xi_H=l0。实际 S 等于各格 cell_chemical_scale，z+u_H 应保持常量。保存输入与两终点均偏离该关系，且两新区间的残差非零；完整 36 格与 24 格区间原始带符号值见同名 JSON。没有设置新容差或改判 PASS。

连续物理域上，供体限定的 carbonate_rate／hydroxide_rate 在 c=0、h=0、l=0 三个面有向内或切向源；这是纸面符号推导，前提包括非负相库存与正迁移率。当前保存输入不满足这些前提；不能用连续域论证证明 BDF 离散非负性。load_native_checkpoint（106–124 行）核对源码身份并返回原始 native y，随后 producer（105–107 行）传入 BDF；身份一致与物理域准入是不同条件。

Q*x=Q 在所有实际 x=1 格中精确成立，Q-Q=0；负号不是在此处对两个近似 Q 的相减新产生。S*z 的乘法舍入另列，但不会把非零 z 变成符合 simplex 的状态。精确等价的 decoder 重排不能让未改变的 x=1、z≠0 同时满足三相非负。现有证据没有保存内部 accepted native 轨迹、BDF 历史、Newton 残差、实际 Jacobian 或 RHS；不能唯一归因到某次更新、Jacobian 或浮点路径。本轮没有调用模型函数补齐这些数据。

Fraction.from_float 表示保存 JSON 经 binary64 解释后的精确二进制有理数，不是材料真值，也不是原始十进制精确值。所有 source 引用、native 索引、完整来源身份和算术字段存于 JSON；55 源码与保存 P94 源文本一致。

P94 局部四产品时间差和端点原预算 PASS 保留。严格非负仍 FAIL；干燥余水两组 0.1358920787402553%／0.1358920759321227% 高于原 0.1%，仍 FAIL。CaO 精确零预算仍 null／false／undefined_zero_budget；历史失败、P78 新声明初态条件、0 measured、高温 assumed 和全模型未完成状态不清除。

下一唯一提案为在真实 14400 s 输入导出一次 native RHS 与一次实际 calcium 相关 Jacobian 行，核对连续线性关系在实际生产算术中的表现；不启动 ODE、不修改生产源码，不自动采用。Git、Drive 元数据和恢复另列收据；实际恢复为 0。
