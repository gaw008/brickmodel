# 事前独立制造oracle计划

无EOS、生产模块或现有native重跑。仅标准库Fraction/Decimal，固定温度依赖线性稳定液体v(T,p)=v0+alpha*(T−320)−beta*(p−1e6)，beta=1e-14 m3/mol/Pa、alpha=1e-8 m3/mol/K、v0=18e-6。这些是显式制造解析公式，不充作真实水/污泥常数。

原机器算术独立手写：rho_float=float(m/v_true)，liquid_float=(nl_float*m_float)/rho_float，nrt=(fsum(gases)*R)*T，Fhat=fsum(liquid,nrt/P,-V)。声明eps=1e-18包含本构造输出volume roundoff，逐点评估先核该约束；不能事后增大eps。使用wide J=[8e5,1.3e6]Pa、V0=.001±1e-12，物理量正normal；fullT域[300,340]。nlA=.25，nlB=.25000001，gasA(.125,.25,1e-12)，gasB(.125,.25000001,1e-12)。另交换A/B、相同端near cancellation、nlB=.125三个固定案例。

至少：完整J正v与根端符号；Γ计算与25个固定P点×3个V点两端实际Fhat−精确G逐点比较；精确二次方程Decimal(100digits)根在J，每个V下两根差由D/c界覆盖；两个T误差箱各±1e-6K，独立计算真正T偏移根并核new continuation+原L不缩的桥接；原J比个体名义eP箱宽，新L-only不得偷偷沿用旧小初始箱。正/负D均由完整区间角点核验。

负例固定：根符号不包住、不同V不能消去、只两个采样点不能证明全域单调、vStarMin<=eps或下溢normal域拒绝。负例不依赖新生产入口。最多20秒纯计算；任何断言失败保留原输入/脚本/log，不改公式/门槛使其过关。

此为独立解析/机器算术制造验证，离散Γ点检查不代替全域符号推导；真实端点观测的ε/B与来源资格仍须其自己的证据/明确条件。
