# 来源温度反解的条件压力传播

基线 e0a7f4a。新增 `source_inverse_pressure`，把原来源温度反解误差传播到压力区间，保留原同端点比较与事件政策。它支持实际 SourceWetStorage 的正液体/正气体状态和保存记录；不是完整材料准入或耗尽执行器。

## 实现与物理范围

固定库存和可用流体体积下，闭合函数为
`G(P)=Nl*v(T,P)+Ng*R*T/P−V`。在整个声明域内连续稳定液体 `vP<=0` 假设下，
`−G_P>=Ng*R*T/Pmax²>0`。原残差、表示误差和液体物性/体积误差给出初始根包络；整个围栏在域内时，端点符号和严格单调性共同保证唯一根。

`uP=−T*vT−P*vP` 给出
`dP/dT=(P/T)*(1−Nl*uP/(Vg−Nl*P*vP))`。
因为分母不小于 `Vg=Ng*R*T/P`，在原温压矩形内可采用
`L=Pmax/Tmin*(1+Nl*B*Pmax/(Ng*R*Tmin))`，其中 `B>=|uP|` 是全域声明。
先验证 `P±(eP+L*eT)` 的完整围栏；eT 非零时必须严格位于实际机械压力域内。
然后才在已建立的小温压矩形上收紧 L。全程 Fraction 算术，不截断出界区间。
推导来源和初始根证明见 [原压力路径](../source-endpoint-comparison-v1/pressure-path.md)及 [根合同](pressure-contract.md)。

`enclose_source_inverse_pressure` 重核实际储能/源资产/库存/目标 U、液气同压、来源 Cp 积分及最小热容、能量误差、温度误差、原闭合残差/分辨率与三层压力误差。原未知的固体体积、总焓和拟合误差保持 None。
保存资产表允许等值 dict/只读 Mapping，但键类型、值类型和内容严格核对。三个原算术 helper 仅提取复用，不改变原式、舍入顺序或调用者门槛。

`propagate_source_trial_pressure` 使用成功试算的真实前缀/参考端点，另存
`|Pa−Pb|+ePa_full+ePb_full` 与 conditional_gate。原四项事件门槛、完整压力认证状态、事件时间状态不覆盖；没有原显式事件政策就不判 gate。

当前全域平滑/稳定性、uP/物性误差包络、保存能量舍入及名义来源 Cp 曲线仍属条件合同；本接口没有重新求解底层 EOS，也没有推导全部原生能量项的误差。原泥 Cp 拟合误差和真实几何仍未知。因此 source_certified、event_admitted 和材料资格始终为 false。

## 实际验证

| 验证范围 | 实际结果 |
|---|---|
| 映射互操作修复前的完整相关集成批 | 源码 107 项 / 67.96 s；非 editable 安装 107 项 / 67.65 s |
| 最终映射修复后的受影响模块，含新增回归 | 源码 31 项 / 16.67 s；安装 31 项 / 16.88 s；未重复不受影响的 77 项 |
| 最终安装文件身份 | 121 Python 模块、128 包文件与源码逐字相同 |
| 独立 Python 反例 | 最终 29 项 / 0.678 s |
| 三个 helper 与 HEAD 原算术 | 14 项逐位/精确值/异常比较 / 0.13 s |
| 独立映射互操作反例 | 8 项 / 0.47 s |
| 稳定仿射液体独立解析根 | 1,030 项检查、492 个 Decimal100 二次根 / 0.01136 s |

解析案例同时包含非零初始残差、体积误差和温度误差，覆盖正/负/零热膨胀、严格域边界拒绝及区间收紧。参考根不调用被测求解器。该有限根检查是在解析已知的制造 EOS 条件下验证算法，不是实际水的全域认证。最终 pure 函数 AST 与该次独审完全一致，身份/元数据修复未改其算术。

可读审查：[物理](analytic-review.md)、[Python](python-review.md)、[代码](code-review.md)、[映射修复](mapping-code-review.md)、[运行器](runner-review.md)。
精确文件版本见 [最终冻结](final-freeze.json)；原测试/失败/源码快照见 [原始归档](raw-evidence.zip)。

## 六个实际保存端点

使用固定源试算 7c0907af… 的三格前缀及参考终点，原时刻 1/16384 s。
按原构造重建一个真实 storage（所有六端点模型身份匹配），不伪造原完整 trial。
同一运行器和原输入复验完成 35 检查，六个全域/收紧斜率与半径及三个成对界，
全部与 [前阶段独立 Fraction 结果](../source-endpoint-comparison-v1/pressure-endpoints.json)精确一致。
另经独立标准库 [86 项保存结果审核](saved-audit-review.md)通过，0.02524 s，核对原输入/域、两层围栏、成对结果及累计构造成本，没有新 EOS 求值。

| 格点 | 温度传播后的成对压力上界 / Pa |
|---|---:|
| 0 | 0.0025853136999620355 |
| 1 | 0.002934899677443897 |
| 2 | 0.0035392830997053887 |

这三个显示值不作为舍入后的判据；原分数保存在 [实际结果](saved-repaired-installed.json)。
每个端点都含非零可用体积误差。原案例没有来源事件政策，conditional_gate 为 null。

首次执行失败于资产 Mapping 容器误拒绝，1.098459 s；修复后相同条件执行成功，1.148738 s，
其中构造 0.873627 s。两次各有两个 HEOS 后端构造/参考锚点检查，累计四个；
两次新端点求值尝试均为零。这是固定构造代码路径的锚点计数，不是所有 native 内部运算计数，
不能称为完全没有 EOS 计算。原 20 s 软预算 / 30 s 外层预算与科学门槛未更改。
见 [执行前登记及复验理由](PREREGISTRATION.md)、[首次失败](saved-installed.json)和 [运行器](run_saved.py)。

## 已修复的真实失败

- 4 个独立 RED：错误/缺失液压及等值 Fraction 气体常数被接受，已加入严格来源身份校验。
- 5 个独立 RED：来源点可丢失 source_ids，或把资格、拟合误差、固体体积、总焓改成无依据的更强结论，现按原来源点合同拒绝。
- 原生运行及独立映射 RED：合法反序列化字典被误拒绝；局部修复容器互操作，缺键/多键/改值/错误类型仍拒绝。
- 首次解析审核的边界反例错误地先触发温度域退出；审核脚本修正案例定位，保留原失败，未改模型门槛。

## 重现与下一步

在锁定依赖的安装环境中运行：

```sh
python -m pytest tests/sandbox/test_source_inverse_pressure.py -q
python docs/sandbox/research/source-inverse-pressure-v1/run_saved.py "$PWD" /tmp/source-pressure-replay.json
```

运行器需要现有、清单核验通过的 HEOS 依赖及来源文件，会执行上述参考锚点；并非全周期模拟命令。
安装身份检查复用前阶段 `check_install.py`，本阶段没有新建验证框架。

下一项按 [既有根引导路线](../source-prefix-trial-v1/next-route.md)复用全部 4N 库存首根竞争，从真实首/中点样本提出严格在首根下界之前的正库存区间，采用原 DepletionPolicy.safe_inventory_fraction 及原步长/炉程节点约束，再调用既有 SourcePrefixTrial 真正求值该区间。普通推进继续使用 integrate_exact，不复制事件控制器。
独立时间精度、运输成对液体及同供体焓、干界面/再润湿、源记录与应用仍未完成；同原泥成套材料、反应/烧结/冷却、三机制公开留出验证、全周期及多代搜索仍是原 Goal 必需范围。
