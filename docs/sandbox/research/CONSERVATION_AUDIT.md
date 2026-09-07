# 独立物种、质量、元素与储存内能账本审计

复审更新：原 33 项测试之外，新增权重乘积先舍入导致假通过、两格相反能量漂移和两格相反物种漂移共 3 个先失败反例，该轮36项通过；再加下述schema反例后最终37项通过。权重乘积与残差在 Fraction 中保留输入二进制浮点的精确值，直到完整残差才转为显示浮点；判定仍用精确残差对精确门槛。新增每格物种和能量的累计前缀检查。因此下文最初 12 组检查扩为 14 组，旧基准耗时/内存仅代表修补前版本，不能继承为当前性能。

实现：`src/sludge_sandbox/conservation.py`。测试：`tests/sandbox/test_conservation.py`。

最终接口复验还加入非法列表状态的先失败回归，统一返回 ConservationAuditError，当前37项通过。主代理在精确乘积与单元前缀修补后重新实测：1000个实际接受步、36000个残差检查，开启 tracemalloc 的审计耗时4.238 s，新增Python跟踪峰值176888 bytes；不含已存在轨迹，不是进程RSS。完整参数与源码hash见 `g2-conservation-benchmark.json`。

本模块独立读取积分器接受的状态与交换记录，检查它们在数学上能否闭合。它不调用 `Rates.derivatives`、积分器内部 RK 步或物理算子来生成“真值”，不读取积分器自报残差当作证据。当前仅完成 manufactured 软件验证；没有真实原污泥材料资格或外部实验结论。

**能量范围固定为 `stored_internal_energy_ledger_only`：核对保存的 U 与面能量/单元外功，不从物种热化学重新构建 U。** 完整热化学重构、生成能基准、液水/蒸汽潜热、反应热是否重复、机械功来源是否物理正确，仍需独立更高层验证。

## 输入与使用

```python
from sludge_sandbox.conservation import (
    ConservationBasis, ConservationPolicy, audit_conservation,
)

# result 是实际 integrate(...) 返回的 IntegrationResult。
# 以下只是接口展示：系数、元素身份与误差政策必须由调用方明确提供。
basis = ConservationBasis(
    species_order=species_ids,
    molar_masses_kg_mol=masses_in_species_order,
    element_order=element_ids,
    element_matrix=atoms_per_species,
)
policy = ConservationPolicy(
    relative_tolerance=registered_relative_allowance,
    amount_absolute_tolerance_mol=registered_amount_absolute,
    amount_scale_mol=registered_amount_scale,
    mass_absolute_tolerance_kg=registered_mass_absolute,
    mass_scale_kg=registered_mass_scale,
    element_absolute_tolerance_mol=registered_element_absolute,
    element_scale_mol=registered_element_scale,
    energy_absolute_tolerance_j=registered_energy_absolute,
    energy_scale_j=registered_energy_scale,
)
report = audit_conservation(result, basis=basis, policy=policy)
payload = report.to_dict()  # 可交给 JSON writer；不包含非有限数值。
```

- `amounts_mol[cell,species]` 是单元实际 mol，不能直接传参考体积浓度。
- `molar_masses_kg_mol` 与状态列一一对应；`element_matrix[element,species]` 为每 mol 物种含的 mol 元素原子。允许明确伪组分的非负分数计数，但不自动授予其材料真实性。
- 每个物种列和元素行必须有非零元素覆盖；身份重复、空/不匹配矩阵、负计数、非法/非有限值和非正摩尔质量拒绝。
- `IntegrationResult` 当前没有自带物种 ID，故数组列与 `species_order` 的来源身份绑定由运行服务负责。只要调用方在两处一致地错标身份，纯账本审计不能发现材料被偷换。
- 审计报告保存完整物种顺序、摩尔质量、元素矩阵和误差政策，便于重算；运行服务还应将这些值绑定到冻结的来源/参数图。

## 离散检查与符号

第 j 个接受步由 `states[j] → states[j+1]`，账本为 `steps[j]`；物种面交换 `F[f,k]` 是整步积分的 mol，能量面交换 `Q[f]` 是 J。面正方向统一为左到右，边界面是 `f=0` 和 `f=ncells`。反应 `S[i,k]` 是有符号物种 mol，`W[i]` 是该步单元外功/外部功率积分 J。

每格每物种：

```text
r_N(i,k,j) = N_after(i,k) - N_before(i,k)
             - F(i,k) + F(i+1,k) - S(i,k)
```

每格储存内能：

```text
r_U(i,j) = U_after(i) - U_before(i) - Q(i) + Q(i+1) - W(i)
```

全部残差加减项用独立的 Fraction 精确算术累计输入浮点数，不按 `large + small - large` 顺序把小库存或小功抹掉。权重乘积同样保留低位，不能先将每个乘积舍入再依靠 fsum 补救。内部面篡改即使在系统总量中抵消，也会被逐格检查发现。

系统物种账本将所有格库存差与两侧边界和全部反应源比较。系统质量和元素分别按显式 M/A 权重检查：

```text
Δm_system = sum_k(M_k * (F_left,k - F_right,k))
Δb_e      = sum_k(A_e,k * (F_left,k - F_right,k))
```

质量和元素系统平衡**不把反应源列作允许的外部输入**；同时在每格、每步独立要求：

```text
sum_k(M_k * S_i,k) = 0
sum_k(A_e,k * S_i,k) = 0
```

因此，即使有人同时修改反应账本与后续状态，使逐物种差分仍闭合，不配平的质量/元素源仍会失败。反应总摩尔数可以变化，不要求 `sum(S)=0`。

系统储存 U 与两外面能量及全部单元外功比较：

```text
ΔU_system = Q_left - Q_right + sum_i(W_i)
```

每个接受步和从起点到该步末尾的每个前缀都检查。前缀使用当前库存与初始库存的差，累计真实边界/反应/功项，不把已计算残差反过来定义“应有的”边界量。仅比较最终端点无法发现中途误差积累后抵消；本实现保留最坏前缀位置。

前缀累加用短浮点展开保留低位项，最后由 Fraction 将全部展开项纳入精确残差，避免 `1e20,+1,-1e20` 的 +1 在跨步累加中消失。它不在每个前缀重新扫描所有历史步，因此不会引入随步数平方增长的重算。权重运算保留逐物种库存差和乘积的精确二进制值，避免中间舍入丢失小变化。加权溢出、完全下溢或其他不可表征审计运算会抛出 `ConservationAuditError`，不能返回通过。每格的物种和能量也检查从初态出发的全部前缀，防止不同格的相反微小漂移相互抵消后仅系统总量通过。

## 固定误差政策与结果

每种量的通过门槛为：

```text
abs(residual) <= absolute_tolerance + relative_tolerance * fixed_physical_scale
```

四类量分别为物种 mol、质量 kg、元素 mol-atoms、能量 J。所有值必须显式传入，scale 严格正，各门槛正且有限；允许零相对容差以只用绝对门槛。政策在一次审计内不随单元/步/流量或 U 大小变化，也不会读取积分器的误差控制值自动代替。实验前登记与科学理由由验证计划负责，接口本身不创造材料尺度。

报告包含 12 组检查：

| 检查组 | 定位 |
|---|---|
| `cell_species_step` | 步、格、物种 |
| `system_species_step`, `system_species_prefix` | 步/前缀、物种 |
| `reaction_mass_cell_step`, `reaction_element_cell_step` | 步、格、元素（适用时） |
| `system_mass_step`, `system_mass_prefix` | 步/前缀 |
| `system_element_step`, `system_element_prefix` | 步/前缀、元素 |
| `cell_energy_step` | 步、格 |
| `system_energy_step`, `system_energy_prefix` | 步/前缀 |

每组保存次数、单位、固定 scale、绝对门槛、总门槛、最大绝对/缩放残差、该处有符号残差及时间/索引。最大值相同按首次出现定位。报告另含初始和最终物种总量、总质量、元素量及储存 U；这些汇总显示值可能受单个 float 的最终舍入影响，审计残差始终从分格和原始交换项独立构造。

`passed` 仅表示所给轨迹的账本检查通过。`integration_status` 和 `trajectory_completed` 单独保留：资源耗尽或取消后的有效接受前缀可以通过账本，但不会变成完成的仿真。零接受步为 `not_evaluated_no_steps`。步数、状态数、时间数不一致，时间不严格递增，或账本起止时间与实际状态时间不匹配，均拒绝而不计算通过状态。

## 实际验证

先写测试，在实现文件尚不存在时实际得到 `ModuleNotFoundError`；实现后执行：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_conservation.py -q
```

当前 **33 passed in 0.34 s**。包括：

- 实际积分器生成的两格开放边界、内部输运、C/O2/CO2 配平反应和外功账本。
- 审计时将 `integrate` 和 `Rates.derivatives` 替换为抛错回调，审计仍通过，确认没有调用前向求解器作为参照。
- 内部物种/能量面被修改但系统边界不变；单独修改边界能量或单元功。
- 反应产物源和所有后续状态一起被改写，逐物种仍闭合而反应质量/元素与系统物理总量失败。
- 独立错改摩尔质量向量或元素矩阵，分别触发对应检查。
- 每步低于门槛的 U 偏差中途累积超过门槛、最终抵消，仍由前缀检查拒绝。
- `1e20` 的平衡直通物质/能量不抹去小库存；保存的 `U=1e20 J` 不能用巨大的状态尺度掩盖未计入的 `1 J` 功。
- 跨步 `1e20,+1,-1e20` 的 +1 保留在前缀残差中。
- 无步、有效部分轨迹、非法形状/时间/基准/门槛、加权运算溢出与只读结果。

这些测试的物性、参数、几何与边界是制造验证数据，不是新的实验数据。

性能测量另使用实际积分器生成 1000 个接受步、2 格、3 物种、2 元素的惰性轨迹。独立审计执行 **28,000 个残差检查**并通过；开启 `tracemalloc` 时耗时 **1.247 s**，审计过程新增的被跟踪 Python 内存峰值 **158,907 bytes**。该内存数不包含已生成积分轨迹，不是系统 RSS；不据单个简单案例承诺复杂砖模型性能。

## 尚未证明的内容

这个审计器不能发现状态和所有物质/能量交换被协调改写为另一个仍守恒的物理过程；不能证明物理算子、真实材料参数、反应产物分配或边界条件正确。反应源已经聚合为物种 mol，因此不能区分“多条错误反应在同格同一步中刚好元素抵消”，逐路径计量需要在反应注册/运行层另查。

当前 StepLedger 的 `face_energy_j` 已聚合导热、辐射、对流或物质焓，`cell_work_j` 也不标物理来源。审计只检验这些积分数据与保存 U 的数值一致性，不证明焓基准、物质焓、反应/相变热和变形功的物理构成。完整全周期验收仍需要逐物种热化学重构、各类能量分项来源、全部机制的耦合检查、空间/时间收敛和公开实测对照。
