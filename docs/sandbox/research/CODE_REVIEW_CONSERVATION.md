# G2 独立守恒审计器代码与算术审查

审查者：`code_review_g1_b2`；2026-09-07 UTC。范围为 `src/sludge_sandbox/conservation.py`、`tests/sandbox/test_conservation.py` 和 `CONSERVATION_AUDIT.md`。审查者只读源码、执行独立探针和测试，仅编写本报告，未修改实现或提交。

**最终 Approve：可以作为账本一致性审计模块做局部阶段提交。** 初审的加权假通过、局部累计漂移和畸形状态错误均已修复复验；当前范围无遗留 CRITICAL/HIGH 问题。本报告只确认保存状态与交换账目的数值一致性检查，不构成热化学重构、真实材料或整砖物理验证。

## 初审发现与修复

### [HIGH，已修复] 先舍入加权乘积能制造质量和元素假通过

位置：初审 `_product()` 返回单个浮点乘积，再由 `_Check.observe()` 使用 fsum 合计。

独立构造：`a=1+2^-52, n=1e16`，两个显式伪组分的摩尔质量为 `(a,1)`，C 元素行为 `(a,1)`；初态 `[n,0]` 到末态 `[0,n+2]`，反应源为 `[-n,n+2]`，物质边界、U 与功均为零。固定质量/元素绝对门槛均为 `1e-9`。初审 audit 返回 passed、加权残差为零；但按输入二进制数的精确乘积，残差是 `(n+2)-a*n = -0.22044604925031308`。每个乘积的低位已经丢失，后续 fsum 无法修复。

最终 `_product()` 在数值范围检查后返回精确 Fraction 乘积，库存变化与全部加权项也保留 Fraction 直至完整残差形成。`_Check` 用精确残差最大值与公开保存的 limit 的精确二进制值比较，显示字段才转 float。原始反例现在 failed，reaction mass/element 和系统加权检查得到正确非零残差。摘要库存可能最终舍入成相同显示值，但不再作为判定依据。

### [MEDIUM，已修复] 相反方向的逐格漂移被系统前缀抵消

位置：初审只有 `cell_species_step/cell_energy_step`，累计前缀仅在系统层检查。

独立构造两格零交换系统，共 10 步，每步将第一格 U 增加 `0.5e-9 J`、第二格减少同量，绝对门槛 `1e-9 J`。初审每格单步都通过、系统前缀恒为零，所以整体 passed；各格实际累计偏差已达 `5e-9 J`。物种库存同方向构造也有相同缺口。

最终新增 `cell_species_prefix` 与 `cell_energy_prefix`，各自累计真实本格面流入、面流出以及反应/功，从初态到每个接受步核对。两种原始漂移现在都 failed：物种最大偏差 `4.999999969612645e-9 mol`、能量 `5e-9 J`，不会因两格相消而放行。共 14 组检查保留了系统及局部两个层级。

### [MEDIUM，已修复] 畸形 status 泄漏不可哈希 TypeError

位置：`audit_conservation()` 的 IntegrationResult.status 集合成员检查。

`replace(valid_result, status=['completed'])` 原先得到原生 `TypeError: unhashable type: 'list'`；修补后先验证字符串类型，独立复验得到 `ConservationAuditError('unknown_integration_status')`。它没有把畸形数据写成通过。公开报告/政策方法的返回类型与浮点展开 docstring 也已同步。

## 独立性与科学边界

- 审计从接受轨迹及 StepLedger 重构残差，不调用 integrate、Rates.derivatives、RK helper 或物理算子作真值。测试用抛错回调替换这些前向入口，审计仍能运行。
- 每格物种残差使用 `ΔN-F_left+F_right-reaction`，每格 U 使用 `ΔU-Q_left+Q_right-work`。内部面只有一份；篡改内部面即使系统层抵消，仍会被局部检查定位。
- 系统质量和元素只允许物质外边界改变其总量，不把反应源当作外部质量/元素输入；每格聚合反应源另按完整显式 M/A 向量检查。质量与元素依据独立应用，不能相互替代，也不要求反应总 mol 不变。
- 前缀基于原始库存和实际累计交换构造，包含中途最坏位置；没有用已观察误差反向修补应有流量。短浮点展开保留跨步低位，最终用精确残差比较；加权溢出或完全下溢明确拒绝。
- 政策的绝对门槛、相对容差及固定 scale 由调用者明确提供；不会从大形成能、大库存、大穿流或 solver 自报误差动态放宽。物种列的真实身份、元素矩阵、摩尔质量与来源冻结仍须运行资格层核查。
- 无接受步不评为通过。合法部分前缀可通过账本，但独立保存 integration_status 和 trajectory_completed，不能变成已完成仿真。形状、有限性、时间单调性和账本起止时间重新检查，不信任 dataclass 本身代表数据正确。
- 输出固定 `stored_internal_energy_ledger_only`、`thermodynamic_reconstruction=not_evaluated`、`ledger_consistency_only_not_material_validation`。模型与全部交换若被协调改写成另一套仍守恒的过程，纯账本审计不能证明其物理正确；聚合反应也不能替代逐路径资格检查。

## 实际验证

初审实际运行 **33 passed in 0.32 s**，仍真实发现上文反例。最终运行 `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_conservation.py -q` 得到 **37 passed in 0.44 s**。作者新增回归的红阶段按其记录保留；本审查独立观察过全部原始错误结果。

额外独立检查包括：

- 100 个确定种子的序列、每序列 30 次前缀累计，指数范围 −600 至 600，并插入相反大项；将每次浮点展开项的精确 Fraction 和与原始全部输入的精确和比较，**3,000 次前缀比较全部相同**。这验证的是低位保留，不是性能外推。
- 对一份真实制造积分轨迹与 4 份独立篡改轨迹，用单独 Fraction 算式计算每格单步 U、每格前缀 U、系统单步质量和每格反应质量的最大残差；**20 项报告最大值与独立精确算式一致**。
- 修补后的原始加权反例准确报告 `-0.22044604925031308`；相反的局部物种/能量漂移均失败；畸形 list status 得到结构化错误。

原文档 33 项版本的 1,000 步耗时/内存记录只代表其历史实现；最终加入精确乘积与局部前缀后，不能继承旧性能测量为新版本成绩。当前没有 ruff/mypy/pylint/black 可执行文件，未虚报静态检查通过。

| 文件 | 最终 SHA-256 |
| --- | --- |
| `src/sludge_sandbox/conservation.py` | `e787ae71be271bfbfbdedca96bc9b7f4b20bd9aa61f730ca0bdc4e35e5904cdc` |
| `tests/sandbox/test_conservation.py` | `019d94115f652909df0a13883b20790013c6f53d20edd043f310c3373b0eba32` |

这些制造轨迹、人工篡改和独立算术探针是软件与数值验证证据，不能登记为实验数据，也不能替代后续热化学能量分项和公开实测对照。
