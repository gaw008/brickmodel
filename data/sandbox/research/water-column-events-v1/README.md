# 相变、续算和熵账的原始记录

本目录对应[两小时报告](../../../../docs/sandbox/research/water-column-events-v1/REPORT.md)及[执行合同](../../../../docs/sandbox/research/water-column-events-v1/CONTRACT.md)。全部是明确虚拟输入下的条件通道计算，不是砖实验、材料训练集或完整烧砖轨迹。

## 数据组织

- `compressed/*.jsonl.gz`保存原始JSONL的无损压缩版本；解压后的JSONL留在本地并由本目录`.gitignore`忽略。完成、主动停止、计算错误前缀均保留，原件不覆盖。
- `archive-manifest.json`给出每个成员名称、压缩/原始字节数、记录类别计数、末次状态和检查点；`archive-manifest-initial.json`是最后64格续算仍运行时的首次封存记录。压缩件实际读回并解析JSON，没有SHA。
- `pressure-partition-state-comparison*-summary.json`是两次34,224状态比较摘要；逐状态差值位于相应`compressed/*.json.gz`。v2追加稀薄分支/分母量级指标，不改变旧结果。
- `event-convergence-matrix-v2.json`保存原干燥8/16/32/64格及积分/扫描细化；v1保留旧分析字段。`pressure-root-full-trajectory-comparison.json`比较相平衡算法变更前后完整轨迹。
- `condensation-convergence-matrix.json`是至32格的比较；64格最终比较见`condensation-convergence-matrix-v2.json`，不能用旧结果冒充新运行通过。`condensation-boundary-profiles.json`记录准确34s快照，包括原64格失败前缀。
- `*-entropy*.json`为BDF多项式上的2/4点积分核算；`*-source*.json`为直接IAPWS/独立表达式重建。两个工作流的独立性和共享部分见主报告。
- `pressure-root-domain-review.json`把两条64格轨迹全部458,368个接受库存与各自Gibbs矩形的摩尔体积系数界配对，核对单压力根的稀薄支路前提；不含未保存的迭代试探。
- `all-accepted-balances.json`给出两条64格轨迹7,162个接受步的28,648项逐组分/U收支最大残差及精确有理数表示。
- `execution-notes.json`和两份`*-error.txt`记录失败、主动停止、修复依据和未实施任务。早期无检查点的中断记录仅作失败证据，不能使用续算命令。

没有打包私人通信、原文PDF/图片或依赖环境。物性快照在轨迹头保存；新增ENEA来源数值位于相邻独立目录。

## 全新克隆后的解压

在仓库根目录运行下列Python标准库命令。使用排他创建，不覆盖已有解压记录；本地已经有原文件时直接使用现有记录。

```sh
python3 - <<'PY'
from pathlib import Path
import gzip, shutil
folder = Path('data/sandbox/research/water-column-events-v1')
for archive in sorted((folder/'compressed').glob('*.gz')):
    output = folder/archive.stem
    with gzip.open(archive, 'rb') as source, output.open('xb') as target:
        shutil.copyfileobj(source, target)
PY
```

使用已有离线依赖环境复算，不需要联网。例如：

```sh
.venv/bin/python -I examples/sandbox/analyze_water_column_events.py \
  --parameters parameters.water_column_pressure_algorithm_review.json \
  --output /tmp/water-pressure-comparison-new.json
.venv/bin/python -I examples/sandbox/analyze_condensation_boundary.py \
  --parameters parameters.water_column_condensation_boundary_review.json \
  --output /tmp/water-condensation-boundary-new.json
.venv/bin/python -I examples/sandbox/review_equilibrium_water_column.py \
  --parameters parameters.equilibrium_water_column_review.json \
  --trajectory data/sandbox/research/water-column-events-v1/pressure-root-sixty-four-base.jsonl \
  --selection events --output /tmp/water-source-review-new.json
```

湿态/边界节点检查点的来源被冻结在记录中。继续64格原停止文件时，显式保留本次采用的启动政策：

```sh
.venv/bin/python -I examples/sandbox/run_implicit_equilibrium_water_column.py \
  --resume-from data/sandbox/research/water-column-events-v1/pressure-root-condensation-sixty-four.jsonl \
  --initial-step-policy parameters.water_column_initial_step.json \
  --output /tmp/water-condensation-resumed-new.jsonl
```

这会使用当前代码建立新的BDF历史，不能逐位重放历史算法。相平衡算法名称、原来源和本次政策均入记录；没有自动重试或来源替换。

## 34s启动探针复算含义

`condensation-sixty-four-initial-probe.json`从原检查点的N/U和原面通量构造`f0`。按已安装SciPy的`select_initial_step`，`scale=atol+abs(y0)*rtol`，`h0=0.01*rms(y0/scale)/rms(f0/scale)`，上限为该段剩余时长，`y1=y0+h0*f0`。本例不触发极小范数分支，得到1.28668320355s。它是积分器的启动探针，不是接受的物理时间步；相应全汽候选502756Pa不能当成实际湿态压力。

比较器明确区分完整轨迹和共同区间。部分观测通过不能证明未保存的后半段；有限事件扫描也不能排除漏掉成对根或切触根。所有误差预算保持本阶段执行前的定义。
