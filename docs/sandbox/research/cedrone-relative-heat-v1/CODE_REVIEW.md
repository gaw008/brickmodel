# 离线相对供热 API/CLI：最终独立代码审查

**APPROVE。** candidate02 三文件已绑定作者冻结SHA；两项实际HIGH已修复，无开放阻断项。范围是保存结果的源物性、原验收门及本次热差算术，不把JSON复核称为证明历史进程真实执行的认证。

原负控实际2 failed/0.10 s已保留：初始H₂增加1e−6 kmol仍被接受；两份记录R/全部物性/总H翻倍仍被接受。新 `_admit` 明确消费初末 `_inventory` 全门；新 `_physical_point` 将R绑定已登记的精确SI N_A×k_B，再投影binary64。两项独立原探针在最终候选 **2 passed/0.05 s**，全程禁止Cantera导入。实读既有NIST登记及SHA匹配的保存提取文本，N_A/k_B两行均为精确定义量；乘积207861565453831/25000000000000给出8.31446261815324 J/(mol·K)。没有扩展来源认证框架。

其余路径核查：先恢复明确JSON/Fraction值，重读固定源包并核原系数/相密度/T/P，再复用 `_property_check`、`_diagnostics` 及 `check_cedrone_oxygen_result`，检查原池、原子量、全部原门和质量账。linalg仅须原门通过，不强求跨平台后验位级相同。19项H、两入口O₂/N₂、ν·h、目标零和及实际残差差均保留；没有seed混合物替代H_feed、额外pV/形成焓或库存裁剪。合法旧新serializer及计时差异不误作物理不一致。

CLI只读两份≤4MiB保存记录，已完成读取的路径/SHA/字节前缀先落盘；不从source-root导入代码。新目录及RESULT独占，比较返回先保存再查30 s离线边界；读取/序列化/写入/后验失败非零退出，不许诺I/O失败文件完整。此边界不声称能中断阻塞读取。正式SMOKE_PLAN另有10 s外层subprocess超时/回收，只运行一次已安装 -I λ1/4离线比较；没有新平衡或性能点。

实读作者原19项0.29 s、修复后受影响正例与两负控3项0.18 s记录；独审只另跑原2项。正式21项留给ROOT安装验收，未重跑旧全套。两个原失败、candidate01均保留；独审报告准备时一次误读candidate02清单层级的KeyError也保存在FINAL_REPORT_READ01_FAILURE.log，修正读取字段后SHA全匹配，与生产/物性无关。

资格仍为条件相对净供热；共同原料初态、外置状态相同及800K预热入口是明确条件。绝对Q、自热、炉燃料及材料误差继续未知/false。

冻结 SHA：
- `src/sludge_sandbox/cedrone_heat.py`: `4d2b9e4df035b5d6c48feb388ae60bc0ae4a028c3b21bb8511943aa47f0a52b1`
- `examples/sandbox/compare_cedrone_heat.py`: `b423ec4f36e021a4f0bcd03189e074fe2a4c07ef0a850804278c878f465c1586`
- `tests/sandbox/test_cedrone_heat.py`: `e0bcbb7367fb41a18fc72b562cd0645acf5238e55e95cdcfdf11ee6eae3e309d`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass; 2 resolved |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 可进入唯一离线CLI验收；0新EOS/Cantera导入/平衡，未改生产或复跑旧全套。
