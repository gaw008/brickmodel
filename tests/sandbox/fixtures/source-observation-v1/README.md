# 来源观测读写的实际保存样本

`native-captures.json` 从 ac04d8b 所保存的唯一 N3 运行中提取原索引 0、16
两条完整观测。观测内部字段、原 ordinal 和原 adapter provenance 未改。
这是一个便于测试的提取文件，不能当作完整运行或新的实际物理实验。

原完整 JSON 位于
`docs/sandbox/research/source-multicell-transition-v1/raw-evidence.zip` 的
`root/native-result.json`，SHA-256 为
`2660d33ec0e832e006d5adcccd8ddcf38cc314ac5e65a17830cdf2f73cbdc51d`。
两条记录分别是原全湿探针与仅中间格干态的观测；原研究整体事件/材料
资格为 false，软件 codec 测试不改变此结论。提取没有调用 EOS 或求解器。
