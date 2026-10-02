# 初始参考体积的保存结果比较

scripts/reference_volume_compare.py 仅汇总已保存的广延量。输入 coarse/fine 保存摘要及根 geometry.area；fine 的真实保存面必须包含 coarse 的每个面，按原材料区间精确累加子格，绝不插值、移动边界或按当前收缩位置重分区。mol/kg/J 可求和，温度和摩尔分数不能使用此映射。

compare_saved(coarse, fine, area_m2) 返回带符号原始量、局部与累计差、参考体积密度、当前体积和独立CO2端点供给账本。零分母显示 null，不新增floor、物理阈值或验收结论。完整源数据与外部C结果在 runs/full-cycle/p45-calcium-coordinate/leaf-integration 中登记。

P44全域direct网格差3.01853436%保持未资格。其最外层区间差为负，主要正差在距表面约0.42–0.94mm；不能用P41旧均匀网格97.902%的外层解释。保存数据没有逐面molecular/Darcy分解及局部完整能量历史，不能借后处理确认物理离散缺陷。当前集成简化为精确嵌套映射，未纳入C测试、非嵌套重建或ULP几何门槛。
