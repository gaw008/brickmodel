# 四气体局部交叉扩散的方程资格通过

2026-09-25 UTC。新增等温等压理想混合气体的Maxwell–Stefan局部求解器，输出摩尔平均和质量平均参考系下的通量、两参考系相对速度与熵产生。物理关系来自[Bothe2010](https://arxiv.org/abs/1007.1775)式5/7/8、13/15/17/18及19–21。当前使用已来源复算的自由气体二元D；它们的真实实验精度未因本次方程验证自动提高。

108个四组分状态与80位独立原方程求解、54个二元Fick极限全部通过冻结预算。生产解速度对称摩擦矩阵，参照独立解通量非对称矩阵；二元D由保存的Cantera碰撞表重新用高精度Lagrange表达式计算。

| 核对量 | 最大误差或残差 |
|---|---:|
| 摩尔平均通量对高精度参照 | 6.136054e-18 mol/(m²·s) |
| 质量平均通量对高精度参照 | 1.680907e-18 mol/(m²·s) |
| 总摩尔通量 | 7.806256e-18 mol/(m²·s) |
| 质量平均参考系总质量通量 | 2.032880e-20 kg/(m²·s) |
| 原始四个MS方程残差 | 6.576771e-14 mol/m⁴ |
| 力乘通量熵产生对参照 | 3.742254e-15 W/(m³·K) |
| 两两摩擦熵产生对参照 | 1.756671e-14 W/(m³·K) |
| 二元Fick极限通量 | 8.322856e-19 mol/(m²·s) |

所有记录的熵产生非负，零梯度状态为零；参考系转换不改变熵产生。54个算例出现某气体自身组成梯度为零但通量非零，显示交叉影响。例如300K、50kPa、x=(.1,.2,.3,.4)、梯度=(0,2,−1,−1)/m时，CO的摩尔平均通量为−3.860577e-5mol/(m²·s)。这是指定数学条件下的模拟，没有复现任何具体实验。此次条件没有出现沿自身梯度的反向扩散，未宣称已演示该现象。

式17给出的对称正摩擦意味着A半正定：vᵀAv=Σ(i<j)xi*xj(vi−vj)²/Dij≥0；正组成下唯一零方向是共同平移。约束Σxi*vi=0排除此方向，因此局部解唯一。结合grad(xi)=−(Av)i，Π=−RcΣvi grad(xi)=Rc vᵀAv≥0。这是所声明局部本构的数学结论；不涉及任意非等温、不同压力或有限跳跃的离散面。

第一次启动因输出目录不存在而未运行；建立目录后的首次计算在JSON写入时遇到NumPy布尔类型，原stderr保留。将报告布尔值明确转为Python布尔后生成`local-source-review-v2.json`。物理公式、根参数与误差预算未改。未新增或运行软件测试，无SHA计算。

未加入Darcy、Knudsen、孔隙、Soret、反应或有限体积时间推进；与热反应模型连接仍需单独推导和全程验证。`binary_diffusivities_experimentally_validated=false`、`material_qualified=false`、`training_eligible=false`。

复建：`.venv/bin/python examples/sandbox/review_maxwell_stefan_isothermal.py --parameters parameters.maxwell_stefan_isothermal.json --output data/sandbox/research/maxwell-stefan-isothermal-v1/local-source-review-v2.json`。
