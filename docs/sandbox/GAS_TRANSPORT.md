# 气体输运研究：当前可以运行什么

这一组模型回答给定气体、温度、压力和孔结构条件下，气体怎样扩散、压差怎样消退、通气后怎样形成贯通流。它们可用于检验烧砖模型的气体输运部分，当前仍采用规定的理想孔结构，尚未与同材料的干燥、化学反应和烧结收缩连成已验证全过程。

| 可以研究的问题 | 使用的模型 | 当前证据 |
|---|---|---|
| 两种自由气体的组成怎样均匀化 | Maxwell–Stefan 的二元 Fick 极限 | 128 格连续解析解、离散时间解、物种库存、混合熵与时间精度通过 |
| CO/CO₂/O₂/N₂ 怎样相互影响扩散 | 四组分 Maxwell–Stefan，自由气体、固定总压 | 64→128 格空间对照及各档全轨迹通过；无需各组分独立服从 Fick 定律 |
| 单种气体受孔壁碰撞时压差怎样消退 | 纯 Knudsen 数学极限，Darcy 项设为零 | 128 格连续解析解、孔隙库存和密度熵通过；不把有限直管的真实渗透率说成零 |
| 四组分在孔内同时扩散并受压差驱动 | Dusty Gas，分子碰撞、壁面碰撞和 Darcy 流动 | 局部与有限面来源核对、2–256 格完整轨迹/时间与 128→256 空间对照通过，见[报告](research/dusty-gas-four-species-column-v1/REPORT.md) |
| 两端持续供排纯 N₂ 时建立怎样的压力分布和流量 | 等温开放 Darcy–Knudsen 柱 | 32 格稳态格平均压力误差 0.424 Pa；全轨迹物质/热量/组合熵及两档时间对照通过 |
| 两个有限气罐通过孔隙列交换气体，压差怎样消退 | 等温纯 N₂ 气罐—孔格共同库存模型 | 128 格完整守恒、热量、组合熵、时间与 64→128 瞬态空间对照通过；精确最终平衡压力 93939.39 Pa |

两端持续供排算例长 2 cm，总截面积 50 cm²，孔隙率 0.3、直管孔半径 1 μm、温度 600 K。初始内部 100 kPa，两端随后维持 120/80 kPa。它计算每格浓度、压力、摩尔数、各面气体流量、流动携带的焓和维持等温所需的热浴交换。空间资格针对稳态压力，整个阶跃瞬态的空间精度尚未由独立连续解确认。

## 运行一个已核对的通气配置

在已有项目 Python 环境中，从仓库根目录执行：

```bash
.venv/bin/python examples/sandbox/run_dusty_gas_open_isothermal_column.py \
  --parameters parameters.dusty_gas_open_pure_column_tightened.json \
  --mesh thirty-two --tolerance refined \
  --output /private/tmp/brick-open-nitrogen-refined.jsonl
```

输出路径使用一个尚不存在的文件。运行不需要联网；依赖须事先备齐。输入全部来自根参数与已保存物性文件。结果的第一行包含实际采用的完整设定与数值容差，后续保存初态、接受步、观察时刻和末态；仅出现 `completed` 不等于科学核对通过。

原始已审查过程和核对结果在 `data/sandbox/research/dusty-gas-open-pure-column-v1/`。大轨迹按 gzip 分片无损保存；各 `*-archive.json` 记录顺序与逐字节回读结果。完整资格看 `thirty-two-full-audit.json`，失败历史看 `two-full-audit-v3.json`，不能只挑通过结果。

## 怎样追查物理设定

物性取自有出处的气体输运关联式，来源算术核对与实际物性精度分开。原子量、碰撞参数、自由气体黏度与扩散系数均可沿根参数链追查；氧气黏度的历史来源对照仍有偏差记录。新的 [CO₂–N₂ 扩散来源](research/co2-n2-crusius2018-v1/REPORT.md)已单独核对；[NIST 汇编与其引文的冲突](research/co2-n2-diffusion-source-review-v1/REPORT.md)保留，旧轨迹所用简化物性不会被静默替换。Wilke 混合黏度和 Dusty Gas 方程的独立核对见[混合黏度](research/wilke-gas-mixture-v1/REPORT.md)与[局部孔隙输运](research/dusty-gas-source-v1/REPORT.md)。

孔隙率、半径、迂曲因子和渗透率是明确声明的理想几何输入。通量使用总截面积，库存使用孔隙体积 εV；混淆这两个基准会改变时间尺度。开放模型的[原始 Sandia 报告](research/dusty-gas-open-pure-column-v1/SOURCES.md)也独立支持这个定义，并记录了原文标签笔误。

开放系统需要同时计算砖体、进出气流与热浴，不能只看砖体熵是否增加。单温度非反应模型选择能量零点只是一种参考规范，不是把气体热容或生成焓设为零。这一规范不能直接充当湿砖—高温反应的统一能量来源。

改变输入后得到的是一个新算例，需要重新核对时间与空间误差。现有数值资格不提供实测砖孔参数、有限化学反应速率或真实砖材预测精度；这些输入仍在[材料依赖记录](research/three-hour-20260922/NEXT_PHASES.md)中单独列明。
