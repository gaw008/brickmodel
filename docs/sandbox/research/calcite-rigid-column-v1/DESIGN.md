# 刚性反应一维柱：空间阶段定义

以已核RigidCalciteMixture和rigid_reactive_face为单元/面，构造固定2cm长度、1cm²截面的封闭绝热柱。每格Ca=10000mol/m³乘单元体积，总C/N2/U为实际库存；两半初态按双小室算例的密度和温度给定。所有网格在中点有边，初态总库存和源内能相同，不通过每格归一化制造网格差异。

体积Vj=A dx，面导度G=kA/dx，Lb=lambda_b A/dx、Ld=lambda_d A/dx。k=.1W/(m K)、lambda_b=lambda_d=1e−7mol²K/(J m s)为明确虚拟连续场系数。每格dC/dt=Nc,left−Nc,right，dN/dt=Nn,left−Nn,right，dU/dt=Eleft−Eright；面流只计算一次；两端为零。总熵增长等于各面正定产生之和，各格熵率由(dU−muC dC−muN dN)/T重组。反应仅为瞬时平衡，尚无物理反应时间。

两格参数应复现此前两小室；之后4/8/16等格分别研究时间与空间误差。初态跨中点不连续，因此早期细化误差不能跳过却宣称全场收敛。禁止因目标未过而重新放宽目标。每个已完成轨迹须核来源重组、逐格守恒、熵和选定时间/空间观测，再报告适用范围。当前尚未完成空间资格。
