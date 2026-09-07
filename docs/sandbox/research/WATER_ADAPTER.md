# 有界纯水物性适配器

`src/sludge_sandbox/water_properties.py` 提供可追溯的纯水热力学状态，当前公开域为 **293–500 K、正压力且不超过 100 MPa、稳定液体或稳定水汽**。它依据 IAPWS-95 方程计算，不提供污泥蒸发速率、水活度、吸附或毛细参数。源研究、原始下载定位和许可见 [WATER_SOURCE_FEASIBILITY.md](WATER_SOURCE_FEASIBILITY.md)；本适配器没有改动任何上游源码。

## 来源与离线门禁

来源 ID 为 `iapws-r6-95-2018`、`jjgomera-iapws-1.5.5`、`nist-h2o-chase-1998-reference`。每个返回状态保留这些 ID、方法 ID、完整参考态对象及 `material_qualification="pure_water_only"`。

`load_water_properties(source_directory)` 必须显式取得 `data/sandbox/water/` 路径。构造时核对五个固定 SHA256：官方 PDF、作者原始 wheel、从 wheel 原样保存的 `iapws95.py`、GPLv3 LICENSE 和 NIST/IAPWS 数值事实摘录 `source_facts.json`。预期哈希固定于适配器，不因可编辑清单改变而自动批准新来源。返回的 `source_asset_sha256` 是只读映射，可与运行账本共同保存。

适配器要求已安装 `iapws==1.5.5`，同时核对模块版本和包元数据版本，并将安装目录内 wheel 所列的全部 Python 源文件及 VERSION 与已核验 wheel 逐字节比较。出现额外的 `IAPWS95_anc.json` 辅助饱和表时拒绝使用，保证相平衡仍走本次核读的完整 Helmholtz 求根路径。首次加载不联网、不安装依赖、不修改包；缺证据、hash 不符和版本不符都抛 `WaterSourceError`。该门禁不是对任意运行时 monkeypatch 的沙盒隔离机制。

IAPWS [官方发布文件](https://iapws.org/technical-guidance/release/IAPWS-95.download)首页允许保留署名的全文或部分再出版。作者 [iapws 1.5.5](https://pypi.org/project/iapws/1.5.5/) 为 GPLv3；缓存保留原始源码及许可证。适配器调用这一外部依赖，没有把 GPL 来源改写成无署名的项目代码。NIST [Water 页面](https://webbook.nist.gov/cgi/cbook.cgi?Name=water&cTC=on&cTG=on)仅保存必要数值事实和出处，未将 SRD 编纂内容标作 public domain。

## API 和相态

```python
from sludge_sandbox.water_properties import load_water_properties

water = load_water_properties("data/sandbox/water")
liquid = water.state_tp(298.15, 100000.0, phase="liquid")
vapor = water.state_tp(500.0, 100000.0, phase="vapor")
pair = water.saturation_pair(450.0)
ideal = water.ideal_vapor(300.0)
```

返回值为 frozen dataclass。实际液/汽状态均有明确 phase、T/K、p/Pa、rho/(kg/m3)、Cp 和 Cv/(J/(kg K))、原生 h/u/(J/kg)、平移后 h/u 的质量与摩尔形式，以及压力/压力功残差。`native_entropy_j_kg_k` 明确保留 IAPWS 原熵基准，不冒充 NIST 标准熵。`saturation_pair(T)` 返回同温、同压的液/汽状态、共同饱和压力和化学平衡残差；`latent_enthalpy_j_mol` 由两相焓差计算。

`state_tp` 首先用同一 EOS 求该温度下的饱和压力，再检查所请求的稳定相：p 高于饱和压力时才允许液体，低于时才允许水汽。距饱和压力不超过数值压力容差的 `(T,p)` 被判为相态不唯一，必须调用 `saturation_pair`。这一数值带不表示实验相界宽度。500 K、1 bar 因而返回水汽；请求液体会报 `WaterDomainError`，不能将约 2.639 MPa 的饱和液态作为该常压状态。

求解后还检查后台 x 相态标志、实际密度所在的液/汽分支和正等温压缩稳定性，不能只根据调用者给的名称标相。后台 `status=1` 本身不足以通过验证。压力上界 100 MPa 是本项目主动缩小的初始域；它避免在 IAPWS 原 1000 MPa 域中还需另建高压冰相判定。293–500 K 内负压、亚稳液体、超出声明温度/压力域或未知 phase 均不允许，即便库能返回数值也不放行。

`ideal_vapor(T)` 仅给同一 IAPWS 理想 Helmholtz 部分的热量性质，方法为 `derived_iapws95_ideal_helmholtz`。它不是一个有限压力的纯水汽状态，没有 p/rho，也不能用于液态水热容。没有向现有气体热化学协议自动注册任何水物性方法。

## 单一能量平移和原生常数

IAPWS 印刷第 3 页 Eqs. (1)–(5)、第 4 页 Eqs. (7)–(8)、第 9 页 Table 1 和第 11 页 Table 3 定义了方程、拟合常数与能量参考态。保留作者实现的 `M=0.018015268 kg/mol` 和原生 `R95=461.51805 J/(kg K)`，对应摩尔常数 `8.314371357587 J/(mol K)`。不能代入另一 R 再声称仍在复现已核验系数。

由 NIST Chase 水汽 H 参考系数 `-241826.4 J/mol` 在 298.15 K 锚定原生理想水汽焓，运行时推导一个共同偏移：

```text
C = Hf_gas_NIST(298.15 K) - M h95_ideal(298.15 K)
  = -287728.9703011956 J/mol
h_aligned_molar = M h_native_mass + C
u_aligned_molar = M u_native_mass + C
```

所有液态、实际水汽和理想水汽 h/u 都使用同一个 C。没有液体专用调零，没有添加汽化潜热热源，因此保持同一 EOS 的相变焓差和 `h-u=p/rho`。298.15 K 只使用 NIST 的参考生成焓事实；没有把仅从 500 K 开始有效的气相 Shomate 曲线外推到低温。返回对象可查询原生值、平移值、C、M、R、来源和参考态名称。

这个选择也保留了可审计的跨来源差异：平移后 298.15 K、1 bar 液体焓比 NIST 同页液态 Chase 参考低约 8.42833 J/mol；500 K 的理想水汽焓比原 NIST Shomate 分支低约 0.174811 J/mol。详细原始值见 `data/sandbox/water/reference_alignment.json`，本接口没有偷偷补偿这些差异。

`water.reference.relative_gas_constant_difference(R_external)` 给出原生摩尔 R 与外部 R 的相对差异。对于已有的 `8.31446261815324 J/(mol K)`，差约 **−10.9761232 ppm**。`require_same_gas_constant` 遇到任何非相等值抛 `WaterCompatibilityError`。同 R 只是必要条件，不是混合物 EOS、分子量或参考态一致的充分证明。

现有理想混合气若继续采用原 R，必须在耦合层显式定义并量化水汽的能量/压力功模型转换，不能把水相 R 伪填为现有常数。实际非理想水汽不能使用混合气总压力当水汽纯物质压力。与其他化学物种的化学势/反应平衡还需统一标准熵；本模块只完成能量平移，熵仍标为 `native_iapws95_not_aligned_to_nist`。这些耦合当前未获自动批准。

## 上游理想内能缺陷的隔离

缓存作者源码第 1574–1578 行在 `.u0` 的压力功里漏掉 MPa 到 kJ 的 1000 因子，`.a0` 也依赖该值。原始异常和数值差保留在来源研究。本适配器不读取 `.u0/.a0`，不修补固定 wheel。

适配器直接通过官方理想 Helmholtz 导数计算：

```text
tau = Tc/T
u0 = R95 T tau phi0_tau
h0 = u0 + R95 T
cv0 = -R95 tau^2 phi0_tautau
cp0 = cv0 + R95
```

这是具有独立方法 ID 的派生性质。300 K 时原生理想内能为 `2412975.6545980154 J/kg`；被隔离的上游 `.u0` 为 `2551292.614183009 J/kg`，两者不能混称。测试将上游 `.u0/.a0` 变成读写即报错的属性，证明理想接口连完整流体状态构造都不需要，且不依赖这两个错误输出。实际液/汽 `.h/.u` 的压力功换算正确，仍另行通过 EOS 恒等式验证。

## 数值验收与错误分类

| 检查 | 运行时数值门槛 |
|---|---:|
| 后台结果温度 | 绝对偏差 ≤ 1e−9 K |
| 重新代入 EOS 的压力残差 | ≤ max(0.01 Pa, 2e−8 × p) |
| h−u−p/rho | 绝对值 ≤ 1e−6 J/kg |
| 后台 h 与 EOS h 一致 | 绝对差 ≤ 0.002 J/kg |
| 后台 s 与 EOS s 一致 | 绝对差 ≤ 0.002/T J/(kg K) |
| 后台 Cp/Cv 与 Helmholtz 导数一致 | 绝对差分别 ≤ 1e−5 J/(kg K) |
| 两相 h−Ts 差 | 绝对值 ≤ 0.001 J/kg |
| 机械稳定性 | `1+2 delta phir_delta+delta² phir_deltadelta > 0` |

求解过程中发出的 warning 也会拒绝；不把未收敛求根作为物性结果缓存，不剪裁、归一化或自动降级到近似曲线。`WaterDomainError` 表示所请求的输入或稳定相超出声明域；`WaterNumericalError` 表示域内请求未取得通过检查的数值解。两者不能混为“物理上不可能”。缺证据/依赖与模型兼容错误分别为 `WaterSourceError`、`WaterCompatibilityError`。

上述阈值是本项目数值验收选择，不是 IAPWS 实验不确定度，不构成原泥误差范围。物理方程的不确定度仍须依据官方 §6 和图表按实际温压、物性分别评估；材料层还需独立处理不确定度。

复审新增比热检查依据 IAPWS Table 3：Cv=−Rτ²(φ0_ττ+φr_ττ)，Cp=Cv+R(1+δφr_δ−δτφr_δτ)²/(1+2δφr_δ+δ²φr_δδ)。1e−5 J/(kg K) 是对同一方程两条计算路径舍入差的绝对容差，未放宽任何既有门槛，不是经验物性误差。SI 转换后及独立 EOS 的 h/s 必须先检查有限，再比较残差，避免 NaN 比较自动为假或热容乘1000后溢出却获接受。

## 验证与剩余边界

先建立测试，模块未存在时实际得到 `ModuleNotFoundError`，再实现适配器。定向命令：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_properties.py -q
```

首版 **73 passed**；复审新增5个先失败热容/非有限值反例并修补后，当前 **78 passed**。其中 33 项直接核对 IAPWS 印刷第 15 页 Tables 6/8 的原始出版数值；275 K、625 K 项只检验固定后台程序，不扩展适配器公开域。其余验证覆盖 SI 与显式相态、450 K 官方饱和值、同偏移保留潜热/压力功、298.15 K 生成焓锚、500 K 常压相态拒绝、液体实际压力密度、饱和点歧义、源 hash/运行时版本、不可变返回值、常数兼容拒绝、上游错误接口隔离、求根失败/warning 和破坏物性后的拒绝。官方程序表不是独立湿坯实验数据。独立复审记录见 CODE_REVIEW_WATER_ADAPTER.md，不能以测试数量代替审查结论。

纯水适配器尚未集成湿砖相变/积分器。真实原泥的水活度、毛细压力与饱和度、吸附解吸、相间界面积、传质动力学和几何孔连通性仍为独立来源缺口。本模块可以提供一个相态明确的水物性部件，不能使原污泥整砖模型自动获得材料适用性或独立验证资格。
