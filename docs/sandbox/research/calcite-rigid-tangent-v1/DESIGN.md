# 刚性反应状态的分支内解析导数

本阶段是已声明条件模型的数学响应核查，不新增材料事实，也不绕过一维柱尚未通过的空间资格。

固定Ca库存A与总体积V，守恒坐标为y=(C,N,U)，气相CO2量g。令d=vc−vl，B=V−A vl−C d，Vg=B+g d，P=(g+N)RT/Vg。两固相共存时，f=ΔG°−(P−p°)d+RT ln(gRT/(Vg p°))=0，且：

- fg=RT(B²+g N d²)/(g Vg²)>0；
- fC=d(RT−P d)/Vg，fN=−d RT/Vg；
- gC=−fC/fg，gN=−fN/fg，gT=ΔU/(T fg)。

ΔU=ΔH°−RT+p°d；固相u=h°−p°v，气相u=h°−RT。U=A ul+C(uc−ul)+gΔU+N un，因此UT=Cv,eq，UC=uc−ul+ΔU gC，UN=un+ΔU gN。得到dT=(dU−UC dC−UN dN)/Cv,eq，再由dg=gC dC+gN dN+gT dT重组。单固相分支g随C一比一变化，gC=1、gN=gT=0。相边界存在分支导数变化，不做平滑、不赋予有限反应时间。

由d(μi/T)=−hi°dT/T²+R dln(pi/p°)，解析重组熵Hessian，核对Maxwell对称和局部凹性。交换面使用同一平均h、平均摩尔分数与两种Onsager模式的完整乘积法则，包含平均h和摩尔分数的变化；无账本反馈列。柱Jacobian组装为邻接稀疏矩阵，不改变速率方程。

先在预先登记的单相与共存状态、有限差分步序列、相同/不同状态交换面上核对导数，再进行相同初态与参数下的轨迹对照及完整守恒/熵积分。差分截断、舍入与相边界须分开报告；参数、缩放和预算位于根目录参数文件。原物理库存差分路径保留为独立轨迹对照。
