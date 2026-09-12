# Cedrone Fig.3 十二锚点有限独审

**APPROVE：17 项核对通过，0 失败。** 实际查看两张原嵌入图，并只读 PDF p4/p8–9 的方法、残水及峰归属；不扩大检索，不拟合、积分或调用 EOS。一次调用提取函数重算到新文件 `ANCHORS_RECOMPUTED01.json`，完整 payload（包括全部实际 RGB 像素和仿射顶点）与原 `ANCHORS.json` 相同，原字节未覆盖。

- 校准数学成立：全部标签 ±2 px 约束的可行顶点逐项满足约束，x 斜率全正、y 全负；固定符号分母下，物理读数的线性分式极值可取可行顶点。像素半宽相交列取法、纵向 ±1.5 px 包围和名义顶点平均均与协议对应。名义读数在精确 Fraction 包围内。
- 原图确为绿色 TG/紫色 DTG、红色 DSC/黑色面积基线；DSC 吸热向下。12 目标中 11 可读，575°C 处实际存在缺失红线列，保持 unknown；未拿黑色基线补值。825°C 的 TG 点超出 DSC 温区，明确不是同温联合观测。CSV 12 行与 JSON 对应，初筛颜色修正原记录及重构历史 hash 保持一致。
- 原方法为同一均化原料的不同 aliquot；TG/DSC 分别 N₂ 60/50 mL/min，均10°C/min。原料报告残水2.4±0.6 wt%，不能保证每个 aliquot 的水份完全相同。保留图示质量百分比、W/g 装样质量解读和原正负号，不转成绝干基或瞬时残余质量归一化。108.83 J/g 为打印峰面积，涉及水蒸发/水合物分解，本次没有重积分或改称反应焓。
- ±2/±1.5 px 是分析员条件读图范围；压缩晕边、仪器、重复性、基线与 aliquot/气流迁移误差没有因此获界。此次确定性重提取只是复现，不是新实验或独立材料校准。

**LOW 操作边界：** 原冻结脚本 main 固定 `write_text` 到 ANCHORS.json，会覆盖已有输出。本审未调用 main，仅使用函数定义并以 exclusive 新文件保存；后续复核也应采用新输出或隔离目录，不能直接运行该 main 覆盖事实。无需为本次已保全的锚点重写原证据。

提取脚本 SHA256：`d28f1aeff7c21829028f657e73706e0790e2f2d0099790690bb0152e595644b4`；原锚点 SHA：`5c6f4cdb8ad4b1ecf48338790803200a3ded5d6f6f2c035b682ad921986f2b28`。详细核对与新副本 SHA 见 `CHECK01.json`，执行记录见 `RECOMPUTE01.log`。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 1 | frozen script output caution |

Verdict: APPROVE — 限于这12个条件读图目标，不授予曲线积分、动力学、联合材料或烧结砖模型资格。
