# Next slice: local managed source-trajectory checkpoint/reopen

只新增普通来源段的跨进程恢复，不重新运行已完成湿→干事件，也不把旧
`SourceStudyRecord` 的 `resume_authorized=False` 改成 true。范围是本地受管理
运行目录的完整性、相同程序/资产重建及原累计预算。文件哈希不证明来源不可
伪造，也不认证历史耗时；不引入签名、远端时钟或通用恢复框架。

## 最小文件与接口

新增 `source_trajectory_record.py`：闭合版本 envelope、持久关联审核。

```python
class SourceTrajectoryCheckpointRecord: ...  # 仅纯数据、资产路径和已验证引用
def read_source_trajectory_checkpoint(directory) -> SourceTrajectoryCheckpointRecord: ...
```

新增 `source_trajectory_service.py`：本地文件发布与有成本的来源重建。

```python
def save_source_trajectory(session: SourceTrajectorySession, output) -> SourceTrajectoryCheckpointRecord: ...
def resume_source_trajectory(directory, output, *, cancel=None) -> SourceTrajectorySession: ...
```

恢复接口不收新的 end、policy、step_sizes、mode 或额度。调用者需要改变这些时
是另一个明确的新试验，不是恢复。CLI 只薄接 save/read/resume；不另造求解器。

`source_trajectory.py` 只做必要小提取：把现有 open 中“已验证父记录→观察器下
build→湿身份→实际 dry view→Session 初始化”的共同逻辑抽成内部函数，增加显式
已存普通段状态/累计成本入口。保留原 open 的新段语义。
不能先正常 `open_source_trajectory()` 再赋 `session.checkpoint`：那会重置普通
RHS 计数和 begin，破坏 `_continuation_state`、`last_counts` 与原绑定。

## Envelope 必须闭合保存的内容

1. `schema=source_trajectory_checkpoint_v1`、`status=paused`、精确已接受边界，
   以及 material/full_firing false。保存原普通 checkpoint 的完整 canonical bytes
   至 `ordinary-checkpoint.json`，直接复用现有 codec；其原 binding 不重写。
2. 原父 source-run 的受管理目录引用、manifest/result/study 的 SHA、case/config
   SHA、asset manifest SHA 和完整 runtime identity。父源目录可以通过显式相对引用
   复用而不复制大记录，但引用必须固定在受管理根内；缺父记录、源文件或任一必须
   资产都不能恢复。单独 export JSON 不足以恢复。
3. 原 selected candidate index（当前只 1）、原 start/end/initial、reference policy、
   ordinary policy、`SourceOrdinaryStepSizes.binding()` 或 None。重复字段均需与 cp
   problem、父候选末态和规则 `step_sizes.apply(reference_policy)` 完整比较。
   起点必须是父候选 reference 末点；cp 末点只用于继续，不改写问题起点。
4. 原 wet/dry operator identity、energy identity、完整 interface_modes、每格 fixed
   dry mass、各 storage/volume 的内容身份、config/asset 绑定。历史 Python `id()`
   不能序列化成恢复证据；只在新建对象内部重新检验 `is` 关联。
5. 原 study 的 `parent_counts`、`parent_elapsed_seconds`；普通段所有历次实际
   constructor/anchor、RHS start/return、initial-U、wet-request 的累计计数。
   不能只保存 rhs_returned；未返回/失败尝试也要保留。原 segment 的 attempted、
   rejected、evaluation、step、next h 已在 cp，不另推算或置零。
6. 截至该干净边界的完整普通来源 captures、contexts 和其对应 journal 引用。
   原父 captures 不重复冒充本段；每段/重开进程 journal 有明确 owner ID，
   `events/000001.json` 不得跨目录混淆。旧普通 captures 原顺序与索引保留。
7. 原完整累计 balance 输出，及本段自首次 open 起的累计耗时 debit、整个 source
   lifetime 累计耗时、保存时本地实时时钟戳。保存时 stamp 与累计 debit 取同一
   cutoff；最后 manifest 发布耗时落在此 cutoff 之后的暂停区间中。
8. 本次创建记录之前的 publication/cancel/failure disposition 与 journal 截止引用。
   只有无未提交尾部、无 observer/publication failure、无 stop_status 的 clean pause
   可发布为恢复点。仍保留失败结果证据，但不能给它同样的恢复资格。

推荐文件布局是 envelope、普通 cp、普通 observation record 和原 journal 的
显式引用；父完整 source-run 单独通过固定 SHA 引用。所有依赖均列入闭合清单，
禁止路径越界和未知附加恢复字段。临时/未完成目录不作为有效 envelope。

## 可直接复用的审核；需要新增的桥接

- `read_run_with_source_record` / `verify_source_artifacts`：父完整文件清单、case、
  summary 与完整 study 的一致性、原 transition 数值准入状态。不要仅检查摘要。
- `load_source_run_config` / `validate_source_run_assets` / `BuiltSourceRun.check`：
  固定来源 bundle 和完整实际对象关联。缺资产直接拒绝，不下载替代或补默认来源。
- `decode_exact_checkpoint`：闭合类型、位/映射顺序、所有原问题/账本/计数/next h
  的被动 RK 重演。依旧不证明它的 Rates 来自真正 source operator。
- `encode_source_study({}, contexts=..., captures=..., metadata=...)` 可以直接保存
  本段完整观察集合，其现有审核保留失败返回并对成功 SourceObservation 逐项检验；
  空 roots 不提供普通积分绑定，必须由新 envelope 做下面的显式桥接。
- 新增一一对应：本段 captures 数量 = cp.observations 数量；每个原实际输入、
  exact time 与 cp observation 相同。成功返回的完整 source evaluation 经原
  observation codec 验证，其 Rates 必须与 cp Rates 完整一致。失败类别/消息/
  返回与未返回状态也必须对应，不能把有 failure 的记录当成功 RHS；无法解释的
  对应明确拒绝，不能重新求 EOS 来补证据。
- `_audit_balance_fields(..., post_dry_references=(cp.result,))`：从原 study 初态
  贯穿 wet、terminal/writeback、dry，再到本普通段全部接受步，使用原 reference
  policy 的 N/U 预算。新 record 逐字段比较保存 balance 与本次纯重算结果。
  现有 0.6+0.6 总预算 trap、原 cp 的 N/U/stretch/component 陷阱可原样复用。
- 恢复时仍执行原 `runtime_identity` 完整相等；本小版本没有跨版本迁移。

## 原计数和时间：不要重置两层预算

`parent_counts` 永远是最初 study 的原计数。本段 recorder.captures 加载截至暂停
的全部普通 captures，再追加新尝试，因而保留现有关系：

```text
rhs_started_total = parent_rhs_started + len(all_ordinary_captures)
rhs_returned_total = parent_rhs_returned + count(actual returned ordinary captures)
```

新的 builder 构造在 observer 下继续增加先前总计数，不重新做 initial U、probe、
seed、事件定位或压力四点。构造器的 HEOS anchors 是真实新开销，必须留 journal，
不能称恢复完全无 EOS。被动 cp/study 审核则是 0 新 EOS、0 RHS。

对已保存的本段耗时 `S`（从最初 open 起，含先前重建/审核/暂停）、本地离线暂停
`D`、本次新进程实际耗时 `A` 和原 cp.result.elapsed `C`，使用 Fraction 加法及
原 `_upper_float` 形成：

```text
ordinary admission credit = S + D + A_before_integrate - C   # 必须 >= 0
ordinary lifetime elapsed = S + D + A_total
source lifetime elapsed   = parent_elapsed + ordinary lifetime elapsed
```

原 ordinary maximum_wall/steps/rejections 与 config outer/callback 额度均保持。
读档、passive replay、来源重建和发布的实际时间都进入 A；积分器内部的 admission
重演由原 core 自己计时，不能再重复加一次。不可使用新 monotonic begin 清除 S。

最小本地实现可用持久 `saved_wall_time_ns` 与重开时本地实时时钟差算 D（非负 exact
纳秒 Fraction），同进程段仍用 monotonic。本地实时时钟回退即拒绝；向前跳会保守
消耗预算。明确这是受管理本机时钟记录，不是外部 wall 认证，无法识别恶意改钟。
当前同会话暂停计入 wall，跨进程离线暂停也计入，不能静默改成只计 CPU 活动。

## 重建和失败原子性

1. 先创建独占新 output 和一次性 resume-attempt claim，绑定原 checkpoint SHA。
   claim 属于本地受管理的可追加尝试账本，不修改原父 sealed source-run 文件。
   已开始但无明确成功新检查点的尝试不能从旧点免费重试；本小版本直接拒绝此类
   unfinished/failed resume lineage。复制 bundle 不提供全局唯一性/防伪承诺。
2. 有界读取/验证父、envelope、数值 cp、全部 source observations、累计账本和
   剩余额度；缺文件、改政策、未完成尾部、budget 已用尽均在新 EOS 前拒绝。
   保存 actual admission_failed 原因、已耗时间和 claim disposition。
3. 用已保存总计数初始化 _Recorder；observer_scope 下原 build_source_run，
   start 先写 journal，返回立即记录，再校验。重建异常、取消、程序杀死都不会
   获得运行成功标记；已有部分 constructor/anchor 证据仍保留。
4. 按原 open 的规则比对 wet identity 与 energy，使用完整保存 modes，在本次
   built 的同一 storages/volume 对象上重建 dry adapter。验证所选 dry cell 的
   零库存、其余格原模式以及 adapter unpack 能接受 cp 原初态和当前接受末态。
5. 用共享内部 factory 建 Session，加载旧普通 captures/contexts、checkpoint、
   已审核 balances、counts、constructor_counts 和 last_counts；重新建立仅本
   进程使用的 `original_binding` / `_continuation_state`。原 start/end/policies
   不变。运行当前 session._check 后才返回可 advance 的 live Session。
6. 下一次 `advance` 直接走原 integrate_exact_checkpointed continuation；第一个
   新 RHS 必须是下一原 RK 请求，不加初始探测。只在又一个 clean pause 时发布
   新 manifest/恢复点。文件使用 publish_record_bytes 独占发布，manifest 最后；
   发布失败、尾部 cancel 或 post-commit audit failure 都关闭来源恢复资格。

## 下一轮必要行为测试

1. 制造真实 source 类的非静止 mixed-mode 场景：连续、同会话 pause、两独立 Python
   进程 save/reopen 三者全部接受状态/时刻/拒步/ledger/capture inputs 与原累计
   balance 相同；区别仅是明确新增 constructor/anchor 计数及实际 wall。
2. 精确断点位于拒步之后；原 next h、完整原问题和 source observation 对应保持，
   恢复不重复已完成 RHS，也不把 passive replay 算成新 RHS。
3. 原 study+普通段已用 callback 额度接近上限，恢复后下一真实请求被原总 cap
   阻断；ordinary step/rejection cap、S+D+A wall 和 source outer 都不能清零。
4. 原初态累计 N/U trap 经过文件恢复仍拒绝；仅比较本段末点或局部账本会漏过的
   0.6+0.6 样例必须实际击中。
5. 缺/替换来源资产、runtime/模式/policy/end/parent SHA 改动、source Rates 与
   cp Rates 交换、旧普通 captures 遗漏、重哈希计数减小均拒绝且 0 新 EOS。
6. 第二个 constructor 失败、途中取消、返回后 journal 失败及进程被杀：保留已开始/
   已返回实际计数；重复旧 claim 拒绝，不能恢复免费重试。只有完整 manifest 准入。
7. 本地时钟回退、离线耗尽 wall、读取/重建超限分别拒绝；不把 elapsed 作为可随意
  传入的零值默认参数。文件边界沿用 regular-file、FIFO、symlink/path 和重复 key 反例。

本次只读既有代码和接口；未运行测试、EOS、安装，也未改动任何生产文件。
