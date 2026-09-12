# ROOT 物理与算术复核

已完整阅读 SOURCE_HESS_DESIGN.md 及 hess_arithmetic.py。定义
C_U=DeltaU_*+kappa*q_rep 后，DeltaH=DeltaU+Delta(pV)，因此
H_F=H_P-H_O+kappa*q_rep-C_U-Delta(pV) 的符号正确。
若报告量已是同目标的负反应焓，C_U=-Delta(pV)，不得二次转换。

从保存原池独立逐元素重算，五项检查实际通过：指定完全燃烧计量D、
液态水产品的气体摩尔差、298.15K虚拟参考的理想气体pV项、原文Eq1
打印中心值重放以及名义0.5g热值缩放。见ROOT_CHECK01.log。没有EOS或
平衡调用，也没有重跑原源池。

源方法页的缺项说明合理；本ROOT复核使用作者实际核读记录和既有已核源包，
本次没有再目视PDF。脚本的assert用于默认未启用-O的独立研究算术，不能
用作不受控用户输入API。源文件SHA固定、未知基准/校正/凝聚PV未填零，
没有制造原料参考焓、原弹温度或烧成热耗。允许归档为符号能量约束与有限
算术结果，不授予整体原泥能量闭合或材料资格。
