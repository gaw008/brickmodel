# B2 调用/预算预登记

本次隔离实现仅标准库，单进程/单线程；代码/LLM墙钟上限3600s，数值累计≤900s，峰值RSS≤512MiB。

开发 RED/GREEN 优先做不积分的输入/系数/单步/状态/路径测试，记录实际命令。正式源快照提交后：
1. run_tests.py --out validation/tests001 --budget-seconds 300：A-SEALED 3次，A-DIFF 6次，B2 R回归4次、B1安全副本哨兵4次，W03/L02/C03每个空间3次+时间2次（共享N31/dt.25）共15次；合计32次额外积分。预留8次仅已指名C01/C02/C04控制与失败路径，不增加参数case。
2. run.py --suite frozen --out validation/demo001 --budget-seconds 180 --verification validation/tests001/verification.json：22默认；从启动计时包含证据绑定/审计/报告。
3. audit.py只读，超短预算0.000001真实exit3；构建≤20MiB离线包。
4. 在本模块内新副本离线重放；不得自动重跑失败的全套demo；若超限/数值门失败，停止报告Manager，不增预算或放宽容差。

GOV-002独立Safety不由Engineer写passed。合法custom即使同名W03只能audit_only；本轮production_approved=false。
