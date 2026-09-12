# 公开中文 CLI 保存结果独审

PASS：一次纯保存比较，19 组检查通过、0 失败；没有 EOS、应用导入、原生重跑或旧测试。完整对照初态、构造点、构造前缀、最后返回点、provenance、初始化、run 和 flash policy 八个对象；字段/结构及数值类型均比较，浮点使用 binary64 十六进制比较，未用容差吞掉差异。

唯一对象差异均是执行耗时，完整路径与原值/新值：

| 路径 | 原 native（s） | 新 CLI（s） |
|---|---:|---:|
| `/initialization/elapsed_seconds` | 19.109686249983497 | 19.146411416993942 |
| `/run/elapsed_seconds` | 21.509186125011183 | 21.34831829101313 |
| `/run/initialization/elapsed_seconds` | 19.109686249983497 | 19.146411416993942 |

除此之外完整对象相同，包括每个物性原值、库存/U、实际 μ、试次、费用和物理时钟 `[0,1] s`。这使新入口结果可直接连接原128门及171项保存独审证据。脚本还独立重算全部动态账本累计观察、水/U与 Q−H−分解残差；出水为 5.854529373478879e−5 mol，末温为 330.00338747114915 / 332.8223222770653 K，与原记录相同。

执行元数据另按路径列在 COMPARISON01.json：原 `INPUTS.json/integration_seconds=40` 对应新 `/budgets/integration_s=100`；原 driver80对应新 `/budgets/driver_s=150`；初始化仍40。新 `/elapsed_seconds=43.269878624996636` 对应原 `ACCEPTANCE.json/driver_seconds=42.802157833997626`，两者记录口径明确不同，均属执行时间，不替代物理时间。

监督49.29613520798739 s、exit0、leader_reaped=true、无清理错误，165+5 s 门保持。2795输入的完整集合、前后及当前 SHA/字节数相同；原2792输入和旧物理结果保留，已审入口/PLAN/launch SHA及186包文件/179 Python模块源码安装冻结一致。实际运行终态完成且保留 unknown、材料/训练 false；这只验收限定研究入口，未授予现实材料、全周期或全场误差资格。

## Review Summary

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 完整保存物理对象与原单步结果一致。
