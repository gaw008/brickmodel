# P96：真实干燥起点的 RHS／Jacobian 单点诊断

P96 唯一科学窗口已完成；负库存尚未修复，整体模型仍未验收。读取真实 P68 drying_ramp 14400 s native275／context37，原 RHS 一次、原 Jacobian 一次，未重跑工艺。根参数仅新增独立导出行政合同；55 生产源码、758 科学参数、物理、容差及旧根合同条件不变。

实际窗口 wall 1.2037349161691964 s、子 CPU 0.9648389999999998 s、rc0，已 closed／reaped；case、point、stdout、stderr 共 2,480,216 B，在 120 s／4 MiB 内。0 重试、0 窗后生产调用。完整 RHS275、48×156 Jacobian、原 signed 输入、context37、config／source55、索引／单位／权重／计数保存在 runs/full-cycle/p96-saved-calcium-derivative-Jacobian/science，不将原始场加入 Git。

实际 native RHS157／Jacobian1，156 个复扰动列与原源码列序一致。必要内部 rates157，resolved-instance unpack314、condensed_state314、mechanical_rates157、elastic_response2983；这些是 strict load 后透明实例入口计数。构造器辅助调用、super 直接入口、NumPy／SciPy 原语和 Newton 内迭代未动态测量，不用源码预测代替。initial／ODE／额外 rates／decode／势值／梯度／summary／fit／UQ 为0。

对保存机器数的 Fraction 精确二进制解释，12 格 OH—脱水进度的加权 RHS 及 12×156 对应 Jacobian 行均精确为0。加权钙相 RHS 有12格非零差，最大绝对值 6.723289881361413e-57 mol/s；对应 Jacobian 有145个非零差，最大绝对值 3.1806645300722436e-38 mol/s。binary64 先乘再加另列，不能把运算后零与已舍入数的精确乘积恒等式混同；没有新增容差、判 PASS 或削除符号。

这限定了一个真实点：当前 OH 源和 Jacobian 行没有显示漏项／不匹配。P95 输入及端点的 OH—extent 状态偏离和三相负库存仍存在；单点不能还原旧 BDF 接受历史、Newton／LU 更新残差或定位唯一成因。越域输入的导数不证明物理有效、全轨迹非负或修复。

原两组干燥余水 0.1358920787402553%／0.1358920759321227% 高于原0.1%仍 FAIL；CaO零预算 null／false／undefined_zero_budget、P45及其它旧 FAIL、P78声明初态条件／历史t0缺失、高温assumed、direct synthetic290–350K、0measured、wholefalse 均保持。

仅生成一个最小后继提案，不自动修复或求解。普通 Git 与本地≤2MiB原始增量另列收据；本次没有授权新 P96 包外发，上传0、恢复0。P95云端包已获批准成功与本次新包权限分开。
