# CO₂ 稀薄气体黏度：2017 原文关联式

实现 Laesecke 与 Muzny 2017 的零密度黏度 η₀(T)，作为替换简化碰撞模型的独立物性选项。它通过公式算术和原文计算值核对，不因此取得砖材或高压气体资格；已有轨迹没有更换物性。

来源为 [NIST 目录](https://www.nist.gov/publications/reference-correlation-viscosity-carbon-dioxide)及 [Europe PMC 公开作者手稿](https://europepmc.org/article/PMC/PMC5514612)，DOI 10.1063/1.4977429。已直接读取第 5.1 节式 4、表 2、表 6，并检查网页 MathML 的分式、平方根和指数层级。精确结构和数值表存入 `source-formula-and-tables.json`。出版方全文需付费，未绕过；公开作者手稿由正常页面展开读取。

取 θ=T/(1 K)，q=θ^(1/3)，原文形式为

`η₀ [mPa·s] = 1.0055 sqrt(θ) / [a₀ + a₁ θ^(1/6) + a₂ exp(a₃ q) + (a₄+a₅q)/exp(q) + a₆ sqrt(θ)]`。

7 个系数和单位换算全部在根参数 `parameters.co2_dilute_viscosity2017.json`。1.0055 是原文用于对齐实验参考值的尺度因子，不是本项目调参。采用原文 100–2000 K 范围；其 10000 K 外推检查值只作公式转录核对。原文对式 4 给出 300–700 K 约 0.2%、其他温区约 1% 的估计不确定度，本记录不自行赋予覆盖因子或硬误差界。

80 位独立实现保留原分式，生产实现合并指数与幂；温度导数由独立高精度微分对照解析导数。13 个温点最大相对数值差 4.35e−16、导数差 5.28e−16，分别低于预定 1e−13、1e−12 门槛。表 6 的 100、2000 和 10000 K 三个值均落入印刷舍入半单位。它们是原文计算值，不是三次实验。

与历史 NIST 网页 300–1000 K 表值的最大差为 0.487%，8 点均落入该表显示的 5% 筛查范围；网页压力未明确，因此不作独立实验资格。原 Lennard–Jones 黏度在 300–1200 K 相对此关联式的偏差约 −0.508% 至 +0.581%，600 K 为 +0.0603%；并非所有旧物性都有扩散系数那么大的偏差。

最终证据为 `review-v2.json`；初版 `review.json` 保留，v2 仅把报告单位转换移入根参数。运行命令：

```bash
.venv/bin/python examples/sandbox/review_co2_dilute_viscosity2017.py \
  --parameters parameters.co2_dilute_viscosity2017.json \
  --output /private/tmp/co2-viscosity2017-review.json
```

当前仅 η₀(T) 和 dη₀/dT，不包含密度残余、临界增大、混合黏度修正或孔壁效应。没有新增/运行软件测试，没有生成/比对 SHA；这里是来源公式和数值证据的复算。`material_qualified=false`，`training_eligible=false`。
