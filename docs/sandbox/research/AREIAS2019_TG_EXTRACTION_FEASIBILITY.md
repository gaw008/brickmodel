# Areias 2019 Figures 38–40：TG提取可行性核查

结论：绿色重量曲线适合后续有限点读图，当前未数字化。可取得原生嵌入栅格；本轮未发现仪器数组。仅核查本论文、现有材料目录及一次UENF元数据搜索，不能据此断言公开数据不存在。

## 实际检查

实际查看PDF103/104（印刷100/101）的2200px整页渲染，以及 pdfimages 抽出的三个原生PNG。原PDF身份沿用 data/sandbox/research/areias2019/source.json。`pdfimages -list`和`pdfdetach -list`已实际执行、退出0；后者返回0 embedded files。目录中现有composition/thermal/batch-links是已核读派生事实，不是仪器文件。文本中附录检索命中规范附件语句，未定位TG数组；并未逐页审核全篇所有内容。

| 图/样品 | PDF页/图对象 | 原生宽×高 | 标示分辨率 | TG左轴 |
|---|---|---|---|---|
|38 / lot1|103 / 619|592×400|96×96ppi|绿色 Peso (%)，40–100，每20个百分点主刻度|
|39 / lot2|103 / 620|575×393|96×96ppi|绿色 Peso (%)，40–100，每20个百分点主刻度|
|40 / lot3|104 / 622|634×436|106×106ppi|绿色 Peso (%)，20–120，每20个百分点主刻度|

三图横轴均 Temperatura (°C)，0–1200，每200°C主刻度。坐标轴范围不等于曲线在0°C处有实测值。标题和印刷99页正文分别给lot1/2/3及采样日期；名义批次链接见batch-links.json，不证明同分样、同含水基准或采前从未加灰。

绿色下降线为重量，不是累计失重，不能直接以y值充当转化率。蓝线对应右外轴 Derivada do peso (%/°C)，棕红线对应右内轴 Fluxo de calor (W/g)，Exo Up标记可见。还有品红曲线与左内刻度，但没有足够清晰的独立量名/单位说明，本轮身份保持unknown，不能冒称第二导数或另一热流。三图蓝轴范围不同，Figure40 TG轴也不同，不能复用同一纵坐标标定。

原生图较小但颜色能辨；TG线约像素级宽，部分交叉处受其他颜色遮挡。放大整页不增加原始信息。有效绘图区约数百像素，单像素对应数°C与约0.2个百分点量级，仅用于判断分辨能力，未经坐标校准，不能作为承诺读图误差。

## 可靠下一读取方法与验收

固定上述原生PNG/hash，分别核选所有带数字主刻度建立每图映射并检查中间刻度残差；只选可辨绿色线的有限点，保存原始像素/图号/坐标单位/叠图。事前声明点选、线宽及刻度误差包络，报告横纵条件区间；交叉或不可辨点明确缺失，不平滑补齐、不把同一线密集像素当独立观测。独立复读者核查选线和坐标换算后才能产出digitized observation candidate。若未来拟合，先锁定批次留出规则；三批一个升温率不能称多速率验证。

无法从这些图可靠读出仪器原始采样间隔、精确温时轨迹、基线/浮力修正、初始重量与归一化基准、样品误差/重复、各反应产物、未知曲线身份。绿色线不能提供矿物/有机物分解份额或绝对反应能。方法气氛和TG/MS区别沿用thermal/facts.json，不由图中“氧化”解释改写。材料和训练准入仍为false。

## 一次有界公开元数据检查

查询 `site:uenf.br "Isabela Oliveira Rangel Areias" "2019" dados tese`，返回官方论文、博士目录及校友/硕士目录。实际打开[UENF博士目录](https://uenf.br/posgraduacao/engenharia-de-materiais/teses-e-dissertacoes/teses/)，2019段为此题名、作者、导师及PDF链接，没有该条目附带的仪器数据链接。原件是[官方博士论文PDF](https://uenf.br/posgraduacao/engenharia-de-materiais/wp-content/uploads/sites/2/2019/10/Tese-Doutorado-ISA-OK.pdf)。没有扩展搜索其他数据库，也没有联系作者。

## 缓存证据

完整图和全文未获得新的再分发许可，仅在ignored缓存保留。以下路径相对仓库；哈希是本轮实际字节计算。未写提取程序、未拟合、未运行EOS/测试。

|资产|SHA256|
|---|---|
|runs/sandbox/source-cache/areias2019-20260907/thesis.pdf|25fdc22871243cd8b1ffde042e53a8afc6ddb32f3a80ded535108c4d722c857d|
|runs/sandbox/source-cache/areias2019-20260907/tg-image-inventory.txt|d9e0e739b4b3212305d4ab5a4177519e0afe8dda8527b463b0e3d80ad333894b|
|runs/sandbox/source-cache/areias2019-20260907/tg-embedded-files.txt|b598e8defe2b1052cb7712293ce6fd0fb9d5225e770ebbca300edc6cf51970b6|
|runs/sandbox/source-cache/areias2019-20260907/tg-feasibility-103.png|c81d5374c0e648109e11f6a386505245005c6356f5280e6f7181e8d6aa6745bb|
|runs/sandbox/source-cache/areias2019-20260907/tg-feasibility-104.png|fb4a6457314922f81c8fa81c812802accb06e634fdf85ed85f95156057bad689|
|runs/sandbox/source-cache/areias2019-20260907/tg-native-000.png|d9cbc90c7dddf156a62c1c150473946301ae9b98fa67c2abb8631b92471ab366|
|runs/sandbox/source-cache/areias2019-20260907/tg-native-001.png|4068a01f135fba45694751634077f6f45d797629ba476c7639899ffd117c4d71|
|runs/sandbox/source-cache/areias2019-20260907/tg-native-002.png|8d531a0b3ea859e3e82bc6accb3281131af2e0da81bc4f24512ce6bc94dc7a3f|

独立复核补记：主代理实际查看三张原生图，核对绿色Peso轴、Figure40独立20–120纵轴、横轴与蓝/棕红轴身份；读取pdfimages与pdfdetach实际输出，8个登记资产SHA均重新计算匹配。有限点提取可行性得到复核，未知品红线和未找到数组的有界结论保持不变。此步骤未生成观测点或模型验证结论。
