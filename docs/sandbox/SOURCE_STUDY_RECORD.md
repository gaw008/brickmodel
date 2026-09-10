# 查询完整来源运行记录

`source-study-import` 将明确支持的旧研究运行 JSON 转为可安装包读取的完整记录。
`source-study-inspect` 检查记录并查询原试算、事件、失败或捕获到的单格观测。
两条命令使用与 Python 相同的服务；读取过程只核对已保存的内容和可重算的数值关系。

## 导入与查询

下面的输入路径指向已有原始运行，输出路径必须尚不存在：

```sh
sludge-sandbox source-study-import /absolute/path/native-result.json \
  --source-format source_multicell_native_v1 \
  --output /absolute/path/study-record.json

sludge-sandbox source-study-inspect /absolute/path/study-record.json

sludge-sandbox source-study-inspect /absolute/path/study-record.json \
  --capture-index 16 --cell 1 \
  --path transition/cell_selected_pressure_gates
```

`capture-index` 是原始顶层 captures 的零基下标，`cell` 是原空间格下标。
失败或尚未返回的求值仍占据原位置；不会因内部去重而重新编号。
失败观测显示原输入和错误，不能为它选择并不存在的完整格观测。

路径从保存的阶段开始，可选 `seed`、`proposal`、`approach`、`refinement`、
`common_endpoint`、`transition`、`failure` 中实际存在的键。
用 `/字段/序号` 继续查询；不存在的阶段或字段明确报错。
也可以从 `captures/原下标` 或 `metadata` 查询原捕获和运行设定。
例如 `captures/0/evaluation/time/seconds` 可追查返回后校验失败的原始求值时间；
此类返回仍会保存，但不生成通过校验的 `observation`。失败摘要给出相应 `recorded_return_path`。
大对象需要选择更具体的字段：单次查询限制为1 MiB，并在展开过程中检查节点数和深度。

## Python 接口与保存内容

```python
from sludge_sandbox.source_study_service import import_source_study, inspect_source_study
from sludge_sandbox.source_study_record import decode_source_study

import_source_study("/absolute/path/native-result.json", "/absolute/path/study-record.json")
result = inspect_source_study(
    "/absolute/path/study-record.json",
    capture_index=16,
    cell_index=1,
    value_path="transition/cell_selected_pressure_gates",
)
```

`decode_source_study(bytes)` 返回不可变的阶段 `roots`、全部原 `captures`、其余顶层
`metadata`、明确的上下文 `contexts`、同位置 `observations`、来源路径摘要 `provenance`
及逐项声明范围的 `audit`。数值包含精确分数、事件时钟和 binary64 数组；记录中的共享内容
可以去重，完整字段和原始捕获序号保持。

审计会拒绝未知类型、缺失或额外的类型字段、非有限值、无效数组、错误依赖引用及超限输入。
合法的原试算失败可被完整保存，不能因此改成成功。
原文件大小限制为64 MiB，只读取常规文件；输出通过独占发布避免覆盖。

## 这些状态各自说明什么

- `source_study_record_valid`：该文件通过当前声明的保存格式和被动关联检查。
- 原 `numerical_event_accepted`：保存时对声明模型及原门槛得到的条件数值结果。
- `material_qualified=false`：这些记录没有授予实际污泥材料预测资格。
- `source_assets_verified=false`：解码没有重新获取并认证原论文、物性来源或运行环境。
- `resume_authorized=false`：旧记录中的进程标识与被省略的 live 对象不能作为当前恢复凭据。

原始 JSON 没有保存的 provider/adapter 对象以明确的 unavailable 引用表示。
结果重读不会重新运行模型或调用水物性；完整记录仍需与原运行的证据包、版本和实际来源一起审阅。
新增记录能力并不意味着湿砖干燥、原泥反应、烧结和冷却的完整材料模型已经完成。
