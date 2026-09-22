# 一维液汽通道阶段报告

2026-09-22 UTC。开发冻结`c01da26`，后续快速势函数/缓存增量冻结`decb2cf`；前置相变单元已由[V-B3](../equilibrium-water-review-v1/REPORT.md)限定复核。本阶段按[合同](CONTRACT.md)分开开发与验证，由同一助手采用不同计算方法复核，不是第三方认证。原生M1 Goal仍blocked，未创建替代全项目Goal。

## 已实现的连续过程

10mL的一维虚拟流体通道，含O₂/N₂、水汽及局地滞留液水，附有0.02mol外置石英储热体。0–2s环境从330K升到335K、保持到20s，20–25s降到315K，再保持到40s。共同面上进行混合扩散、Darcy输运、气体携焓和导热；外表面求解膜对流与灰体辐射热平衡。液水耗尽后继续积分剩余水汽和载气，潜热通过同一内能与相平衡关系体现，没有再加一笔蒸发热。

这能够描述此条件世界内的温度分布、气液水库存、压力和对外物质/能量交换。它不是黏土孔隙模型：无毛细/吸附水、液体跨格流动、收缩、反应、致密化或冷却应力。40s是指定程序结束，液水耗尽不等于现实砖坯达到某个干基含水率。

## 来源和近似

[根参数](../../../../parameters.equilibrium_water_column.json)逐项记录来源及虚拟选择。水使用[IAPWS-95](https://iapws.org/technical-guidance/release/IAPWS-95)，O₂/N₂复用已复核NIST气体包；水汽使用IAPWS理想项及已登记共同参考态桥接。石英低温热容来自[NIST Shomate表](https://webbook.nist.gov/cgi/cbook.cgi?ID=C14808607&Mask=2)298–847K段；σ来自[NIST常数表](https://physics.nist.gov/cuu/Constants/Table/allascii.txt)，程序保存其有限位数表示。

石英只提供显热曲线。外置储热体的量、通道几何、热/气体输运系数、发射率和边界程序都是虚拟设计；没有将这些值标成实测砖参数，也没有用石英体积推造孔隙率。固体取不膨胀近似Δu=Δh°，气液局地瞬时平衡、理想载气/水汽与压缩纯液水的耦合仍有模型近似。运行不联网。

## 显式计算与复算

五组最终表面模型轨迹：1格/320步、2格/160步、2格/320步、4格/320步、4格/640步，共1760接受步。

- 27,520个逐格及全局库存/能量等式，扣除已记录二进制投影后残差均为0。最大库存投影2.70108e−20mol，最大能量投影1.74058e−15J；不能称浮点存储完全无误差。
- 最大气液分水闭合残差6.77627e−21mol，最大储能反解残差2.66454e−13J；保存的接受点和中点库存、液水及气相水没有负数。
- 独立Brent表面方程重建与运行温度最大差5.55644e−10K；运行表面功率残差最大3.57721e−11W。实际判定使用根参数的绝对加相对功率预算，不只比较绝对项。
- 4格/640步的初态、末态及首次全部液水耗尽状态，共12个格状态，用源公式和直接IAPWS调用重建。石英显热另由Cp数值积分获得，最大总储能差1.27676e−14J，最大固体储能差1.29063e−14J。EOS后端相同，未独立认证IAPWS实现。
- 对4格/640步保存的2560个面状态计算名义熵产生，最小0W/K、无负值；静止内面允许0。只覆盖保存的显式中点和该热库近似，不是离散总熵、全域稳定性或材料第二定律认证。

时间细化2格160→320步的最大格温差0.00161582K、表面差0.000369269K、总水差1.94311e−8mol；4格320→640步分别为0.00519764K、0.000810539K、1.00346e−8mol，均在预设0.02K/1e−7mol比较目标内。相界使不能直接据此宣称全程二阶。

空间1→2格的表面差2.62703K，2→4格为1.64172K；后者最大格体积平均温差0.519465K、总水差1.11121e−6mol，均未满足相应0.2K/1e−6mol目标。最大表面差出现在25s冷却瞬态，而不是最后时刻。原失败完整保留于`explicit-analysis.json`。

## 隐式计算及当前准入

隐式BDF使用同一物理构造和通量，同时积分外部物质/能量累计量。新增的EOS缓存仅保存一次固定温度求值中的精确压力键，不插值、不舍入、不持久缓存。

4格BDF已完成40s程序，共376个自适应接受步、320个观测点；实际耗时332.21s。全局累计库存残差最大2.20229e−19mol、能量残差3.50830e−14J，没有在积分后投影成0。另重建12个状态，总储能差最大1.73195e−14J。

在321个共同采样节点（含初态）与4格/640步显式轨迹直接比较，最大格温差0.00136479K、表面差0.000248643K、总水差2.64895e−9mol，满足原时间比较目标。首次把320点BDF记录线性插值到更密的相界采样时，格温差0.0315359K未达标，结果及解释保存在`bdf-crosscheck-analysis.json`和`CROSSCHECK_SAMPLING_NOTE.md`；不得将插值误差当作积分器误差，也不据共同采样点通过声称连续时间误差已完全界定。

直接EOS在细网格的重复求值成本过高，随后单独构建并复核[液水Gibbs势函数表示](GIBBS_REPRESENTATION.md)：65个来源节点、341个独立网格点比较及整个多项式域的稳定性系数界限通过；再以完整4格轨迹对照原物性。8/16格直接EOS试算在新表示通过后主动中断，部分记录保留；其未完成状态不算失败或成功。

最终已完成11组40s轨迹：5组显式、3组4格BDF（直接、精确缓存、Gibbs表示），以及Gibbs表示的8格、16格和16格收紧精度计算。6组BDF的7704个全局累计收支观测最大库存差3.65918e−19mol、能量差3.50830e−14J；所有保存库存及液水非负。

| 完整采样轨迹比较 | 最大格体积平均温差K | 最大表面温差K | 最大总水差mol | 原目标判定 |
|---|---:|---:|---:|---|
| Gibbs 4→8格 | 0.283162 | 0.560400 | 3.11594e−7 | 空间未通过 |
| Gibbs 8→16格 | 0.110860 | 0.157588 | 8.45202e−8 | 空间比较通过 |
| 16格BDF容差收紧10倍 | 2.75739e−6 | 2.54869e−6 | 4.28617e−12 | 时间比较通过 |

每行均直接比较321个共同节点，无时间插值。细格按相同控制体体积平均，另比较真正的表面温度；所有中间未通过结果仍在`final-analysis.json`。0.2K与1e−6mol是研究用空间比较目标，不是现实误差或连续时空误差上界。32/64格只是配置中可选值，本轮没有运行。

对16格基准的5136个保存状态（16×321）采用直接IAPWS、源气体公式及石英Cp积分逐一重建：最大格储能差5.57332e−14J、压力差1.01863e−10Pa；湿态化学势相等和干态水汽不高于液体的条件均满足沿用的数值预算。5120个保存面状态由独立标量通量公式重建后，名义熵产生最小5.86142e−30W/K，无负值；极小值只代表近乎无流的内面，不作为严格正熵证明。记录在`final-source-trajectory-review.json`，显式复算参数在根文件`parameters.equilibrium_water_column_review.json`。

16格基准记录温度范围321.8641–332.6039K，40s终态平均温度326.7776K，总水3.75032e−6mol，为初始8e−5mol的约4.69%，全部为水汽。16格全部液水耗尽只被定位于(3.5,3.625]s；8格为(3.375,3.5]s，不能宣称耗尽事件时刻已无网格/采样误差。

**D-B4开发及V-B4限定科学复核完成。** 准入的是上述物理近似、温压域、边界和采样比较范围内的一维通道研究。没有授予黏土砖准确性、实验干燥时间、训练、高温烧结或冷却力学资格；也没有把M1标为完成。后续依赖资料的阶段见[NEXT_PHASES](NEXT_PHASES.md)，当前证据不足以继续到真实材料全周期。

## 失败、旧尝试和可复现性

- `failed-initial-scalar-type/`保留NumPy标量与既有严格物性接口不兼容的首次失败；温度显式转换为内置float后运行，不改变物理系数。
- `initial-node-radiation/`保留把末格中心当辐射表面的旧试算；它不参加最终表面求解模型的收敛判断。
- `interrupted-initial-bdf/`保留首个BDF试算的输入/初态。该次计算在五分钟以上未返回首个区间后由操作者中断；不能称其已证明求解器失败。最终驱动逐接受步记录进度，仍采用同一BDF方法和误差参数。
- 未运行或新增软件测试、未生成或比对SHA、未新增护栏。语法读取与科学轨迹/数值复算的实际结果单列；原文件没有被悄悄覆盖。Gibbs复算首次序列化失败的原始部分文件带有行尾空格，原样保留，因此全变更空白检查会提示该证据文件；代码/参数/正文的空白检查另行排除此原始片段。

根参数、`examples/sandbox/{run_equilibrium_water_column,run_implicit_equilibrium_water_column,analyze_equilibrium_water_column,review_equilibrium_water_column}.py`以及`data/sandbox/research/equilibrium-water-column-v1/`构成离线复现包。每次输出要求新文件名，原始轨迹保留。安装依赖使用现有离线环境，不在计算时下载物性或资料。

在仓库根目录使用已有环境，例如：

```sh
.venv/bin/python -I examples/sandbox/run_implicit_equilibrium_water_column.py --parameters parameters.equilibrium_water_column_gibbs.json --mesh sixteen --tolerance base --output /tmp/water-column-sixteen.jsonl
.venv/bin/python -I examples/sandbox/analyze_equilibrium_water_column.py --directory data/sandbox/research/equilibrium-water-column-v1 --output /tmp/water-column-review.json
```

第二条只读取已保存的科学轨迹，不重跑主机。独立源复算命令为：

```sh
.venv/bin/python -I examples/sandbox/review_equilibrium_water_column.py --parameters parameters.equilibrium_water_column_review.json --trajectory data/sandbox/research/equilibrium-water-column-v1/sixteen-bdf-gibbs.jsonl --selection all --output /tmp/water-column-source-review.json
```

后续真实材料与全周期的具体准入缺项见[NEXT_PHASES](NEXT_PHASES.md)。
