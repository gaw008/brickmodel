# 动态固体/流体边界主机上的水相变

WaterPhaseTransfer 现在显式接受第三种主机 ProgrammedSolidFluidHeat。结构为 `WaterPhaseTransfer → ProgrammedSolidFluidHeat → SolidFluidHeat`，没有反向循环依赖或鸭子类型准入。

只在来源身份、制造门禁及完整库存列定位时获取program.base_model。实际每次evaluate仍调用外层program主机，使用当时边界的气体面流与热量，再加入原有等mol液水→水汽源。`WaterTransferEvaluation.base_evaluation` 原样保留完整 `ProgrammedSolidFluidEvaluation`，包括boundary/reservoir、表面温度、热平衡残差、真实storage_states与完整inverse，而不是伪装成静态FluidHeatEvaluation。

制造门禁同时包含相变系数、program新增换热系数、底层输运、气体热量、固体和几何分类。虚拟边界程序是显式设计输入，不冒称观测；所有source IDs继续汇总。理想水汽/真实液水的共同参考、固定pref及水源资产身份门禁不变。仅加库存相变，不额外添加潜热到U。

`breakpoints_s(start,end)` 动态主机转发程序节点，两个静态主机返回空tuple。当前integrate不会自动发现该方法；调用者必须显式写 `integrate(...,breakpoints_s=op.breakpoints_s(start,end))`。本轮积分测试实际这样传入，不声称只新增方法就能阻止跨节点步进。

测试先写，第一次收集因新programmed模块不存在而ModuleNotFoundError。新测试计划：第三host真实动态边界诊断保留；显式节点转发；动态外热+真实水相变的积分，核固体/载气不变、水两相总mol不变、总U变化与累计边界face_energy_j一致，源项无额外cell_work；静态主机空节点；制造授权与伪装对象拒绝。测试所有固体、输运、几何、换热和相变速率/数值界均沿用明确制造fixture，不能据此准入原泥材料。

程序节点0、0.0005、0.001s，外气温度330、340、335K，关闭外气物种输运，仅开启外热与水相变。因此水两相总库存应守恒，能量由同一面账本核对。动态压力/组成驱动气流属于program主机自身测试范围，不在此重复声明。

实际命令：`PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_programmed_water_phase_transfer.py -q`，5 passed in13.96s。原两个主机的相变回归交独立审核者最终串行执行，避免重复并发重CPU；本记录不预报旧回归结果。
