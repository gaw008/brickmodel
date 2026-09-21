# D-B1：共同气体边界实现

状态：基础开发完成，独立V-B1尚待执行。依据[合同](../../../GOAL_DB1_OPEN_GAS_BOUNDARY.md)及用户选项1，允许条件基础开发；材料/训练及完整D1干燥资格保持未取得。

## 已实现

- [边界核](../../../../src/sludge_sandbox/open_gas_boundary.py)对全部显式组分计算带符号扩散和平流、热传导、各组分携焓及总能量；正号表示从计算单元流出。`apply_open_gas_rate`更新库存/U并保留每项二进制投影差，不夹断负库存、不伪造补气或单加潜热。
- [列适配器](../../../../src/sludge_sandbox/open_gas_column.py)将该笔通量放到外侧面，复用`SourceWetColumn`的逐组分更新及普通中点积分；记录预测步和接受步，避免把预测交换再累计一次。固定载气的`equilibrium_transport`接口保持独立，未宣称已接入局部平衡路径。
- [根参数](../../../../parameters.open_gas_boundary.json)显式给出气体体积、接触几何、传递系数、环境组成/压力/温度及运行参数；条件全部标为虚拟选择，摩尔质量与热化学有来源。没有隐式材料默认值。
- [离线入口](../../../../examples/sandbox/run_open_gas_boundary.py)用同一边界核推进纯气体体积的N/U，再反解T和P；JSONL保存完整参数/热化学快照、各接受步和最终状态，异常保留已完成的前缀。脚本从显式根参数所在项目的`src`导入，不声称已经完成安装包验收。

## ADR：复用共享面核、分开旧选择性汽口

状态：Accepted；2026-09-21；范围由用户选项1决定。

现有气体核已有全组分扩散和Darcy输运。沿用它比重写输运更简单，也保持原质量参考系和供体约定。单纯放开旧选择性汽口的O₂/N₂零值，会遗漏这些载气的库存、携焓和记录，因此采用显式独立适配器。旧固定载气平衡求解器还有专门前提，本增量不同时改造它。

代价是湿列适配器仍依赖旧湿主机的执行条件。本轮实际运行的是无SHA的纯气体入口；湿主机构造/运行含既有摘要生成及核验，与当前用户约束冲突，故只完成代码接线和后续静态复核，不绕过或伪装旧主机。新`case_id`只作明确的案例标签，不是内容身份认证。

## 物理定义与出处

扩散采用质量参考系：`j*k=−ρf(Mk/Mbar)Dk ΔXk/L`，修正项使`Σjk=0`。该连续形式见[Cantera官方扩散方程](https://www.cantera.org/stable/reference/onedim/governing-equations.html#diffusive-fluxes)；仓库修正漂移采用供体质量分数，属于既有离散选择，不声称逐点等于连续表达或已证明完整熵产生非负。

平流采用`v=−K kr ΔP/(μ L)`，正负速度选择实际供体；其体积通量定义可追溯至已有[MOOSE来源快照](../../../../data/sandbox/transport/moose-governing-equations.md)的Advection/eq:darcy。未重复乘孔隙率，未加入重力、热扩散或真实孔结构闭合。

扩散携焓取公共面温度，平流携焓取供体温度，`Eout=Qout+Σ(hdiff Ndiff+hadv Nadv)`；`dNk/dt=−Nout,k`、`dU/dt=−Eout`。流动功已包含在焓中；固定体积、无反应/相变的示例不另加pV功或潜热。开放控制体的内能/流焓约定见[Cantera控制体方程](https://www.cantera.org/stable/reference/reactors/controlreactor.html)。储能与气体焓共用已存NIST生成焓加显热基准，因此携带能量的正负不能直接解释为炉热耗。

纯气体示例使用已有[NIST气体包](../../../../data/sandbox/thermochemistry/nist_gases_v1.json)；本次重读[水汽原表](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1&Type=JANAFG&Table=on)确认其第一段为500–1700K及分子量18.0153。示例初温540–560K且储槽550K；不把该段外推到低温湿砖，也不使用这里的圆整水摩尔质量覆盖湿主机的水质量约定。

## 实际使用

在项目根目录执行，无需安装新依赖、访问网络或加载湿主机：

```sh
.venv/bin/python -I examples/sandbox/run_open_gas_boundary.py \
  --parameters parameters.open_gas_boundary.json --case outward \
  --resolution medium --output /tmp/new-open-gas-outward.jsonl
```

输出路径须未占用；`--case`还可选择`inward`、`equal_initial_pressure_temperature`，`--resolution`从根参数显式选择50/100/200步。第三个案例只规定初始同压同温，后续T/P由库存/U决定，不能称全过程等温或仅有扩散。

本阶段实际执行outward的1秒100步，得到T=550.7241610015626K、P=99417.70333807691Pa；三个组分库存均有变化。原始[103行记录](../../../../data/sandbox/research/open-gas-boundary-v1/development-outward-medium.jsonl)包括输入、初态、100接受步和summary。新改四个Python文件完成语法解析；没有执行/新增测试或SHA。这次运行证明入口可执行，尚未给出独立误差或物理准确性通过结论。

环境探测`.venv/bin/python -c 'import sludge_sandbox'`曾返回`ModuleNotFoundError`，表明该虚拟环境未安装项目包；这不是物理求解失败。已交付入口明确按根参数位置使用当前源码，无安装或联网降级。本次记录参数与根文件相等，文档本地链接可解析，Git差异无空白错误。

下一独立V-B1固定开发提交检查来源、算术和条件数值行为。低温湿列整段运行、时间/空间全域收敛、传递系数适用性、完整熵验证及真实砖坯精度均未由本阶段证明。
