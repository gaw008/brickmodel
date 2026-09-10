# 共享恒定体积下的干态压力差

本推导属于 `derived_from_evidence` 的声明模型数值关系。上游为实际
`SourceWetStorage` 的来源干物储能、`IdealGasPhase` 的气体储能与
`SourceDryPressure` 已检查的完整逆温度区间；不是新的材料经验参数。
来源 ID、R、固定干质量、体积和原误差随每个实际记录保存。

在无液水、固定干质量、关闭反应和理想气体热容合同下，
U(T)=m_d u_s(T)+Σn_i u_i(T) 与恒定可用体积 V 无关。因此每端原完整
温度误差可用于整个原 V±eV。此结论不推广到湿态、非理想气、变形功或反应。

令 N_a、N_b 是各实际 binary64 库存分量的精确和，T_a∈[L_a,H_a]、
T_b∈[L_b,H_b] 为独立区间。两个端点必须来自同一个实际 storage 和 volume
对象，才能共享唯一的 V∈[V_min,V_max]。内容相等的独立对象不满足条件。

计算 A_lo=R(N_a L_a−N_b H_b)，A_hi=R(N_a H_a−N_b L_b)。
压力差的理想区间是 A_lo/V_min、A_lo/V_max、A_hi/V_min、A_hi/V_max
四值的最小和最大；此公式也覆盖负差及跨零区间。各端独立误差 η_a、η_b
分别扩张，取扩张区间端点绝对值的最大作为联合界。

每个 η 包含实际保存的流体压力误差、原总误差加法的投影余量和完整 T/V
箱的前向舍入界。用原 `wet_fluid_pressure_bounds` 严格重建 global、extra、
total 三项并要求逐值一致；不从一个未知 surplus 猜测可抵消的体积误差。
投影余量为 |Fraction(total)−Fraction(actual_fluid)−extra|。

设 Nhat=fsum(n_i)，nr=float(Nhat·R)，dN=|Fraction(Nhat)−N|，
dnr=|Fraction(nr)−Fraction(Nhat)R|。令 S(x) 为向上表示到 x 以上的
有限正常 binary64 点处一个完整 ULP，则保守全箱舍入界为：

```text
s = S(|nr| H)
eta_box = (dN R H + dnr H + s) / V_min
          + S((|nr| H + s) / V_min)
```

全部角点和误差组合采用 Fraction。无法证明有限的舍入范围、完整温度域或
扩张后的单端绝对压力域，结果保持 unresolved；压力差小不等于绝对压力合法。
R 是当前模型已声明的同一数值常量，不附加虚构的常数统计不确定性。

最终只选择联合界。原独立界保留在旁，尚未证明它覆盖新增的完整机器误差
目标，不能直接取两者最小值。零体积误差的实际制造反例证实该区别；原草稿
失败保存在证据归档中。原 1e-4 Pa 事件门槛及旧失败均不改变。

本界仅支持声明假设下的数值比较。来源认证、材料资格和压力对自身的事件
准入均为 false；湿→干转换的数值接受还必须通过原 clock/N/U/T 与完整前缀
账本。它不能证明原污泥的真实烧结行为，也不能把旧保存 JSON 变成新的
live 共享参数证明。
