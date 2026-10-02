# P59 原生signed S生产输出与离线重算

P59 原生完整signed S输出/replay已静态实现（2026-10-02T20:50:29.822311+00:00），尚未生产执行或replay，0constructor/RHS/Jac/ODE/physicaloperator/fit/UQ/search。共享gas summary复用已有completeS及原生累计末两槽，无新状态/热源/物性/采样rate求积；按各区间起点分别作差，保存signed/abs/relative/原尺度和阈值完整record，旧native熵误差/flags不改。直接文件stdlib重算只读必需新字段，P57/P58缺序列不回填；package -m会导入模型，不作为此纯入口。原escale仅初凝聚相参考Cp尺度，不含孔气Cp。根681=144literature537assumed0measured，旧669完整records/所有旧live合同/名义配置保持；新增12为未分配两stage边界记录，无材料物性增加。两互异stage end5/10×time_scale6→实际0–30/30–60，原T/gas/geometry/tols/step/domain/原生初态保持；未来1ctor/1integrate/2solve_ivp(中点restartBDF)，900s/12MiB仅提案，完整manifest估算另列，不能提前运行或称非零起点已验证。当前矩阵directcycle absent/P41非均匀未实现已精准归历史，生产能力/元数据/材料/待执行验收分层；观察候选不导入，inverse/UQ Ca留存未改。P58最终158必要路径12922129B>12582912B超339217B，预检及actual资源均FAIL/partial；旧数值PASS不追认。P34/P40/P44/P45/P50撤回/P51失败、名义余水0.135892078740%>0.1%、CaO零预算nullfalse及wholefalse全部保留。科学、静态实现、工艺、材料、Git/Drivemetadata/实际恢复/历史容量分别判断。

## 接口与来源

`FiniteGasFullCycle.summarize` 把本次同一汇总循环已有completeS、原末两累计槽分别按`q*escale/Tr`缩放的Ip/Ie、原始无量纲槽和已知times/endpoints传给`entropy_ledger_report`。原完整S包含凝聚相、孔气混合、持水及骨架/相态存储；不再调用thermo/rates。气体/热弹性共享父summary，因此现CLI/Python全report共用字段。旧专用saved producer合同不改；未来提案的summary_report_keys显式选择新增字段，不把旧过滤输出称已有新字段。gas.storage=0历史FullCycle不属于此次有限气体输出合同。

字段`report.entropy_ledger`使用根`entropy_ledger_output.report_schema`。`series`保存时间、complete_stored_entropy_j_k、cumulative_entropy_production_j_k、cumulative_entropy_exchange_j_k、原两槽；`intervals`显式保存whole与每stage首尾index；`normalization`保存实际escale/Tr及原reference.temperature/acceptance.entropy_relative完整records。全窗口是声明的窗口，省略原阶段不会变成原八段。

每区间包含首尾和全部保存点，`deltaS=S[k]-S[i]`、`deltaIp=Ip[k]-Ip[i]`、`deltaIe=Ie[k]-Ie[i]`，严格left-associated`R=(deltaS-deltaIp)-deltaIe`。负交换/负原始增量原样保留；absolute只用于单独abs/relative，归一化无floor。分别缩放后作差可能与旧两槽先求和/乘/除存在舍入差，旧nativeentropy_error/通过字段原表达式不改。新ledger只是保存同源收支，不授独立势导数、独立熵产分支累计或连续/BDF内部资格。

## 标准库离线入口（尚未执行）

新函数`replay_saved_entropy_file`必须显式指定JSON层级；从三条物理保存序列重新计算各区间增量/残差/原尺度relative，不拷贝旧passed。读取原两槽但不独立重算其缩放，此范围不是坐标转换复核。缺字段按必需合同自然KeyError，无历史回填/默认/重试。

```sh
python src/sludge_vme/entropy_ledger.py path/to/summary.json --ledger-path entropy_ledger --out path/to/entropy-replay.json
python src/sludge_vme/entropy_ledger.py path/to/saved-result.json --ledger-path report entropy_ledger --out path/to/entropy-replay.json
```

必须用上述直接文件入口以避开包__init__的model导入。Python调用可用标准库`runpy.run_path`加载此文件（非`__main__`）取得函数，避免包导入链；同样尚未执行。本轮只有AST/声明JSON静态读取，没有生产新数组、调用helper/replay或造数据验证。P57/P58未存完整序列，目前不能回放。

## 两阶段提案与决策

提案完整case在`runs/full-cycle/p59-native-signed-entropy-static/proposal-case.json`；stage命名为direct_transient_first/direct_transient_second，end为未scale的累计5/10s，temperature/gas来自P58完整records。实际0–30/30–60，30s保留所有state与累计ledger但重启BDF，因此不能宣称原P58轨迹逐值不变。严格同26cell27face/mode3/Ca1、298.15K、原gas/P、.0125/.5/rtol/atol/time_scale6与合成directL温域。第二段Ip/Ie真实非零值只能未来执行后读取，本轮没有该证据。

未来候选1job/worker/attempt/constructor、1continuousintegrate/2solve_ivp，900s唯一childlaunch→import/read/ctor/两段/summary/JSON/reap，完整必要≤12MiB仅建议未分配。必要依赖清单和保守估算单独文件；超额即停在决策前，无减少历史原件/改变阈值/借用P58预算。该科学目的只验新原生S及区间非零起点/replay；随后回最新核原八段受影响验收，不进入新的synthetic延时或精度搜索循环。

## 静态审阅及历史资格

三修改源码AST可解析；既有gas除summary外全部method AST和旧diagnostic函数保留，原entropy_error/relative表达式保留。独立只读审阅已发现并更正escale来源文字，没有修改其计算值。当前specific_gaps中的directcycle absent和P41分区未实现归入精准历史字段，既有direct/extent/per-cell/mode3实现与未执行八阶段验收分别列。独立观察模块候选未应用，portlandite/实际stage条件投影及inverse/UQ Ca留存仍独立缺口。

P58全部158路径12922129B越额、事前漏项和唯一51.007s科学已消费保留；不重写任何P58预算/资格/数值结果。旧phase、mesh、CaO、P45和serialization失败、工艺余水、0实测及wholefalse保持。普通Git/Drive增量metadata、实际字节恢复和历史容量分列终态收据。

未来提案manifest snapshot：准备输入5540860B +虚拟Gitblob132329B +新不同路径冻结副本1571510B +结果/程序/行政完整reserve4849664B = 12094363B；建议上限12582912B。本manifest和最终本轮receipt/live增长纳入未来最后重stat，非事前完整清单已通过或预算授予。本轮未创建future_directory/launcher/实际数组/replay。最终P58交付口径15unionpaths/3own增量，较早12/1文本已标历史。
