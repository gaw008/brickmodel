# Hess 有限算术代码独审

APPROVE。只静态读 `feed-energy-design/hess_arithmetic.py`、SOURCE_HESS_DESIGN及已保存ROOT/RUN记录；未运行该脚本、物性或旧源池，没有再核读文献。本文不重复来源代理的论文核读资格。

代码从固定来源HHV/CHONS/水分分数及已接受结果的实际A、R重算名义量，输入SHA断言、请求元素池对应和独占新输出明确。此次独立研究脚本以普通Python运行，assert确实启用；它没有被作为可接受任意用户输入的生产API。Fraction输出的浮点另标approximate_display，不混充包围端点。

单位与计量正确：15 MJ/kg→15,000,000 J/kg；名义0.0005 kg样品→7500 J，打印±量相应为150 J，未冒称原弹热。原文Eq1按9mH+moisture重放，1.2525 MJ/kg扣项得到13.7475 MJ/kg；这里9是原式因子，不替代精确原子质量或完整量热校正。

凝聚原料、液态产物水、CO₂/SO₂/N₂参考产品下，耗氧D=bC+bH/4+bS−bO/2；气体摩尔差`Δng=bC+bS+bN/2−D=bN/2−bH/4+bO/2`。代码仅计算RΔng和指定298.15 K的RTΔng，标签明确这是选定参考温度，不是实际弹温，也未调用800–1200 K域以外的EOS。未把凝聚体pΔV、酸/矿物终态或已实施校正填零。

符号设计采用`C_U=ΔU_*+κq_rep`，故`H_F=H_P−H_O+κq_rep−C_U−Δ(pV)_*`；正C_U降低同目标下反推的H_F。若原报告已是该目标的−ΔH，则C_U=−Δ(pV)，两项抵消而非再加一次。该定义与代码保留的未知项一致；脚本没有输出确定H_feed，也没有把整体15 MJ直接认作0.704 kg子池的形成焓。

已核读原运行成功日志及ROOT五项保存检查记录，未为审查重跑这些检查。可归档为单位/计量算术和带符号余项的Hess关系；不能据此授予HP/UV闭合、真实热耗或材料资格。

## Review Summary

| Severity | Unresolved | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 有限算术与符号关系一致，未知物理校正保持未知。
