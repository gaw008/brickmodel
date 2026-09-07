# 气体热化学来源、能量约定与验证

核查日期：2026-09-07 UTC。实现：`src/sludge_sandbox/thermochemistry.py`。
参数包：`data/sandbox/thermochemistry/nist_gases_v1.json`，版本 `nist-webbook-gases-20260907-v1`。

本模块实现有来源定位的纯气体热容、含生成焓的焓、理想气体内能及给定摩尔库存后的温度反解。它没有液态水、固体、污泥伪组分、凝结/蒸发平衡或材料反应模型。加载来源 ID 不等于证据注册表已经批准材料适用性，实例明确标记 `source_links_declared_not_registry_validated`。

## 1. 实际核读的物性和来源

采用 NIST Chemistry WebBook SRD 69 的 **Gas Phase Heat Capacity (Shomate Equation)** 表，原参考为 M. W. Chase Jr., *NIST-JANAF Thermochemical Tables*, Fourth Edition, J. Phys. Chem. Ref. Data, Monograph 9, 1998。数据库 DOI：`10.18434/T4D303`。原系数顺序为 `A,B,C,D,E,F,G,H`，全部保留，没有重新拟合或跨研究挑选系数。

| 物种 | 原系数温度区间 K | 具体来源 |
|---|---|---|
| O₂ | 100–700、700–2000、2000–6000 | [Oxygen：Temperature columns、A–H rows](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Mask=1&Type=JANAFG&Table=on)；表注为 1977 年审查，2009 年新拟合 |
| N₂ | 100–500、500–2000、2000–6000 | [Nitrogen：Temperature columns、A–H rows](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7727379&Mask=1&Type=JANAFG&Table=on)；同上 |
| CO₂ | 298–1200、1200–6000 | [Carbon dioxide：Temperature columns、A–H rows](https://webbook.nist.gov/cgi/cbook.cgi?ID=C124389&Mask=1&Type=JANAFG&Table=on)；表注 1965 年审查 |
| H₂O(g) | 500–1700、1700–6000 | [Water：Temperature columns、A–H rows](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1&Type=JANAFG&Table=on)；表注 1979 年审查 |

**H₂O 的 298.15 K 参考态不代表其 Shomate 拟合允许算到 298.15 K。** 本包在低于 500 K 时拒绝调用水汽物性，因此尚不能支持湿砖干燥和环境温度含湿气氛。CO₂ 也不能从 298 K 以下任意外推。表中较低温度理想气态性质的数学定义不保证该纯物质在任意压力下都保持气相；混合气体是否适合理想气体近似，仍需后续温压/组成域检查。

生成焓采用同一套拟合的 H 行：O₂/N₂ 为 0，CO₂ 为 −393.5224 kJ/mol，H₂O 为 −241.8264 kJ/mol。另核读 [CO₂ 气相热化学表](https://webbook.nist.gov/cgi/cbook.cgi?ID=C124389&Mask=1) 和 [H₂O 气相热化学表](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1)：同一 Chase 参考的生成焓分别显示 −393.52 和 −241.83 kJ/mol，与 H 行在各自显示精度下一致。没有把页面上另列的 CODATA 生成焓值与 Chase 多项式拼接。

R 由 [NIST CODATA 2022 complete listing](https://physics.nist.gov/cuu/Constants/Table/allascii.txt) 的精确 Avogadro 常数和 Boltzmann 常数相乘，得到 `8.31446261815324 J/(mol K)`。使用十进制计算定义值，再存为最近的二进制浮点值；数值表示误差不叫物理常数不确定性。初始 `Value?r` 链接在浏览工具规范化参数后未提供有效常数页，故采用上述完整官方列表，未从记忆补值。

## 2. 能量定义与单位

令 `t=T/1000`，原 Shomate 公式为：

```text
cp(T) = A + B*t + C*t² + D*t³ + E/t²                   [J/(mol K)]
Δh298(T) = A*t + B*t²/2 + C*t³/3 + D*t⁴/4 − E/t + F − H [kJ/mol]
h(T) = formation_enthalpy_298 + 1000*Δh298(T)             [J/mol]
u(T) = h(T) − R*T                                        [J/mol]
cv(T) = cp(T) − R                                        [J/(mol K)]
U(T,N) = sum_species(N_species * u_species(T))             [J]
```

这是 ADR-SBX-001 的含生成能约定。反应或相变以后改变 N，再从固定或受边界交换影响的 U 反解温度；不能向同一 U 再添加已经包含的显式反应焓或相变潜热。本模块没有提供第二个 reaction-heat 加项。

G 为原表的熵系数，本版保留以确保原系数组完整，但没有用它实现化学平衡或 Gibbs 求解。不能因为存在 G 就宣称已经有污泥反应平衡模型。

`CaloricSpecies` 协议为将来的液/固相提供接口，但不提供占位物性。凝聚态需自己的 `u=h-pv` 等有依据关系，不能继承气体的 `u=h-RT`。

## 3. 分段接缝与温度反解

原始四舍五入系数并不保证相邻区间的 h 完全连续。本次实际计算得到下列右侧减左侧差值：

| 物种/接缝 K | Δh J/mol | Δcp J/(mol K) |
|---|---:|---:|
| O₂ / 700 | −1.714022 | +0.00067994 |
| O₂ / 2000 | +1.237167 | +0.00669425 |
| N₂ / 500 | +0.768385 | −0.00007525 |
| N₂ / 2000 | +0.105833 | −0.00534225 |
| CO₂ / 1200 | −3.167189 | −0.03463617 |
| H₂O / 1700 | −2.928677 | −0.00815305 |

这些是原多项式的数值接缝，**不是物理相变潜热**。本版不静默改 F、不覆盖 H、不平滑接缝。共享温度点由高温区间拥有，`seam_diagnostics()` 返回全部差值及处理规则。

温度反解对活跃物种取温度有效域交集，并按所有原接缝划为连续分支。加载时通过各单项在正温度区间的区间下界及必要的递归细分，确认 `cv>0`，而非只检查几个采样点；每一连续分支因此允许单调二分求根。跨缝能量缺口返回 `energy_in_property_gap`，多个有效根返回 `ambiguous_temperature`。不夹住能量、不假定整个温区单调、不从两个分支间插值出虚构值。

求根默认能量容差为 `1e-8 J`、温度容差为 `1e-9 K`，最多 100 次二分。内部求根同时要求能量残差在容差内、区间宽度不超过温度容差的一半，浮点零残差不能单独判定成功。返回前累加输入总能量和各库存能量项的浮点间距（完整 ulp，避免最小次正规数除二后变零），除以混合物 `Cv`；若对应的温度分辨率超过温度容差的四分之一，返回 `insufficient_energy_resolution`。这项检查防止已量化的能量被反解为虚假的精确温度，是浮点可表示性防护，不是所有多项式舍入误差的形式化界限。

这些容差是可配置数值策略，不是材料误差。超范围、空库存、负/非有限库存、无共同物性域、非正热容和不收敛都有独立错误。能量及热容求和统一检查有限性，并把 `math.fsum` 溢出转为模块异常。已知零库存不强行调用物性，但未知物种即使给 0 也会拒绝。

后续连续全流程若需要穿过拟合能量缺口/重叠，应新增**明确版本化且记录每项修正的**一致热容积分/参考焓模型，并独立验证其与原数据的偏差。本版的拒绝行为不代表那些温度在真实世界不可实现，也不是已经解决了全流程连续热化学。

## 4. 来源文件、许可与重取

机器来源记录位于 `data/sandbox/thermochemistry/sources.json`，每个系数段和物种都保存稳定 `source_ids`、原温区、生成焓基准以及原表定位。R 有自己的常数来源节点。

已经通过浏览工具实际核读原站文本。但当前环境使用 urllib 直接请求四个物种页、R、常数列表及版权页均返回 HTTP 403，尝试记录位于 `runs/sandbox/source-cache/nist-thermochemistry-20260907/manifest.json`。随后把浏览工具提供的源文本保存为 `*-web-extract.json`，明确类型为 `web_tool_extracted_text_not_original_html`。登记的 SHA-256 对应实际抽取缓存；`original_html_sha256=null`，不能把抽取缓存 hash 冒充原始 HTML hash。来源行号指向该次抽取文本，HTML 中的稳定定位仍是物种 ID、Shomate 标题、温度列和 A–H 行。

若需重取原文件，在能直接访问 NIST 的环境按 `sources.json` 的 URL 逐项保存响应字节并计算 SHA-256，登记新的访问日期及原始文件路径；不得覆盖本次 403/抽取记录。求解器本身不联网。

[NIST 当前版权说明](https://www.nist.gov/open/license) 明确区分 SRD 与其他 NIST 数据；WebBook 页面声明 SRD 编纂版权，不能因为机构属于美国政府便标为 public domain。本仓库只记录本研究所需的有限系数事实、转换和来源摘要，完整页面抽取留在本地 `runs/` 缓存中，不随参数包发布；没有取得或宣称整库/页面的再分发许可。页面未提供 Shomate 系数协方差或完整拟合误差，相关不确定性保持 unknown，显示的小数位不被解释为实测置信区间。

## 5. 实际验证与使用

测试先于实现，首次执行确实因 `sludge_sandbox.thermochemistry` 尚不存在失败。实现后，又用新增回归实际发现并修复了极小库存时的过早终止、未知 schema 字段被忽略、有限项求和溢出的问题。审查追加的两个次正规库存反例（O₂ `1e-320 mol` / `1500 K` 与 `5e-324 mol` / `380 K`）先执行得到 2 failed，再增加能量分辨率拒绝；O₂/N₂ 各 `8e302 mol` 在 `6000 K` 的求和溢出也有回归。最终实际命令：

```sh
cd /Users/wanggaoying/Desktop/brickmodel-github
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_thermochemistry.py -q
```

结果：Python 3.12.13 / macOS arm64，41 项通过，0.04 s，退出码 0。源文本独立解析核对了 32 行、80 个原系数，全部与参数包一致。[验证记录](../../../data/sandbox/thermochemistry/validation_report.json) 包含实际计算的全部接缝、系数逐行比较和参数包 hash。

覆盖：10 个 NIST 打印表点、各物种 `dh/dT=cp`、`du/dT=cv`、`h-u=RT`、不同组成的温度反解、低温水汽拒绝、零/负/非有限输入、接缝缺口与多解、热容区间内部变负、制造模式隔离、严格 schema，以及制造组分在固定总内能下改变生成能后的升温。

表点比较按原显示精度预先设置：cp 绝对容差 `0.0051 J/(mol K)`，显示两位小数的 Δh 绝对容差 `5.1 J/mol`。这是**源码抄录和公式实现验证**；NIST 打印表本身也是拟合评价，不是独立于该拟合的材料实验。因此本模块尚无砖坯外部实验验证，也不覆盖 Goal 要求的三个现实机制组验证。

```python
from sludge_sandbox.thermochemistry import load_thermochemistry

thermo = load_thermochemistry('data/sandbox/thermochemistry/nist_gases_v1.json')
n = {'O2': 0.2, 'N2': 0.7, 'CO2': 0.06, 'H2O': 0.04}  # mol, explicit design example
energy_j = thermo.mixture_internal_energy_j(n, 800.0)
temperature_k = thermo.temperature_from_internal_energy_j(energy_j, n)
sources = thermo.source_ids_for(n)
seams = thermo.species('CO2').seam_diagnostics()
```

该示例是气体热化学演示，不是已标定污泥烧制案例。真实材料包还需要低温水汽/液水/固相、原泥及残炭/挥发物身份和能量、相变与机械/界面能等有依据的依赖。
