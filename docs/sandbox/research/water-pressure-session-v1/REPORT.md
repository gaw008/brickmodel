# 累计压力计算会话

三个正式模块provider_v2、pressure_seed、pressure_session已独审应用。数学原语和原误差门槛不变；新结构化失败类型、实际数值初值记录及跨查询累计预算分开保存。旧provider类与结果字段保持原字节实现。

会话时间从创建起计，包含中间host计算；seed与四类proof操作各自累计，不把任何计数冒称全部底层EOS求值。unknown child成本会阻止继续计算。native_calls=0仅表示会话不新增原生物性查询。

独审13项及3独立负控通过；与stage一起的正式源码/非editable安装各110项通过（20.23s/20.07s）。当前104模块。原文档用词No EOS已纠正为No native EOS calls，原版本保留。此处纯测试不构成真实材料或时间步准入；实际运行证据另存。
