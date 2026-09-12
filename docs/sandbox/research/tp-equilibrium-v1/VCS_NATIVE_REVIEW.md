# VCS 四点保存结果独审

**PASS：新 VCS 四点按原计划完成，独立被动审查 81 组检查与 608 项标准物性比较全部通过。** 审查仅用 JSON、Fraction 和保存的浮点物性，零 EOS/新求解/测试重跑；原 Gibbs 首点失败仍原样保留。

| 实际点 | 求解秒 | 最大末态元素残差 / mol | 同池归一化 G gap | C(gr) / mol |
|---|---:|---:|---:|---:|
| 1000 K / element_basis | 4.763008417 | 3.46054e−16 | 2.50858e−9 | 0.513505194 |
| 1000 K / methane_shift | 4.239975458 | 3.76910e−16 | 2.64060e−9 | 0.513505194 |
| 800 K / element_basis | 4.256576292 | 1.68458e−16 | 6.39663e−10 | 0.697117908 |
| 1200 K / element_basis | 4.248192917 | 3.05245e−16 | 8.25917e−12 | 0.406064217 |

逐点初/末态以实际 kmol 的精确二进制值乘1000，重算五元素及请求池残差；原元素门全部满足。读取 λ 后重新计算全部候选 partition、同池 G/下界/gap，以及请求池下界和 `λ·residual−RTδΣresidual`，与原保存值精确一致。原归一化 gap 范围 [−1e−10,1e−7]、活动化学势、石墨条件、G下降及 H−G=TS 账均保持；没有另拟合元素势或再求平衡。

初末态19种×4标准物性×4点与冻结 REFERENCE 同温分段比较，共608项全部通过，重算记录与 SERIES 逐项一致。最大无量纲差2.84217094e−14，未改原 `2e−10+5e−12|ref|` 门。实际加载物种/系数/1bar参考、初态 seed 投影、源包及实际提供者身份相符。

1000 K 两初猜的19物种比较全过：最大差3.57908690e−11 mol；G差1.58604536e−10 J，原门0.00275208713 J。两初猜、四点顺序和唯一四次调用符合冻结 driver；每点记录3次 factory/prepare/equilibrate 包装器返回，这不是内部多项式调用计数。

实际 solver=vcs，policy V2 仍明确 requested rtol=1e−10 未被 VCS TP bridge 消费，内置 major/minor 与 secondary 容差分别另存；原外部接受门未放宽。完整请求源模型、源 SHA、源码 `da382eea…14849c`、CLI `5553a152…910f82` 和安装187文件/180模块一致，20项安装回归记录通过。监督1218输入 before/after/当前 SHA 全等，driver17.587847250 s、监督22.660594208 s，原10/40/50+5秒门未变；exit0，leader已回收。

证据：`VCS_NATIVE_AUDIT01.json`、`VCS_NATIVE_AUDIT01.log` 与 `audit_vcs_native01.py`；本次首轮被动审核通过。旧 `root-execution/native01` 单点五元素失败、SERIES、监督记录对照上一冻结均未变。不得把这次 VCS 成功覆盖为旧计划成功。

本证据仅支持800/1000/1200 K、1bar、指定虚拟CHONS池及19候选的名义封闭TP平衡。表中石墨是该条件模型输出，不是原泥实际焦炭产率；不能推出材料资格、反应动力学、热负荷、TG拟合或烧结全周期。unknown、material_qualified=false、training_eligible=false保持。

## Review Summary

| Severity | New findings | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: PASS — 新限定四点验收已独立核实；整体 Goal 与材料验证仍未完成。
