# 保存参考网格的嵌套分区提案

`scripts/propose_nested_reference_partition.py` 读取两份保存的 P44/P46 格式记录，以指定时刻、指定广延量的局部差选择原粗格，输出可直接读取的初始参考 faces/centers/volumes 和精确保守映射。标准库实现，只依赖已有的 `scripts/reference_volume_compare.py`；不加载主模型、构造状态、调用速率/RHS/Jac、积分、fit 或 UQ。

## 输入与用法

所有选择参数必须由调用者显式给出。面积从调用者指定的根参数格式 JSON 及参数键读取，单位必须为 `m2`。优先使用该保存作业的物理参数快照，不改写任何根参数。

下列命令是已执行的一次 P44 保存数据生产转换，不是 CLI 的默认运行配置。`10 s`、direct extent 和分裂 `1` 个粗格在转换前固定，没有搜索其他时刻、场或参数。

```sh
python3 scripts/propose_nested_reference_partition.py \
  --coarse runs/full-cycle/p44-nonuniform-direct-transient/baseline.json \
  --fine runs/full-cycle/p44-nonuniform-direct-transient/mesh_refined.json \
  --parameters runs/full-cycle/p44-nonuniform-direct-transient/root-snapshot.json \
  --area-parameter geometry.area \
  --time-s 10 \
  --field reaction_extent_mol.direct_carbonation \
  --split-count 1 \
  --output /absolute/caller/chosen/proposal.json
```

输出目录由调用者事先提供。`--time-s` 必须在两份记录中各精确出现一次，单位为秒；不做时间插值。粗网格每个初始面必须精确出现在细网格中，面积与域边界复用现有 C 工具的相等要求，不吸附面、不引入几何容差。

`--field` 使用保存记录的字段名。以下为生产器实际保存的广延字段及其原单位，不能传温度、压力、孔隙率、收缩率或亲和力：

|字段|单位|含义|
|---|---|---|
|`reaction_extent_mol.<reaction>`|mol|独立累计反应进度，reaction 必须存在于输入样本|
|`gas_inventory_mol.<species>`|mol|保存的逐格气体库存，species 必须存在于输入样本|
|`calcite_inventory_mol`|mol|逐格 calcite 库存|
|`lime_inventory_mol`|mol|逐格 CaO 库存，保留原负值|
|`portlandite_inventory_mol`|mol|逐格 portlandite 库存|
|`calcium_inventory_residual_mol`|mol|保存的带符号逐格 Ca 库存残差|
|`residual_carbon_kg`|kg|逐格残碳质量|

单位来自上述保存 schema，记录在输出 `inputs.amount_unit`；程序不进行单位转换。缺失字段直接报错，不替换场、不重建 extent。

## 选择与映射

1. 复用 `ReferencePartition.from_saved`，读取 `actual_initial_state.initial_reference_faces_m`、`initial_reference_bulk_m3`；原 centers 也保存为来源。坐标为初始材料参考坐标，单位 m；参考体积单位 m3，面积单位 m2。P44 的坐标从对称侧 0 m 向外表面 0.015 m 增加；这两个数是该输入的保存值，代码不固定域长度或原点。
2. 复用 `ConservativeMap(fine, coarse)` 与 `compare_profile`，对同一参考区间计算 `delta_i = sum(fine_saved_child_amounts) - coarse_saved_amount_i`。只按 `abs(delta_i)` 排序，使用原量单位；不换成密度误差、相对误差或带 floor 的量。
3. 排序为绝对局部差降序，完全相等时按零基原粗格索引升序。只有包含已保存内部细面的粗格能分裂；无可插入面的粗格保留在完整排名中并跳过。显式数量超出可分裂格数直接报错。
4. `--split-count` 指要分裂的原粗格数量。每个选中原粗格插入其全部已保存细网格内部面，因此插面数量可大于分裂格数。全程只对原粗格排序一次，不在新格上估计误差或继续优化。零差也按显式数量和相同平局顺序处理。
5. 保留所有粗面及域边界。新参考体积取覆盖该新格的保存细格参考体积精确求和；新中心为相邻参考面几何中点。输出各格体积相对 `area * width`、以及合回原粗格的原始带符号浮点残差，不调整到阈值或强制归零。

输出 `conservative_maps` 包含 fine→coarse、fine→proposal、proposal→coarse 三个映射，每行记录源格索引与广延权重（均为 1）。`proposed_initial_partition` 保存参考面/中心/宽度/体积、原粗格父索引、保存细面索引，以及每个新面的来源。`saved_fine_amount_on_proposal` 只重分区已有细网格量，不能视为 proposal 的新模拟解；粗格子量未知，没有 coarse→proposal 延拓。

完整原排名、原有带符号局部/累计差、保存来源路径、case/schema/identity、已记录的坐标模式、frozen_job、选中样本索引及面积参数元数据均输出。缺少的模式信息记 null，不猜测。

## 已执行范围与边界

一次 P44 末时刻转换的实际结果：12/24 格输入，选择零基粗格 9，局部 direct 差 `+4.40684098008704e-6 mol`；仅插入保存细网格面 19（`0.014348958333333333 m`），输出 13 格。最外粗格 11 的局部差为 `-1.3494033863597327e-9 mol`，绝对差排第 8，未被自动选中。

保存细量总量减 proposal 总量为 0，via-proposal 与 direct fine→coarse 的逐格差全部为 0；这只是本次已保存数据的代数重分区结果。体积合回粗格仍保留第 4/5 格 `+3.3881317890172014e-21 / -1.6940658945086007e-21 m3` 的原始浮点残差。

生产转换耗时 `0.011271125171333551 s`，JSON 输出 `38862 B`。实际执行 AST 解析、CLI 帮助和这一条生产转换；没有新测试或断言脚本，没有 SHA，没有模型调用。独立工作区的小数据读取/静态检查/生产转换合计低于 60 s，交付总字节数另见工作区 receipt。

该文件只登记网格提案，不表示任何收敛阈值通过、误差减少预测、渐近阶或新的模拟资格。P46 目前只有 12 格 mode1 基准；P44 mode0 细网格不能让 P46 获得同模式加密资格。匹配参考域本身不能证明物理条件一致，调用者必须阅读所保存来源。原 P34/P40/P44/P45/P46 的失败和 undefined、全部物理边界、0 实测状态与名义工况保持。本工具不修改根参数、主 P47 文件或 C 采样接口，也不把 proposal 自动接入求解器。
