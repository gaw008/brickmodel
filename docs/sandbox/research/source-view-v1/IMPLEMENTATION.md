# 已保存来源运行的只读界面：第一增量

本增量把同一份标准 `sandbox_run_manifest_v1` 来源运行包接到 Python、CLI 与现有中文本地界面。只读取已保存证据；不启动 EOS、原生积分、来源执行、重放或检查点恢复。它是 G5 来源可用性进展，不能代表 Goal 或全流程界面完成。

## 公共接口

- `source_run_view.inspect_source_run(directory, capture_index=None, cell_index=None, value_path=None, capture_offset=0, capture_limit=50)`：先使用已有 `read_run_with_source_record` 完成一次包校验与解码，再通过公开的 `describe_decoded_source_study` 格式化。逐请求解码一次，不创建物性 provider。
- `read_source_run_asset(directory, asset_id)`：浏览器使用对原相对路径取 SHA-256 的不透明 ID，仅选择清单内来源文本；限制 1 MiB，读取后再校验散列。HTML 原文作为文本显示。
- `export_source_run(directory)`：复用 `export_run`。规范来源记录始终是原 UTF-8 文本，不经过浏览器数字格式转换；报告不包含来源资产或事件文件，不能单独重放。
- CLI `inspect RUN [--capture-index N --cell N --path FIELD --capture-offset N --capture-limit N]`；CLI `export RUN [--output NEW_FILE]`。命名与既有命令无冲突；输出文件用独占创建。

可启动纯只读界面：

```sh
PYTHONPATH=src .venv/bin/python -m sludge_sandbox ui \
  --view-source-run /private/tmp/brick-source-run-service-v1/native-job01/run \
  --storage /private/tmp/source-view-local --port 8765
```

`--view-source-run` 只由可信启动者提供。无需假造案例或水数据。原案例界面仍使用成对的 `--case` 和 `--water-data`，可同时带来源挂载。未配置案例的服务器拒绝变更、启动与继续任务。

HTTP 全部沿用原本机 Host/Origin/token 防护：

- `GET /api/source-run`：摘要和第一页原捕获列表。
- `GET /api/source-run/study?capture_index=N&cell=N&path=FIELD&offset=N&limit=N`：按需选择，查询字段均可省略；单页最多 50 项。
- `GET /api/source-run/asset?id=OPAQUE_ID`：读取已选来源文本，无浏览器文件路径接口。
- `GET /api/source-run/export`：原规范记录报告。

来源视图不自动轮询。现有任务轮询保留轻量状态更新；非活动任务的详情仅在显式请求或保存状态变化后读取。

## 证据含义与边界

`artifact_hashes_verified=true` 仅表示已有包的文件身份和记录对应关系通过既有校验；被动服务原有 `source_assets_verified=false` 与 `material_qualified=false` 均保留。这不是现实材料验证或独立签名认证。

原捕获列表按 `capture_index / ordinal / phase / role` 显示，完整 RHS 观测也不自动成为接受点，不绘制来源捕获时间轨迹。现有 codec 要求缺少 evaluation 的捕获带原 failure 标记，因此既有 `failed_capture_indices` 通常也涵盖没有保存返回的调用。新增 `return_identity=no_saved_return` 与原 failure/failure_kind 并存；不为展示伪造无标记、可通过 codec 的未返回记录。

浏览器响应将所有精确分数 `numerator/denominator` 转成十进制字符串，同时把其他超过 JavaScript 安全整数范围的整数转成字符串。浮点显示时钟只供展示，不能用于恢复。

按需从已有 `builder_returned` 事件选择 `source_column/cells/{i}`，使用有界、无类型构造的数据投影读取原干基热容注册表、来源元数据和流体声明。来源 ID 仅在原注册表存在相同 ID 时建立连接；原观测的水资产散列与清单逐项对应。干热容原文、引用定位、元数据散列和适用性保留原值，缺失的 `water_implementation_v1.json` 等关联保持 unknown。

来源事件查找最多前 256 个事件、累计 8 MiB，单事件最多 1 MiB；投影最多 10,000 次访问、深度 48。HTTP 普通响应最多 1 MiB，显示遍历最多 100,000 个节点；整包读取预检最多 10,000 个清单文件、每文件 64 MiB、累计 512 MiB。不满足上限会拒绝或明确报告来源关联未知，不构建新来源图框架。

后续项：来源执行入口、原生后续段、一次性检查点恢复和冷却证据专用适配器。本增量不改变这些行为，也不将不兼容失败归档转成标准运行包。

## 作者检查

- `AUTHOR_RED.log`：最初缺实现的 TDD 红。
- `AUTHOR_ITERATION01.log`：测试构造了未约分时钟，现有 codec 正确拒绝。
- `AUTHOR_ITERATION02.log`、`HTTP_ITERATION01.log`：测试构造缺 failure 标记且无返回的捕获，现有 codec 正确拒绝。
- `SANDBOX_SOCKET_RESTRICTION.log`：受限沙箱拒绝 loopback bind；没有修改或放宽服务验证。
- `AUTHOR_ITERATION03.log`：17 项 Python/API/CLI/实际历史包的被动读取检查通过，5.93 秒。
- `HTTP_ITERATION02.log`：14 项新增 HTTP 检查和 22 项既有 UI 检查通过，6.79 秒；仅限定本机监听测试获准在沙箱外执行。
- `PYTHON_GREEN.log/xml`：新增视图与既有被动 study 服务的回归，48 项通过，7.12 秒。

测试全程不运行 HEOS 或时间积分，使用隔离临时副本、明确标注的测试包与只读历史公共记录。独立 Python/JavaScript/安全审查和浏览器验收由主代理另行安排；这里不预先声称通过。


## 独立审查后的定向修复

只读启动现在也拒绝旧任务取消请求，HTTP 负控同时检查没有写入 `cancel.json`。显示投影在展开引用和编码前累计 JSON 字节预算，包含键、容器标点、转义字符、整数和单个大字符串；不再先构造大 JSON 再检查上限。事件与投影结构缺失或错误转成明确的来源关联 unknown；校验后文件散列发生变化仍拒绝整个请求，不能降级为 unknown。

浏览器本次校验失败会清空旧的已校验摘要和相关控件。来源加载、资产读取和导出都同时隔离过期成功与失败；旧请求不能覆盖新选择或新错误提示。

修复前实际失败分别保存在 `REVIEW_BOUNDARY_RED.log`、`REVIEW_CANCEL_RED.log`、`REVIEW_ASYNC_RED.log` 与 `REVIEW_EVENT_RED.log`。修复后作者检查：`REVIEW_PYTHON_GREEN.log/xml` 60 项通过（7.29 秒），`REVIEW_HTTP_GREEN.log/xml` 37 项通过（6.93 秒）；最后事件结构与校验后篡改修复的 `REVIEW_EVENT_INTEGRITY_GREEN.log` 6 项通过（1.57 秒）。这些是分批有交集的检查，不能将数量相加为全量套件结果。`REVIEW_ASYNC_FINAL_GREEN.json` 记录 9 个 VM 检查和 2 个修复观察，均通过；VM 不是浏览器验收。

`REVIEW_FIX_READY.json` 绑定本次交还的源码与测试。原 `AUTHOR_READY.json` 保留为修复前身份。最终独立复核、实际浏览器与安装验证仍由主代理完成；没有执行物理轨迹。
