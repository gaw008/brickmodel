# 同源刚性吸附耦合独立代码审查

APPROVE。本候选无未解决的实际代码问题。批准范围是零过量体积、同一水提供者、制造几何/输运、禁止液流和干界面的直接一维耦合；不包含旧恢复协议、新 native 验收或材料资格。

基线 `2541b32`。只读检查三个生产文件、两个新测试及其直接调用路径；执行 11 项独立制造边界探针，实际 **11 passed in 0.14 s**，见 `BOUNDARIES_GREEN02.log/.xml`。没有构造水 EOS、运行 native、安装、改生产或重跑旧物理路径。作者及父任务的其他测试结果不冒充本审查独立执行。

## 候选字节

| 文件 | SHA256 |
|---|---|
| `src/sludge_sandbox/arlabosse_rigid_sorption.py` | `abcfe0d3fab764deddf21d0716a3b11dbdd15090b91cd86ac77363af169613d6` |
| `src/sludge_sandbox/arlabosse_sorption_phase.py` | `969096dde6713cb7c2ec6929d42a7319e86491178faf49e4ac0273b94a63d5fb` |
| `src/sludge_sandbox/source_wet_column.py` | `85f3c47d40ffdc7b9ac473dd248809152b9b9ffb204ee7f213662b29cd27c9db` |
| `tests/sandbox/test_arlabosse_rigid_sorption.py` | `67fb1c9578f4a97ded162d2036ab3f23593ee983dd9f45a4336577330ea74feb` |
| `tests/sandbox/test_arlabosse_sorption_column.py` | `33e991eff3162775f2e8dacc15243fc37a3a17caef7a3ecefa8dea127ee339d8` |

同一快照和检查范围保存在 `REVIEW_SNAPSHOT.json`。旧 `exact_source_column.py`、`programmed_source_wet_column.py` 相对基线未修改；`git diff --check` 无报告。

## 核对结果

- **完整内能和误差**：过量 U/S/F 从现有二进制节点、精确表示的 W 及分段积分组成 Fraction；总 U 加上基底后仅做一次投影，其舍入误差加回原基底数值界。反解实际采用完整 U 二分，而不是先舍入移位目标；原能量/温度容差、符号可辨识及端点门保留。固定库存的机械方程、闭合热容和下界不变。未知材料/插值/温压推广误差未包装成数值证书。
- **相变和共享面**：当前液压进入纯水平衡，源活度修正平衡压；源偏焓修正脱附焓。相变只在凝聚水和蒸气槽间成对迁移，内能没有第二次吸附/潜热源。气体迁移焓及传热仍来自原共享面路径，新的凝聚相液流被明确拒绝。
- **参考与域**：实际基底和 wet 的水类型、implementation、reference、源资产、摩尔质量及气体 R 受门控。W 只来自凝聚水，不包括气体水；初态、正向、反解和积分试算保留原 T/W 域及完整 P±error 条件域。90–110 kPa 是明确探索上限，不宣称实验适用域。
- **新旧模型隔离**：独立 `ArlabosseSorptionColumn` 类型承载新语义，普通 `SourceWetColumn` 拒绝新 storage，异类 storage 混用被拒绝。直接 midpoint 积分显式支持新类；旧 exact/programmed 类型门提前拒绝它，未放宽记录白名单或重用旧能量身份。
- **失败与记录**：新增状态通过原积分器先完整求值、后提交的顺序，越域/反解失败不会提交半步。原已接受前缀与失败分类继续保留。公共点字段经过源一致性和条件域复核，不因 dataclasses.replace 保留了模型身份便自动获准。

## 本轮发现及修复证据

实际发现一项公共输入边界问题：初版 `evaluate_sorption_phase` 仅核 point 类型/身份，复制点改成 120 kPa 或 370 K 后仍返回相变结果。独立 `PHASE_DOMAIN_RED.log/.xml` 保留 **2 failed、2 passed**。父任务已在 EOS 调用前补 T、P±error、平面共压、由库存导出的 W，以及源活度/μ/偏焓复核。最终对应独立测试通过。普通 column 调用原本生成正常点，未将该问题描述成已经发生的实际物理越域运行。

审查同时指出废弃纯水中间速率可能先于修正活度后的速率溢出；最终候选以零系数调用原 pure helper，仅在最终 sorption 速率中使用真实系数。独立大而有限系数探针实际通过。修复在该探针首次执行前已到位，没有声称捕获此问题的旧代码 RED。

证据文件按实际内容解释：`BOUNDARIES_RED.log` 为预置文件名，内容是 2 passed；`DISCARDED_RATE_RED.log` 内容是 1 passed。`BOUNDARIES_GREEN.log` 保留 1 failed、10 passed，是审查探针沿用了旧临时类型门的错误文字，而最终子类已经由旧接口正确拒绝；仅修正该期望文字后得到 `BOUNDARIES_GREEN02` 的 11 项通过，没有修改生产或放宽物理阈值。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 无未解决代码发现；实际运行成本和物理路径仍须按另行登记的 probe/集成计划取得证据。
