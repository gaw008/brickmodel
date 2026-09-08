# 多格自由相容形变与局部约束功

基线5c5f09a。新增CurrentSolidStorage、free_slab_rates、FreeSolidSlab；integration的free功schema新增mechanical_constraint。实际状态(n_i,t,N_i,E_i)经当前网格逐格反解，使用同一真实温压组装共享面，再全局求共同横向速率，逐格分配不可省略的约束功。

MECHANICS.md为从现有制造势能定义直接推导的约化力学，不冒充文献给出的原泥材料定律；TRANSPORT_HOST_SEAM.md给当前几何/单次反解入口；CODE_REVIEW.md记录独立设计、源码与实际结果检查。CurrentSolidStorage与已验证Dynamic单格接口暂时并存，后续共用核心提取必须保留原字节兼容，不在此阶段伪造统一。

- 原缺模块、原schema拒绝RED保留。Current点候选原始9项及中间误差测试修正记录在current-storage-candidate.zip。
- 新瞬时率17项0.13s；新旧点/率56项0.60s；组件49项1.43s。原始XML分别保留。
- 主机+独立干态轨迹4项1.43s：.1s两cap实际6/8steps、1/0reject，局部E误差1.605862e-6/6.980263e-7J，伸长误差3.928028e-8/1.706953e-8，原门槛通过；全prefix能量最大2.206839e-7J。漏约束功的负对照仍可过全局守恒但局部错.0810722J。
- 真水fixedphase两格wet01：41.693s通过，1/2steps，8/15eval，13.1258/24.5859s；T终值299.9999889194692/300.99999007520626K，两cap表示相同。外功最大4.208e-11J；全部full轨迹/账本与源hash在wet01.json/status，原命令/日志/XML保留。独立结果复算见审核。原材料等效常数和exact-volume误差仍是制造定义。
- 非editable离线安装实际61模块测试前后与源码逐字节一致；/private/tmp cwd无PYTHONPATH，150相关测试8.46s通过。之后只增3项测试，再实际安装验证3项0.535s通过（21deselected，不是skip）；代码无变化。最后源码24项0.65s补充门槛也保留。没有重复高成本wet原生计算来补安装数字；dry独立轨迹安装运行输出与源码相同，见installed-tests.log。

源码主机b78efa42、率21bc4cb2、点4b94d58a的完整hash在审查/安装身份中。wet运行时160源/测试hash由独立代理复核，当时一致；后来两测试文件追加3守卫有独立XML，原snapshot仍保留，不能声称所有测试文件仍与wet快照逐字相同。

范围：当前新主机的实际湿态集成验证有共享热流、固定库存和自由力学，没有活动蒸发、液体迁移或非零气体面流；也没有真实原泥材料、空间收敛、烧结冷却或外部实验验证。下一步按原Goal接入相变/耗尽、非零物质输运、组成相关骨架反应及炉温程序，完整停止条件仍未满足。
