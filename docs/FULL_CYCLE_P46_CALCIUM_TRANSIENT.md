# P46：同物理条件的新CaO坐标单例

P46唯一单例在构造前读参失败（2026-10-02T05:24:16.997599+00:00）：05:13:28.562353UTC启动、05:13:29.342829UTC rc1/回收，1sciencechild attempt、0constructor/RHS/Jac/ODE，首构造时钟和deadline均未启动，0动态数值摘要。现确认并修复16操作参数source未注册问题（7继承P45+9本轮P46），改为已有policy键、原说明移note，所有value/unit/range/status与45host源码保持；既有read_parameters实际通过567条。旧558“metadata完整保持”例外恰为这7来源/说明元数据，不掩盖原失败快照。567=144literature423assumed0measured；名义mode0/direct未启用。全部动态账本/逐相/严格熵/域审查/保存P44表示比较未执行，不授PASS或zero-budget资格。原P45净U、P34/P40/P44及名义0.135892078740%>0.1%失败保持，wholefalse。首作业已关闭，无自动补跑；下一同物理/solver修复读参后的单例候选尚未分配。

原分配是1模型构造/1ODEattempt/唯一300s从首实际构造/1worker/2MiB/无重试。45host冻结929c4c3a；P44quad12、原10s/recipe/T/gas/L和maxstep0.1s/rtol1e-5/atol1e-7全部保持。原P46预算120s/512KiB候选从未执行，本次300s/2MiB是明示单例分配，非旧窗口续期。

本次子进程只运行到既有read_parameters，报 `ValueError: missing unit/source: validation.ca_coordinate_appendix.maximum_jobs`。所以实际构造入口/solve入口/唯一科学deadline均为null，预构造childwall0.778354s、launcher0.783415s。CPU统计注册尚未执行，CPU未记录，不能报科学CPU或编造solver内部调用。无域外轨迹、无accepted knots、无新summary。

源码要求parameter.source是root.sources的键。P45附录7条当时写入完整授权说明，P45局部probe直接JSON后构造未覆盖这个读取入口；P46又复制相同写法新增9条。现在只改这16条为已有policy，原说明移note，不改材料/数值参数值、单位、范围或assumed身份。失败root-snapshot/日志原样保留；不能继续称旧558所有metadata字节保持。已有命令read_parameters当前根配置实际通过567条、读取wall0.005783s，0主机调用，未创建测试或新校验代码。

| 本次门槛 | 状态 |
|---|---|
| 修复后根参数reader | 实际通过 |
| 原sciencechild | 失败、回收、额度关闭 |
| 质量/元素/完整能量与四gas | 未执行 |
| 三相signed预算及真实初始CaO | 未执行，不能推断零分母 |
| strictOH/carbonate/direct与raw库存 | 未执行 |
| accepted knots/t_eval物理域 | 未执行 |
| 相对保存P44四指标/extent/相库存 | 未执行，不冒充加密 |
| 全八阶段/比较/反演/UQ/CLI solver | 未资格 |
| 原工艺/实测 | 历史余水失败、0measured |

同一来源问题下一次至多再尝试一次；只有明确后续资源决定才能启动固定单例。候选1construct/1ODE、单新job/首实际构造300s/1worker/2MiB，累计sciencechild至多2，无自动第三job、加密或搜索。此候选尚未授权或执行。P45净U的1e-11失败与完整动态能量0.1%门槛是不同问题，不能互相翻判。

源元数据修复与本轮失败资料沿正常逐路径Git和一个必要小增量交付。metadata readback不同于恢复；原始压缩、历史轨迹及独有Git保留，20GB/历史完整恢复/GitHub容量告警未解决。本轮不下载/恢复/SHA/自动任务或新增测试。
