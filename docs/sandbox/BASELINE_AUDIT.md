# 基线与复用决策

基线提交 `4b4f2d3`，2026-09-07 UTC 在 macOS arm64 工作区读取。这里是初始代码核查；尚未进行旧 VME 全套复跑。

| 现有部分 | 证据 | 本 Goal 处理 |
|---|---|---|
| 元素式/计量、单位工具 | `src/sludge_vme/chemistry/`、`units.py` | 经过对应测试后复用；新内核独立声明量纲和基准 |
| L0/L1 | `models/common.py`、`l0.py`、`l1.py` | 保留旧实验；完整温湿/能量/压力状态需新内核，不能重贴真实材料标签 |
| 氧气 | 旧 common 以初始氧加边界最大可供氧累计量限制反应，GASES 不包含 O2 | 新模型必须以局部 O2 库存和真实跨面通量求解，显式载气 |
| 能量 | `FORMULA_CODE_MAP.md` 明确 reduced-effective-enthalpy ODE | 用统一组分能量和流动焓通量替换，禁止宣称旧残差是完整能量 |
| 液相/收缩/性能 | `PARAMETER_SOURCES.md` synthetic/unknown；sigmoid liquid | 不进入证据支持的材料包；待有据本构及域匹配 |
| B1 | 等温 C/O 无量纲 FV/SSPRK2，历史 Linux 14/14 | 可作为特定极限参照；不能继承成整砖验证 |
| B2 | 给温系数、固定孔隙；历史 audit false | 在副本定位、修复必要代码、保存新证据；不改旧失败 |
| DTU | 四原始工作簿，SSA/黏土，小圆片 | 复用原始来源与单元格；仅验证覆盖的无机/终态指标 |
| 旧 source registry | 背景文献/链接和概括性 validity | 不能满足逐参数证据/适用域查询，需要新依赖图 |
| 旧 CLI/产物 | forward/inverse/verify 等 | 保留入口；新接口共享新内核，提供明确模式与迁移说明 |

策略：新建独立 `sludge_sandbox` 包，与旧 `sludge_vme` 并存，逐项采用通过测试和语义核查的工具。避免在旧 synthetic 输出协议中偷偷换物理意义。

关键可行性：编程工作可继续；当前尚无证据证明公开资料能完整闭合一个真实原污泥—基料—全烧成条件域。来源调查是运行资格的一部分，不通过假设常数补洞。
