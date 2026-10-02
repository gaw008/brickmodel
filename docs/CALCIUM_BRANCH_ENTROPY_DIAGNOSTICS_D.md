# 钙反应支路的保存标量熵诊断

scripts/diagnose_calcium_branch_entropy.py 的 diagnose(record, config) 只读取源标量和显式根配置，无主机/RHS/积分调用。输入branch取hydroxide/carbonate/direct，Δμ是产物减反应物；σ=−rΔμ/T，单位W/K。R、参考压与算术identitylimit来自现有根参数，不用环境变量或CLI物性默认。

已知负熵先保留；库存、系数或单位缺失分别记录unavailable并标incomplete。有效供体为OH/CaO/Cc，方向与气体共供体按原三支律选择。直接数值符号检查不使用容差；其独立标量重算与原数组可能运算顺序不同，component-budget诊断不是形式舍入界或动态验收。negative_active_donor仅为物理域外见证，不能推断产生它的积分器原因。数据错误直接显露，未增加尺寸护栏或默认限额。

P44负carbonate熵属于普通Cc/CaO支路，direct保存样本熵为正。缺同位置库存/rate/Δμ历史时不能归因。D原隔离包31回归结果保留为外部证据，主工程选择性改写后不沿用这些结果作为本模块全覆盖；未纳入新增测试、硬编码4ULP、24/128样例数或16/2MiB限制。实际集成核查见P45报告。原P34/P44失败及动态严格正性未资格保持。

接口的mobility_per_s为当前温度完整有效k；OH包括factor·A·exp(−E/RT)，carbonate的Arrhenius已在k中而reverse_factor/phase_multiplier单列，direct才直接用独立L。裸A不是此输入，不能把输入错误称为主机缺陷。
