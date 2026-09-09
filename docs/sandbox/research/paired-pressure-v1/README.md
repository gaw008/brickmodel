# 条件压力比较证据

`evidence-before-identity-fix.zip` 保存设计、候选及原失败测试、源码/安装测试、两个实际水物性探针、独立审查与 Fraction 重算输出。另含当时全部 64 个模块及原失败事件的案例/结果作为证据依赖。manifest 列出 ZIP 及每个成员 SHA-256；封存时检查无重复成员、CRC 通过。

此包对应 host bcf0613816fb339d2b45ee21f4374d1289399292652adfffc94799103962edc6，早于最后观测回调后的身份检查修复。旧运行不能称为后续源码的重新验证。原审核及失败均原样保留。

`native/audit_probe.py` 是当时执行的标准库数据重算脚本，含原 `/private/tmp` 和工作区绝对路径；原样直接在任意机器运行不具备可移植性。其 exit0 输出在 `native/audit-result.json`。重放应在隔离副本中映射输入路径并绑定包内 `runtime-source`，不能把当前后续源码强行当作当时源码。

该独立重算覆盖保存输入的区间运算、端点内容一致性与记录源码绑定。共享参数盒相等不独立证明其来自原案例；额外体积误差也未由该脚本独立重建。因此这是有边界的数据/算术审计，不是全部主机、根包含性、材料适用性或真实事件验证。

科学范围与后续工作见 [PAIRED_PRESSURE.md](../../PAIRED_PRESSURE.md)。

`identity-fix-and-adoption.zip` 另存最终身份修复、RED/GREEN、独立审查、安装34测试/64模块身份、修复后真实非零探针及只读接入设计，共27成员；独立manifest/CRC检查通过。修复后probe只改输出路径，未改输入或gate。`ADOPTION_PLAN.md` 为下一步可直接读取的合同，不是已完成实现。
