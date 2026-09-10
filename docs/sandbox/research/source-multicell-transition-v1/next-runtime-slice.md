# 下一步复用调查：湿邻格压力与保存记录

范围：只读当前代码和已保存文档；未执行测试、模型构造、EOS 或当前原生运行。当前 N3 运行由 Root 管理，本文不预判其终态或门槛结果。所有路径相对仓库根目录。

## 结论

现有代码没有可直接用于真实 `SourceWetStorage` 湿端点、同时覆盖完整逆解温度区间的共享体积联合压力入口。可以复用来源验证、全温度连续围栏、原误差分解和已有成对根的纯算术思路；不能直接把干态联合界或旧报告温度证书接入湿格事件门槛。

| 入口 | 可复用部分 | 必须保留的限制 |
| --- | --- | --- |
| `src/sludge_sandbox/source_inverse_pressure.py`：`enclose_source_inverse_pressure` / `propagate_declared_pressure` | 实际 state/inverse/source 绑定；原闭合残差复核；完整 `T±eT`、全域后局部的 `L` 与 `eP+L·eT` 围栏 | 当前两端点比较是独立半径之和，没有共享参数证书；稳定光滑分支和原声明 `abs(uP)≤B` 仍是条件 |
| `src/sludge_sandbox/source_dry_shared_pressure.py` | 同一 live storage/volume 的显式声明与篡改重核模式；实际误差与表示误差不得丢弃的设计 | 其数学合同要求 `Nl=0`、固定干质量及理想气热量对 V 无依赖；湿态不能借用这个资格或删除干态守卫 |
| `src/sludge_sandbox/paired_pressure.py`：`certify_paired_pressure` | 同一压力支点区间上的闭合差、残差区间和正顺应性下界的 Fraction 算术 | 只覆盖报告温度；输入是 mol 固体、固体摩尔体积、bulk/J/reference volume 模型；不能伪造这些字段来适配固定 kg 的来源模型 |
| `src/sludge_sandbox/paired_pressure_host.py` | 旧模型如何绑定液体端点证据、整个支点根区间的范例 | 要求原 manufactured reacting host，可能执行新液体端点求值；不是来源模型的被动恢复入口 |

## 共享体积可以消去什么

湿格报告温度闭合为 `G_i(T_i,p,V)=Nl_i·v(T_i,p)+Ng_i·R·T_i/p−V`。在同一个 V 和同一个 p 上求 `G_a−G_b`，共同的 `−V` 项确实代数消去。但要把这个残差差变成根差上界，仍须完整支点压力区间、各温度下液体体积包络、正顺应性下界、原域内性及数值表示余量。原体积误差仍参与建立根区间和域，不能简单从旧压力半径里减掉两份体积项。

未来最小数学桥接可先研究“报告温度成对根界 + 原 `L_a·eT_a + L_b·eT_b`”，用三角不等式覆盖原完整温度箱。它必须先证明与保存压力/实际机器输出为同一目标，并保留独立 EOS/残差/舍入项；这是待实现和独审的合同，不是当前可调用的证书。湿态 `u(T,P)` 对压力的依赖已经进入能量和温度误差，不能沿用干态 `U(T)` 与 V 无关的论证。

当前端点保存了各自实际 `(T_i,P_i)` 的水状态，不等于保存了两种报告温度在共同支点整个压力区间上的液体体积证据。旧 `LiquidEndpoints` 明确要求该完整区间及两端误差。仅凭已有两个水状态不能直接构造更紧的旧成对证书；需要先审定可由现有包络推出的区间，或另行登记有界新端点求值。离散 EOS 点本身也不会把声明包络升级为独立验证的全域 EOS 定理。

## 不得因同一 provider / storage 而抵消的项

- 两次闭合的实际 `fluid.pressure_error_bound_pa`、液体摩尔体积 EOS 误差、闭合压力/体积残差及分辨率；`liquid_pressure_error_bound` 重算的 nominal 只是最低要求，不能取代更大的实际保存误差。
- 两端独立的液/气内能误差、实际能量求和舍入、逆解能量残差、来源总 U 表示误差，以及原 `Nl·B·eP` 压力致能量项；相同水源或 Cp 来源没有声明这些数值误差的相关结构。
- 原 `eT` 和各自连续围栏 `L·eT`。包括由原体积不确定性经 `Nl·B·extra_pressure_error` 传入的能量误差，在上述最小合同中也保持原值，不能再凭“共享 V”二次扣除。
- 实际 float 的 gas sum、乘除、液体体积/压力投影和总界向外舍入；共享参数不代表两次计算舍入相同。保存 global/extra/total 超出重算值的余额不能随意归入“可消去体积误差”。

这些是当前误差合同中的独立保留项，不是实际物理误差的已知下界。

## 最小可执行步骤：先做保存端点预算审计

新增一个独立的被动审计脚本，固定本次终态 JSON 和运行器 SHA，只处理实际保存完整的湿格 0、2 的 event/common 两组对应端点；缺失端点就明确记录缺项。输出每格每组：原 `abs(Pa−Pb)+radius_a+radius_b`、原阈值、每端 actual fluid/nominal/global/extra/total 及超额、原 `eT`、原 `L·eT`、源能量误差组成和域资格。复用 `closure_diagnostics`、`liquid_pressure_error_bound`、`wet_fluid_pressure_bounds` 与 `propagate_declared_pressure`，先核对原字段再展示分解；读取保存的包络和输入，不构造水后端。

尤其检查原 `L_a·eT_a+L_b·eT_b` 是否已经达到或超过原压力门槛。如果达到，则上述仍保留这些项的“报告温度联合界 + 原温度余量”方案不能靠体积抵消取得更小于该小计的最终上界；等于门槛时还需其他项恰为零才可能通过。这只是对这一保守界形式的可行性判断，不证明真实误差过大或所有未来方法无效。审计不输出新事件准入，不改旧独立结果，不假设后续联合界必过。

## 保存 / 恢复的直接复用入口及最小缺项

| 已有文件 | 可直接复用 | 本次最小缺项 |
| --- | --- | --- |
| `docs/sandbox/research/source-multicell-transition-v1/run_native.py` | 已冻结递归保存：类型/完整字段、Fraction、float64 ndarray、实际输入/回调/失败/部分候选；原子 JSON 与 live provenance | 序列化刻意省略 live `adapter` / `dry_adapter` / `storage`；完整 JSON 不等于恢复这些对象或证明当前对象 `is` |
| `docs/sandbox/research/source-net-panel-v1/replay_native.py` | 固定白名单被动 dataclass 解码、完整字段、构造后 canonical 往返、原 Fraction/数组验证；`SavedSourceSample` → panel | 当前白名单含 `ProgrammedLiquidSourceRates`，未含本次 `LiquidSourceColumnRates`。只需为端点审计增加这一明确被动类型及确认实际选中记录依赖；不从输入动态 import，不放开任意类 |
| `docs/sandbox/research/source-net-prefix-v1/replay_native_prefixes.py` / `source-net-roots-v1/replay_native_roots.py` | 保存样本重建原 panel/prefix/roots，纯数值核对 | 脚本绑定旧原生输入和旧 SHA，需要新独立输入清单；它们不是整条实际 trial 的恢复器 |
| `docs/sandbox/research/source-endpoint-comparison-v1/run_saved.py` 与 `src/sludge_sandbox/source_endpoint_comparison.py` | 保存完整 source 样本的同一精确时刻 N/U/T/报告 P 比较，样本绑定；原完整政策 codec | 其范围明确是端点账目而非 trial restoration；完整温度 P 需继续走本轮所述原连续围栏审计 |
| `docs/sandbox/research/source-inverse-pressure-v1/run_saved.py` | 已保存 source state/inverse 附着到实际 storage 后，原 `enclose_source_inverse_pressure` / `.check()` 的被动验证模式 | 该脚本 `make_case` 实际执行两次 HEOS 构造参考锚点校验，不能称全程零 EOS。本次纯审计不重建模型；未来重新附着 live storage 时必须如实计数 |
| `src/sludge_sandbox/exact_record.py` | `pack/unpack/_policy/canonical` 已用于来源完整政策复制/绑定，可继续用 | 当前完整运行 schema/registry 是另一宿主体系，没有 source trial/terminal/dry candidate 全套类型；不能把其 read/resume 能力声称为来源运行恢复 |

若下一步只是上述端点审计，不需要实现整条 trial 恢复。若未来要再次调用完整来源 `.check()` 或继续执行，则还缺明确 source 保存 schema、必要完整记录白名单、外部构造的真实 adapter/storage 附着和逐格对象关联校验。离线的相同 digest、配置或保存的 `id` 都不能创造跨运行的共享对象身份；目前 N3 显式共享声明只覆盖 cell 1，不能从它推出湿格 0、2 已获新的共享资格。
