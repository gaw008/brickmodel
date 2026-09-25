# 等温多孔气体输运：局部来源与熵资格计划

2026-09-25 UTC。四气体自由扩散之后，需要分别处理分子间摩擦、孔壁摩擦与压力黏性流。采用[Cantera 3.2 DustyGasTransport明确给出的原方程](https://cantera.org/3.2/cxx/dc/de6/classCantera_1_1DustyGasTransport.html)；同版本头文件、实现和BSD许可证已经保留到本地。只取等温局部关系，未复制其组分偏移、隐式渗透率或有限面中点算法。

原方程为 Σ(j≠i)(x_j N_i−x_i N_j)/D^e_ij + N_i/D^K_i = −grad(c_i)−(c_i/D^K_i)(κ/η)grad(P)。有效D为(ε/τ)D_free，Knudsen系数为(2/3)(rε/τ)sqrt(8RT/(πM_i))。全部流以静止固体和材料总截面积为参考，不要求ΣN_i=0。c_i是孔内气相体积浓度。

生产计算把N拆为扩散部分c x_i v_i及Darcy部分−c x_i κ grad(P)/η。这里v是按材料总截面积定义的表观速度，而非孔内实际分子速度。前者用对称摩擦矩阵求v：非对角为−x_i x_j/D^e_ij，对角再加x_i/D^K_i；右侧−x_i grad ln(c_i)。独立80位参考直接求原非对称浓度方程的总N，避免只与同一种矩阵装配比较。

等温理想气体的熵产生−RΣN_i grad ln(c_i)，可分为三个非负量：cRΣ(i<j)x_i x_j(v_i−v_j)²/D^e_ij、cRΣx_i v_i²/D^K_i、κ|grad(P)|²/(ηT)。这里壁碰撞项使用扩散速度，Darcy耗散单独计账。此恒等式从上述分解推出，作为待核查的项目推导，不声称引用来源已经验证了本实现。

事前冻结3个T、3个P、3组组成、3组明确虚拟孔结构与4种组成/压力力；补充κ=0数学极限、单物种解析限、物种重排、全部梯度反号和零力。根JSON冻结80位精度和全部预算。Knudsen系数另与源公式直接高精度比较；不靠调渗透率或改变熵符号闭合结果。

虚拟孔取直圆管束，ε=0.3、τ=1、半径0.1/1/10μm，渗透率按[Poiseuille连续层流关系](https://openstax.org/books/university-physics-volume-1/pages/14-7-viscosity-and-turbulence)推得εr²/8。仅表示黏性项的模型几何；Dusty Gas的稀薄—连续叠加不是完整Boltzmann解，也没有实际砖孔结构证据。纯气物性和Wilke近似的实验不足保持，不把来源算术通过提升为实材精度。

本阶段不求整列，不含热方程、热扩散、反应、孔径演变或烧结。局部来源和熵全部通过后才考虑有限面与完整时空演化。`material_qualified=false`、`training_eligible=false`。无软件测试或SHA新增。
