# D-B3：液汽相变与可变载气开发记录

本轮在起点`34fb9ac`之上新增可运行的水相平衡单元。它可计算蒸发冷却、冷却引起的冷凝，以及液水耗尽后的气相继续换热/通气；同时更新O2、N2和总水库存。纯水与载气的虚拟单元没有砖基体，不提供真实砖坯干燥速度、内部湿度分布或预测误差。M1仍未通过材料准入。

## 实现与来源

- [物理模块](../../../../src/sludge_sandbox/equilibrium_water_cell.py)接收三个总库存和总内能。其中H2O包含液相及气相；[开放边界入口](../../../../examples/sandbox/run_equilibrium_water_boundary.py)只让气体穿过边界，用已有统一物种通量和携焓更新这些守恒量，再反解温度与相分配。
- [根参数](../../../../parameters.equilibrium_water_boundary.json)集中记录物性文件、体积、初边条件、传递系数和求根/步长设置。几何和传递系数是虚拟条件；没有宣称它们来自实际砖坯或设备。为避免借用污泥Cp成为砖物性，本例不放入固体。
- 液水使用已保存的[IAPWS-95发布原文](https://iapws.org/technical-guidance/release/IAPWS-95)，本轮重新读官方发布页及本地Eq4/5；熵公式按Eq5、Table1/3计算。复用`RecordedWaterProperties`和IAPWS1.5.5运行库，保存本地来源事实，不进行内容摘要认证。没有重新审遍剩余Helmholtz项；先前V-B2出版参考点对照仍是历史证据。
- O2/N2焓沿用项目NIST包；水汽焓使用IAPWS理想部分及已有共同NIST能量平移，避免把500K起的水汽Shomate段外推到低温。水汽熵沿用IAPWS原生基准，不冒充NIST绝对熵。

关键闭合关系为：

\[
W=N_l+N_v,\quad V_g=V-N_l M/\rho_l(T,P),\quad
P=(N_{O2}+N_{N2}+N_v)RT/V_g.
\]

\[
U=N_lu_l(T,P)+\sum_{i\in gas}N_i[h_i(T)-RT].
\]

液水存在时要求\(\mu_l(T,P)=\mu_v(T,p_v)\)，其中液体取总压、水汽取分压，\(\mu_v=h_v-Ts_v^0+RT\ln(p_v/p_0)\)。液水耗尽后采用\(N_l=0\)、\(\mu_v\leq\mu_l\)的气相状态。零水时水汽化学势趋于负无穷，记录为null而非伪造有限数。无独立潜热源；相变能量已经包含在两相内能中。

这是一种**纯液水＋理想混合气＋局部瞬时平衡近似**。保持IAPWS拟合R与混合气精确R之间的显式区别，并非把两者当同一常数。固定1bar标准压与熵定义一同构成该近似。现有初边状态和整个温度反解区间使假想初生液体处于稳定压缩液分支；不支持任意压力、无载气纯蒸汽、毛细负压或冻结。没有气体溶解、孔道吸附、曲率和成核势垒；瞬时平衡能否描述具体砖坯时间尺度尚未验证。

## 开发中发现并修复的问题

最初先求压力、再用两个近等数相减恢复液水量。在临界点产生`−1.9111247427707058e−18 mol`液水。原[计算与说明](../../../../data/sandbox/research/equilibrium-water-boundary-v1/initial-pressure-root/NOTE.md)保留。最终算法直接以液水量为未知，在物理区间`[0,W]`求解化学平衡，内部联立机械压力；没有截断负库存或添加隐藏容差判断。

原“condensation”算例输入较湿且较热气体，实际上总水增加而液水减少。现将它准确命名为`humid_inward`；新增冷边界算例才用于展示冷凝。原名称与运行结果仍保存在初版记录中。

相界点上下各偏移总水量百万分之一的计算分别得到全汽态和正液水量；名义临界点返回全汽态、液水为零。封闭单元初始330K，加0.05J后为330.41515K且液水减少；取走0.05J后为329.57933K且液水增加。加0.8J后为341.50916K、液水耗尽；随后取走0.8J，返回330K附近，液水与初态差约`6.2e−19 mol`。这些是固定库存热力学计算，不是设备热响应实测。

## 实际运行与科学自查

最终单元的计算记录在[证据目录](../../../../data/sandbox/research/equilibrium-water-boundary-v1)。初版压力法算例不计入最终算法数量。开发自查与后续冻结提交的独立V-B3分开。

| 算例 | 时间/步数 | 终温K | 液水变化mol | 解释 |
|---|---:|---:|---:|---|
| 蒸发 | 1s/40 | 327.3121113 | −1.86722e−6 | 较干气体带走水分并产生蒸发冷却 |
| 冷凝 | 1s/20 | 326.4496901 | +2.59199e−6 | 外界移热使部分水汽转回液水 |
| 湿气输入 | 1s/20 | 331.0178008 | −8.93153e−7 | 总水增加约1.96505e−6mol，但同时升温使液水仍减少 |
| 液水耗尽 | 10s/80 | 334.1718182 | −1.75289e−5 | 耗尽后继续计算气体与能量交换 |

[保存记录复算](../../../../examples/sandbox/summarize_equilibrium_water_records.py)不导入物理主机，使用Fraction分别处理库存、边界交换和浮点投影。液体EOS数值取自记录，不能将代数复算说成独立液体EOS实现。每步三个库存和总U共四个独立收支；总水与液/汽加和另列为相分配一致性，不重复当作独立物理定律。

最终9组260步的1040个扣投影收支等式全部精确为零。接受态及中点独立储能复算最大残差约`3.25e−11 J`，相分配水量和最大残差`6.78e−21 mol`，机械压力差约`3.20e−8 Pa`；液汽共存的化学势差最大约`2.91e−10 J/mol`。液水和水汽库存均非负；所有已采样全汽态满足相态不等式。

[节点熵计算](../../../../data/sandbox/research/equilibrium-water-boundary-v1/pointwise_entropy.json)对单元与理想储库的合系统计算
\(\dot S=\dot E_{out}(1/T_r-1/T_c)+\sum\dot N_{i,out}(\mu_{i,c}/T_c-\mu_{i,r}/T_r)\)。最终260个中点均为正，最小约`3.92e−6 W/K`。这不是离散时间步整体熵证明，也不证明整个参数域的输运闭合均满足第二定律。

蒸发算例10/20/40步终温差缩小比约4.102，液水差缩小比约4.110，符合此光滑算例的二阶表现。液水耗尽算例10/20/40步终温为332.27818、334.12051、334.16595K；粗步长仍明显影响结果，不能据非常大的差值比声称高阶收敛。耗尽时刻仅按采样限定为`(6,7]`、`(6,6.5]`、`(6,6.25] s`，不是精确事件时刻。追加80步后终温334.1718182K，与40步相差0.00587181K；耗尽采样区间缩小到`(6,6.125] s`。20/40/80步差缩小比约7.74，不稳定为固定阶数，不据此给出误差上界；相界时刻和完整域数值精度仍需独立验证。首次8组复算保存在`eight-run-review`子目录，最终汇总另含80步计算。

[相平衡近似比较](../../../../data/sandbox/research/equilibrium-water-boundary-v1/calorimetry.jsonl)在300/330/340K给出相对原生纯水饱和压约−0.111%、−0.418%、−0.585%的差异，包含理想水汽与液体总压处理的模型差别。这些数值不是对真实湿空气的实验误差或误差上界，不能说本例精确复现原生IAPWS液汽共存线。

## 离线复现与当前边界

在项目根目录执行，下列输出名必须尚不存在，避免覆盖已保存证据：

```sh
.venv/bin/python -I examples/sandbox/run_equilibrium_water_boundary.py --parameters parameters.equilibrium_water_boundary.json --case evaporation --resolution fine --output /tmp/brick-evaporation.jsonl
.venv/bin/python -I examples/sandbox/run_equilibrium_water_boundary.py --parameters parameters.equilibrium_water_boundary.json --case condensation --resolution medium --output /tmp/brick-condensation.jsonl
.venv/bin/python -I examples/sandbox/run_equilibrium_water_boundary.py --parameters parameters.equilibrium_water_boundary.json --case liquid_depletion --resolution refined --output /tmp/brick-depletion.jsonl
.venv/bin/python -I examples/sandbox/equilibrium_water_calorimetry.py --parameters parameters.equilibrium_water_boundary.json --output /tmp/brick-calorimetry.jsonl
.venv/bin/python -I examples/sandbox/summarize_equilibrium_water_records.py --directory data/sandbox/research/equilibrium-water-boundary-v1 --output /tmp/brick-water-balances.json
```

旧记录嵌入实际运行的完整配置，早期10/20/40步记录没有随后追加的`refined`名称，但这些三档数值和物理参数未改变。初版压力求解记录保存的是更早参数，不能与最终算法混作同一收敛序列。

本轮按`engineering:code-review`范围检查了守恒量含义、相界分支、能量基准、来源温域及失败传播，发现的问题如上保留并修正。没有新增/运行软件测试、SHA操作、安全护栏、运行时联网或依赖安装，没有新增作者联系。开发与本轮科学自查不代替独立V-B3；下一验证应冻结最终提交，特别检查相界数值敏感性和局部平衡假设的适用范围，然后再决定是否进入空间湿列开发。M1 Goal继续blocked，材料/训练资格保持false。
