# 原生面通量与完整能量采样

P48已additive集成生产源码；默认关闭来自根明确enabled=0，整个合同缺失直接报错。仅静态接线资格，本轮0模型/动态采样；P47三相账本保留。普通CLI/acceptance baseline writer已接，其他workflow未验证。

## 用户操作

在获分配的运行根参数配置中设置：

将 `parameters["diagnostics.face_energy_sampling.enabled"]["value"]` 改为 `1`，
保留该条目的其余元数据。根默认时刻为 `[0.0]`，
这样普通名义配置和短窗配置均可直接启用初态采样。若需要动态剖面，事前将
`diagnostics.face_energy_sampling.times.value` 明确改为**已有 summary 时刻**。
例如已另行批准、既有输出步长 0.5 s 的 0–10 s 窗口可声明 21 时刻：
`[0,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6,6.5,7,7.5,8,8.5,9,9.5,10]`。
名义输出步长为 120 s，不能直接把上述短窗列表用于名义配置；工具不增加 t_eval、不插值或 snap。

既有普通 runner 命令保持不变（**本任务没有执行该命令**）：

```sh
sludge-vme full-cycle /absolute/path/to/declared-parameters.json --out /absolute/path/to/new-output
```

结果为 `summary.json`、`fields.json` 及根契约指定的 `face-energy-samples.json.gz`。
`fields.json` 只加入小型 `face_energy_sample_export` 收据，不重复写原始采样 payload。
输出目录使用新目录；gzip 文件以 exclusive-create 一次写入，不覆盖已有采样文件。

12 格和 24 格分别使用根登记的 faces/cells 索引表；默认全部保存，包括对称面与外侧面。
gas species 与输出文件名也来自根契约。其他格数需先明确登记索引表，不能临时选网格求通过。
配置缺字段/不存在的时刻会直接报错，字节超限报错且不截断或另开日志。
单个 gzip 侧文件的**解压 JSON 上限 2 MiB**来自根参数；它不自动增加未来整个运行的总输出额度。

## 冻结接口和符号

`configured_sampler(model)` 只消费已有参数/参考几何；sampler 不调用模型求值方法。
summary 当次唯一既有 `rates(t,y)` 调用前设置临时捕获字典，返回后立即关闭。
RHS/Jac/自适应步路径不启用捕获。保存后仅追加序列化的选定记录，最后写一次 gzip。

- face 0 为对称面，face N 为外库面，内部面 1..N−1。
- positive 朝外；左格 −F，右格 +F，内部同一值反号；gas molar face 已为 mol/s，不再乘面积/体积。
- 原生 heat 面为 `−internal` 和外侧 `−qext`，单位 W，不再反算 cell heat。
- molecular/Darcy 气体能流使用 transport 已有 `hg`；共享 `energy_flux` 仍是原 flow 的唯一计账值。
- 完整 U 为原未修改 state_thermo condensed+pore gas、surface、binding、additional_storage 五项，单位 J。
  相/石英 calorics 已在 h 中，不另加反应热、相变热或散热源。
- 局部 pressure work 为恒外压 `−P*(bulk−bulk_first)`；局部 signed 残差保留，不授予新的通过判定。
- 已有 independent reaction extents 全部保存；只有实际启用 direct 时才提供 direct 别名，不伪造零 direct。

临时 bundle 字段 `_face_energy_sample_bundle` 只供 writer 消费，不应自行 JSON-dump 整个原始 fields。
自定义 runner 使用 `write_full_cycle_artifacts(out,report,fields)` 才导出侧文件；直接 `model.integrate()`
保持无磁盘 I/O，返回待导出的 bundle。`--acceptance` 目前只写 baseline 侧文件；其 refined 内部结果
未自动导出。compare/fit/UQ 输出流程未扩展，不能据此宣称那些工作流已接通。

## 静态证据与合并提醒

候选 4 个 Python 文件语法解析和根 JSON 解析完成；7 个操作参数以外的原参数条目一致。
patch 对已提交基线副本 `git apply --check` 返回 0。
patch 对随后只读拷贝的当前 P47 工作文件副本 `git apply --check` 也返回 0。
主工程随后推进到 `091dfedc92d79138787a02dad3e2f017072dcd31`；最新明确文件快照上的
`git apply --check` 仍返回 0，见 `final-apply-check.json.gz`。
`git diff --no-index --check` 没有空白错误输出，返回 1 表示候选与基线有改动。
没有导入模型包或运行候选模块；这些证据不能替代真实主机接入/动态验证。

检查开始时 `full_cycle_gas.py` 与根参数有 P47 未提交改动，随后已提交；父协调仍须合并最新版本。
只应用 additive patch，**不要用 candidate/ 整文件覆盖主工程**，其中整文件以 f9a3abd 为基线。
不改 CaO 状态、calcium 逐相报告、原温差或守恒验收；独立采样字段空间只在 fields/侧文件。
未来动态运行、采样时刻列表和**总输出**预算须另登记，不占用此前 P45/P46 额度。

交付：`production-face-energy-wire.patch.gz`；完整候选源码在 `candidate/`。
`source-read-receipt.json.gz` 和 `static-syntax-receipt.json.gz` 记录基线与本轮静态范围。
