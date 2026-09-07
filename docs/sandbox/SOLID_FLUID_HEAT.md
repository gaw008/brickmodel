# 固体库存参与的流体与热量主机

`SolidFluidHeat(storages, inventory_layout, transport)` 接受 `SolidFluidStorage`、显式 `InventoryLayout` 和已有 `RigidFluidHeat` 的输运配置。每格的 `fluid_template` 必须是对应 transport storage 的同一个对象，以绑定完整水来源、气体热量曲线、压力政策与数值 envelope；不是只比物种名称。模板 available volume 不参与本主机的实际解码，每次真实孔容由 `Vbulk−ΣNs vs` 得到。

InventoryLayout 明确完整 species_order、液列、气体顺序和固体顺序，必须无遗漏/重复/重叠；允许固体在第一列、液体在中间。所有gas/solid库存均按名字查列，不使用 `row[1:]`。面物种数组保持完整列数，只有气体列接收共享面的通量，固液列严格为0。

总内能和真实固体库存交给 SolidFluidStorage 正向/反解，返回独立 `SolidFluidHeatEvaluation`，保留每格完整 SolidFluidInverse 及其条件数值预算。没有将新状态伪装为旧 FluidHeatEvaluation；没有调用旧fluid解码器或把含固体总U传给旧fluid inverse。复用范围仅为已验证的气体面交换 `_face`、气相焓 `_enthalpy` 和导热公式。面积×格宽与storage.bulk要求绝对差不超过两者最大ULP的2倍；这是浮点几何表示核对，不是材料形变/不确定性准入。

`WaterPhaseTransfer` 显式接受这两种主机。新主机取layout液列，气水列按H2O身份查询；仍以真实总气压作为液压、真实水汽分压作为驱动力。相变只将等mol液水移到气水，总U不再额外加潜热。原水/水汽桥来源身份匹配保留，新增固体和几何的制造分类也需显式测试授权。

未知泥料参数没有默认值。两格演示中的固体Cp、体积、几何、扩散/导热/界面速率与误差envelope均为明确制造测试输入。固体原料配比、体积模型或真实传质关系不会由主机自动获得。标准资格为固定固体库存/条件流体输运，非全砖模型。

## 验证记录

先写layout测试，首次运行因新模块不存在得到ModuleNotFoundError；实现后4项通过。接入真实storage后最初7项中2失败：一项两格相同气体比例本就没有组成扩散（测试改为不同气体比例）；另一项制造solid体积误差1e-12 m³/mol经压力误差传播超过温度精度要求，被正确拒绝。随后用显式制造数值界1e-18 m³/mol及bulk1e-18 m³连接验证，不称物性误差改善、不放宽核心门槛。

实际新测试命令：

```
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_solid_fluid_heat.py tests/sandbox/test_solid_water_phase_transfer.py -q
```

10 passed in17.17s。包括实际两格气体+热传导积分、固液零面流、各物种总mol/总U守恒、完整新inverse状态、template/geometry门禁、固域退出；单格实际水相变积分以固体Cp10与100 J/mol/K对比：两者均蒸发降温，较高固体Cp降温更小；固体/载气恒量、水两相总量和U保持。液列刻意置于第3列以防旧下标假设。未添加多格湿砖性能或真实材料精度声明。

旧水相变兼容回归：`PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_phase_transfer.py -q`，16 passed in37.95s。随后补3项非法液列标识检查，定向 `-k 'layout or column or liquid_label'` 实跑8 passed /2 deselected in0.35s；新增总计13项，最终全集由独立审核绑定。

审核补充：`ConservedState` 本身没有layout哈希；同shape但调用者擅自置换列无法由容器识别，完整列序是调用者必须遵守的主机契约。新增固域测试在fluid有效300K处令solid域301–500K，明确只测试固域错误映射。制造opt-in测试核验整个制造host，未冒称独立隔离只solid/只geometry分类分支。

两种固体Cp的原有蒸发轨迹现在进一步采用最终 `decode_inverse.temperature_error_bound_k`：要求低Cp温度区间上端低于高Cp区间下端，且高Cp区间上端低于300K。该检查验证效果能被当前声明数值预算分辨，不仅比较名义浮点温度；不增加积分、不延长0.001s、不修改原数值门槛。独立审核者将保留既有29项收集版本记录并单独执行这一新增断言。
