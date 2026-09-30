# 全流程近似模型：离线使用与结果解释

当前权威状态（2026-09-30T23:11:44.927781+00:00）：P19/P20已完成来源纯黏度改进及当前三档物理数值验收，**P21当前核三方案分布与排名稳健性仍未完成，整个模型不能判完成**。原8组配对×3=24次设计与禁止重启旧24批次存在授权冲突；前述预算决定仍待用户明确答复，尚未启动任何当前核UQ。

根现317参数：86 literature / 231 assumed / 0 measured。来源μ(T)及同温度Wilke已接入原共享Darcy通量，未新增储能或热源。81项质量/元素/完整能量最大残差0.05451679%，108项气体预算0.04842094%，四项要求最大加密差0.13112792%、附加压差0.36178638%，均通过原门槛；批次墙钟442.228086s，无重跑。名义干燥余水0.13602835%仍高于0.1%，工艺失败保留。

水黏度超过1173.15K推荐上限的面采样1198/1198/2398个，Calcite热容超过1200K亦保留assumed外推。数值负小库存/熵量未裁剪；目标材料及产品代理精度待实测。P20同场九类映射/Python前向与CLI导入通过；P18固定方案及合成恢复属于旧黏度核，不能自动升级为新核分布或拟合证据。详见FULL_CYCLE_P20_SOURCE_VISCOSITY_RESULTS.json/.md及FULL_CYCLE_P21_UQ_BUDGET.json/.md。

P18两个增量实际云字节恢复已由协调会话完成并读回收据；本次P19/P20增量尚按独立交付收据推进。全部历史/独有Git/离线环境恢复及20GB目标仍未完成。下方P01–P18“完成”结论均为历史阶段记录，当前判断以本段和FINAL_ACCEPTANCE.current_acceptance_matrix为准。

当前Python只存汇总入口见`runs/full-cycle/p20-source-viscosity/cycle-worker.py`；`report.viscosity_source_domains`列实际Darcy面温度的来源域统计。名义alpha1读取根公开μ0公式，alpha0仅原幂律显式对照。所有系数预存在根文件，前向不导入iapws或沙盒，不下载来源数据。已有CLI --compare将触发24个完整周期，P21预算未明确前不得据示例自行运行。以下旧次数属于各自历史核。


## P16–P18历史入口和运行证据

P16–P18版本当时完成了必要运行验证，详见FULL_CYCLE_CURRENT_MODEL.md；下方P06–P11的次数/版本为历史记录。当前根304条参数（70literature/234assumed/0measured），六种纯物质背景Cp使用根caloric_background的公开五项式，h/s、总容量与面携焓一致；report.caloric_source_domains记录采样温区及来源域外次数，域外延拓仍assumed。

最新实际离线CLI命令与exit0、10次真实前向收据在runs/full-cycle/p18-current/recovery/execution.json，必要摘要已纳入FULL_CYCLE_P18_CURRENT_VALIDATION.json。派生window.parameters.json只含drying_ramp+drying，根配置没有被拟合写回。九类观测已在P16同一当前轨迹上读取，非重新完成九条实测曲线校准。新名义干燥0.13602805%>0.1%，合成窗口通过不能改判。旧--compare的24次UQ及旧三参数/双参数恢复没有在新热容核上重启，其历史结果不自动验证新核全部假设。

只保存必要汇总的当前原方案Python调用示例及实际运行包装器在runs/full-cycle/p18-current/scenario-worker.py；最终报告含完整质量/元素/能量和四气体预算，无原始场。使用现有CLI前应按所选选项阅读下方输出行为。

P11已完成可运行与检查的接口及未来实测校准入口；这不是整个模型停止条件。当前按物理化学定律及公开论文/数据继续开发，缺少目标材料数据不阻塞独立验证；原名义干燥失败和真实预测限制见下文。P11实际完成58项纯数据回归、CLI负例和help启动验证；本次没有重新积分或拟合。

项目保留在 `/Users/wanggaoying/Research/brickmodel-github`。统一输入是根目录 `parameters.full_cycle.json`；采用明确的一维半厚度、假设材料和给定炉温/窑气外库。模型用于研究近似和条件化比较，材料适用性、强度/吸水/缺陷代理与现实对照待实测。

## 已有环境与入口

本轮实际读取的环境为 Python 3.12.13、NumPy 2.5.2、SciPy 1.18.1，与 pyproject.toml 的前向依赖一致。求解过程使用本地 Python/依赖/源代码，无在线 API、运行时下载、CDN 或远程字体。当前 .venv 的 Python 指向本机 uv 安装位置；代码备份不是完整可搬迁的 Python/依赖安装包。新离线主机需部署前备齐 pyproject.toml 声明的依赖与源码。当前 .venv 未安装 sludge_vme 包，因此源码入口显式加入 src；不要求联网安装项目。

在项目根目录运行现有 CLI：

```sh
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-run
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-acceptance --acceptance
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-comparison --compare
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-calibration --synthetic-calibration
.venv/bin/python examples/run_full_cycle.py parameters.full_cycle.json --out runs/full-cycle/your-measured-fit --calibrate path/to/observations.json
```

以上是可选操作，不能为接续工作全部重跑。普通前向和 `--acceptance` 会按既有行为写 fields.json；本轮工作只保留汇总，采用下方 Python 入口在内存中消费原始场。原始场不得入 Git。不要覆盖已有运行目录。`--compare` 与 `--synthetic-calibration` 按既有入口只保存汇总和合成观测/派生参数。

退出状态须与结果一起读：普通前向和 `--compare` 的成功只表示各自物理核算通过；合成恢复的成功表示指定恢复条件通过；这些不要求名义干燥达标。`--acceptance` 还要求三档物理、一次时间/网格比较和工艺端点全部通过，原名义干燥失败将使总体结果为 false。退出码0不能单独证明整个模型或真实工艺完成。

## Python：只保留必要汇总

```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'src'))
from sludge_vme.models.full_cycle import read_parameters, run_cycle, write_json

config = read_parameters('parameters.full_cycle.json')
report, fields = run_cycle(config)
write_json(Path('runs/full-cycle/your-run/summary.json'), report)
# 在内存中使用 fields 后释放；不将原始场写入 Git。
del fields
```

`read_parameters` 检查根参数条目、来源、单位、范围和身份。每个重要材料/工艺/数值参数均来自该文件；不使用环境变量注入。`changed(config, overrides)` 是已有显式派生工具，不改原配置；派生计算不能冒充名义结果。加密的分母尺度读取 `acceptance.floor.*`，不重新选择容差或放宽门槛。

`report['gas_ledger_endpoint_totals']` 保存当前配置窗口初始和每个阶段末端的全域孔气库存、累计净反应进度及边界进出。`report['gas_species_ledger']` 给出 O2/N2/H2O/CO2 的窗口总账与分段账。whole_cycle 键在截断配置中仅表示该配置窗口，读取 scope 一起判断，不把两段干燥写成八段全周期。

气体残差为末库存减初库存、减反应净源、减边界进入、加边界流出。预算归一化与相对全窗口初始库存归一化分别列示；后者不是通过判据。保留带符号净反应、近零负边界增量和原始残差。端点闭合不证明每个中间时刻或每个单元均闭合；不能替代原质量/元素/完整能量账本。

## 观测与反演

既有接口 `sludge_vme.inverse.full_cycle.map_observations(config, observations, report, fields)` 在同一解上映射观测，不重新积分；`predict` 会先求解一次；`fit` 接受指定参数和标记来源的数据；`joint_drying_synthetic_demo` 使用根预先声明的双参数/双通道干燥设计。

| kind | 单位 | 模型定义与解释 |
|---|---|---|
| tg | 1 | 凝聚质量/初始干质量，不等同纯水分 |
| dsc | W/kg | 有限孔气模式的净热边界功率/初始干质量，非仪器专属响应 |
| dilatometry | 1 | 厚度相对初始值的变化，包含当前热弹性与永久应变 |
| kiln | K | 根工艺给定炉温 |
| liquid_water | kg/kg | 全域液水质量/初始干质量，不含孔汽、矿物结合氢或额外虚构结合水库存 |
| surface_temperature | K | 模型外边界温度，区别于炉温和最外格中心温度 |
| absorption | kg/kg | 冷却产品吸水代理，待实测 |
| strength | Pa | 冷却产品强度代理，待实测 |
| defects | 1 | 冷却产品缺陷代理，待实测 |

曲线观测逐行使用 `kind`、`time_s`、`value`、`unit`、`scale`，产品观测不需要时刻。时间为当前窗口起点起的秒；时间插值采用既有线性插值。拟合数据集还必须提供 `measurement_kind`（synthetic 或 measured）、`source`、`fit_parameters`。`scale` 是残差归一化尺度，不自动等于测量标准差。

完整周期7类合成设计与2通道干燥设计是两个独立演示；干燥窗口不得使用冷却产品输出证明产品资格。无噪声同模型恢复只检验指定条件下参数恢复及接口；局部Jacobian秩不能证明全局唯一、抗噪或实材辨识。合成拟合仍为 assumed / synthetic_fitted，派生 fitted.parameters.json 不写回根名义值。

## 追溯与未通过项

最终运行、物理/数值验收、工艺失败、待实测、Git和备份分别见 `FULL_CYCLE_DEVELOPMENT_PLAN.md`、`FULL_CYCLE_REPORT.md` 以及最终验收矩阵。历史 d8bc6f1b 三档证据保留在 `FULL_CYCLE_PORE_GAS_RESULTS.json`；只有确认主机/根物理参数未变后，才可在原范围复用。

旧 UQ 的渗透率固定为3.75e-14 m²，最终比较继续固定该值以及已声明固定系数。新的比较不会覆盖所有271参数的范围，不能写成全面不确定性验证。原名义干燥余水0.13505646%高于0.1%门槛；关闭结合能、历史延时、合成真值或拟合结果不得替代此失败。历史两次广渗透率成本失败与干燥两次有界处理均不重启。

## 本轮已实际执行的入口

完整周期 `sludge_vme.cli.main` 的 `full-cycle --synthetic-calibration` 分支已返回0，实际22前向；随后 `joint_drying_synthetic_demo` Python入口实际17窗口前向，包装进程exit0。源入口 `.venv/bin/python examples/run_full_cycle.py --help` 也已返回0，仅用于启动验证。其余上列命令是已有可选操作，不声称本轮全部执行。

运行器、根参数快照、逐次执行记录位于 `runs/full-cycle/final-inverse-20260930/`，必要汇总见 `FULL_CYCLE_FINAL_INVERSE_READBACK.json`。原记录中的 `gas_ledger_present=False` 是运行器查错report层级，不能用于判定账本存在；账本本体及P01/P05证据以顶层 `report['gas_species_ledger']` 为准。

## 干燥判据的三个分母（P09澄清）

`example_endpoints.drying_remaining_fraction`取最湿单元在drying末的液水/同单元t=0初水。0.1%门槛不是干基0.1%；对应干基门槛为根门槛乘`material.water_dry_ratio`。当前0.13505646%剩余初水相当于约0.02025847%干基，仍高于原等效0.015%干基门槛，不因换单位改判。

恒温drying账本初水在drying_ramp末（当前14400s），冻结根`n_eq_over_n0`分母却是当前drying末的液水（86400s）。两者均不可直接当t=0初水分母；P09报告已统一到初水后比较。冻结根/单次细化/端点余额各有独立适用范围，详见FULL_CYCLE_P09_DRYING_ATTRIBUTION.md。

## 反演输出留存（P10）

既有CLI合成/标定命令和三个Python合成入口保持调用方式。完整合成的synthetic.observations.json新增truth_audit；两个窗口的truth_window_audit追加顶层气体账本与实际阶段范围。calibration.json保留原forward_*字段，并新增forward_gas_species_ledger及可用性诊断；窗口仍用forward_window_balance。

后续外部记录包装使用sludge_vme.inverse.full_cycle.forward_call_summary(report)，需要必要预算则使用forward_audit(report)；两者不积分。gas_ledger_status=present仅表示数据存在，missing对应明确诊断及审计中的null，不能据普通物理通过推断气体账本通过。缺少必需普通预算字段时直接报错。

runs/full-cycle/final-inverse-20260930/entrypoint.py和原39次记录为历史快照，保留错误字段，不作新运行维护入口。旧完整真值预算未保存且不可从摘要恢复；新版留存只作用于后续真实调用。详见FULL_CYCLE_P10_INVERSE_EVIDENCE.md。

## 未来实测数据的最小接入（P11）

填写起点见 [`examples/full_cycle_observations.template.json`](../examples/full_cycle_observations.template.json)，只包含 `liquid_water` 与 `surface_temperature` 两种观测的占位行。复制到新的数据文件后，按实际采样增加行。模板身份为 `template`，来源、值、时间、材料/配方/批次、几何及边界条件未知项均为 `null`，`fit_parameters` 为空；它不是实测数据，也不能直接传给准备或拟合入口。两种通道不保证任意参数组合可辨识。

根 `observation_contract.target` 当前未知不阻塞已有前向或合成计算。实测拟合前，需根据原始记录明确目标材料及条件，并在统一根配置与输入数据中如实声明；声明相符只表示准入条件相符，不证明材料有效性或实验真实。

1. 填写数据集 `source`、逐行 `source_id` / `source_locator`，以及身份与条件相容性的 `identity_source` / `compatibility_source`。真实原始实验才可用 `measurement_kind="measured"`、`source_kind="raw_experiment"`；论文表格或曲线数字化使用 `reference` 与 `paper_table` / `digitized_curve`，不能仅凭材料名称相似改称目标实测。
2. 从实验记录填写材料、配方、批次、几何、初态与边界程序。`conditions.configuration` 采用 `configured_conditions(config)` 返回的阶段列表与参数 value/unit 结构；该函数只是**配置快照**，不是实测条件或相容性证据。应逐项对照有来源的实验条件并处理差异，不能盲目复制快照制造匹配。不同批次、主干燥与后续调湿记录分别处理。
3. 每行据原记录填写测量方式 `acquisition`、阶段 `segment`、值、时间及来源。模板预列的量、位置、基准和单位是目标语义，不证明实验采用了该定义。两类主干燥观测需对应 `in_situ` / `main_drying`。`time` 包含数值、单位、原点、到过程起点的偏移秒数与来源；映射为 `time_s = elapsed_seconds + offset_to_process_start_s`。原点为 `process_start` 时偏移必须为零，不能凭猜测对齐。
4. 显式填写正的 `scale`、目标单位 `scale_unit` 与 `scale_source`。水分的目标单位是 kg/kg，表面温度是 K；即使原温度以 degC 输入，scale 仍按目标单位声明。scale 是残差归一化尺度，不自动解释为测量标准差 sigma，接口不替你传播不确定度。按研究问题选择根中有非零范围的 `fit_parameters`；已声明固定的几何、初态、配方和边界条件不能同时拟合。

水分的分母必须明确：模型 `liquid_water` 是液水/初始干质量。当前干基、湿基以及 MR 不能直接填入该值；当前干基或湿基转换需同源且有身份记录的当前干质量/初始干质量因子。MR 只接受明确的 `water_over_initial_water` 公式及有来源的初水/初始干质量分母，不能借用根名义初水，也不能猜测包含平衡水分扣除的 MR。百分数须依据原记录显式换成比例，接口不自动猜测。最小模板采用初始干基，不含这些可选转换项。

坯体内部温度不是 `surface_temperature` 的别名；炉温对应 `kiln`。烧后吸水率也不是干燥液水的别名：它对应独立 `absorption` 产品观测及烧后干质量基准，模型端仍为待实测代理。未知位置、干燥后的再调湿、称量方式与模型采集语义不符时，应保留差异，不能改标签制造符合。

填好记录后可先做纯数据准备。下例仅供后续使用，本轮未执行；`prepare_dataset` 不调用前向、优化或求根，积分次数为零：

```python
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'src'))
from sludge_vme.models.full_cycle import read_parameters
from sludge_vme.inverse.observations import prepare_dataset

config = read_parameters('parameters.full_cycle.json')
dataset = json.loads(Path('path/to/observations.json').read_text())
prepared = prepare_dataset(config, dataset, for_calibration=False)
print(prepared['admission'])  # 映射和声明问题；不是拟合成功或材料资格。
# 只有拟用于目标标定的完整记录才作以下准入检查；仍然零积分。
admitted = prepare_dataset(config, dataset, for_calibration=True)
```

`for_calibration=False` 可用于字段完整的文献 reference 映射，保留原行及转换说明；不能补齐未知测量值或修复来源缺失。文献 reference 不进入目标实测拟合。`for_calibration=True` 会检查身份、目标/输入条件、观测语义、窗口及拟合参数，失败直接报错。`fit` 及上方既有 CLI `--calibrate` 路径都会在优化和前向前调用该准入检查，用户不必靠手工预检查才能阻止不合格输入。准入通过后执行拟合才会发生新积分；本轮不执行该步骤。

输入已由 `prepare_dataset` 归一后也可传给 `fit`；二次准备始终重新读取 `mapping.original`，不会把转换后的初始干基当成新的实测原值而丢掉假设分母限制。要更正数据，应修改原始输入再准备。文献烘干参考质量另用 `basis="dry_reference_mass"` 和显式 `dry_reference_over_initial_dry`，不能悄悄等同当前或初始干质量。所有转换因子/MR分母必须带 `status`；要用于目标实测拟合，还须是 `measured`，并在因子的 `material` 中给出与数据集一致的 material_id/recipe_id/batch_id。非实测因子仍只能参考。
