# 氮气来源更新复现完成；氧气历史差异继续追查

2026-09-25 UTC。[Sotiriadou/Assael/Huber2025](https://doi.org/10.1007/s10765-025-03516-6)式2、表1与表8已视觉核对，原始CC BY 4.0 PDF及作者/DOI保存在`data/sandbox/research/gas-conductivity-source-resolution-v1/source/`。新增纯N2零密度导热率及温度导数；参数和单位全部由根JSON提供，运行不依赖网络。

18个70–3000K点的值/导数与80位独立幂和及数学微分相符，最大相对误差分别5.290881e-16和1.900905e-15，低于冻结的1e-13/1e-12预算。表8在126.2K及500K的两个零密度计算点误差分别0.00003014、0.000007202mW/(m·K)，均在印刷半末位0.00005内。这是计算复现，表8不是实验数据。

| 温度 | 2004版 λ₀ W/(m·K) | 2025版 λ₀ W/(m·K) | 相对旧版变化 |
|---|---:|---:|---:|
| 300K | 0.02593609 | 0.02593106 | −0.01939% |
| 700K | 0.05029212 | 0.05125624 | +1.917% |
| 1000K | 0.06535364 | 0.06939374 | +6.182% |
| 1200K | 0.07467057 | 0.08085936 | +8.288% |

与旧NIST氮气网页八个300–1000K点相比，全在原表3%加舍入范围内，最大差2.6535%。旧网页未明示压力，因此仍非同压力实验验证；2004版此前1000K不满足旧表范围的结果保持原样。2025论文直接讨论了高温理论值与旧实验/关联式的差异，不能把不同来源拼成未经说明的单一真值。

式2的70–3000K拟合域是对Hellmann2013理论计算的拟合范围；原文给出的不确定度是300–700K约1%、70/1200K约2%，属于来源报告，本项目未独立复现其全部实验/量子化学依据。未编造这些节点间的不确定度插值。完整密度模型需Span EOS、残余项及临界增强，本次均未实现；其完整EOS温区不能和式2理论拟合温区混用。

氧气1982历史零密度式的原文已取得并核读附录，来源版本追查尚在进行。未替换已有模拟系数，混合物、孔隙和真实砖资格不变。`pressure_matched_experimental_validation=false`、`material_qualified=false`、`training_eligible=false`。

复建：`.venv/bin/python examples/sandbox/review_nitrogen2025_dilute_conductivity.py --parameters parameters.nitrogen2025_dilute_conductivity.json --output data/sandbox/research/gas-conductivity-source-resolution-v1/nitrogen2025-review.json`。本阶段没有新增/执行软件测试或SHA检查。
