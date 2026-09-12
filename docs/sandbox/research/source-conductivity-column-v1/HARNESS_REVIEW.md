# 动态 Septien 导热 native01 静态审查

APPROVE。在已审最终生产字节上，该唯一编号的原生验收方案可执行，新增 Fourier/熵数值对应缺口已修复；本报告仅作静态审查，不声称原生运行已经通过。审查者未运行 EOS、积分、安装或已完成的旧 probe。

## 参数与运行门

`native_case.py` 相对前阶段原文件仅增加 provider import、实际 Septien 构造，以及将原 face 的静态 (.5,.7) k 置零并明确 mixed_source_exploratory。两格初始库存/气体/330 与 333 K、每格 .01 kg 干料、固定孔体积 1e-5 m³、.001 m² 面积/.02 m 格宽、同一实际 Python 水、phase/gas 系数、U inverse 和压力包络都保持。构造虽先建立原 None 分支 Column，但没有以旧 k 求值或积分。

沿用已完成阶段的实测 RHS 成本来选择两步，不重跑旧 probe。模型时钟仍为 binary64(.05) 的精确 Fraction，两步/六次 RHS；integrator 60 s、driver 80 s、supervisor 100 s 和 5 s cleanup 保持。原 U/T inverse 门 1e-5 J / 1e-6 K，累计投影门 1e-8 J / 1e-12 mol 及末态温差超过 inverse bound+1e-6 K 都未放宽。

原每格每步 U/凝聚水/三气体守恒、全局与累计前缀、闭边界、实际 U target/residual、温压域、活度与相变 µ/熵、正库存和资格 false 仍被断言。driver 从实际嵌套存储属性读 T，不依赖序列化 JSON 顶层不存在的温度属性。

## 新导热断言

实际接受步的 face integral 保留真实 midpoint witness；W 从该 midpoint 的 Nc/M/md 独立重算。名义 k 由原打印节点 (23/77,.056)、(47/53,.062) 做 Fraction 插值，再核 binary64 投影；同时核真实中点 k 与终点 k 不同、最终 k 与初态 k 不同，以及全局 source ID 和 false 标志。

原初稿仅有 Q×dt 和正熵门，不能独立证实面热流数值，已向 ROOT 报告并修复。当前另从两侧 k/T 和原几何重算 Fraction R/G/exact Q，核 G 投影；按共享核原浮点顺序核实际 Q；核保存的 F(Q)-exact Q 算术残差；核 F(Q)*(1/TR-1/TL) 的熵投影。这些是额外等式检查，无新增物理、容差或重复 EOS。

## 保存与监督

构造每返回一格即保存 CONSTRUCTION_PREFIX，初态和来源在积分前保存，原 RUN 在验收前保存。ACCEPTANCE 保留全部已完成断言及统一 finished 时刻的 elapsed，异常写 FAILURE 后原样抛出。两个运行目录均独占创建，原失败不能被同编号覆盖。OS 强制终止时未返回的物理调用无法承诺完整 Python failure/trajectory 文件；外监督仍保存原有输出、终态和 cleanup 结果。

执行使用已安装解释器、`-I`、清除 PYTHONPATH、显式 importlib 载入同目录 case。外监督输入列表包含本方案/三个脚本、SOURCE_FREEZE、整个项目与 installed 包、iapws 包与原始水资产、wet/caloric 原资产、气体/元素依据、两份新 Septien JSON 和原始 JATS XML。监督在前后观察这些字节，源变更使 complete 降为 failed；这不是不可变文件系统证明。继承的 cleanup 仅约束原 process group，不宣称能容纳自行逃逸 session，亦不宣称内核硬截止。

最终静态快照时 native01 和 supervised-native01 均尚不存在。源码已另有最终独审，安装回归由 ROOT 进行；本报告不把未结束的安装回归当作通过。

科学边界保持：另一种 donor sludge 的名义 k(W) 条件接入制造几何/剩余传输；测量温度、温压延伸和跨材料误差 unknown；原节点重复测量区间不是总模型误差；material/training false，无空间时间收敛或全烧结周期声明。

## 审查字节

| 文件 | SHA256 |
|---|---|
| `NATIVE_PLAN.md` | `40ccbcc12ee00f078f8bb9b198b5c85988056ec6468c4cb98dccbc1dbbf62d75` |
| `native_case.py` | `c87837cc16788b17603c43bc8ba98340c233b302e40e42fcb7180124264c188a` |
| `native_driver.py` | `0f7977c14a792052e1bd223146511107d9786f090af3bc3f9422f0c526835e7e` |
| `run_supervised_native01.py` | `3aef4e5ee059e83764a4e3806486fde88febb24d3db4f9b7b19f9a41f8c3728b` |
| `install/SOURCE_FREEZE.json` | `10314a59397b583010c044e03f1928734c04f9500fa14d9f9b046c7b36eea333` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — 当前静态方案无未解决问题，后续以唯一实际运行及被动保存结果审核为准。
