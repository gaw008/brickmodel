# 离线复算

在项目根目录使用已备齐`pyproject.toml`依赖和水物性依赖的Python环境。本窗口使用项目`.venv`；运行入口不联网、不下载数据。可用依赖版本固定在项目配置中；源JSON/边界/数值设置随各轨迹保存，不声称记录包含完整代码或环境快照。

## 启动条件过程

```sh
.venv/bin/python examples/sandbox/run_sorptive_gas_column.py --parameters parameters.source_sorptive_column_fine.json --mesh four --tolerance base --output /tmp/sorptive-column-new.jsonl
.venv/bin/python examples/sandbox/audit_sorptive_gas_column.py --parameters parameters.source_sorptive_column_audit.json --trajectory /tmp/sorptive-column-new.jsonl --output /tmp/sorptive-column-review.json
```

输出使用排他创建；复算请选新文件名。`--tolerance refined`选择根文件中的更紧容差。湿度反转改用`parameters.sorptive_humidity_cycle.json`。线性能量坐标另明确加`--energy-coordinates parameters.sorptive_energy_coordinates.json`，不是物理模型变更。

## 停止与续算

```sh
.venv/bin/python examples/sandbox/run_sorptive_gas_column.py --parameters parameters.sorptive_humidity_cycle.json --mesh four --tolerance base --execution-parameters parameters.sorptive_column_execution.json --stop-at inside_dry_hold --output /tmp/sorptive-stopped.jsonl
.venv/bin/python examples/sandbox/run_sorptive_gas_column.py --resume-from /tmp/sorptive-stopped.jsonl --output /tmp/sorptive-resumed.jsonl
```

两处保存时刻已实际续算并与完整原过程比较。SIGINT/SIGTERM处理按接受步保存，具体信号触发路径尚未作为单独实际运行核对。旧进程输出中断且没有检查点时，必须先让其写进程停止，再使用`checkpoint_from_sorptive_prefix.py --trajectory ... --output ...`显式生成派生检查点；不修改原文件，每行都须能解析，畸形尾行直接报错。已用本轮真实输出失败前缀完成恢复，失败原文件保留。

## 解压大记录

`early-archive-manifest.json`等清单每条`records`记录给出来源路径和有序`parts`。逐个gzip解压并按列出的顺序连接，正好得到原JSONL字节，不插入或重复头；每份清单保存实际末态和逐字节往返结论。示例只解压清单指定的记录，不运行模型：

```python
import gzip, json, shutil
from pathlib import Path
manifest = json.loads(Path('data/sandbox/research/source-sorptive-column-v1/early-archive-manifest.json').read_text())
record = manifest['records'][0]
with Path('/tmp/restored-sorptive.jsonl').open('xb') as output:
    for part in record['parts']:
        with gzip.open(part['path'], 'rb') as source:
            shutil.copyfileobj(source, output)
```

清单不证明物理准确性；科学结论由报告中对应的来源、能量、熵和时间/空间审查限定。含失败前缀的记录不能当作完整仿真。

## 数值求导和续算选择

已核对的反馈状态求导可明确加`--jacobian-parameters parameters.sorptive_physical_jacobian.json`。它使用锁定SciPy内部差分接口，账本的零反馈列不再进行数值扰动；科学比较见`PHYSICAL_JACOBIAN.md`。

续算恢复来源、物理参数、N/U和温度起点；能量坐标/Jacobian两个可选数值路径按本次命令选择，不从前一段选项隐式继承。希望继续同一数值路径时，须在续算命令再次给出相应根文件。新记录在每个启动/恢复处明确写入实际选择，包括未选择时的物理U/默认稀疏Jacobian；旧策略记录作为历史前缀保留。该记录补充未改变数值计算。
