# 精确耗尽案例的运行、续算和查看

案例 `data/sandbox/cases/reacting-wet-free-exact-events-v1.json` 使用统一服务中的显式精确事件路径。原始物理参数、初态、终点和数值验收门槛保持，时间与耗尽记录采用精确有理表示。材料仍为制造固体/反应/骨架和有来源水物性，不能用于原污泥产品合格判定。

## 使用

在已核验依赖和水资产的安装环境中：

```sh
python -m sludge_sandbox validate data/sandbox/cases/reacting-wet-free-exact-events-v1.json
python -m sludge_sandbox run data/sandbox/cases/reacting-wet-free-exact-events-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --output /tmp/brick-exact-run
python -m sludge_sandbox trace /tmp/brick-exact-run --quantity temperature_k
python -m sludge_sandbox replay /tmp/brick-exact-run --output /tmp/brick-exact-replay
```

若协作取消后保存了非空接受前缀，可用 `python -m sludge_sandbox resume /tmp/brick-exact-cancelled --output /tmp/brick-exact-resumed`。所有输出目录应为新目录。续算绑定原始初态、完整策略、案例、运行实现及父记录，重新执行四项审计后恢复；返回历史已经包含父前缀，不可再拼接一次。

界面可用同一案例启动：

```sh
python -m sludge_sandbox ui --case data/sandbox/cases/reacting-wet-free-exact-events-v1.json --water-data data/sandbox/water --evidence-data data/sandbox --storage /tmp/brick-exact-ui --port 8767 --maximum-jobs 6
```

界面的整个进程时限和求解器累计预算是不同限制。默认界面允许至120秒；实际实验的独立运行器另使用90/180/180秒监督上限，未改变原案例800秒/512面板预算。实际依赖和资产要求见 [CLI说明](CLI.md)，不宣称其他平台已获验证。

## 记录与显示

- `exact-run-record.json` 是完整规范记录；四份 `exact-audit-*.json` 分别记录前缀、终端证据、比较和资源审计。
- 保存的完整数值记录先于后置审计与终态快照落盘。后置诊断失败保留原数值轨迹，同时服务状态明确失败。
- 在构建前取消或失败的子运行没有自己的规范轨迹，`integration` 保持 null；父记录单独保存，不能当成子运行的新结果。
- `integration.times_s` 是相对于原始起点的浮点显示坐标。`exact_times` 保留绝对时刻的分子/分母字符串，续算不用显示值。
- 不同精确时刻的显示坐标可以重合；图保留原顺序全部点并说明碰撞。未知显式时间schema拒绝展示，绝对时间与经过时间不混合绘制。
- `run_service.export_run` 及界面“导出结果”保留完整规范JSON为不透明字符串，绕过源文件预览大小限制。此导出是结果、清单和规范记录，不是包含全部来源资产的独立重放目录。

没有成功终态快照时，最终结果查询返回不可用；已接受前缀仍可查看。目录、源码和资产的一致性检查不等于独立现实验证。

## 已取得的实际证据

服务源码与非editable安装各76项测试通过，87个实际安装模块一致。另有独立20项服务审查测试、前端独立22项检查；修前失败均保留。

真实水服务实验的取消、续算、重放三个独立监督进程均退出0并已回收。取消保留1步；续算与重放均完成30步、2事件、685次求值。两者所有接受时间、状态、账本和非墙钟数值字段一致，19处耗时差异明确保存。四审计、原预算、完整父记录、精确终点和4,189,324字节原始导出均获独立保存数据复核。

此证据证明当前两格短时精确服务生命周期，不是空间收敛、原污泥材料准入或湿坯到烧成冷却的全周期验证。

实际浏览器另完成案例校验、伪材料合格声明拒绝、运行、取消、续算、同图比较、结果追溯、来源文件展开和完整导出。取消保存13步，续算完成30步和2事件；两个子进程均已回收。可见报告5,766,261字节，其中规范记录5,035,493字节与实际保存文件逐字节相同。大文本框直接读取超时后通过可见文本复制完成核对，未宣称下载落盘已验证。

永久证据：[服务实现与测试](research/exact-service-v1/README.md)、[原生生命周期](research/exact-service-native-v1/README.md)、[真实浏览器与前端审查](research/exact-ui-v1/README.md)。各归档均已逐成员核验；外部来源资产树按清单排除，不是独立重放包。
