# 保存面短时生产运行入口

`scripts/run_saved_reference_transient.py` 读取冻结源码、完整case和必要路径，直接调用既有 `model.integrate()`。预算在根合同，外部既有固定deadline监督回收；正常solver与native summary真实调用计数，不增加独立RHS/Jac/本构算子、搜索或拟合。

case按既有P46/P44物理合同、P49保存13格mode3和baseline max_step/rtol/atol完整条目构造，启动前冻结。observer读取原summary返回locals及原热导函数return，保留内面与边界、gas/water outward和heat into-left/into-brick的带符号值，C采样保持0。没有新阈值、分母或物性。

P51唯一实际attempt在最终JSON序列化失败，数值未落盘，原失败证据永久保留。当前源将既有 `plain(result)` 放到文件及stdout输出之前；独立P52唯一实际attempt已成功写出两者。P52 live合同为 `public_reference_cases.saved_reference_transient_json_recovery`；只有冻结snapshot做行政alias供原selector读取，原live P51失败合同不变。旧raw schema中的P51仅为复用格式名。

P52原质量/元素/完整U、四gas及native累计熵判据通过限定0..10s；CaO预算0仍relative=null/passedfalse，整相不PASS。严格非负只覆盖21保存时刻，原生signed面输运不等于空间准确性；完整独立累计熵storage/production/exchange序列未保存，不能独立重放。两个科学窗口均关闭，本文不构成再次运行许可。详细事实与范围见 `docs/FULL_CYCLE_P51_SAVED_REFERENCE_TRANSIENT.json/.md` 与 `docs/FULL_CYCLE_P52_SAVED_REFERENCE_TRANSIENT.json/.md`，当前全模型仍未完成。

P53独立合同 `saved_reference_time_refinement` 复用同一已修producer与P52实际冻结源，只应用根完整0.05s max_step记录。同13格10s一次实际运行成功，四原时间指标采用细化分母和既定floor通过；其结果不授空间、独立势导数、八阶段或整模型。P52基准原文件只读、没有重跑/整份复制。0.05s预算窗口已关闭，不构成再次运行许可；详情 `docs/FULL_CYCLE_P53_TIME_REFINEMENT.json/.md`，交付 `runs/full-cycle/p53-saved-reference-time-refinement-final-delivery-state.json`。

P54 `saved_reference_space_refinement`/`saved_reference_space_partition` 仅在新snapshot行政alias供原producer与geometry selector读取。现有直接case入口执行26格原生初态及10s/.05前向，原13faces区间二分，实际13vs26原四空间指标通过，fine26时间与全周期仍未资格；窗口关闭。详情 `docs/FULL_CYCLE_P54_SPACE_REFINEMENT.json/.md` 与 `runs/full-cycle/p54-saved-reference-space-refinement-final-delivery-state.json`，P53真实基准只读不重跑/整份复制，原失败保持。

P55 `saved_reference_26cell_time_refinement`：复用P54实际26格27面case，仅完整max_step=.025s记录最后替换；一次10s原生前向，四原时间指标通过。P54基准只读不重跑或整份复制，原源保持，窗口关闭；一般空间/全状态/八阶段/整个模型未资格。详情 `docs/FULL_CYCLE_P55_26CELL_TIME_REFINEMENT.json` 和 `runs/full-cycle/p55-saved-reference-26cell-time-refinement-final-delivery-state.json`。

P56独立离线观察入口 `scripts/run_calcium_energy_observation.py` 读取P56 root-snapshot，原P4512格declared_zero旧/新各一次RHS并记录原操作值。2ctor/2RHS、0ODE，原U向量FAIL重现且归因已保存；不是动态入口或独立势导数验收。详见 `docs/FULL_CYCLE_P56_ENERGY_OPERATION_OBSERVATION.json`、`runs/full-cycle/p56-calcium-energy-operation-observation-final-delivery-state.json`。

P57同一离线入口 `scripts/run_saved_reference_transient.py` 使用 `runs/full-cycle/p57-low-temperature-60s-transient/root-snapshot.json` 与项目根，真实26格27面/0..60s/121样本、1ODE已执行。仅case最后完整time_scale6，计数扩原生Pythonframe；旧P51 schema为历史格式。限定验收见 `docs/FULL_CYCLE_P57_LOW_TEMPERATURE_60S.json`，交付读 `runs/full-cycle/p57-low-temperature-60s-transient-final-delivery-state.json`；60s未时空加密，不能用10s资格外推。

P58同入口/冻结原producer，`runs/full-cycle/p58-low-temperature-60s-time-refinement/root-snapshot.json`；同26cells27faces/60s/time_scale6/121点，仅case最后max_step.0125；真实一次ODE及原四time判据通过。基线只读并计科学字节，CaOnullfalse，未授空间/全模型；详见 `docs/FULL_CYCLE_P58_60S_TIME_REFINEMENT.json`、`docs/FULL_CYCLE_CORE_DEVELOPMENT_ASSESSMENT.md` 与 `runs/full-cycle/p58-low-temperature-60s-time-refinement-final-delivery-state.json`。
