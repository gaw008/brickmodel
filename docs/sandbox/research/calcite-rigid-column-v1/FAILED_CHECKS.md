# 保留的未通过事项

## 空间比较

第一次2/4/8格比较comparison.json如实失败。4→8格最大体积平均温差0.130765K、粗单元对细网格平均温差12.63285K、平均压差5555.36Pa、总CaO差7.3194e−7mol、温差降至1K的事件差90.1190s；都超原目标。初始总库存和源U在各网格相同。大局部误差随初态中点不连续层向更早时刻移动，不可删去这些时刻后声称全场收敛。2格时间精度与旧双小室路径通过是不同结论。

后续8→16、16→32、32→64仍有空间目标未过，详见refinement-comparison.json、thirty-two-comparison.json和fine-comparison.json。32→64局部温差9.41525K、均压差377.326Pa、CaO差4.37487e−8mol均超目标；均温差和事件差通过不能覆盖其余失败。

## 结果序列化

首次two-refined-audit和eight-refined-audit在科学积分完成后，写入NumPy bool标志时JSON编码失败，原不完整JSON、stdout及stderr保留，不能把它们当作完整成功报告。将汇总标志显式转换为Python bool后，用独立serialized-audit文件重新执行，后续以有完整终结字段的文件为准。没有改计算方程或放宽预算。
