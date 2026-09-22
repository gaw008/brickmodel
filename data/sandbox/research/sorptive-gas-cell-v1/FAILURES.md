# 实际失败记录

来源算术首次导出在NumPy布尔值写JSON时抛出`TypeError: Object of type bool is not JSON serializable`。原输出前缀保存为`source-arithmetic-review.failed-prefix.txt`。仅把两个由NumPy比较产生的布尔值显式转换为Python bool；没有修改物理参数、来源数据、求解或误差目标。后续完整结果另写`source-arithmetic-review-v2.json`。

原虚拟连接的渗透率1e−16m²首次动态运行在约40s后压力根无括区。最后接受状态t=40.1216263111s、T=324.951708501K、P=109848.800572Pa、W=.126003603489；物性/相平衡声明压力范围90–110kPa。保留`drying-base.jsonl`接受前缀和`drying-base.stderr.txt`。后续`parameters.sorptive_gas_cell_vented.json`仅把虚拟连接渗透率改为1e−14m²，是新装置条件，非同工况修复、材料拟合或扩大压力范围。

全过程来源/熵审查首次在2点积分进度输出时遇到同类NumPy标量JSON序列化错误，尚未写入最终审查文件；原stderr保留`entropy-review-first.stderr.txt`。在独立来源重建函数的输出边界显式转成Python float，不改变方程、积分、参数或预算；之后重新执行两档完整积分。
