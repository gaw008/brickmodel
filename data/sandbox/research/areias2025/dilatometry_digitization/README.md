# Figure 4 实线有限点数字化

归属：Isabela Oliveira Rangel Areias、Felipe Sardinha Maciel、José Nilson França Holanda (2025), *Minerals* 15, 879, DOI [10.3390/min15080879](https://doi.org/10.3390/min15080879)。原PDF第1页明确 CC BY 4.0；本目录修改为图块拼接、红圈标点和坐标换算。原论文来源/哈希/方法上下文沿用上级 source.json/facts.json，未改原事实。

实际读取 PDF第9页 Fig.4 A=MIA1、B=MIA3 的**实线、左轴 dL/L0（%）**。每图13点，共26点，约100–1180°C。右轴虚线是长度变化率，未读取。未取得仪器原始数组；没有生成点间平滑数据，没有从端点图注1197.5/1198.2°C臆造长度值。

- `picks.json`：人工核选像素坐标、全部有数字主刻度及事前像素包络；像素从各图native分块竖向拼接的左上角起算。
- `panel-A/B-picks.png`：实际看图核对后的红圈点位，与CSV point_id对应。图中原实/虚线均保留供审查。
- `points.csv` / `points.json`：名义温度、长度变化百分比、无量纲长度比与独立横/纵读图区间。
- `digitize.py`：确定性坐标换算与图块/标点复现；`--check`精确重算CSV/JSON并核原PDF哈希。
- `pdf-image-inventory.txt` / `raster-layout-evidence.json`：PDF 11块约500ppi栅格/版面转换证据，不能宣称曲线原始矢量path。
- `provenance.json`：原始/派生资产hash、许可定位、提取版本和限制。

误差是**条件读图包络**：点坐标±4横像素、±14纵像素，tick中心±6像素，另纵向3像素覆盖末tile非统一缩放。后者由SVG比例0.145475/0.144253与276pixel给出不到3pixel的版面差，不是实验波动。主刻度首末点建立仿射变换；另外主刻度最大偏离作为独立校准残差（A横1.4683°C/纵0.00338百分点，B横1.3266°C/纵0.01081百分点）。对点与两个端点的像素误差取所有角点、用Fraction精确算术，再加刻度残差，区间十进制向外舍入。典型横区间约±5–6°C、纵A约±0.043/B约±0.074**百分点**，不是百分比相对误差。包络并非证明人工选线必然正确，也不是统计95%区间；未知实验误差单独null。

源实验为预处理市政污泥（65°C48h后加15wt.%熟石灰）与黏土/石英/石灰岩配方，膨胀仪25–1200°C、10°C/min、空气。MIA1无该污泥、15wt.%石灰岩；MIA3有10wt.%该污泥、5wt.%石灰岩，两者均70wt.%黏土+15wt.%石英。不要把这套曲线当污泥灰、未经处理原泥、烧制后冷态收缩或本地砖验证。

所有点仅 external_validation_candidate，material_qualified=false、training_eligible=false；无收缩模型参数准入。若未来用这些点拟合，须先另定校准/留出，不可同时声称独立验证。

复现（仓库根目录，已存在上级缓存原PDF；需要Poppler pdfimages及Pillow）：

```sh
.venv/bin/python data/sandbox/research/areias2025/dilatometry_digitization/digitize.py --check
```

去掉`--check`会重建该目录CSV/JSON/overlay与ignored缓存图块；脚本不联网，不改运行模型源码或原source/facts。
