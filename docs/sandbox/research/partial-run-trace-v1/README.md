# 缺终态的来源查询

包含独立候选/审核、原始 RED/GREEN、永久测试、实际非 editable 安装核对，以及对真实取消记录的七项来源查询。实际完整结果七项查询与修复前逐项相同；取消记录封存字节未变。

这些是保存结果的只读查询，未重算 EOS。取消时 value 和 result_pointer 均为 null，并显式说明 final_snapshot_unavailable；不把初态或已接受前缀当作最终输出。原生生命周期来自相邻 paired-service-lifecycle-v1 中修复查询前的冻结实现，二者实现版本不同。
