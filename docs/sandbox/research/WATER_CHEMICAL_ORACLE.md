# 独立理想项化学势对照

本检查在运行脚本之前登记。它检查新化学势模型的推导与理想水汽近似的量级，不是污泥干燥验证，也不证明 IAPWS 全域误差界。

独立参考直接使用已核读 IAPWS R6-95(2018) Table 1 的常数，在脚本中计算理想 Helmholtz 项及其导数，不调用新化学势模块或上游 `_phi0`。饱和液体的 h、s、p 仍由已来源门控的 IAPWS 适配器提供，因此液相不是独立 EOS 实现。

固定标准压力 p0=100000 Pa，tau=Tc/T，delta=p0/(R95_specific T rhoc)。

- phi0=ln(delta)+n1+n2 tau+n3 ln(tau)+sum(n ln(1-exp(-gamma tau)))。
- phi0_tau=n2+n3/tau+sum(n gamma/(exp(gamma tau)-1))。
- h_g=R95_molar T (1+tau phi0_tau)+共同能量平移。
- s0=R95_molar (tau phi0_tau-phi0)。
- s_g(T,p)=s0-Rmix ln(p/p0)，mu_g=h_g-T s_g。
- mu_l=h_l-T s_l，peq=p0 exp((mu_l-h_g+T s0)/(Rmix T))。

T 为 293、298.15、313.15、333.15、373.15、423.15、473.15、500 K。原始常数、脚本、来源文件及运行输出均保存 hash。比较新模块的 peq 相对误差门槛为 1e-10，h 和 s 绝对差分别为 1e-6 J/mol 和 1e-8 J/(mol K)。这些门槛只衡量代数/浮点实现的一致性。

peq/native_psat-1 是近似差异，必须完整报告，不设“应等于零”的通过门槛。两相共用 native IAPWS 熵约定与同一能量平移；没有把熵改称 NIST 绝对熵。标准压力固定是模型定义的一部分：native R95 与 Rmix 不同，不能任意改变 p0 而不同时修正标准熵。

单纯饱和液参考对照不意味着混合模型的纯水两相机械平衡已解出；液体稳定支要求与总压力仍需单独检查。真实泥料的活度、毛细压力及相变速率系数均未由此取得。
