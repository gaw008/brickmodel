# Rosheim 污泥解吸等温关系

原论文：Amadou等，2006，DOI [10.2495/AFM06014](https://doi.org/10.2495/AFM06014)。已实际核读出版社开放PDF的方法、Eq1、Table1与Figures2–4。来源原值和限制见`source.json`，原PDF保存在忽略缓存，不随仓库再分发。

这是Rosheim生物处理后机械脱水市政污泥的**解吸平衡拟合**：30°C时k=0.112、n=0.416，50°C时k=0.0938、n=0.484，Xeq=k[aw/(1−aw)]^n，X单位为kg水/kg干固体。只支持两个原温度点。表中反向不等号和图中百分号标签都保留；0.10..0.80分数活动度范围是结合方程和图示的显式解释。

`observations.json`保留第6页16个蓝色实验符号的源路径、坐标、图示包络及打印系数复算。所有16点的打印曲线值均落入保守图示包络，最大中心读数差约0.00847694kg/kg。这是作者拟合数据的重建，不是新留出验证；包络包含整个符号和定位余量，不能等同测量误差。表中EQM保持原值，未用作误差门槛。

复算需要合法获取原PDF并生成相同SVG：

```sh
curl -L --fail -o .tools/source-cache/amadou2006/sorption.pdf https://www.witpress.com/Secure/elibrary/papers/AFM06/AFM06014FU1.pdf
pdftocairo -f 6 -l 6 -svg .tools/source-cache/amadou2006/sorption.pdf .tools/source-cache/amadou2006/sorption-page6.svg
python3 data/sandbox/research/amadou2006-desorption/digitize.py
```

先创建缓存目录。脚本核对来源和导出文件身份，不同PDF或不同导出字节需重新检查来源与图形，不能绕过检查。完整实验方案见`DIGITIZATION_PLAN.md`。提供器和已安装接口实际验证见`docs/sandbox/research/amadou2006-desorption-v1/REPORT.md`。

此关系不提供连续温度导数、吸附热、吸附分支/滞回、动态扩散率或砖体材料资格。不能直接替代Wang2021、Nylen2024或工厂污泥的本构；完整热湿能量模型仍须单独建立。
