# Goal 验收矩阵

状态：`pending` 未实现或证据不足，`in_progress` 正在实现，`verified` 有相应范围实证，`gap` 已识别证据缺口。不得将本表条目被记录等同于通过。

| ID | 合同要求 | 应有实现/证据 | 当前状态 |
|---|---|---|---|
| G00 | 完整合同、分支、WIP保护 | 合同、Git基线、BASELINE_AUDIT | verified（仅初始化） |
| G01 | 持续进度、恢复、阶段提交 | GOAL_STATUS、实际提交与恢复记录 | in_progress |
| G02 | B2失败定位与必要修复 | B2_ROOT_CAUSE、0634e80、b2-bound-0634e80实际绑定22情景/审计 | verified（仅原B2域） |
| E01 | 八种知识/输入类别，禁止混用 | schema、分类校验/测试 | in_progress |
| E02 | 逐参数具体原文定位和元数据 | source/parameter registry及核读证据 | in_progress |
| E03 | 派生/转换/拟合链完整 | 依赖图；IAPWS与Baloi原值/单位/派生代码已核查，全结果链尚未闭合 | in_progress |
| E04 | 来源文件、hash、日期、许可 | 合法原始缓存与registry | in_progress |
| E05 | 材料/气氛/温压/几何匹配 | domain gate与域外测试 | in_progress |
| E06 | unknown传播、无默认补值 | 下游阻断、fixture隔离测试 | in_progress |
| E07 | 参数相关性与不确定性依据 | 成套材料包及joint约束 | pending |
| E08 | 任意结果能查询到原始证据 | CLI和UI trace端到端 | pending |
| M01 | 原污泥与SSA等身份分离 | materials身份类别+测试；真实包仍未核准 | in_progress |
| M02 | 元素/氧化物/矿相/LOI分离 | MassAnalysis typed类别/基准；phase独立ID，运行资格仍待接入 | in_progress |
| M03 | 湿坯初态、成型水不重复 | prepare_green_batch水账目通过；完整相库存待实现 | in_progress |
| M04 | 明确原污泥材料域可全周期运行 | 来源完整案例；不能用fixture替代 | pending |
| P01 | 一维厚度场、几何适用性 | 网格、边界、尺度论证与收敛 | in_progress |
| P02 | 炉温/壁温/气氛分段程序 | BoundaryProgram 41测试；ProgrammedGasHeat 15测试，动态气体库与表面串联换热已在刚性气相组装，全湿砖待接 | in_progress |
| P03 | 导热/对流/辐射 | 半格/膜串联与非线性表面平衡；解析升降温及80独立根检查，完整材料域待验证 | in_progress |
| P04 | 液态水/蒸气迁移、蒸发 | 有据干燥本构与实验对照 | pending |
| P05 | 组成/温度储能、流焓、反应/相变 | PhaseStorage 22测试，给定相压力物种储能/条件反演；机械闭合与相变仍未实现 | in_progress |
| P06 | 原泥热解与残炭氧化分开 | 成套反应/计量/热效应证据 | pending |
| P07 | 必需矿物脱羟/分解 | 适用反应及独立/公开验证 | pending |
| P08 | 局部有限O2与真实边界交换 | 氧库存场、无氧/有限库验证 | pending |
| P09 | 气相含必要载气、组分缺口诚实 | 摩尔/质量/分压/总压/体积一致 | in_progress |
| P10 | 扩散/压力驱动流动及反馈 | 有据Fick/Darcy等、极限验证 | in_progress |
| P11 | 有据烧结/液相/黏度关系 | 覆盖判断；无旧sigmoid冒充 | pending |
| P12 | 孔隙/连通性/渗透及闭孔处理 | 同一几何库存、域边界事件 | pending |
| P13 | 收缩/密度/体积与变形输运一致 | 参考/当前构形推导及守恒 | in_progress |
| P14 | 冷却、适用域相变/应力 | 有据热力本构、边界、验证 | pending |
| P15 | 强度/破坏概率等不冒充实测 | 输出资格和unknown约束 | pending |
| P16 | 必需过程真实双向耦合 | 开关耦合变化+账本集成测试 | pending |
| X01 | 候选是可操作、自洽设计 | 混配/粒径/水分属性联动 | pending |
| X02 | 批量实验可取消、恢复、限资源 | 持久任务和恢复/超时测试 | pending |
| X03 | 敏感性与有依据不确定性 | 分类型误差、关联采样、分析 | pending |
| X04 | 真实多代、父子关系和停止标准 | 实际评估/失败/选择记录 | pending |
| X05 | 冻结模型/材料/目标/种子 | 不跨版本混分的运行测试 | pending |
| X06 | 多目标/约束及候选重新复算 | Pareto、复算、未验证指标排除 | pending |
| X07 | 事件时间/局部残碳/未达事件 | 定义、阈值依据与采样误差 | pending |
| X08 | 数值失败/缺证/域外/约束分开 | 类型化状态及搜索行为测试 | pending |
| V01 | 事前登记验证与容差理由 | VALIDATION_PLAN及版本记录 | in_progress |
| V02 | 单位/计量/比例/正性 | 独立针对性数值测试 | in_progress |
| V03 | 传热/扩散/密闭反应/有限氧极限 | 解析/半解析/制造解，独立oracle；G2刚性气相/反应已实际积分，全湿砖仍待实现 | in_progress |
| V04 | 时空收敛与刚性失败 | 刚性气相导热空间/时间二阶及失败证据已验证；全耦合收敛未完成 | in_progress |
| V05 | 分时段质量/元素/能量独立账本 | conservation独立分格/分步/前缀审计已实现，完整多相储能重建待接入 | in_progress |
| V06 | 不静默clip/改阈值/删除失败 | 修正记录与回归检查 | pending |
| V07 | 干燥/传热公开实验验证 | 来源、条件、留出/拟合、误差 | pending |
| V08 | 原泥反应或残炭公开实验验证 | 同上，区别char制备条件 | pending |
| V09 | 烧结/收缩公开实验验证 | 同上，区别SSA与原泥 | pending |
| V10 | 未调参条件预测及独立层级 | split记录及独立对照 | pending |
| V11 | 尝试耦合过程外部对照 | 实测对照或明确未验证范围 | pending |
| V12 | 干净环境全流程运行 | 锁定依赖、实际命令/产物 | pending |
| V13 | 当前平台与声明平台实测 | 平台报告；无假支持声明 | pending |
| V14 | 畸形/域外/缺项/恢复检查 | 真正的集成反例 | pending |
| U01 | 共享内核的Python/CLI/UI | 同输入一致性与实际启动 | pending |
| U02 | 输入校验/单例/批量/UQ/搜索/重放 | 所有命令实际运行 | pending |
| U03 | 中文界面编辑/取消/失败/比较 | 浏览器实测及证据 | pending |
| U04 | 曲线/空间场/未知项/来源跳转 | 浏览器与trace集成实测 | pending |
| A01 | 世界/政策/方程代码映射文档 | WORLD_SPEC,EVIDENCE_POLICY,EQUATION_CODE_MAP | in_progress |
| A02 | 支持域/已知缺口/验证报告 | SUPPORTED_DOMAIN,KNOWN_GAPS,VALIDATION_REPORT | in_progress |
| A03 | 运行原始输入/轨迹/账本/状态/报告 | 成功和失败均持久化 | pending |
| A04 | 物理/数值与代码审查问题关闭 | 实际审查者、证据与修复记录 | in_progress |
| A05 | 软件/科学/部署三维状态 | 全部入口/报告一致 | pending |
| A06 | 最终可操作说明与Git证据 | 真实启动/迭代/溯源命令和产物 | pending |

可选项目：整窑CFD、复杂三维断裂、ML替代模型不作为通过本合同的替代要求；若实现，其声明同样必须有相应证据。所有必需条目保持原合同语义，不能通过拆分或删减矩阵来降低完成条件。
