# 全流程近似模型：离线使用与结果解释

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
