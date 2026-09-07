# Areias 2025 Fig. 4 数字化独立审核

结论：**APPROVE，限已发表图的有限点数字化与条件读图区间**。未发现需要修复的高置信度代码或证据错误；本审核不是材料准入、仪器误差核证或收缩本构验证。只读源/数据并写本报告，未修改生产代码、测试或事实记录，未运行 EOS。

## 实际核验

- 完整阅读 `digitize.py`、点选合同、`picks.json`、派生数据与 provenance；实际查看原 PDF 第 9 页缓存图，以及 A/B 两张点选叠图。逐一检查每图 13 个红圈，共 26 点：位于左轴实线相对长度变化曲线，不是右轴虚线导数。原图题注明 A=MIA1、B=MIA3。数字化约覆盖 100–1180°C，没有把峰值导数标记误当长度点。
- 核对原 PDF 的题名/许可和方法文本：CC BY 4.0；膨胀仪 25–1200°C、10°C/min、空气。污泥经 65°C、48 h 干燥并混入 15 wt% 熟石灰，不能当未经处理的原污泥。MIA1 为无污泥参照，MIA3 使用该预处理污泥；膨胀仪气氛不能转填为未报告的 TG 气氛。烧制试样尺寸也不能冒充膨胀仪试样几何。
- 独立逐项验证 provenance 的 original_assets、raster_evidence_assets、derived_assets，共 **25 个文件的 SHA256 和字节数**，均一致。PDF SHA256 为 `9c59141a717cb3b062aed6f28b48ed6005c5564aa3ce5a86de1c083bb6eae8a6`。图像分块与 SVG 记录支持“栅格图而非可提取曲线 path”；归属和裁图、读点、换算的修改说明保留。
- 从 `/private/tmp` 使用仓库 `.venv/bin/python` 和脚本绝对路径实际执行 `digitize.py --check`，退出码 0，26 点通过。脚本用自身路径确定仓库位置，因此不依赖 cwd。该命令检查 CSV/JSON 重算及原 PDF hash；其余资产 hash 是审核者另行核验，不扩大命令本身的保证。
- **未导入或调用提取器作为 oracle**：独立使用 Decimal 75 位，从原始 picks 重算所有 26 点的标称坐标、每轴 8 个端点角点、全部中间刻度残差、向外舍入及百分比除以 100。输出各字段全部一致。终端记录为 `independent_Decimal_rows 26 all_corner_enclosures_and_units_PASS`。

## 数值和代码判断

轴映射为明确的线性分式。当前校准端点误差盒内，分母不跨零；因此逐坐标单调性允许用角点包住给定像素盒的映射。中间带数字刻度最大残差另外加入区间。A 的温度/纵轴残差分别约 1.4683153°C / 0.00337838 百分点，B 分别约 1.3265704°C / 0.01081081 百分点。

点位横向 ±4 px，纵向 ±14 px 加 3 px 图块几何预算，刻度 ±6 px，均有显式声明。末块不同纵比例对应约 2.338 px，额外 3 px 没有被隐藏为无误差拼接。Fraction 保留输入十进制值和积分式的精确有理运算；Decimal 上下界分别向外舍入。百分数除以 100 得到相对长度变化的无量纲值，而非给长度比凭空加 1。

脚本是固定、可信本地证据资产的派生工具；没有网络调用或 shell 拼接执行，也没有拟合、插值填充出的假观测。其有限输入合同不能被解读为面向任意用户 JSON 的通用验证器。作者首次 CRLF 重现失败及显式 LF 修补保留在合同中；本审核只独立执行了最终成功版本。

像素包络属于条件性读图假设，不是实验误差、统计置信区间或完整的人工辨线错误界。横坐标也有不确定性，不能仅使用纵区间宣称固定温度下的准确测量。输出正确保留 `material_qualified=false`、`training_eligible=false` 与实验不确定性 unknown。单次升温方向长度变化混合热膨胀、相变化及烧结收缩，不能据此直接识别动力学、各向同性体积变化或孔隙闭合规律。以后若拟合这些点，必须另行分配校准和独立验证数据。

## 最终绑定

| 文件 | SHA256 |
|---|---|
| digitize.py | `9a5a6f9d9c6f5a637f37d8f829f2adfe2a33aca28727bf36aa647da480744653` |
| picks.json | `2c95ac0b7c62dff68cb7bd5fd98f4a747b213da7233829f8513e23e7a8d111c7` |
| points.csv | `4a6f7029b03072ec1579b9c2f11c8f65f663ed0ac9965c011555edce6b889d41` |
| points.json | `dc9544aa0e2e8e8cb156753a2af5804d873c8e5277247c74f6d201942c4e8e7e` |
| provenance.json | `c15aeefaeaa4d687fc9aaf34790aa15c70b9e7215b1dbf70c8f9459202f6ba74` |
| AREIAS2025_DIGITIZATION.md | `75a7eca4478fd56a7a80601589b961f8a4fa89af06aad8be0bfb9700608541e8` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 限已核验的 26 个图上点、可重算派生和条件读图区间，不构成材料物性准入。
