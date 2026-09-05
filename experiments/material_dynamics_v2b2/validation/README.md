# 验证证据

正式顺序与预登记预算见INVOCATION_PLAN.md和模块README.md。源提交先于tests001/demo001，运行产物不自动修改源文件。

- tests001：真实单元/参考/B1哨兵/收敛/审计攻击/绑定负向证据。
- demo001：22默认的本次raw、审计、绑定标签、离散筛选与中文SVG/报告。
- timeout001：真实超短预算exit3与active/ceiling。
- reproduction_result.json：新副本真实重放与确定性字节比较。
- acceptance_evidence.json：原24 ID的Engineer阶段映射，未执行独立Safety必须not_run。
- b2-repro001.tar.gz：最终离线闭合包，≤20MiB。

开发期单步构造与合法custom输入/状态控制不是新材料场景，也不是完整求解证据。复制文件时一次per-command工作目录误解曾使六个新快照临时落在worktree根；立即检查git status并将这些未跟踪副本移至授权B2目录，未覆盖任何原文件。最终git差异须仅B2。
