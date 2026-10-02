# 保存面主机的瞬时离线诊断入口

`sludge_vme.models.instantaneous_diagnostics.saved_reference_host_case(root)` 复制根合同所选物理案例的完整参数记录，随后使用 P49 保存面case。`observe_initial_rhs(case, events_path=..., retained_failures=...)` 构造一个主机，在真实初态和 `model.times[0]` 上调用一次原RHS，观测原调用返回及共享面，保存带符号的库存、尺度、导数、质量/元素/完整U/S和严格分项。它不积分，也不额外调用rate/thermo/summarize。

源代码入口为 `scripts/diagnose_saved_reference_host.py`，根合同 `public_reference_cases.saved_reference_host` 给出物理/几何案例和必要输出路径，`validation.saved_reference_host.*` 给出统一作业、时间和字节预算。既有源目录bootstrap避免本机旧editable pth指向Desktop；不联网、不改venv。P50的已执行窗口已经关闭；此文档不是重跑授权或新的预算。

既有 `validation.hydroxide.identity_tolerance` 只用于声明的瞬时导数/闭合判据，完整周期和加密的根判据保留为未资格。Ca初态读回比值只有描述意义，没有适用既有判据；零预算relative=null/passed=false。U/S共享导数闭合、共享面±相消均不能授独立微分、非零传输或动态资格。C采样默认0。

实际首次数据见 `runs/full-cycle/p50-saved-reference-host/diagnostics.json`；其中两项Ca读回的首次资格偏差由同目录 `eligibility-correction.json` 撤销。原数据和执行源码副本不改写；当前生产入口资格元数据修正仅静态核对、没有第二次执行。完整范围、计数、失败及交付分离见 `docs/FULL_CYCLE_P50_SAVED_REFERENCE_HOST.json/.md`。
