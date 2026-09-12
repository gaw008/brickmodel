# Septien 动态导热接线独立代码审查

Verdict: APPROVE。针对基线 `3683a6f` 后本次 provider、两份来源/模型 JSON、Column 接线及相关测试，当前没有未解决的实际问题。仅批准条件探索分支的实现；不代表真实泥料导热率、热压响应或完整烧结过程已经验证。

本次只读检查暂存/未暂存差异、完整 provider、新旧 Column 接口、共享 Fourier 核、实际中点积分和原精确/程序接口类型门。审查者没有修改生产、安装依赖、调用 EOS 或运行原生轨迹。审查产物仅写入本 scratch/code-review。

## 实际证据与检查

独立制造探针 `INDEPENDENT01` 为 7 passed / 0 failed，0.16 s；最终元数据 pin 更新后 `INDEPENDENT02` 同样 7 passed / 0 failed，0.14 s。探针使用实际 provider 类及制造 JATS fixture，实际 Column 动态 k 路由、共享 Fourier 算术与 `_integrals`；存储 inverse、相变、气相以及非热面分量使用明确制造替身。它们不能算作完整 EOS 或真实材料验证。

7 项覆盖非零共享热流下溢拒绝、非零熵下溢拒绝、同温真零与正有限 G、左右交换 Q 反号/熵不变、全部 inverse 后逐格一次 k 并重用内部格、N=1 的源变更/越域拒绝，以及接受步保留实际中点 witness、共享热量只计一次。修复到达早于这些探针，故绿色日志不是该修复的 RED 证据。

已读取作者当前元数据测试原日志/XML：33 passed，0.12 s。已读取 ROOT 原 `COLUMN_TESTS01`：63 pass / 2 fail，保留两项测试构造问题（半宽硬编码、基类构造拷入新增子类字段）；修正后受影响 `COLUMN_TESTS02`：10 passed，27.59 s。没有隐藏原失败，也未把这两项测试错误描述成已复现的生产失败。

## 接线与来源结论

- 新 provider 严格限定实际类型，必须明确 `mixed_source_exploratory`，存储 face 的静态 k 必须为 (0,0)。旧 None 分支 binding 内容和共享面算法保持；旧 ExactSourceColumn/ProgrammedSourceWetColumn 的实际类型门继续拒绝 Arlabosse 子类。
- k 从每次 inverse 的当前 T 和凝聚水 W 计算，含 N=1；provider 身份加入模型 binding，全局来源也不依赖面数。源文件变更会使后续读取拒绝。
- 动态 k 经临时 WetFace 进入原共享面核，`shared.face_energy_w` 为唯一能量来源。新增见证和积分类只保留实际中点的 k/G/Q/熵与算术残差，不再次加入 Q。导热率正值、有限投影、非零下溢拒绝和有符号热熵检查一致。
- 原 XML 先经固定 SHA 校验再解析；两行原表文字、物理列、湿基转干基和置信区间分别校验。新 JSON 使用合同分类：原读数 measured_public_data、模型 derived_from_evidence；温度冻结和跨材料使用明确 virtual_design_choice，数值策略与 unknown 分开。元数据补正未改原数值、域或资格。
- 模型仅限名义 W=.30–.80、T=308.15–368.15 K 坐标。原读数来自另一种 VIP faecal sludge；测量温度未知，85°C 是干燥准备条件。两个 90% 原样本区间不成为插值或跨材料总误差。若 inverse 区间越出名义域，不可凭中心坐标宣称整个不确定区间获支持。
- 材料、训练资格持续 false；气相传输、相变系数和几何仍有制造设定，凝聚水 Darcy 支路及干界面继续拒绝。本次没有提供空间/时间收敛、总熵审计或全烧结周期证明。

实际运行 harness 的检查单独写 `HARNESS_REVIEW.md`；本代码结论不代替它，也不代替后续保存结果审计。

## 最终字节

| 文件 | SHA256 |
|---|---|
| `src/sludge_sandbox/source_wet_column.py` | `cdf1941cc35613057b80c33d86d81ebb4f2530b30198c50c0c34a046cbfd07c2` |
| `src/sludge_sandbox/septien_conductivity.py` | `d12b1670ebdb45849e9aa662eb5133a5663bb3c592f2fb7566201e9322512df5` |
| `data/sandbox/research/septien-conductivity-v1/source.json` | `5d68c9d8e4d2c2b263270b66af62d6f7b6d1dbd141bbdb9db53fa0d61cd16abd` |
| `data/sandbox/research/septien-conductivity-v1/model.json` | `c5d36c30be29b8f9aea569dde355ad0580b6c5d8474a0f85cc4a036c6976cb15` |
| `tests/sandbox/test_sorption_conductivity_column.py` | `abb1438c38475e8e7812f997055f99819856264fa50ae5735660b8f4432629b4` |
| `tests/sandbox/test_septien_conductivity.py` | `a865141c45fb03e7fedd79d1c7a9bc8d7adad105964d6ffb1557b2b0d2420bd3` |
| `tests/sandbox/test_arlabosse_sorption_column.py` | `376fc3c34e3fec742b43b9d627ddbdcf81dd99fa1eb08874c72805c6d564443a` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 限本次有明确来源与未知误差的条件动态导热实现。
