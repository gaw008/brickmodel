# G2 水物性来源可行性：IAPWS-95

结论：**纯水/纯水汽物性已有一套可合法缓存、离线复现的完整方程方案；尚不能直接接入现有统一理想气体能量接口。** 本次只选择 IAPWS-95 配合作者的 `iapws==1.5.5` 作数值核验，不继续扩展候选。293–500 K 内的液态 h/u/ρ、饱和水汽 h/u/ρ、饱和压力均已实际计算，官方数值核验表的 **33/33 项通过**。对接仍需解决固定气体常数、相态、生成焓基准及已发现的库 API 缺陷。没有修改项目源码或依赖。

## 1. 采用来源、版本与许可

| 来源 | 已核读定位 | 获取及许可 |
|---|---|---|
| International Association for the Properties of Water and Steam, **IAPWS R6-95(2018)**, *Revised Release on the IAPWS Formulation 1995 for the Thermodynamic Properties of Ordinary Water Substance for General and Scientific Use* | [官方发布页](https://iapws.org/technical-guidance/release/IAPWS-95)、[19 页官方 PDF](https://iapws.org/technical-guidance/release/IAPWS-95.download) | PDF 首页明确允许署名后全文/部分再出版；原始 PDF 与提取文本已缓存，保留完整署名 |
| jjgomera，`iapws 1.5.5` | [作者仓库](https://github.com/jjgomera/iapws)、[固定版本 PyPI 页](https://pypi.org/project/iapws/1.5.5/)、[作者 API 文档](https://iapws.readthedocs.io/en/latest/iapws.iapws95.html) | 2026-03-27 发布，GPLv3；固定 wheel、sdist、包元数据、原始源码与许可证已缓存；两个压缩包 SHA256 均与 PyPI 官方元数据一致 |
| NIST Chemistry WebBook SRD 69，H₂O，Chase 1998 | [同页 Gas/Liquid Phase Heat Capacity 表](https://webbook.nist.gov/cgi/cbook.cgi?Name=water&cTC=on&cTG=on)，H 系数与温度范围 | 仅保存本研究必要的数值事实和定位，不缓存/发布整页；SRD 编纂版权不能标为 public domain |

原始证据、派生核验和 SHA256 清单位于 `data/sandbox/water/`。`iapws-1.5.5-iapws95.py` 是从固定 wheel 原样取出的来源证据，不是本项目实现；源码未修改。其类说明仍写 2016 修订，采用的能量零点系数与本次核读的 2018 表 1 相同；2018 文档说明该修订主要增加说明/误差描述，不更改可测性质或性质差。这里用 2018 官方核验表明确核对，不能仅凭版本名称推断一致。

## 2. 可用公式、常数与有效域

IAPWS PDF 的**印刷页码**定位：第 3 页 §2/Eqs. (1)–(3) 为常数，第 3–4 页 Eqs. (4)–(6) 为 Helmholtz 方程，第 9–10 页 Tables 1–2 给全部理想/剩余项系数，第 11 页 Table 3 给性质与相平衡关系，第 12–14 页 Tables 4–5 给导数，第 15 页 Tables 6–8 给程序验证值。

```text
T_c = 647.096 K
rho_c = 322 kg/m3
R_95 = 0.46151805 kJ/(kg K)       # 方程拟合所固定的质量比气体常数
delta = rho/rho_c; tau = T_c/T
f/(R_95 T) = phi0(delta,tau) + phir(delta,tau)
p = rho R_95 T [1 + delta phir_delta]
u = R_95 T tau (phi0_tau + phir_tau)
h = R_95 T [1 + tau(phi0_tau + phir_tau) + delta phir_delta]
u = h - p/rho                    # 压力和能量必须先转成一致 SI 单位
```

饱和压力及两相密度由同一方程的液/汽等压、等化学势条件求解；本次使用的 wheel 没有 `IAPWS95_anc.json` 快速辅助表，因此实际走源码 `MEoS._saturation` 的完整 Helmholtz 相平衡求根。没有另外拼接 Antoine 曲线、固定比热或固定汽化潜热。潜热来自同温同压的 `h_v-h_l`，无需虚构常数。

作者 API 的 `P` 单位为 **MPa**，`h,u` 为 **kJ/kg**，`rho` 为 **kg/m3**。本次导出统一 SI，同时保留原始核验值与单位。`IAPWS95(T=T,x=0/1)` 明确指定饱和液/汽；`IAPWS95(T=T,P=P_mpa)` 根据状态确定相态，必须检查其返回相态，不能因为希望得到液态就将汽态结果命名为液体。

IAPWS 第 5 页 §5 批准稳定流体区从熔化线到 1273 K、压力不超过 1000 MPa；液汽饱和线由三相点 273.16 K 延伸到临界点 647.096 K。293–500 K 位于该温区内，但**温度本身不足以定义液态有效域**：液态仍须满足对应压力/相稳定条件。亚稳超热液、负压毛细液体、溶盐/有机质改变的水活度均不能仅凭这段温度范围批准。

以下是本次实际求解的**饱和纯水物性，属于文献方程计算值，不是实验新数据**：

| T/K | p_sat/Pa | ρ_liq/(kg/m3) | h_v−h_l/(J/kg) | 饱和汽 Z，使用 R_95 |
|---:|---:|---:|---:|---:|
| 293.00 | 2317.66954 | 998.192615 | 2453874.327 | 0.99865744 |
| 298.15 | 3169.92934 | 997.003352 | 2441676.175 | 0.99836202 |
| 300.00 | 3536.80675 | 996.513027 | 2437289.241 | 0.99824384 |
| 373.15 | 101417.99666 | 958.349052 | 2256403.722 | 0.98450611 |
| 450.00 | 932203.56363 | 890.341250 | 2025249.195 | 0.93278942 |
| 500.00 | 2639195.87176 | 831.313450 | 1827047.845 | 0.86651279 |

500 K 的饱和液态对应约 2.639 MPa，不能把该液体状态直接当作常压湿坯中的稳定自由水。表中 Z 也显示“293–500 K 一律把饱和蒸汽当理想气体”并不成立。含 N₂/O₂ 的孔内混合气不能直接用总气压调用纯水汽 EOS；理想混合物应使用水汽理想极限的摩尔焓，并单独审查水汽分压/逸度及混合物近似。

IAPWS 的不确定度见第 6–7 页 §6、第 16–19 页 Figs. 1–4，焓误差另指向 Advisory Note No. 1；这些不是统一统计置信区间。本次 1e-8 的程序核验容差只处理出版表数值舍入，不作为物理不确定度。

## 3. 与 NIST 生成焓的对齐：一套水只能使用一个能量平移

IAPWS 第 4 页 Eqs. (7)–(8) 的约定是三相点饱和液体 `u=s=0`，其 h 约为 `0.611782 J/kg`。现有气体包使用 298.15 K 的元素标准态生成焓基准。两者相差一个能量零点，不能将未平移的正数蒸汽焓与 NIST 的负生成焓直接相加。

为保持本项目已有 Chase 气相基准，选其水汽 Shomate **H 系数 -241826.4 J/mol** 作为 298.15 K 的理想气形成焓锚。这是使用参考量，不是在 298.15 K 外推其仅允许 500 K 以上的 Shomate 曲线。水汽低温理想热容/显热从 IAPWS 自己的 `phi0` 和第 12 页 Table 4 求得；它是气相性质，不是液态比热。

令质量转摩尔的 `M=0.018015268 kg/mol`（固定作者实现），则一致的派生平移为：

```text
C_E = Hf_gas_NIST(298.15) - M h_ideal_95(298.15)
h_aligned_liquid = M h_liquid_95(T,p) + C_E
u_aligned_liquid = M u_liquid_95(T,p) + C_E
h_aligned_vapor  = M h_vapor_95(T,p) + C_E
u_aligned_vapor  = M u_vapor_95(T,p) + C_E
h_aligned_ideal  = M h_ideal_95(T) + C_E
```

这里质量性质先统一 J/kg。对所有水相的 u/h 加同一个 C_E 保持相间焓差及 `h-u=p*v`，不会改变潜热或添加热源。若使用化学势/熵，还须另外选定一致的理想气标准熵和 1 bar 压力基准，为所有水相采用相同熵平移；只做能量平移不能声称化学平衡基准也已完成。NIST Chase 理想气 1 bar 标准熵行为 188.84 J/(mol K)，其出处及舍入与 CODATA 行需分清。

`reference_alignment.json` 保存本次实际数值：

- `C_E = -287728.9703011956 J/mol`。
- IAPWS 理想气原始 `h(298.15)=2547981.5399468704 J/kg`；液态 `h(298.15,1bar)=104918.89282781036 J/kg`。
- 平移后液态 `h(298.15,1bar)=-285838.82832863927 J/mol`，比同页液态 Chase H 系数 `-285830.4 J/mol` 低 **8.42832864 J/mol**。这是两个资料之间的可查差异；不能再给液态单独加 8.428 J/mol 并声称仍保持原 IAPWS 汽化焓。
- 500 K 的平移后 IAPWS 理想水汽焓为 `-234901.930019666 J/mol`，现有 NIST Shomate 为 `-234901.755208333 J/mol`，相接跳变 **-0.174811333 J/mol**；Cp 分别约 `35.22628070` 与 `35.21836175 J/(mol K)`。即使差值很小，也不能无说明地拼接或靠给低温支路调零同时破坏 298.15 K 锚。

建议下一实现为水相固定使用此 IAPWS 方程包并显式保留以上交叉核查差异；高温转入另一水汽方程包之前，必须建立有方法标记的转换/误差审计，不在此次来源准备中修改系数。

## 4. 两个必须在适配器解决的问题

**固定气体常数不能被偷偷替换。** IAPWS 第 3 页明确要求使用其拟合常数 `R_95=461.51805 J/(kg K)`；更换为较新的数值会破坏原系数定义。作者实现采用 `M=18.015268 g/mol`，对应 `R_m,95=8.314371357587 J/(mol K)`；与本项目已有 `8.31446261815324` 相比低 **10.97612322 ppm**。这是方程常数约定差异，不是可随手“修正”的录入错误。

真实液/汽性质应保留 IAPWS 原质量基准和 `u=h-p/rho`，转换到 mol 时记录一致的 M。若理想混合气仍坚持现有 R，则必须显式选择并量化水汽理想近似的 h/u/PV 转换；不能给该水相伪填现有 R 以绕过 `GasFaceExchange` 与热化学的常数一致性检查。单一 C_E 不能解决不同 R 下的 `h-u=RT` 差异。对于整个模型，该衔接目前仍为待实现门禁，未批准自动混用。

**固定版本的 `.u0` API 必须隔离。** 实际源码 `iapws-1.5.5-iapws95.py` 第 1574–1578 行计算：

```text
self.v0 = self.R*self.T/self.P/1000
self.u0 = self.h0-self.P*self.v0       # 原始代码，不是本项目修订
```

`P` 为 MPa、`h0` 为 kJ/kg，这里的压力功缺少 1000 因子；对照第 1593–1597 行实际流体 `fase.u = fase.h-self.P*1000*fase.v`，以及官方 Table 3 即可核对。本次 300 K 状态库返回 `.u0=2551292.614183009 J/kg`，官方理想恒等式给 `h0-R_95*T=2412975.6545980154 J/kg`，差 **138316.959585 J/kg**。该差值保留在 `properties_293_500.json` 的隔离字段中，不作为可用物性。

可用替代是**独立派生**的官方理想 Helmholtz 公式 `u0=R_95*T*tau*phi0_tau`，等价于 `h0-R_95*T`，应有自己的方法 ID 和验证；不能称原库 `.u0` 已复现正确。`.a0` 也依赖错误 `.u0`，不可直接用于后续自由能模型。实际液/汽 `.h/.u/.rho` 及 `.h0/.cp0` 不依赖这条错误的理想内能赋值。本任务保留原源码与异常，不修改上游包。

## 5. 离线复现与下一实现边界

本次通过临时目录解压固定 wheel，然后在现有 Python 3.12.13 / NumPy 2.5.2 / SciPy 1.18.1 环境执行，没有安装或修改依赖。`official_verification.json` 包含第 15 页 Table 6 的 12 个 Helmholtz/导数值、Table 8 的 3 个温度 × 7 个饱和物性值，以及逐项实际结果/误差，**33/33 通过**。275 K、625 K 仅作官方边界外侧程序检查，不扩展本项目当前 293–500 K 使用声明。该 wheel 没有辅助曲线文件，实际使用相平衡求根。

固定 wheel + 已有数值运行时可完全离线重算；例如以下命令不会安装包：

```sh
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
import tempfile, zipfile, sys, json, math
root = Path('data/sandbox/water')
with tempfile.TemporaryDirectory(prefix='water-source-check-') as temporary:
    with zipfile.ZipFile(root/'iapws-1.5.5-py3-none-any.whl') as archive:
        archive.extractall(temporary)
    sys.path.insert(0, temporary)
    from iapws import IAPWS95
    checks = json.loads((root/'official_verification.json').read_text())['checks']
    for check in checks:
        w = IAPWS95(T=check['temperature_k'], x=0.5) if 'density_kg_m3' not in check else IAPWS95(T=500, rho=838.025)
        properties = dict(pressure_mpa=w.P, rho_liquid_kg_m3=w.Liquid.rho,
                          rho_vapor_kg_m3=w.Gas.rho, h_liquid_kj_kg=w.Liquid.h,
                          h_vapor_kj_kg=w.Gas.h, s_liquid_kj_kg_k=w.Liquid.s,
                          s_vapor_kj_kg_k=w.Gas.s) if 'density_kg_m3' not in check else w._phi0(w.Tc/500, 838.025/w.rhoc) | w._phir(w.Tc/500, 838.025/w.rhoc)
        assert math.isclose(properties[check['property']], check['expected_printed'], rel_tol=1e-8, abs_tol=1e-11)
    print(len(checks), 'official program checks passed')
PY
```

若要在全新机器也不联网，需另备与目标平台匹配且有 hash 的 Python/NumPy/SciPy 安装介质；本次只缓存水物性包，没有把当前本机运行时冒充跨平台离线安装包。

下一实现应是带 SI 单位、明确相态和来源 ID 的水物性适配器，优先暴露 `(T,p)` 液/汽状态与 `T` 饱和两相状态；确认求根收敛、相态顺序、相平衡残差与来源域，隔离错误理想 API，保存能量平移/常数选择诊断。先执行官方核验及 `h-u=p/rho`、两相参考平移不改变潜热的测试，再进入总能量积分器。

这些物性不提供原泥水活度、毛细压力/饱和度关系、吸附与解吸、闭孔/曲折度、相变界面积或非平衡蒸发速率。纯水的 p_sat 不等于真实污泥的局部平衡蒸气压，也不提供湿坯到炉气的传质动力学。上述材料来源仍为独立 unknown；不能因为纯水物性可复现便放行原污泥整砖模型。
