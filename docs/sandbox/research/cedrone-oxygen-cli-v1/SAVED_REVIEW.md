# 公开有限氧 CLI：实际保存结果独立复核

**PASS：28组独立保存检查及152项原 NASA 无量纲比较全部通过。** 只读 JSON/Fraction、实际保存浮点和旧 profile；0 Element/EOS/平衡调用，未重跑测试或旧 native。

本次唯一 λ=1/4 调用已完成并回收。精确读取原表 m、实际 Element A，再重算原 b、D、外加 O/N 和完整质量；与旧同条件请求、policy、基准及来源一致。同次初末相 A 与五个独立 Element 的 binary64 精确表示对应，派生阶段 false、实际核验后 true 的绑定标记正确。

完整 TPResult 对照共检查 2076 个标量；所有物理对象、初末19库存、loaded_definition、h/s/Cp/g/μ、G和全部后验诊断均逐值相同，浮点用 hex 比较。唯一7处差异是 elapsed、两处 construction_timings_s、4处新增 serializer 身份字段，完整路径留在 SAVED_AUDIT01.json。原元素/G门和名义库存/G对照门均保持；152项独立800 K NASA比较最大差 2.84217094304e-14，仍用原2e−10+5e−12|ref|门。

19项绝对 mol、模型 kg、气相分数、C分配及精确质量恒等式重算通过：输入 1.958403141983712 kg，C(gr) 0.1811913384094621 kg；质量残差 2.58311735497e-16 kg，原元素门传播界 2.03348814198e-10 kg，scaled gap 6.0195142834e-10。仍以原1 kg报告样本为基准，不是实际char/燃尽或完整泥料热量模型。

监督声明的4个输入前后及当前一致，单个固定 -I worker、最终1 attempt、exit0、leader_reaped及无signal_errors均成立；仅原进程组范围。实际core/helper SHA与已审候选、已安装文件及当前源码一致；安装记录188文件/181模块逐项同字节，34项安装测试（含当前10项入口测试）0失败/错误/跳过，日志0.22 s。未重查旧安装的1218输入，也未把合法新安装误报旧运行漂移；原有限氧接受记录SHA保持。

成本：模块 4.759636083 s、worker 4.870027833 s、监督 9.920950916 s，原10/30/40+5门保持。serialize 0.012685667 s、gas构造 2.609732292 s、graphite构造 2.125998500 s、Mixture/初态 0.001192250 s。旧保存profile prepare 4.727445000 s、旧模块 4.776495583 s（带profile），新模块不带profile：**没有明显改善，不能称加速成功**。这不否定新表示法、分阶段计时与公开 Element→相绑定路径的实际验收通过。

资格继续 material_qualified=false、training_eligible=false；矿物分配、严格干基、源误差、有限时间动力学和供热基准仍未知/未完成。不授予材料、性能统计或完整Goal资格。

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 本次唯一公开CLI保存结果可归档；无加速成功结论。
