# 完整来源观测的可安装读写与湿端点预算

基线 `ac04d8b`。本阶段完成单条来源观测的正式保存、检查和 CLI/Python
读取入口；软件验证通过。完整 Goal 仍为 active，原合同未修改。

## 已实现的范围

- `source_observation_record.py` 与 `source_observation_schema.py` 支持四种
  来源速率记录：封闭/程序边界，各自带或不带液体输运。固定白名单含
  39 个被动 dataclass，精确时间另用既有 primitive；输入不能指定任意导入。
- 复用 `exact_record` 的有限 binary64、Fraction、不可变数组和规范编码，
  不修改旧 registry 或旧完整运行协议。检查全部原字段、派生字段及记录间
  可被动核验的库存、能量、时间、空间格、共享面和来源包含关系。
- 显式 `SourceObservationContext` 保留固定干质量、算子/储能身份及已有
  interface modes。缺模式就保持 unknown；不根据液量重新猜测历史模式。
- `source-observation-import` 从明确的 captures 文件选择一条完整观测；
  `source-observation-inspect` 查看保存值或原格索引。原文件 SHA、路径、
  索引和 ordinal 可查询。限定普通文件和大小，拒绝重复键与不一致时间，
  用独占发布避免覆盖已有产物。

这是一条完整 **observation** 的 schema/关联检查，不是整段 trial、事件、
运行及累计账本的恢复。它不构建 live provider，不验证原 EOS 确实执行过，
不重新核验外部 source assets，不授权 resume，也不授予材料资格。
来源标签可以证明被记录的引用和内部关系；一致地伪造全部记录及新摘要，
不能靠被动 hash 检查排除。缺完整 evaluation 的失败 capture 明确拒绝，
其原始失败仍保留在原运行产物中。

## 实际验证

| 检查 | 结果 |
|---|---|
| 源码新 codec/CLI 与既有 exact_record/run_service 回归 | 93 passed，15.94 s |
| 非 editable、离线安装，同四组测试；cwd=/private/tmp，无 PYTHONPATH | 93 passed，16.03 s |
| 安装文件与源码实际字节核对 | 131 Python 模块、138 包文件相同 |
| 三份原始保存输入的全部观测 | 111 条，1813 检查，20.660949 s，通过 |
| 安装 CLI 原 N3 索引 16 导入、原格 1 查看与 Python 对照 | 7 检查，通过 |
| 原 N3 湿格压力/能量预算，独立 Fraction 保存审核 | 92 检查，0.251474 s，通过；原事件仍未通过 |

93 项包含 34 个 codec、15 个 service/CLI 和 44 个既有记录/应用回归。
四种制造观测用于软件测试，不计现实材料验证。111 条来自三个已有物性
运行：N3 液体输运 32 条、N1 湿/干 32 条、程序边界液体输运 47 条。
被动运行禁用 provider 构造、物性和积分入口，实际触发次数为 0；本阶段
没有新原生水实验。所有输出与原 state/evaluation 的全部字段精确相同，
再次编码得到相同规范字节。保存值一致不证明物理模型正确。

47 条较老程序边界记录没有外层 phase/identity/modes。研究适配器明确使用
原嵌套身份，角色声明为 `legacy_programmed_observation`，模式保持 null；
此适配不被 CLI 隐式猜测。111 条均保留原输入 SHA、索引和 ordinal。

独立审查发现并实际关闭了 7 个缺陷：深层 identity 递归异常、FIFO 阻塞、
外层时间脱钩、内部共享面缺失、同温不同库存的气体格交换、来源包含链
脱钩、液流方向资格标签升级。原失败探针、当时源码、误接收 JSON 和修复后
结果均保留。作者新增四项关联回归先实际 4 failed，再完整 34 passed。
Root 最初命令尚未实现的失败及正常样本通过/错误时间被接收的失败也保留。
子代理审核属于软件独审，不是外部科学认证。

## 湿格压力下一步

独立审核仅读取上一 N3 原始结果，保留 event=false、原 eV 和 1e-4 Pa 门槛。
湿格 0/2 原完整压力差界分别为 0.0020867669852728784 和
0.0020864234721800507 Pa。体积额外项贡献约 98.01% / 98.03%；两端
温度余量之和约 1.333e-6 Pa，只占原预算约 1.33%。这说明原温度余量
尚未排除联合比较的可能性，不保证新界可成立或通过。

后续推导须针对同一个实际体积参数，并取得两个温度下整个共同压力
区间的液体体积包络与稳定单调性条件。已有单点 v、uP 界不能替代它们。
必须保留独立压力误差及原温度余量，包括已经通过体积进入温度误差的
能量项。不得将干态推导直接用于湿态、缩小原 eV 或覆盖原失败。
详见 [预算审核](wet-pressure/REVIEW.md) 和
[尚未实现/认证的推导候选](wet-pressure/DERIVATION_CANDIDATE.md)。

## 使用

安装和实际验证命令见 [VALIDATION_COMMANDS.md](VALIDATION_COMMANDS.md)。
已有测试提取文件包含原 N3 capture 0、16，第二条就是原 ordinal 17：

```sh
sludge-sandbox source-observation-import tests/sandbox/fixtures/source-observation-v1/native-captures.json --capture-index 1 --output /private/tmp/brick-observation.json
sludge-sandbox source-observation-inspect /private/tmp/brick-observation.json --cell 1
```

输出路径必须尚不存在。若导入原完整 N3 文件，该条索引为 16。
显示的 `source_ids` 和 `source_asset_sha256` 是原记录的来源引用。
`source_assets_verified=false`、`material_qualified=false`、
`resume_authorized=false`、`full_run_validated=false` 保持明确。

Python 同一服务为
`sludge_sandbox.source_observation_service.import_source_capture` 和
`inspect_source_observation`；底层单观测接口为
`encode_source_sample`、`decode_source_sample`、`import_saved_source_sample`。
正式参数与适用边界见 [IMPLEMENTATION.md](IMPLEMENTATION.md)。

## 剩余必需工作

下一数值工作从上述湿态共同体积推导和最小缺失证据开始；保存层还需
完整试算/事件/失败及累计账本协议和受控 live resume、来源查询与界面。
重复耗尽、再润湿及纯输运残余仍需完成。原 Goal 的同材料原污泥反应、
烧结/孔隙几何、冷却力学、三个机制公开留出对照、完整空间/时间收敛、
全周期和多代搜索未被本阶段替代或豁免。部署状态仍只限离线研究。

## 原始证据

`raw-evidence.zip` 含 226 个成员，1,738,876 bytes，SHA-256
`061cf08e37bfd3a24c0795026c88dbe53a20f1deabc36783a1f2359d2ee22eab`。
全部成员已重新打开并与原文件逐字比较，清单见 `archive-manifest.json`。
其中 `source-record/` 保留实现、源码冻结、初始及中间失败、独审、两批 XML、
安装身份和 111 个规范观测；`wet-pressure/` 保留事前计划、首轮 76 检查、
补充后的 92 检查、原脚本与结果。没有将保存审核计作新 EOS 实验。
