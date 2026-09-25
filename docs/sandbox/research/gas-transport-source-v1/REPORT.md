# 四气体来源输运算术完成；氧气黏度参考对照未通过

2026-09-25 UTC。实现CO/CO2/O2/N2在300–1200K范围内的直接Lennard-Jones零偶极碰撞公式，输入和碰撞表均可追到固定Cantera v3.2.0文件；摩尔质量来自所选NIST历史汇编。所有计算可离线重建。该零偶极设定是所选GRI模型的近似，不代表CO的真实永久偶极严格为零。没有导入GRI热化学或反应速率，也没有修改已有虚拟砖内迁移系数。

根参数中的三列37项碰撞数据、四物种井深/直径/摩尔质量和NIST不确定度均与独立重读来源一致。40组纯气黏度和180组二元扩散在80位独立Lagrange/代数计算下，最大相对算术差分别3.478145e-16和3.889089e-16，小于1e-13原预算；二元交换对称和三个压力的1/P关系误差均为零，全部系数为正。这里只证明所选近似方程的实现准确，没有二元扩散实验验证。

| 气体 | NIST表估计不确定度 | 最大相对偏差 | 表范围加舍入内的点数 |
|---|---:|---:|---:|
| CO | 5% | 0.4970% | 8/8 |
| CO2 | 5% | 0.7366% | 8/8 |
| N2 | 3% | 1.5990% | 8/8 |
| O2 | 0.5% | 2.4989% | 1/8 |

对照温度300–1000K；各表半末位舍入幅度已在结果前冻结。O2在300、500、600、700、800、900、1000K超出范围，400K通过，不能放宽0.5%预算来使其过关。其他三气体通过的是较宽的历史表对照范围，不能解释为达到0.5%精度。所选页面未显式给出压力条件，所以所有物种的`pressure_matched_experimental_validation=false`；1100/1200K也没有本次NIST表对照。

举例：300K、100kPa的CO–CO2、CO–O2、CO–N2、CO2–O2、CO2–N2、O2–N2分子扩散系数依次为1.584002、2.095198、2.094778、1.578696、1.598060、2.114028乘1e-5m²/s。它们是自由稀薄气体一级近似结果，不是砖孔中的有效扩散率。

首次执行因脚本未加入项目src路径而失败，stderr保留；修复脚本入口后`source-review-v2.json`完成上述审查。未新增或运行软件测试，未生成或比较SHA；没有修改物理参数、拟合NIST表或调整预算。

## 来源与适用边界

- [Cantera固定GasTransport.cpp](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/transport/GasTransport.cpp)：单分子约化质量、碰撞直径/能量组合、黏度和一级扩散；源代码注明未应用二阶扩散修正。
- [固定碰撞表及插值](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/transport/MMCollisionInt.cpp)、[Ω11关系](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/src/transport/MMCollisionInt.h)、[GRI30输入](https://raw.githubusercontent.com/Cantera/cantera/v3.2.0/data/gri30.yaml)。已在source目录保存原文件和许可证。本模块直接评价碰撞积分，不复现Cantera随后拟合温度多项式的最终API值。
- [Cantera物种单位说明](https://cantera.org/3.2/yaml/species.html#gas-transport)：直径为Å，井深为K，未填偶极按零处理。单位转换显式保存在根参数中。
- [NIST确切常数](https://physics.nist.gov/cuu/Constants/Table/allascii.txt)：kB=1.380649e-23J/K，NA=6.02214076e23mol⁻¹。所得R为8.31446261815324J/(mol·K)，与当前USGS热化学历史R=8.31451不同，不能静默混用；本阶段模块独立，不更换历史热化学常数。
- NIST历史汇编[CO](https://www.nist.gov/pml/sensor-science/fluid-metrology/database-thermophysical-properties-gases-used-semiconductor-5)、[CO2](https://www.nist.gov/pml/sensor-science/fluid-metrology/database-thermophysical-properties-gases-used-semiconductor-4)、[N2](https://www.nist.gov/pml/sensor-science/fluid-metrology/database-thermophysical-properties-gases-used-semiconductor-17)、[O2](https://www.nist.gov/pml/sensor-science/fluid-metrology/database-thermophysical-properties-gases-used-semiconductor-18)：保存所读表格、URL和每页列出的文献。CO2/O2页引用REFPROP7.0，N2/CO页引用较早研究，不能称最新参考关联式。

下一物性任务是核对原始低密度参考关联式及明确压力适用性，优先解释O2偏差。多组分通量、孔隙/曲折率/渗透率、Knudsen及Soret需要各自来源和守恒/熵推导，未在本阶段接入。`material_qualified=false`，`training_eligible=false`。
