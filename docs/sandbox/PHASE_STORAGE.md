# 给定相压力下的物种热储能 primitive

`phase_storage.py` 已实现固定各相摩尔库存、显式给定各相压力时的 U/H/体积计算，以及条件成立时的温度反演。它不解气孔体积—压力自洽、毛细力学、相平衡或相变速率。结果固定声明 `energy_scope="species_thermal_storage_only"`：没有把未知弹性和界面能默认为零再声称全系统能量闭合。

## 输入和来源边界

`PhaseMetadata` 声明物种、相态、摩尔质量/基准、能量参考、来源 ID 和分类。`PhasePoint` 给 T、p、摩尔 u/h/v，检查有限性、正体积和 `h-u=pv`；数值残差限为 1e-8 J/mol，不是材料不确定度。`PhaseProvider` 是明确的温压物性协议，外部固体 provider 必须为 frozen dataclass，具有上述元数据和温区。没有内置原泥固体热容、生成能或默认体积。

来源名称本身不等于资料已审查。`source_status="provider_declarations_not_material_qualification"` 保留这一限制。`manufactured_test_fixture` 必须显式开启 `allow_manufactured=True`；外部 provider 的元数据和温区建构时保存快照、每次使用前后核对。冻结外壳不被当作任意内部实现的安全沙盒。

`LiquidWaterPhase` 使用来源校验后的 `WaterProperties`，从稳定液态实际 `(T,p)` 得到 u/h/密度，不以饱和密度替代实际液压。`IdealGasPhase` 只接受经来源校验的 `IdealWaterVapor` 或具有物种和分类身份的 `ShomateGas`，后者必须显式选择单个段。裸 `ShomateSegment` 不足以识别材料身份，不能被默认重标为水或自动洗去 manufactured 分类。

NIST 气体适配还要求明确摩尔质量及附加来源声明，包括量基准/气体常数依据。它保留原 gas 的 species/classification 和所选段来源。水桥使用其登记摩尔质量，不能任意改写。各相混合要求相同声明能量参考和摩尔基准，同一化学物种跨相摩尔质量必须一致；这里检查一致性，不自动核准任意外部来源的真实性。水的 NIST 生成焓偏移已在底层包含，此层不再加一次。

## 计算语义

```text
U_thermal = sum_i N_i u_i(T,p_i)
H_species = sum_i N_i h_i(T,p_i)
V_i = N_i v_i(T,p_i)
```

N 为实际 mol，U/H 为 J，V 为 m³。输入 phase key 可以区分同一化学物种不同相。输出逐相体积不可变；没有把不同压力的体积之和命名为机械闭合的实际单元体积。

任何未知 phase key 即使库存为零也拒绝。已登记零库存不查询相物性、温区或压力，因此干燥后水相不会无故限制活跃固/气相温度。零库存仍接受元数据完整性检查，这不是物性求值。负/非有限库存、非正活跃相压力、无效返回身份或域外状态明确失败。

## 条件反演，不冒称单调性证明

`temperature_from_energy` 固定库存和相压力，用所有活跃相物性域与 `MonotonicPath` 域的交集括区求根。每条路径必须显式给相压力、连续且严格递增的温区、正的 `du/dT|p` 下界、来源和方法说明。缺声明、无公共温区、目标能量域外或数值观察与下界矛盾均拒绝。

这些外部声明尚未由证据注册器独立准入。有限端点/二分观察只检查反例，不能证明全域唯一性；因此返回 `inverse_status="conditional_on_declared_monotonic_paths_not_independently_admitted"`，并保存不可变的实际 `inverse_paths` 及其来源 ID。调用者不得将条件数值结果升级为已验证材料预测。真实水测试采用明确标记的测试路径假设，不把有限差分样本当作区间证明。

液体固定 p 路径：

```text
du/dT|p = Cp - p * dv/dT|p
```

一般不等于 Cv。适配器不把 sum(N Cv) 用作反演斜率。二分停止同时要求能量绝对误差与温度括区宽度合格；残差恰好舍入为零不会立即触发成功。所有容差为显式 `InversePolicy`，没有使用巨大生成能乘相对容差放宽验收。

`energy_resolution_j` 保留逐相的 `N*ulp(u)+ulp(N*u)` 再加总和 ULP，避免正负大生成能抵消后只看小总 U 而假称精度。该量是浮点表示诊断，不是严格的整个上游物性算法误差界或物理误差。反演将目标 U 自身的一份 ULP 与求值表示预算相加，再检查绝对值和除以声明总导数下界后的温度分辨率。每个 N 乘导数下界以及总下界均必须保持有限正值；下溢到零时明确失败，不进入除零。温度自身 ULP、步数耗尽和矛盾割线也会拒绝。上游物性解误差仍须另行纳入完整求解器的数值误差账本。

## 实际验证

先写测试，实际运行因缺模块得到 `ModuleNotFoundError`，再实现。以下命令目前 **22 passed**：

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_phase_storage.py -q
```

测试涵盖：显式制造固体的线性解析 U/H/V 与反演；真实液水及理想水汽各相求和和混合反演；真实 NIST N₂ 单段适配；固定高压液水的温度导数与 Cv 确实不同；未知与零库存、相压力/域/参考身份、manufactured 门禁；错误大导数下界；无公共区间；不可变结果和路径证据；大生成能量化平台及正负能量抵消不能伪报温度精度。

独立审查发现的大生成能平台反例、主代理指出的裸段身份与嵌套元数据变更、后续相间抵消反例均先保留实际失败，再修补通过。当前通过数不等于独立审查已批准，最终结论由审查报告给出。

本层下一依赖是机械/体积闭合和经证据准入的连续单调路径。湿砖全周期仍须原泥固体物性、液水迁移/活度、相变动力学、几何与应力功，不由本 primitive 代替。
