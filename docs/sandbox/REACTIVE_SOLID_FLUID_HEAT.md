# 固相反应共享源的事前验证门槛

计划在SolidFluidHeat单次整体decode后，以实际T、完整mol库存与bulk体积求反应速率。反应化学计量源加入Rates.reaction_species_mol_s，额外cell_power_w保持0；形成能已在每相储能中，禁止再加一次反应热。Ns变化后下一trial重新计算固体占积和总U温压闭合。

事前门槛：每反应/每accepted prefix元素及总质量误差≤1e-10相应mol/kg量级（另保留实际scale）；封闭总U误差≤1e-6J，库存全部非负。需氧通道在O2=0时严格0，独立无氧通道继续；有限O2消耗不得超量或clip。可分辨温变必须以最终inverse.temperature_error_bound_k组成区间，与初始温度分离；不能仅比较名义浮点T。测试使用明确制造单相caloric/生成能/反应系数，不冒称污泥反应或材料放热实测。

反应输出应保留完整diagnostics/source/classification；动态炉温、水相变及液迁移外层evaluation链必须继续保留原反应诊断。制造反应输入应传到两wrapper授权门禁。

## 接口与守恒语义

可选 `SolidFluidHeat.solid_reactions` 接受精确SolidReactionConfig，配置storages与host逐对象绑定、layout值一致，来源和制造资格传到host及两wrapper。默认None保留既有行为。每次只有一次总U/currentN解码，以每格完整库存、实际decoded T及storage.bulk求reaction源，`reaction_cells` 在evaluation全部旧字段末尾追加。程序边界、水相变和液迁移保留同一diagnostic链；水相变在已有reaction矩阵上加等mol源，没有覆盖固体反应。

这是连续净源ODE：瞬时rate由当前真实反应物库存决定，积分器每stage检查库存正性与误差；未调用旧 `amounts_after_extents`，因此不声称旧gross-step消耗门禁已生效。配平的形成/消耗循环不被禁止，循环/刚性/中间体准确性仍需独立收敛研究。本次有限氧上界验证专门使用无产氧通道的网络。

Ns改变后下一trial照常算Vs与实际孔容，形成能已存在U，不添加反应热cell_power。正活化能使用实际decoded T，动力学温域退出为DomainExit，身份或不可表示数值错误保持IntegrationError路径。动态程序节点仍显式传给integrate。

## 实际制造验证

新增fixture为制造feed(C固相)→char(C固相)与char+O2→CO2气相；两固相采用不同生成能/摩尔体积，气相O2/CO2也为明确制造caloric，不声称实际碳材料或污泥动力学。保留不参与反应的真实水源及载气。该例只验证库存—生成能—体积耦合。

先写配置拒绝测试时发生未知solid_reactions参数RED。完整组装首跑还发现两条制造速率错误共用candidate_id而参数不同，原网络正确拒绝；修为两个显式ID，未改网络门禁。初6项通过2.43s后，独立审核指出新evaluation字段插入旧位置参数中间；添加旧8位置参数回归明确RED。另补动力学温域分类RED。将reaction_cells移动至全部旧字段后、明确动力学域退出后，最终命令：

```
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_reactive_solid_fluid_heat.py -q
```

8 passed in2.43s。包括：无氧时氧化瞬时速率严格0但无氧feed通道继续；有限氧0.0001mol的实际0.1s封闭积分，各accepted prefix元素/质量/U/非负库存与上界检查；feed一阶解析 `N=N0 exp(−0.1t)`；最终T减去inverse误差界仍大于初始300K，Vs变化；正Ea12000 J/mol的300/305K两实际解码速率比与Arrhenius独立指数一致（相对1e-12）；全program→water→liquid→solid reaction诊断/source累加链；仅reaction制造分类控制/去配置负对照；旧位置参数和域分类。

本次没有耗尽至数学上精确零的氧化轨迹（正阶ODE一般渐近耗尽）。实际有限氧轨迹验证不超初始供给，零氧停止另由精确零库存状态验证。制造分类控制仅检查gate，不将重新标记的合成系数冒称为实材数据。
