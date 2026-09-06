# 研究状态与导入记录（2026-09-06）

## 来源

从 Hermes `/home/ubuntu/sludge-brick-dynamics-v2b2` 的干净工作树导出 Git bundle，导入空的 `gaw008/brickmodel` 仓库。保留原始历史，源码未改动。

- 公开材料研究：`2620afe40faaf592fbb42b39e3a6a6a351009ad8`。
- B1：`d051c0982835dbe54fc4f509f1819661b85de055`。
- B2：`3b501c5`，上传前源分支 HEAD。

## 已有独立审核及失败证据

- [Stage1 独立审核](evidence/STAGE1_SAFETY_REVIEW.md)：approved_for_research_stage1。
- [B1 独立审核](evidence/B1_SAFETY_REVIEW.md)：仅 research_diagnostic_scope。
- [B2 失败状态](evidence/b2-demo001/failure.json)：numerical_failure / unknown_numerical。
- [B2 审计](evidence/b2-demo001/audit.json)：147348 项检查时拒绝导出，固定容差 1e-6；passed=false。
- `evidence/b2-demo001/` 保存从服务器复制的完整失败运行，包括输入和轨迹。目录是历史证据，原始路径与绑定字段不改；移动目录后的复验不能宣称继承原源码绑定身份。

B2 不得解释为材料不可行，也不得声称完成修复、复现批准或生产批准。本次任务只上传，不修复或放宽数值门槛。

## 运行

B1/B2 的参考平台为 Linux / Python 3.12。B1/B2 仅用标准库；早期 VME 另有 pyproject.toml / uv.lock 依赖。

```bash
cd experiments/material_dynamics_v2b1
python3 -B run_tests.py
python3 -B run.py --out replay_local
python3 -B audit.py replay_local
```

run_tests.py 会重写模块内 validation 测试日志；如需保留历史工作树，请在独立副本运行。输出目录须不存在。B2 命令见模块 README；其已知失败仍保留。

公开数据已放在 `data/material_design_v2_inputs/`，从仓库根运行：

```bash
python3 -B experiments/material_design_v2/pipeline.py --input-dir data/material_design_v2_inputs --output-dir experiments/material_design_v2/replay_local
```

DTU 四个数据集及作者、DOI、CC BY 4.0 许可、文件哈希见 [原始来源登记](../../experiments/material_design_v2/artifacts/source_registry.json)。工作簿原样复制，分析和图表属于派生结果。Raw SSA 指焚烧灰，不是原污泥。

## 本次上传核验

对模型 Git 历史和新增文件做了常见凭据格式扫描，未发现匹配；未导入 Hermes 配置、OAuth、聊天记录或运行环境。

Mac / Python 3.14.2 的 B1 测试为 12/14 通过，2 项 CLI 返回 invalid_configuration。当前实现有 Linux 资源限制逻辑，因此不能声称支持该 Mac 环境；详细原因尚未独立定位，未修改源码。原始本次日志保存在 evidence/B1_MACOS_*。Linux 复验结果另存于 evidence/B1_LINUX_*。

数值测试、公开材料研究审核和工厂适用性是不同层次：没有真实原泥动力学标定、孔道关闭模型及可靠产品性能映射，不能输出生产配方、窑速或实际烧成时长。

本次 Linux / Python 3.12.3 独立副本复验：B1 **14/14 通过**（60.56 秒）。公开数据 pipeline 成功重跑，4 工作簿、19 sheets、4270 项源派生复算无不匹配，输入哈希未变；没有重跑旧 VME 全套或修复 B2。
