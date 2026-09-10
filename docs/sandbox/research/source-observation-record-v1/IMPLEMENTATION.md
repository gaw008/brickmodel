# 来源单观测被动 codec 实施边界

以下保留实施阶段记录；最终独审与安装结果见 `code-review.md` 和 `REPORT.md`。
本阶段实际验证环境为 Python 3.12.13。临时日志及修复前快照均在
`raw-evidence.zip` 的 `source-record/implementation/` 下。

基线 `ac04d8b`；仅拥有并修改 `src/sludge_sandbox/source_observation_record.py`、`src/sludge_sandbox/source_observation_schema.py` 和 `tests/sandbox/test_source_observation_record.py`。Root 独立负责 CLI/service；未修改旧 `exact_record`、研究 decoder 或已有 fixture。最终源码/测试身份见 `FREEZE.json`，完整字段合同见 `WHITELIST.json`。

## 确定 API

```python
context = SourceObservationContext(
    operator_identity, energy_identity, fixed_dry_mass_kg,
    interface_modes=None,  # 必须保留未知；不能由零库存推断原运行模式
)
raw = encode_source_sample(sample, context=context, provenance={"artifact_sha256": digest})
record = decode_source_sample(raw, expected_context=context)
record.check()
```

`SourceObservationRecord` 提供 `sample/context/provenance/sample_binding/canonical_bytes/sha256/validation_scope/material_qualified/resume_authorized`。`SourceObservationRecordError` 可从 `source_observation_record` 导入；所有公共读取/导入/编码错误采用该 ValueError 子类，并保留原异常链。

旧格式只经 `import_saved_source_sample(raw, *, context, provenance=None)` 显式转换。其 raw 是严格 JSON bytes，顶层恰为 `state/evaluation/role`：前两项沿用研究运行器原 `type/fields`、Fraction 和 ndarray 表示。此 API 不猜单 capture 外层字段、不读取路径、不选择整 run 中的观测；这些由 service 在验证实际外层 capture 后完成。未完成或失败且没有完整 observation 的 capture 不伪造为 SavedSourceSample；本层明确拒绝。

## 复用与白名单

- 数值格式完全复用 `exact_record.pack/unpack/canonical`：hex float、规范 Fraction、精确时间、只读 float64 数组及 Mapping/sequence。来源 dataclass 先投影为普通 mapping 树；不改旧全局 REGISTRY，不引入 JSON 驱动的动态 import，也不为运行对象增加特殊恢复规则。
- 新 schema 明列 39 个被动 dataclass；`ExactEventTime` 单独复用原数值 primitive，总计覆盖 40 种实际/可选记录类型。完整闭包含四种来源 rates、SourceColumnCell/face、水化学/水状态/实现参考、fluid/inverse/envelope、gas/liquid 交换和 metadata、边界/表面、可选 `PressureTrialRecord`。没有 live storage、adapter、provider、trial、terminal、candidate 或完整 run。
- 对 `object`、bare `tuple` 和 `NDArray` 别名提供固定字段合同；未知注解 fail closed。数值字段拒绝 bool；允许原数值策略接受的 int/float 表示并保留原表示，Fraction 不转 float。
- 解码调用固定被动构造器，再重编码比较全部原字段，包括 `init=False`。不会回填/修补不符的派生值。数组来自 bytes backing，映射为只读快照。
- `source_net_panel._validate` 复用原完整 N/4 物种、固定 kg/U、共享面与相变率绑定；新增嵌套类型、inverse U/库存、完整 gas/liquid 列、来源标签包含关系、液体面记录/供体焓投影、原内部/外边界能量表达式和固定资格元数据校验。没有调用水 EOS、Cp、液体流配置或完整来源物理重算。

## 资格和真实性

`validation_scope` 固定为 `passive_complete_source_sample_schema_and_associations_not_eos_authentication_or_resume`；material/resume 永远 false。保存与重建的是数值观测和原标签。哈希可用于预期内容校验，但用户提供的 provenance/hash/完整相容数据不是“这些数值确由某 EOS 执行”的独立证明。原源码、实际调用捕获、外部 artifact SHA、运行/模型构造身份仍属于外部证据。

本层不重新附着 live 对象，不恢复共享 volume 的 `is` 关系，不授予事件准入，也不证明轨迹误差或材料资格。完整 trial/terminal/dry 待单独分层；当前单观测可直接供 CLI 展示 N/U/T/报告 P、原声明模式/未知状态、各格来源和内容 hash。全部模式声明有值时验证 N 个枚举及库存/干态相变条件；未知时保持 None。

## 输入反例与实际验证

先保留模块缺失的真实 collection RED：`before.xml/log`，2 号退出，没有假造失败。首两候选批的实际失败日志也保留：`first.xml/log` 为 NDArray 类型别名识别问题；`second.xml/log` 为 programmed 外表面导热不是 shared gas face 导热。修复依据现有运行代码，没有改变科学容差。未声称保留了每轮候选的完整源码快照。

最终 `final.xml/log`：30 passed，pytest 2.47 s。使用原制造来源 fixture 生成四种 rates 的四份完整观测，之后所有 codec/导入/check 测试禁止来源求值、invert、水状态和化学求值。没有新 native EOS、安装或提交。

覆盖：四变体全字段往返与旧格式显式导入、巨大 exact origin、模式未知/不合法声明、外部 context 不同、解码后修改、不可写数组/映射、bool 冒数、非规范/错误 Fraction、float32/布尔数组、未知类/多余字段、源参考和资格篡改、完整派生 gas 压力不符、可选压力失败记录和空错误文本、嵌套 WaterImplementation JSON NaN、无效 inverse 范围、原 exact_record registry 未污染。输入限制为单记录 16 MiB、250000 树节点、96 层，属于文件资源限制而非数值策略。

AST 解析与限定 `git diff --check` 通过；ruff/mypy/pylint/black/bandit 在现环境未安装。独立代码审查已请求同组 reviewer，冻结后不再改源码，除非发现具体缺陷。Root 统一负责已保存 native 观测的转换实跑和最终安装检查。

## 独审修复与最终冻结更新

独立审查发现原冻结接受内部共享面缺失、相同温度下气体记录跨格交换、机械来源标签与父 fluid 脱钩，以及不可能由原生产者产生的液体方向资格标签。原冻结、三文件完整源码/测试保存在 `before-association-fix/`；独立 RED 和接受的完整 JSON 保留在 reviewer 自己目录，没有覆盖。

作者新增四项对应保存观测回归，修复前实际 `association-red.xml/log` 为 4 failed / 30 deselected。修复限定在新 schema 的原 `validate_associations` 与方向资格枚举：内部和 programmed 外边界要求 shared observation；cell gas 原三物种浓度逐一等于原 binary64 `n/Vgas`，保持 R 和非 reservoir 身份；水参考/实现来源→机械→fluid→point→column 及 envelope/phase 支线按原生产者可证明的包含关系核对，不要求无依据的完全相等；方向资格只允许原 `conditional_direction_resolved` / `nominal_direction_not_certified`。没有新增 EOS、材料认证或物理容差。

最新完整批 `association-green.xml/log`：34 passed，pytest 2.54 s，XML 精确时长和身份见最新 `FREEZE.json`。旧 30 项结果仍原样保留。独立 reviewer 正按新冻结复验原四项，不重复运行大型套件或原生计算。
