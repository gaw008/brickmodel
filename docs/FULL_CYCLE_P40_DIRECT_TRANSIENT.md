# P40 固定短瞬态实际结果与失败

P40固定10s合成动态实际完成三档（2026-10-01T21:55:34.264370+00:00），验收仍partial：原三次启动含首摘要失败，明确追加冻结mesh一次后总4、全回收，原21:53:23.887003UTC截止不延。三档质量/元素/完整能量及四gas低于原0.1%，time四指标通过；mesh峰温差按原1K尺度差7.333352694%>2%，direct累计量较基准差27.875046911%，未获空间收敛资格。三档CaO近零无floor预算失败、strictOH及carbonate均微负保留，原八阶段未覆盖。根500=144literature/356assumed/0measured、旧469/冻结499完整条目保持、名义direct未启用；历史名义干燥0.135892078740%失败与完整模型wholefalse保持。Git/Drive独立收据，未恢复。

## 实现与初始基准

仅 full_cycle_gas.py 增加实际单窗口摘要、实际y0参考和direct采样字段，并修复摘要首行的BDF dense输出原点。配置在make_cycle之前复制根登记的synthetic配方/气体/温度/数值参数，初态由既有initial_state构造；没有后置覆盖物理y0。第八direct extent独立积分，四气体/自由水helper以active8计量接线，完整物种U/S/毛细/骨架储能与原热流/边界焓/压力功账本共用。direct没有第二份反应热/熵。名义direct未启用。

单窗口0–10s只有direct_transient，未虚构drying或cooling端点，两项evaluated=false/passed=null。全部初始质量/元素/完整U/S、Ca池/分相、孔气、8extent和边界/热/功/熵零点直接来自真实solver输入；微小重建CaO初值和后续负值保留，不裁切、不改门槛。域审查仅真实BDFaccepted knots与t_eval采样：三档均在事前290–350K、分压0–200kPa、总压1–200kPa之内，不授予步间连续域、Newton或complexstep试探域资格。

## 实际数值证据

| 档 | mass相对 | elements相对 | completeenergy相对 | direct extent mol | CaO预算比 |
|---|---:|---:|---:|---:|---:|
| baseline | 5.308335572112618e-10 | 4.409768167509832e-09 | 1.3287075120251966e-08 | 0.00022386572735418265 | 0.5636363636363636 |
| time_refined | 6.485455133250056e-11 | 4.900671156992311e-10 | 1.6567645596098218e-09 | 0.0002238639711534696 | 0.8674033149171271 |
| mesh_refined | 7.180907863148847e-10 | 7.223927278693676e-09 | 1.711092233135768e-08 | 0.0002862684038726387 | 0.42857142857142855 |

原普通质量/元素/完整能量及4gas门槛均PASS；最坏普通1.71109223314e-06%、gas预算0.00151361223115%、初始库存归一化0.0197640649142%，均小于0.1%。保存全部signed残差。whole窗口与唯一stage是同一实际区间，不能作为独立重复证据；普通9unique/18duplicated，gas12unique/24duplicated。

| 加密 | 指标 | 原尺度相对差 | 判断 |
|---|---|---:|---|
| time_refined | porosity | 5.29155723259e-08% | PASS |
| time_refined | residual_carbon_kg | 2.96529247938e-14% | PASS |
| time_refined | shrinkage | 3.45745654329e-07% | PASS |
| time_refined | peak_temperature_difference_k | 1.17874947136e-05% | PASS |
| mesh_refined | porosity | 0.000787224533172% | PASS |
| mesh_refined | residual_carbon_kg | 2.3722339835e-12% | PASS |
| mesh_refined | shrinkage | 0.0121584618151% | PASS |
| mesh_refined | peak_temperature_difference_k | 7.33335269426% | FAIL |

分母全部读取根acceptance.floor，阈值仍2%。基准峰温差0.17759525238125207K，mesh0.25092877932388546K，用原floor1K后差7.333352694%，明确FAIL。不能改成峰绝对温度、放大尺度、另选网格或调整迁移率。directextent网格差为基准的27.875046911%、refined的21.798660164%，没有新加自定义门槛；既有温差已失败，新通道不判空间收敛。残碳仅微变、10s收缩微小且带符号，三项通过不能代替烧成工艺资格。

Ca逐相9unique中6PASS/3CaOFAIL；whole/stage重复后18行中6FAIL，原预算无floor，实际CaO残差约1e−17mol/近零库存。严格OH和carbonate单支路熵三档都有微负，direct采样熵为正；不能用既有库存误差尺度physical_consistency=true覆盖严格支路及逐相失败。总熵账本闭合/原耗散条件与逐支路严格条件分开。原P34逐相30/81失败未重新计算或消除。

## 失败、修复、实际预算

首次基准solve到10s，2202RHS，摘要后exactarray_equal/zero组合断言失败；rc1/回收，具体子断言/差值未保存，不能确认首次物理缺陷或从重试逆推。静态SciPy源码说明t_eval0来自BDF dense多项式，不承诺bitwise还原。修复只对输出copy首行使用真实solverinput，完整signed原插值差保留；不改变RHS/Jac、sol.y、末态、物理轨迹或extent来源。重试baseline最大差1.1102230246251565e−16，time为0、mesh同数量级；这是新结果，不叫第一次差异恢复。

原maximum_integrations=3完整历史保留，失败计入；耗尽后协调明确追加一次原冻结mesh24，根单独操作条目+1，总启动4，不伪报3。每例300s/单worker/同问题最多2次/科学摘要2MiB、原唯一900s截止均不改。执行UTC2026-10-01T21:38:23.887003+00:00→2026-10-01T21:49:29.021778+00:00，监督wall665.136553s包括失败分析/修复暂停，非solver时间。三成功实际solver共27.287930917s；首失败未保存完整solver耗时/回调不能补造。四child耗时分别见execution.json，全回收，0第五次/额外RHS-Jac扫/fit/UQ/恢复。三成功RHS7561/Jac28，首失败已知RHS2202，全部已知RHS下界9763，首失败完整Jac/summary计数未知。数值摘要1,481,467B，冻结源码/根/元数据另列，无原始全场/文件SHA。

## 当前矩阵与下一必要项

P40实现及有限执行矩阵完成，模型验收仍partial，勾选保持未完成。缺口已是实际FAIL，不再写“网格未运行”。下一必要动作是基于已有三档有符号场摘要和源码的有界空间离散/通道接线诊断，先定位7.33%温差和27.88%extent差是否有具体离散/源单位错误；当前没有确认bug，不改根物理参数求PASS。任何后续科学调用或修改受影响重验必须另事前登记，不再在本P40额度中积分。不扩网格、不扫容差/迁移率、不用关通道或延时对照替代失败。

完整八阶段新条件核、三方案/反演/CLI当前资格仍未补齐；原名义干燥0.1358920787402553%>0.1%失败不被10s窗口替代。500参数全部literature/assumed、0measured；L=1/s和配方/域只是synthetic，此处非实砖速率、湿膜面积、产品层/工艺验证。旧P21/P26UQ额度不扩，材料适用性与现实对照待实测。

正常Git/push及新明确小增量Drive名称/大小/父目录读回分别保存实际收据。未下载/解包/实际恢复，不删除唯一源/压缩原件/独有历史；历史完整备份、20GB、GitHub容量告警未获解决。

## P40实际交付

P40实际交付（2026-10-01T21:59:41.691049+00:00）：实现及失败矩阵提交39c618f8已普通推送并核对远端；39明确文件+manifest小增量1,064,643B已上传，名称/大小/父目录回读一致，收据FULL_CYCLE_P40_DELIVERY.json。三档实际10s、总4starts含首失败与明确追加mesh，全回收/原截止不延；time四指标PASS，mesh峰温差7.33335%>2%FAIL、directextent网格未资格，CaO/strictOH+carbonatefail保留。500=144literature356assumed0measured、名义direct未启用；历史0.135892078740%干燥/P34旧30/81保持。P40及完整模型仍partial/wholefalse。未下载/解包/恢复，不把metadata当恢复；原件/独有历史保留，20GB/历史全备份/GitHub容量告警未解决。后续仅必要零积分离散定位候选，不在本P40额度再积分。
