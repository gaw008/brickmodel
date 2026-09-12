# Arlabosse 原污泥95°C离散解吸物性

`ArlabosseDesorption95` 提供已审核的水活动度、总解吸热和相对摩尔化学势。原图共提取18项：9项活动度、6项可读热量、3项热量unknown。只有95°C与已提取的离散含水率可查询；没有连续曲线、路径积分或动力学准入。

```python
from fractions import Fraction
from pathlib import Path
from sludge_sandbox.arlabosse_desorption95 import ArlabosseDesorption95

root = Path('/Users/wanggaoying/Desktop/brickmodel-github')
model = ArlabosseDesorption95(
    root / 'data/sandbox/research/arlabosse95/source.json', root)
point = model.at_moisture(Fraction(3, 20), temperature=95, unit='degC')
print(point.to_record())
```

命令行同样调用该接口，并保留精确十进制/分数输入：

```sh
PYTHONPATH=src .venv/bin/python -m sludge_sandbox arlabosse95 \
  --source data/sandbox/research/arlabosse95/source.json --assets-root . \
  --moisture 3/20 --temperature 95 --unit degC --trace
```

这个点的 `aw=1941/3743`，`q_total=166780000/63 J/kg removed water`，相对化学势约−2010.090020 J/mol water。显示小数不替代精确分数与保存的上下界。全部实际查询输出见[RUNTIME_NODES.json](RUNTIME_NODES.json)，逐项依赖见[RUNTIME_TRACE.json](RUNTIME_TRACE.json)。

| W，kg水/kg干物 | 活动度 | 总解吸热，MJ/kg移除水 |
|---|---:|---:|
| 0.10 | 0.364681 | unknown |
| 0.15 | 0.518568 | 2.647302 |
| 0.20 | 0.597916 | 2.536825 |
| 0.30 | 0.694096 | 2.453016 |
| 0.40 | 0.763826 | 2.422540 |
| 0.50 | 0.829949 | unknown |
| 0.60 | 0.881646 | unknown |
| 0.70 | 0.933342 | 2.365397 |
| 0.80 | 0.975421 | 2.353968 |

## 材料与来源

[Arlabosse等2005](https://doi.org/10.1590/S0104-66322005000200009)研究的未焚烧活性污泥来自接收85%工业、15%市政废水的生物处理厂，经过气浮及离心。比例描述废水来源，不是干料配比。本文与已接入的干基Cp有相同论文/材料类别，但同一份试样、同一测量过程没有得到确认。此材料不等同MIA3或本厂原料。

两幅原GIF及缓存出版HTML已经实际读取；[提取协议](PROTOCOL.md)、[提取说明](EXTRACTION.md)、[独立来源审核](SOURCE_AND_CODE_REVIEW.md)保留精确像素、标尺可行域及原提取文件SHA。原图是连续绘图线，没有可辨认的原始实验点。W=0.10/0.60的热量曲线碰到网格线，W=0.50没有可独立识别的离网格像素，因此不补值。

[Ferrasse与Lecomte2004](https://doi.org/10.1016/j.ces.2004.01.002)的原作者上传全文已按文本核读：p1366 Eq4与p1368–1369 Eqs21–24支持总解吸热含汽化贡献、以移除水质量为分母的解释。动态法的传递假设仍适用；不能把读图界称作实测置信区间。没有移植该方法文献中其他材料的参数或精度。

原HTML/GIF按出版方CC BY-NC4.0保持在忽略的研究缓存内，没有收入wheel或公开发布。`source.json`列出实际资产路径、长度、SHA及访问状态。运行需要显式提供完整资产根目录，缺失或修改会拒绝。冻结facts保留历史scratch路径，当前路径以资产清单为准。方法论文及IUPAC全文未再分发；不存在的原PDF字节哈希保持null。

### 在新目录复核原图提取

本目录的两份Python脚本按原字节归档，旧`EXTRACTION.md`里的调用依赖原`extraction/`、`review/`及上一级GIF布局，不能直接在文档目录运行。以下命令从仓库根运行，使用现有Python/Pillow/NumPy环境，在新建私有临时目录复核；不覆盖旧事实或审核报告。新记录的绝对资产路径和运行时版本可能不同，这些字段单独列出，不声称新旧文件字节相同。原科学字段及原脚本/协议/图片SHA必须相同。

```sh
.venv/bin/python - <<'PY'
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

root = Path.cwd()
archive = root / 'docs/sandbox/research/arlabosse95'
work = Path(tempfile.mkdtemp(prefix='arlabosse95-replay-'))
for name in ('extraction', 'review'):
    (work / name).mkdir()
for name in ('extract_pixels.py', 'PROTOCOL.md'):
    shutil.copyfile(archive / name, work / 'extraction' / name)
shutil.copyfile(archive / 'independent_check.py', work / 'review/independent_check.py')
for i in (1, 2):
    shutil.copyfile(root / f'.tools/source-cache/arlabosse2005/figure{i}.gif',
                    work / f'arlabosse-figure{i}.gif')
extractor = work / 'extraction/extract_pixels.py'
for output in (work / 'extraction/facts.json', work / 'review/facts.reviewer_replay.json'):
    subprocess.run([sys.executable, str(extractor), str(output)], check=True)
original = json.loads((root / 'data/sandbox/research/arlabosse95/facts.json').read_text())
replayed = json.loads((work / 'extraction/facts.json').read_text())
metadata = []
for a, b in zip(original['sources'], replayed['sources'], strict=True):
    metadata.append({'original_path': a.pop('path'), 'replay_path': b.pop('path')})
for key in ('python', 'pillow', 'numpy'):
    metadata.append({key: {'original': original['method'].pop(key),
                           'replay': replayed['method'].pop(key)}})
assert original == replayed, 'Source-derived data or algorithm identity changed'
subprocess.run([sys.executable, str(work / 'review/independent_check.py')], check=True)
(work / 'REPLAY_METADATA.json').write_text(json.dumps(metadata, indent=2) + '\n')
print('Replayed data and independent raster check passed:', work)
PY
```

## 计算和边界

相对化学势使用 `Δμ=R*T*ln(aw)`。公式核读自[Hack2011，p1033](https://publications.iupac.org/pac/pdf/2011/pdf/8305x1031.pdf)的PDF文本；截图失败不算原页图核读。Gold Book与Green Book直连403的尝试没有计入正文证据。R复用[NIST CODATA2022](https://physics.nist.gov/cuu/Constants/Table/allascii.txt)的精确定义常数乘积 `kB*NA=8.31446261815324 J/(mol K)`。

输入int/Fraction/有限Decimal为精确值；有限float按最短往返十进制读数解释。单位必须显式给出K或degC。0.15可匹配提取节点；`Fraction.from_float(0.15)`代表不同的精确二进制值，会被拒绝。相邻浮点温度也不自动并入95°C。

计算用50位正确舍入的`ln(分子)`、`ln(分母)`，各以相邻Decimal包围，再用Fraction精确相减及乘RT。所有Decimal上下文字段显式指定，不继承调用者当前或默认上下文。活动度低界/高界按单调性向外传播；单独返回名义活动度处的数值包围。读图范围仅覆盖登记的像素/标尺约定，实验散差、动态法偏差和材料转移误差仍unknown。

q_total已经包含汽化热；不能把它再次叠加到已有液水/蒸气能量差上。Δμ只有活动度自身标准态下的差值，未给绝对μ、蒸气压、比热的温度导数、过剩体积或湿储能。不能仅乘活动度到现有蒸发驱动力而保留不相容的储能模型。连续等温路径热量仍缺可准入的共同连续区间，不因6个共同节点而生成积分函数。

## 已运行检查

新增37项物性测试及已有干基Cp20项共同通过，共57项，0.29s；再增加3项CLI检查后60项通过，0.33s。覆盖原分数节点与单位、3项unknown、全部9点独立160项有理数atanh级数及尾项界、精确单温/离散域、来源篡改/缺失、JSON精度和依赖图。CLI的最初失败及误用error/failed协议名的测试失败均保留，`CLI_GREEN.log`这个早期文件实际含2项失败，最终以`CLI_FINAL_GREEN.log`为准。

真实失败日志保留：首次缺模块；注册表年份/派生依赖兼容错误；代码审查复现的可变`decimal.DefaultContext`干扰。最后一项先新增失败回归，再显式固定全部上下文字段修复。[来源及Python审查](runtime-review/CODE_REVIEW.md)和[代码审查](code-review/REVIEW.md)均批准该限定接口；这些是代理独立审查，不是外部专家或实验认证。新目录原图重放也实际通过，见`runtime-evidence/PORTABLE_REPLAY.log`。本段的源码检查不替代安装与独立实验验证。

`material_qualified=false`、`training_eligible=false`、`full_firing_cycle=false`保持。该增量使真实材料读数和物理派生可以执行与追查，尚不能据此生成全周期砖性能或配方排名。
