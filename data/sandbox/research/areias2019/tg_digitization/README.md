# 三批采集污泥的稀疏TG观测候选

已按事前登记的三个独立坐标系和每图13个固定目标提取 **35个可辨重量点，4个unknown**。这是从UENF官方博士论文Figures38–40读取的 `Peso (%)`，不是反应转化率或仪器原始数组。全过程没有拟合动力学、补插缺点或将数据准入材料模型。

|图/名义批次|原文定位|可辨/目标|保留未知的目标|
|---|---|---|---|
|38 / collected-lot-1|PDF103，印刷100页|11/13|300、400°C，同列完整抗锯齿足迹超过原±2像素包络|
|39 / collected-lot-2|PDF103，印刷100页|11/13|300°C足迹过宽；400°C被品红线遮挡/混色|
|40 / collected-lot-3|PDF104，印刷101页|13/13|无；这不代表无实验误差|

来源链：`points.json`每项有图号、sample_id、目标温度及实际像素对应温度；上游哈希连接 `picks.json`、已提交校准、转换器、论文来源记录、`batch-links.json`及热分析方法事实。`picks.json`保留每点RGB足迹与未知理由。原PDF/原生图路径及SHA、官方URL、页码也在派生文件中。来源记录中早期阅读范围保持历史，不冒充全论文核读。

## 条件误差的含义

x取原目标温度反映射后的最近整数列，y取该列完整可辨绿色足迹的上下端中心。抗锯齿浅色未丢弃，遮挡点不借邻点补值。三图分别使用原数字主刻度；Figure40重量纵轴20–120，与另两图40–100不同。

严格沿用刻度中心±1、点横纵各±2原生像素条件包络。用精确有理数遍历点及首末刻度的全部端点角点，再加各轴中间刻度最大残差，向外舍入到0.01。输出两位小数是存储精度，不是测量精度。独立横纵区间仅描述该点的坐标读取条件，不是整个温区内的曲线包络，更不是实验置信区间；共同刻度误差相关，不能把35点误差当相互独立随机噪声。

初版转换器的60位Decimal中间近似对极高精度有理数可能向内舍入。独立审查发现后改为Fraction整数分/厘单位floor/ceil，保留反例及复审；4项独立小回归通过。最终39个横坐标/35个纵坐标区间、全部RGB足迹与4个unknown经独立核算/看图复读，另40项精确舍入探针通过。`digitize.py --check`实际复现JSON/CSV一致。审核是本任务独立代理审查，不是外部专家认证。

## 实际可复现命令

从项目根目录，使用具有Pillow的Python（本次Python3.14.2/Pillow12.1.1）及Poppler。PDF缓存必须匹配 `../source.json` 登记的SHA；下载入口为该文件中的官方URL，未验证新的再分发许可，原件不随Git提交。

```sh
pdfimages -f 103 -l 104 -png runs/sandbox/source-cache/areias2019-20260907/thesis.pdf runs/sandbox/source-cache/areias2019-20260907/tg-native
python3 data/sandbox/research/areias2019/tg_digitization/digitize.py --check
python3 -m unittest discover -s data/sandbox/research/areias2019/tg_digitization -p test_digitize.py -v
python3 data/sandbox/research/areias2019/tg_digitization/render_review.py --source-directory runs/sandbox/source-cache/areias2019-20260907 --output-dir runs/sandbox/source-cache/areias2019-20260907/tg-digitization-review
```

重新提取在独立临时目录实际执行，3原生PNG逐字节相同。正式renderer用可迁移缓存路径实际生成6张图，均与冻结审阅图逐字节相同；这仅证明当前Pillow/字体环境的复现。图像与全图衍生保留ignored缓存，位置/哈希见 `verification/root-render-check.json`；黑圈表示有效点，红圈只标unknown的待辨位置。选择记录和两轮审查、独立算术结果在 `verification/`，包含原失败发现，不覆写成始终通过。

## 仍然不能支持的结论

三批名义采样日期与同论文XRF表对应，但不证明同分样或统一质量基准；采前加灰经历未定，不能称确证未经任何处理的原泥。TG方法记录N2、10°C/min，正文约300°C“氧化”的解释与氧来源仍未解决。TG/MS是另一He等温实验，不能据此补齐这些曲线的气体摩尔产率。

初始重量归一化、TG具体制样/流量、重复误差、产物/计量、参考能量与反应热未知。三批一个升温速率不提供独立升温速率验证，单TG不能唯一分解水、炭及矿物反应。拟合前另登记批次留出和适用性判定；当前没有模型与公开实验的预测对照。`runtime_material_qualified=false`、`training_eligible=false`、`kinetics_fitted=false`保持。
