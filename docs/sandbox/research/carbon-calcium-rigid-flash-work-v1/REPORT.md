# 定容压力求根中延后热容计算

2026-09-25 UTC。压力求根的试算只需要总体积；现在只在最终压力上计算完整热容响应。平衡方程、来源常数、根精度和输出字段保持原定义。公共定压入口仍返回完整响应；研究用正库存模型同步覆盖内部平衡入口。

## 实际核查

- 三十二格已保存轨迹的30个状态重复10遍：原0.366699s，修改后0.259163s，300次调用实际耗时减少约29.3%。30个完整状态字段精确相同。
- 原108个定压状态、60个正库存定容状态及研究模型60个定容状态的完整字段精确相同。
- 八格精细档重新走完20000s：2706个接受步，81.236s；此前同算例115.14s。1000个观测时刻的温度、压力和物种差均为0。
- 两条八格轨迹分别复核29656个记录状态和129888个Gauss节点状态。来源、逐格元素/U/S、2/4求积、负熵步及时间预算全部通过；最大全局能量残差5.243601e-8J，熵账残差4.552246e-11J/K。
- 新原始记录103540720B，分成两个无损压缩部分共25104604B；逐字节还原一致，不使用SHA。

结果见根参数 `parameters.carbon_calcium_rigid_flash_work.json`、`parameters.carbon_calcium_temperature_deferred_caloric_audit.json`、`parameters.carbon_calcium_temperature_deferred_caloric_archive.json`，以及 `data/sandbox/research/carbon-calcium-rigid-flash-work-v1/` 和温度列目录内 `eight-caloric-deferred-*`。

本次仅减少无用运算。计时只描述所录负载；不增加材料、气体化学势库存Jacobian、空间收敛或真实烧砖资格。`material_qualified=false`、`training_eligible=false`。未新增或执行软件测试。
