# 同一污泥来源下的条件相对供热

这个功能从两份已保存的有限供氧结果计算相对净供热，不再求一次平衡。对共同未知原料初态取差后，初态焓可抵消；外加O₂和N₂的入口焓仍必须计入。

## 公式与已核数据

固定同一原1 kg论文报告样本、800 K终态、1 bar、只有pV功，且各方案模型外部分的初末状态变化相同。虚拟入口气已经预热到800 K，其上游预热能耗在本次边界外：

`ΔQ = H_eq,λ − H_eq,0 − n_O2,add h_O2(800 K) − n_N2,add h_N2(800 K)`

19种产物的全部 `n·h` 都计入，包括石墨。H中已含对应pV，不再重复加形成焓、反应热或机械功项。未知原料H没有赋零；求解器初态seed的混合物H不代表原料H。

| 供氧参照λ | 相对零氧基线的条件净供热差，MJ/原kg |
|---|---:|
| 0 | 0（严格） |
| 1/4 | −3.384040214 |
| 1 | −14.977604298 |

三点的物种焓加和已与原诊断逐项精确重算；独立物理/算术审查22项通过，含两种入口扣除和元素参考平移负对照。负差值仅说明在所列条件下比基线需要更少净供热，不能推出任一点已经自热，更不能直接称实际窑炉节能。

严格守恒目标的元素参考平移抵消；实际保存库存仍有原数值残差。结果逐元素保存 `rλ−r0`，不会把它裁为零或宣称任意参考平移后的浮点结果完全不变。

## 直接运行

仓库包含[三份原始模拟结果](../../../../data/sandbox/research/cedrone-relative-heat-v1/README.md)，全部是既有结果的原字节副本。安装本项目后可离线读取；这个比较命令不需要Cantera的equilibrium extra，也不执行EOS。

```sh
python -I examples/sandbox/compare_cedrone_heat.py \
  --source-root . \
  --baseline-result data/sandbox/research/cedrone-relative-heat-v1/lambda0-result.json \
  --candidate-result data/sandbox/research/cedrone-relative-heat-v1/lambda-quarter-result.json \
  --lambda 1/4 --output-dir /tmp/new-cedrone-heat
```

输出目录必须不存在。改比较λ=1时同时选择`lambda1-result.json`与`--lambda 1`；不能只改标签而沿用另一供氧量的库存。

Python API为`sludge_sandbox.cedrone_heat.compare_cedrone_heat`，接收两份JSON对象、`source_root`及`candidate_lambda=Fraction(1, 4)`。它返回只读的精确Fraction记录，包括19项物种焓贡献、两种入口气焓、元素残差差值、公式条件和来源。CLI将其保存为`INPUT.json`、`RESULT.json`及`STATUS.json`；输入文件路径/SHA和物性字段位置可从输出追查。

读取器复用已有来源物性和库存/后验检查；这是保存记录的数值一致性核查，不是对任意文件所声称历史进程的真实性认证。本目录的三份发布数据另外逐字对照了原运行归档。

## 实际验证与保存结果

Python3.12.13隔离环境非editable安装：沙盒189个文件/182个Python模块与源码逐字一致；同时核对的早期VME34个文件未变。最终21项新模块安装测试通过，耗时0.32秒；未重跑旧物理场景或整库测试。

独立代码审查实际发现并复现两个准入问题：损坏的初始库存未被原离线路径拒绝；同时翻倍R与热物性可能形成自洽但错误的热差。已补回原初末库存门，并将R绑定已有NIST登记的精确定义SI乘积。原2项RED、修复后作者受影响3项GREEN及独立2项GREEN均保留；材料参数和原数值门未改。

唯一实际命令读取公开零氧/四分之一氧的原结果，正常退出0并回收，外层10秒预算保持；CLI记录0.047682208秒，整个子进程0.088612083秒。这是一次保存值离线比较，0新增EOS/平衡。原结果`RESULT.json` SHA为`c5bba836be353124f71798c6aca800017e1ee97fb98a1b11cf69ab7e073272e0`。

ROOT将实际输出与先前独立薄算术逐项比较：两个H、两入口焓、ΔQ、19项物种H/形式系数和5元素参考平移余量全部精确相等；同时核原输入SHA、安装模块身份、终态和unknown/资格字段。检查的是保存binary64所代表值的Fraction算术，不是材料或热化学拟合误差界。见[原检查](SAVED_RESULT_CHECK.json)与[代码审查](CODE_REVIEW.md)。


## 证据范围

来源为[Cedrone 2024报告样本](https://doi.org/10.3390/environments11100210)的条件CHONS池和[已核NASA7相包](../tp-equilibrium-v1/REPORT.md)。[推导](DESIGN.md)、[物理审查](PHYSICS_REVIEW.md)及[实际入口登记](SMOKE_PLAN.md)保留假设和原门槛。

灰矿物/卤素若随供氧改变终态，外置焓差不能消去；若还竞争CHONS/O₂，原产品库存也需重新建模。严格干基、元素分配与源误差仍未知。本比较没有补齐有限时间反应、烧结、砖体形变和冷却，也不能作为独立实验证明同一模拟器准确。完整Goal继续未完成。

完整证据含来源算术、作者候选、实际失败/修复、安装测试、唯一入口、材料缺口核查：59成员、434,774 B，压缩106,784 B，逐项重开核验。归档SHA `7623d21b6bef3c1ac838f246930b9eae877297cff063d8e09b662d56381428eb`；见[清单](EVIDENCE_MANIFEST.json)。
