# 原污泥TG/DSC联合实验锚点

Cedrone等2024，DOI[10.3390/environments11100210](https://doi.org/10.3390/environments11100210)，Figure 3。该研究使用同一份500 g均化污泥的不同热分析试样；TG/DSC各约10 mg，均为10°C/min升温，氮气流量分别60/50 mL/min。

这是公开实验的有限数字化数据，不是材料参数包。TG保留初始试样质量百分比，DSC保留原图W/g与吸热向下的负号。初始试样仍有残留或再吸附水，未换算为绝干基。12个锚点中11个可读，DSC575°C因曲线与基线重叠保留unknown；TG825°C超出DSC温域。不同温度的锚点不能视为同一时刻的成对观测。

[区间净失重约束](derived/CONSTRAINTS.json)给出5个相邻TG区间的原锚点差值、名义程序时长和平均净失重率，保留精确有理数及分析员外包围。它们不提供瞬时反应速率或气体种类。TG从25°C开始、DSC从50°C开始；两者具有相同升温率，但完整热历史不同。

`extraction/ANCHORS.json`保存实际RGB像素、校准顶点和分析员读图包围，`observations.csv`便于查看。完整方法见[PROTOCOL.md](PROTOCOL.md)，原图许可与署名见[source/ATTRIBUTION.md](source/ATTRIBUTION.md)。±2px标签定位及±1.5px曲线余量均为本次分析员设定；仪器误差、基线和试样差异仍为unknown。

安装Pillow后，可从仓库根目录重新提取至一个不存在的输出文件：

```sh
python3 data/sandbox/research/cedrone2024-joint-thermal-v1/extraction/extract_anchors.py \
  --output /tmp/cedrone-anchors-new.json
```

脚本拒绝覆盖现有文件，且核对两张原嵌图的固定SHA。公开副本只调整了输出入口，原提取算法和协议保持；PROTOCOL末尾的命令描述原稿，当前入口需使用上面的`--output`。原稿与独立重算证据见对应研究报告。约100°C的108.83 J/g吸热峰包含水和水合物脱除，整条DSC的偏置和峰面积不能直接作为本模型的反应焓，也不能重复叠加到既有干燥潜热中。
