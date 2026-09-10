# 私有材料表格转录审查

结论：本次固定来源、固定转录字节和已声明算术范围通过；没有发现印刷值转录或算术错误。原 PDF 许可证尚未确定，本报告不授予公开分发许可，PDF、页图和全文继续留在私有缓存。

实际查看了 `material/table4.png` 与 `table5.png` 两张完整原页。Table 4 的 12 行、84 个 yield / printed total 数字，温度 560/565/570/585/960 °C、TG1–TG4 与 3/7/10/12 K/min 的对应均一致。Table 5 核对的是 10 K/min 案例的 5 个原干料元素基数及 960 °C 的 5 个印刷产物总数，不是所有产物的逐格元素分析。

独立脚本 `audit_printed_tables.py` 只读文件，使用 Fraction 对照原 extractor 的固定字面量、JSON、CSV、各行六分量精确和、和与印刷总数之差，以及五个元素的印刷总数减原料基数，共 **320 项通过，0.01079 s**。没有执行原 `extract_tables.py`，没有 EOS、拟合、归一化或物理闭合判定。原 extractor 的 Decimal 运算对当前有限四位小数输入精确；其 `delta` 行来自原表印刷值，并非端点差重算。

当前证据必须保留的差异：

- TG1 在 960 °C 的六项和是 0.9502，印刷 total 是 0.9530，差为 -0.0028。原转录正确，没有把它修成相等。
- 另有 4 行六项和减 total 为 -0.0001。
- 本次额外旁列了 5 处印刷 delta 与两端印刷数相减的不一致（TG1 solid、CO、CO2、total；TG2 H2）。它们是原打印数据之间的差异，不是本转录新增错误；不能借差分重算覆盖打印 delta。
- Table 5 的 C/H/O/N/S 产物总数减 feed 分别为 -0.0430、+0.0025、+0.0148、-0.0123、-0.0112 kg/kg 原干料。计算只针对印刷聚合值；例如各产物打印元素值自身可能另有四位小数求和差异，此记录并未宣称核完它们。

范围：原文 §2.4 说明 liquid 是水加有机液体，并由固体与测定气体的差额推得；不是独立称量的纯水。表题还明确高温 liquid 保持过渡温度值是原研究假设。实验为氮气下污泥热解；这些数字不等同于氧化气氛烧结砖产率，不是现 source low-temperature 运行参数、材料认证或完整烧制验证。不能把 printed totals 的减法当作实验不确定度，也不能把同一推算闭合用作独立留出验证。§3.2 的热量为论文计算量，本脚本没有提取或验证能量闭合。

固定字节：

- `quantitative-record.json`: `741053f768dd8d4a213998b5cdde9ddc8b8e8f7ad396060ef6d529fc6e06d545`
- `extract_tables.py`: `633e5801444641e70206b9a389a616bd06e7387e15302de004ee6e188ee59f57`
- `table4.csv`: `6c8cd53398c36d3bc03ca658dc601ffc02f78c17b9d2061dd4a2fbb3f2308036`
- 私有来源 PDF: `3b49eae9d37fb2fab1c9097b2c5b2606e9ecbfe60e52f639f6e9ae637b78d536`

完整哈希、原行残差和旁列 delta 检查见 `MATERIAL_TABLES_ARITHMETIC.json`。这是对当前固定材料提取的批准；换来源文件后，硬编码人工转录必须重新核对，不能只重新计算 PDF hash 后沿用此结论。

## Review Summary

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 限当前打印数值提取与明示算术范围；无公开 PDF 分发或现实材料资格授权。
