# P85 实际最终冷却保温比较

完成了一次真实、原程序的最终 `cooling_hold` 比较。采用 P80 实际加密冷却终点 154800 s，保持原 275 维状态、37 项上下文和绝对时钟，续算至原 162000 s。生产源码54逐字节不变；根758完整参数保持144 literature、614 assumed、0 measured，名义60s/rtol1e-5/atol1e-7与原P80冷却专用声明不改。最终段使用独立 `cooling_hold_half_step` 30s 声明，solver与保存effectiveconfig一致。

唯一窗口wall=12.134509292s，CPU=11.829464000s，四科学文件=3937159B/4194304B，rc0/reaped。真实RHS3153、Jac16，与solver nfev/njev/nlu=657/16/107分别报告。1load/ctor/solve/newendpoint/decode/completevalue/interval，0initial与baseline/reference重求；内部rates和其他primitive未独立测量，原sourceforecast保持其身份。没有额外科学调用或重试。

| 指标 | 粗解原值 | 加密原值 | signed差（加密−粗） | 原分母 | relative差 | 原门槛 |
|---|---:|---:|---:|---:|---:|---:|
| porosity [1] | 0.48616934273480245 | 0.4861698468928175 | 5.0415801505776514e-07 | 0.4861698468928175 | 1.0369997610504078e-06 | <0.02 |
| residual_carbon_kg [kg] | 6.855517882526166e-21 | -9.3074176978023568e-22 | -7.7862596523064015e-21 | 9.9999999999999995e-08 | 7.7862596523064013e-14 | <0.02 |
| shrinkage [1] | 0.0066707361729363424 | 0.0066707328495032581 | -3.3234330842901727e-09 | 0.0066707328495032581 | 4.9821109003603029e-07 | <0.02 |

孔隙率使用原逐格bulk体积权重，残碳是organic+char的全域元素碳kg，负号保留。收缩仅相对P78新生成的共同declared初始bulk；原P68未保存t0不可恢复，原历史收缩coarse/refined均null、available=false。这三项通过仅表示原hold之后两段冷却半步的终态差低于门槛，不覆盖前六段完整时间加密、连续峰温或网格。

原final区间的质量、H/C/N/O/Al/Si/Ca元素、完整能量与熵、四气体预算账本均低原0.1%。最大primary relative为N元素3.2779534495e-5（0.0032779534495%）。完整原signed残差、预算分母、初始库存分母和进出/反应增量在配套JSON保留；气体与质量残差出现符号翻转，不裁剪。能量原signed残差−0.8182325324→−0.0026386166J，熵+0.0037219482→+0.0000160003J/K，分母仍原114147.479888J与382.852523522J/K。该比较不是独立新热源/反应热核算，也不授机械迭代/热力源外推资格。

严格非负仍失败：粗/加密最小char=−1.2666879580e-18/−8.5823508242e-20mol，负格数见配套JSON。加密全域残碳为−9.3074176978e-22kg；原1e-7kg仅比较分母，不能将负库存判为物理PASS。不得从一次加密推断唯一误差来源或反复加密到通过。

名义干燥0.1358920787402553%>0.1%继续FAIL；CaO零预算relative=null/passed=false/undefined_zero_budget、P45、原资源失败和已撤回历史PASS保持。高温portlandite/calcite热容及H2O黏度解析外推仍assumed，0measured。全程时间/网格/continuouspeak、最新三方案/反演、独立U/S机制资格与实材仍未完成；whole_model_complete=false。

下一最小范围仅建议源码静态核对惰性N2原生log库存与独立边界账本的有限BDF步兼容性，使用已保存真实输入。该候选未采用，无科学窗口、无新checker/solver/物性，暂停的jointBE/char理论不重启。不追加更细时间、完整过程或新空间计算。

Git普通后继/原Drive一次增量、metadata与实际恢复、历史存储分别记录在本轮final-delivery-state。metadata不等恢复，实际恢复0，保留压缩源；历史20GB与GitHub容量警告未解决。默认沙箱Git远端读取DNS失败和一次行政路径读取错误已留证，未发生自动审批拒绝。
