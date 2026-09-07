# 方程—代码—验证映射 v0.1

仅列实际存在的实现，不将架构接口作为代码。来源类别和运行资格另见 `EVIDENCE_POLICY.md`。

| 关系/约束 | 实现 | 实际测试/来源 |
|---|---|---|
| 单位维数、干湿基与数值有限 | `units.convert`；`materials.FeedPortion` | `test_units.py`、`test_materials.py`；质量基准的代数转换，无材料默认值 |
| 证据分类、来源依赖与域匹配 | `evidence.EvidenceRegistry` | `test_evidence.py`；只检查声明元数据 |
| 自带水 `m_w=m_d*x_w/(1−x_w)` | `materials.prepare_green_batch` | 人工质量账目测试；额外加水显式独立输入 |
| `J=λ_n λ_parallel²` 及共享面积 | `geometry.ReferenceSlab.deform` | `test_geometry.py`；运动学推导见世界定义 |
| 开放气孔=总体−固相−闭孔−液水 | `geometry.pore_geometry` | 域耗尽/无clip反例；未包含真实闭孔转换 |
| Shomate cp、积分h含生成焓、气体u=h−RT | `thermochemistry.ShomateSegment` | NIST原表/原系数/导数/参考能测试，来源表在 `data/sandbox/thermochemistry/` |
| 分段混合能量及温度反解 | `thermochemistry.Thermochemistry` | 原接缝、多解/缺口、次正规数分辨率与溢出反例 |
| 理想气体EOS与全species组成 | `gas_transport.GasState` | `test_gas_transport.py`；孔体积/载气显式 |
| 质量平均扩散、Darcy压力流 | `gas_transport.face_exchange` | `GAS_TRANSPORT.md`；中心修正改为漂移上风，空物种格方向及一阶误差已复验 |
| 半格串联Fourier热率 | `exchanges.conduction_rate_w` | `test_exchanges.py`；`HEAT_EXCHANGES.md` |
| 对流+灰表面/黑体环境辐射 | `exchanges.boundary_heat` | 相反方向热输入、独立气温/辐射温度与非法值测试 |
| 扩散/对流分项的物质焓率 | `exchanges.gas_enthalpy_exchange` | 实际热化学/气体模块接口测试；EOS与热化学R一致 |
| B2被动暴露积分误差步长界 | B2 `solver.exposure_step_limits` | 原容差、独立oracle、提交绑定22情景；仅历史synthetic域 |

完整组装器、动力学、水分迁移、烧结、力学和多代实验还没有实际映射，保持未完成。后续任何结果的完整DAG还需绑定实际启用的函数、参数和模型版本，不能用这张人读表替代运行时追溯。
