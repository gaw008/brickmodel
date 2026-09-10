# 来源端点误差比较

2026-09-10 UTC，基线 `00ec847`，分支 `codex/physics-sandbox-v1`。`software_status`：本组件已实现并验证，整体系统未完成；`scientific_status`：限定数值误差核算，真实原污泥材料及全周期验证仍未完成；`deployment_status`：离线研究。

`source_endpoint_comparison.compare_source_trial_endpoints` 先执行原 `SourcePrefixTrial.check`，保留原参考完成、同区间、失败恢复及被动重放要求，再比较已经实际求值的前缀终点和参考终点。复用 `exact_record.pack/unpack/_policy` 递归重建完整 `DepletionPolicy`，以原规范编码绑定外层与全部嵌套设置；不执行机械压力比较、事件校正或模式转换。未提供来源事件政策时保留 `missing_explicit_event_policy`，没有自动生成容差。

对全部四类流体逐格保存精确 `|Na−Nb|`，并分别保存 `|Ua−Ub|`、`|Ta−Tb|+eTa+eTb`、`|Pa−Pb|+ePa+ePb`。运算使用已表示输入的 Fraction，避免小误差项被浮点加法吞掉。P 的误差取 `SourceWetPoint.pressure_error_pa`，包含可用体积误差的额外贡献。N/U/T/报告温度处 P 分别受原绝对事件门槛约束；原积分归一化差异只作为另一项诊断。

上界超过门槛表示未能证明满足要求，并不证明未知真实差异必然超限。非零反解温度误差下，完整反解压力门槛保持 `unresolved`；全部报告端点门槛通过也不授予事件权限。相同端点的时间坐标差为零，不是耗尽事件时间收敛证明。记录检查会重算原数据和政策绑定，拒绝事后修改差异、门槛、状态或材料资格。

`measure_source_endpoint_pair` 是共享的保存样本算术入口，核对完整来源样本、固定干质量、能量身份和同一精确时间，不假装恢复了现场模型。它可用于原生保存记录；完整 `SourcePrefixTrial` 中未保存的 live adapter 不能伪造。保存样本的先前轨迹审计与此次端点核算分别提供证据。

## 实际验证与失败记录

| 检查 | 结果 | 证据 |
|---|---|---|
| 新组件实际制造物性案例 | 14 通过，20.41 s；封闭 N1/N3、开放 N3、可恢复参考失败及独立门槛 | 原始 `third.xml` |
| 最终源码集成 | 81 通过，63.75 s | `source-tests.xml` |
| 最终非 editable 安装 | 81 通过，63.19 s，零失败/错误/跳过 | `installed-tests.xml` |
| 安装内容身份 | 120 Python 模块、127 源包文件与源码逐字匹配 | `installed-identity.json` |
| 独立 Python 审查 | 15 被动检查，0.451 s；包括小于浮点可见增量的误差项、嵌套策略和篡改反例 | [Python 审查](python-review.md) |
| 独立代码/代数审查 | 10 测试，31.06 s；含 27 组精确压力导数代数案例 | [代码审查](code-review.md) |
| 源码保存端点比较 | 30 检查，0.198809 s | `saved-source.json` |
| 安装版保存端点比较 | 30 检查，0.202008 s；除耗时外全部输出与源码一致 | `saved-installed.json` |

源码和安装测试集为 `tests/sandbox/test_source_endpoint_comparison.py`、`test_source_prefix_trial.py`、`test_exact_record.py`、`test_pressure_comparison.py`。先以 `PYTHONPATH=src` 运行；离线非 editable 重装后，在 `/private/tmp` 清除 `PYTHONPATH`，用测试绝对路径复验。实际解释器为 `/private/tmp/brick-water-backend-probe/venv/bin/python`。`check_install.py ROOT OUTPUT_JSON XML 81` 复核安装文件和 JUnit 零失败记录。

先写测试时有缺模块的真实收集错误。首次实现后的 2 通过/12 设置错误来自两个 fixture 共用 monkeypatch：第一组留下禁止旧反应网络的钩子，影响第二组建立；已改为各自作用域。下一次 13 通过/1 失败来自闭合制造案例的 U 差恰好为零，不能验证能量门槛拒绝；增加真实开放炉程 fixture 后验证该门槛。没有因此更改生产容差或造出能量差。独审最初对 MappingProxyType 使用 deepcopy 的错误也保留，属于审查脚本错误。以上均区别于生产缺陷，不冒充已修复模型物理错误。

## 保存的真实物性端点

原输入仍是上一阶段一次真实水物性试算的 JSON，SHA-256 `7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505`，物理时段仅 `1/16384 s`。本阶段没有重跑该算例，也没有新增 EOS 调用。复用固定允许类的既有 decoder，并在解码/核算期间禁止七个来源或物性求值入口。

全三格最大差异：N `1.1954456868856767e−10 mol`，U `1.1525407899171114e−6 J`，T 区间差上界 `5.6182564775326137e−8 K`，报告温度处 P 区间差上界 `0.003380390424404161 Pa`。原记录没有声明来源事件政策，保存结果因此不作事件容差决定。

30 检查核对固定输入/既有审计、原端点角色/时间/状态/绑定、每格独立 Fraction N/U/T/P 复算和非零可用体积误差贡献；额外执行新记录自己的重算检查。该计数不是完整轨迹重新验证。[运行器审查](runner-review.md)逐项限定范围；[独立端点提取](pressure-endpoint-review.md)和 `pressure-endpoints.json` 提供另一条标准库核算路径。

可复现保存端点核算：以安装环境执行 `run_saved.py ROOT OUTPUT_JSON pressure-endpoints.json`，后两项使用实际路径；不需要恢复原生 adapter。原始输入、旧审计和 decoder 从 ROOT 中既有阶段取得并核对固定哈希。来源包仍含制造几何/输运和条件性数值包络，不能凭真实水物性升级材料资格。

## 已查明的下一步压力传播路径

[独立推导](pressure-path.md)利用固定液/气库存和可用体积的闭合关系，以及 `uP=−T*vT−P*vP`，得到 `dP/dT=(P/T)*(1−Nl*uP/(Vg−Nl*P*vP))`。在整个温压域存在平滑稳定液相、`vP≤0` 和既有 `|uP|≤B` 上界的条件下，可以推导完整温度区间的压力变化界，无需再猜热膨胀系数。先建立全域包络再收紧子域，不能直接把局部导数冒充全域界。

独立脚本在原三格数据上得到条件性压力差上界约 `0.0025853 / 0.0029349 / 0.0035393 Pa`。原 B 来源明确是制造的条件性数值包络，局部 HEOS 检查不能证明全域稳定性、根存在和误差界。因此该推导尚未作为生产接口实现，也未被导入本组件充当完整压力证书。

下一具体实现是绑定原来源/固定体积/库存/温压域的条件性压力传播接口，保留独立区间 EOS 证书仍缺的状态；随后沿[先前已审查的根引导路线](../source-prefix-trial-v1/next-route.md)生成真正重新求值的正库存接近区间。完整事件时刻、运输残余成对液体及同供体焓处理、干界面/再润湿、来源持久化与应用仍需实现。完整原泥材料域、反应/烧结/冷却、三机制公开留出、全周期时空验证和多代搜索继续是原 Goal 必需项，未缩减。
