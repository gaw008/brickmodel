# 量纲与保守离散的Engineer推导（待独立Safety复核）

结论：共同时间尺度不可随壁厚或d_ref改变；finite库的双向通量必须与末单元转移同号相反体积系数更新。以下是代数推导，不是材料标定。

以实际L=ell L_ref、孔体积εAL、固定c_star归一化。物质方程ε∂c/∂t=D_eff ∂²c/∂x²−反应消耗；令t_star=ε L_ref²/D_star，τ=t/t_star，则扩散前因子D_eff t_star/(εL²)=d/ell²。Γ=C_s0/(εc_star)，一阶碳库存衰减给df/dτ=−Kfu，氧消耗为−ΓKfu；共同反应进度在CO2中为正。

表面实际流率h_ref(c_surface−c_ext)按εALc_star/t_star归一，得到h_ref t_star/(εL)=Bi_ref/ell=b。每单位ξ体积膜/半格阻力相加，g^−1=b^−1+Δξ/(2a_D)。密闭库dc_res/dt=A h_ref(c_surface−c_res)/V_res，rho=V_res/(εAL)，故du_res/dτ=J_u/rho。跨ell固定rho意味着改变库物理体积，不宣称固定V_res。

每个Euler阶段体内反应增量为(Δu,Δv,ΓΔf)=(-ΔQ,+ΔQ,-ΔQ)，所以Γf+v与u+v的反应变化均为零。内部共享面通量望远镜求和，只余外表面通量；有限库增量rhoΔu_res=ΔτJ_u、rhoΔv_res=ΔτJ_v抵消体内损失。名义质量12Γf+32u+44v的反应变化=-12ΔQ-32ΔQ+44ΔQ=0。

SSPRK2为起始态与两个Euler阶段后的状态各半加权；所有账本使用同权重，因此线性库存保持。非自治第二阶段必须使用τ+h处K/d/g；端点极值及阶段态分别复核正性步长，拒步减半而非clip。CO2累计生成和net outward不混同。

独立uniform sealed参考：du/df=Γ，u=1−Γ+Γf；改用H=∫K dτ分离变量得到f=(1−Γ)/(exp[(1−Γ)H]−Γ)，Γ=1时f=1/(1+H)。oracle.py用expm1稳定实现，真实Gamma0.25/1/2轨迹、独立分段Simpson收敛误差由run_tests保存，不预填数值通过。

有限氧预算由非负氧库存推出Γ(1−f_mean)≤1+rho（sealed去掉rho）；上界不是空间充分条件。由u≤1、df/dτ=−Kfu有f≥exp(−H)，只能用于必要时间暴露筛选。D/长度与K暴露都是机制坐标，不给真实通用合格线。

固定c_star、固定控制体积与给温只驱动系数，未引入状态方程；不宣称恒压空气、能量闭合或热膨胀流。实际系数、length配对、双向交换和stage-time raw tests另见coefficient_and_single_step_checks.json。
