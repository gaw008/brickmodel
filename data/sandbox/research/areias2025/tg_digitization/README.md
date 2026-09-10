# Areias2025 图3 TG 稀疏读图数据

本数据来自 Areias、Maciel、Holanda，*Assessment of the Valorization Potential of Municipal Sewage Treatment Plant (STP) Sludge to Produce Red-Firing Wall Tiles*，Minerals 15 (2025) 879，[DOI](https://doi.org/10.3390/min15080879)。原文 CC BY 4.0 许可、PDF 和图像摘要见 [source.json](../source.json)。这是原图的数字化派生数据，非作者发布的原始仪器数据。

图3（PDF第8页）两个面板各固定22个目标，50–1100°C、间隔50°C。
**35点可辨读，9点为 unknown**；未知位置没有插值，也未用正文失重数字校正。
实际温度由所选图像坐标计算，保留其与目标温度的差异。
纵坐标是图中报告的剩余质量百分数；初始归一化、实验误差和TG气氛没有独立确定。

- [tg-observations.json](tg-observations.json)：完整坐标、刻度、条件误差和所有目标。
- [tg-observations.csv](tg-observations.csv)：可读表格；unknown 的 TG 数值为空。
- [tg-read-overlay.png](tg-read-overlay.png)：原图与35个所选TG读点。
- [provenance.json](provenance.json)：来源、方法、同配方关联和资格边界。
- [DIGITIZATION_METHOD.md](DIGITIZATION_METHOD.md)：保留独审前的原方法说明。
- [独立审核](MATERIAL_DIGITIZATION_REVIEW.md)：实际看图及356项独立计算通过；这是当前审核状态。

读取区间来自点位±2像素、轴端刻度±1像素和内部刻度残差的有理角点包络；
这些是条件读图误差，不能称为实验置信区间，轴标定误差在多个点之间相关。
同图DTA单位是微伏，不能在这里积分为反应热。

面板A是MIA1，B是MIA3，可通过命名配方连接[同文图4膨胀数据](../dilatometry_digitization/points.json)。
这一连接不证明同一试样或同一气氛。两配方分别为黏土/石英/石灰石/预处理污泥
70/15/15/0和70/15/5/10质量份；污泥增加同时伴随石灰石减少，其差值不能作为孤立污泥反应。
原料经过预处理，也不能自动代表未处理原污泥或Arlabosse样品。

现阶段没有拟合动力学、分配产气计量或授予材料资格。图中MIA3标签失重和为
12.618%，正文相应项得到12.616%；这一原始差异保留，不用于移动读点。

复现脚本为 [digitize_tg.py](digitize_tg.py)，需要 Pillow 及脚本固定、已核哈希的原页缓存。
它明确使用990×1400页渲染作为坐标面；更高分辨率提取必须建立新版本，不覆盖这次读取。
