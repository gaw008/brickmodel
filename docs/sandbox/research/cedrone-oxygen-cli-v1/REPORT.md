# 论文样本有限氧：可直接运行的中文入口

新增`sludge_sandbox.cedrone_oxygen`及`examples/sandbox/run_cedrone_oxygen.py`。
用户选择一个供氧比例后，从公开论文元素表和本次Cantera原子量构建条件元素池，
执行一次固定800 K、1 bar平衡，保存输入、19种产物、质量/元素检查与来源。
入口不依赖开发机器的旧结果、临时目录或论文PDF缓存。

## 使用

在已安装本项目及`equilibrium` extra的Python环境中，从仓库根目录运行：

```sh
python -I examples/sandbox/run_cedrone_oxygen.py \
  --source-root . --output-dir /tmp/new-cedrone-oxygen --lambda 1/4
```

`--lambda`必须显式选择`0`、`1/4`或`1`；每次只求选中一点，不预先求零氧基线。
输出目录必须不存在。父入口默认使用已有监督器：模块10秒、worker30秒、
进程监督40秒加5秒清理；底层函数的时间检查本身不能打断悬挂的原生调用。

在结果目录中，父`STATUS.json`和`supervision/`记录进程结果；
`calculation/INPUT.json`记录请求、实际原子量、精确加料、论文来源和当前
两个模型文件的SHA/字节数，`RESULT.json`保存原返回，`OBSERVABLES.json`
给出全19物种和质量账，`STATUS.json`记录检查和调用次数是否最终确认。
求解失败或超时返回非零，保留已经成功写入的前缀；I/O失败不能保证文件完整。

Python使用`derive_cedrone_oxygen_pool`和`check_cedrone_oxygen_result`配合
原`solve_tp`。前者只读取一次固定公开源，`definition()`是纯只读值返回；
后者只有在同次初末相原子量与建池值严格相同时，才把绑定检查置为通过。
不要把手填原子量或仅版本号相同当作这项实际检查已经通过。

## 实际安装与入口结果

Python3.12.13隔离环境非editable安装，188个包文件/181个Python模块与源逐项相同。
依赖锁14个版本保持，只将已用的ruamel-yaml0.19.1明确列为equilibrium直接依赖。
正式安装的34项相关测试通过0.22秒；原失败和针对性修复记录保留，没有重跑整库。

唯一真实入口选择λ=1/4，exec59200退出0并回收。实际Element返回
C/H/O/N/S原子量为12.011/1.008/15.999/14.007/32.06 kg/kmol，精确二进制表示
用于质量转mol；与本次初末相的读数严格一致。只执行一次平衡，没有预热或基线复算。

结果通过原全部门，模型输入1.958403141984kg/原1kg报告样本，C(gr)约
0.181191338409kg。初末库存、完整加载定义、h/s/Cp/g的全部浮点位模式和
Gibbs值，与前阶段保存的同条件点相同。独立保存审查28组及152项原NASA比较全部通过。

模块耗时4.759636083秒、worker4.870027833秒、监督9.920950916秒。
本次声明的父监督输入前后相同，worker记录的两份实际模型源码也未变；
这些记录不冒称全依赖或内存代码不可变证书。材料/训练资格仍为false。

## 构相性能假设的实际结果

旧测量指出耗时主要在prepare。本次只将同一完整derived输入改为safe/pure
block YAML，保留字段顺序、精确浮点、有限值拒绝、两次全新相构造及所有
原检查。新增provider字段明确该表示法和实际ruamel版本，原source/model/
VCS策略不变；旧实现字节及结果保留。

| 本次完成阶段 | 耗时(s) |
|---|---:|
| 完整映射序列化 | 0.012686 |
| gas Solution构造 | 2.609732 |
| graphite Solution构造 | 2.125999 |
| Mixture及初态设置 | 0.001192 |

**没有取得明显性能改善。** 旧同点module为4.776496秒且带profile，新同点
4.759636秒没有profile，不能据此声称稳定加速。记录进一步把主要成本定位到
两个Solution构造，尚未细分其C++内部原因。保留已验证的构造表示和分段计时，
不追加性能试跑或放宽原资源门。表中完成阶段不包含全部loaded/snapshot成本，
也不是对失败中断阶段的完整计时保证。

## 来源和适用边界

材料来自[Cedrone等2024年Table4](https://doi.org/10.3390/environments11100210)，
定义和完整三点比较见[有限供氧报告](../finite-oxygen-equilibrium-v1/REPORT.md)。
原子量来自本次公开Element接口，物种热化学来自已核的Cantera3.2/NASA7包。
λ是指定形式产品的计量参照，21/79是虚拟干混合气；所有输出按原1kg报告样本。
灰/卤素/打印差额、严格干基、矿物分配和材料误差仍未知，不补加残水、不归一化。

这个入口计算固定温压的限定终态组成。石墨不是实测char，气体库存不是实际
排放，H/G差也不是烧成热耗；完整湿坯至冷却、有限反应时间、实际材料验证和
全周期多代搜索仍未完成。该结果目录不是既有动态run/replay/resume协议。

[物理与入口设计](DESIGN.md)、[唯一运行登记](NATIVE_PLAN.md)、
[入口代码审查](CODE_REVIEW.md)、[构相方案](CONSTRUCTION_DESIGN.md)及
[构相审查](CONSTRUCTION_REVIEW.md)均保留。原始输入/输出、安装、测试、
失败和审查已在本阶段归档中保存：112成员、1,034,134 B原字节，压缩243,078 B，逐项重开核验。
归档SHA `36a333b3244c639c74564d62be95c2140b4caa7b739d703ebdb82a5fcb755070`；见[清单](EVIDENCE_MANIFEST.json)和[保存审查](SAVED_REVIEW.md)。
