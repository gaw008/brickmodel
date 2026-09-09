# 当前局部水根接入实际 provider 的下一接口依据

本研究只读现有来源与代码，没有运行 EOS、饱和计算或修改仓库。以下是可直接实现的证明接口和数学步骤，不是已经通过的证书。候选研究域明确为 **295–310 K、10^4–10^7 Pa**；这是拟认证矩形，未修改现有 provider 的原范围或运行门槛，范围外仍拒绝此新证明接口。

## 1. 当前证据能证明什么

coupled_rectangle 已能在给定 T、V 和密度矩形内，以完整区间的异号面及正导数证明每个参数点有唯一局部机械根。它没有区分同一 EOS 的稳定液体、亚稳液体或另一条局部分支。当前 `_heos_kernel.py` 的单点运行先解两相共存，再比较压力并检查密度分支；这些单点行为没有给整个温度区间提供饱和线包络。

IAPWS-95 2018 第4节及表3给出同一自由能的两相共存条件；第5节讨论稳定流体范围与亚稳外推。它还明确辅助饱和公式与完整 EOS 的结果不完全相同。故不能把辅助公式或一次 native QT 返回当作本 EOS 的严格饱和上界。[IAPWS-95 官方原文](https://iapws.org/relguide/IAPWS95-2018.pdf)

IAPWS 的饱和补充发布将其简单关联式定位为方便的近似及初值来源。这里可以用它选数值初始框，但最终通过条件必须来自完整 EOS 的区间残差与包含关系。[IAPWS 饱和补充发布](https://www.iapws.org/relguide/Supp-sat.html)

## 2. 必须保持三种身份独立

1. `local_mechanical_root`: 现有严格局部根包络。
2. `stable_liquid_branch`: 新的全 T 区间共存线包络及从饱和液体到当前根的同一液体分支连接证据。
3. `provider_numerical_correspondence`: 此数学 EOS 与实际 `HEOSWaterProperties`/Python provider 的来源、坐标、舍入和原误差合同的联系。

其中任何一项缺失都不能让 `pressure_radius` 接受普通湿态。`stable_liquid_branch` 通过也不能把原 `manufactured` 液体体积误差提升为真实实验或 native 数值误差认证。

## 3. 全区间饱和线：现有二阶密度 Jet 足够构建首个求证器

建议新增研究级 `enclose_coexistence(T_interval, rho_liquid_box, rho_vapor_box)`。未知量选 x=ln(rho_l)、y=ln(rho_v)，其中 rho 为 **native mol/m³**。EOS 使用 JSON 中的 native R、reducing T/rho 及同一 alphar；不得替换成气体混合物的 R。

令 delta=rho/rho_c，A=alphar，D=1+2*delta*A_delta+delta²*A_delta_delta。对给定 T，构造：

```
f1 = rho_l*(1+delta_l*A_delta_l) - rho_v*(1+delta_v*A_delta_v)
f2 = ln(rho_l/rho_v) + A_l-A_v
     + delta_l*A_delta_l-delta_v*A_delta_v
J  = [[rho_l*D_l, -rho_v*D_v],
      [      D_l,       -D_v]]
```

f1 是两压力差除以 R*T；f2 是两 Gibbs 自由能差除以 R*T。同温度的理想项除 ln(rho) 外相消，所以不需要给当前原语新增全部理想自由能函数，也不需要新的熵零点。上述 Jacobian 可由当前 `residual(...).value/first/second` 构造；这里的 x/y 导数只针对密度，T 是区间参数，不需要以离散温度导数假冒全区间界。

用有向区间 Krawczyk/区间 Newton：整个 T 子区间都进入 f(center,T) 与 J(box,T)，严格证明映射在密度框内部，并保留排他性条件。点逆矩阵只能充当预条件器，不能自身充当证书。成功后保存两相框、全区间 D_l>0/D_v>0、rho_l>rho_c>rho_v>0、共存压力区间及算子的严格包含余量。失败只细分温度/密度框或返回 unresolved，不能以迭代残差小替代严格包含。

开始按数值策略切成 1 K 的 T 子区间；这是可修改的求证网格，不是物理参数。覆盖清单必须无缝覆盖 [295,310]，各框重叠处以唯一性/交叠证据确认同一饱和分支。一次框内唯一性不自动证明全 EOS 不存在别的数学共存解；需结合 IAPWS 的物理分支定义及密度分离，并明确该分支对应关系的证据层级。

## 4. 稳定液体的可执行域检查

对每个 T 子区间生成 `SaturationBranchCertificate` 后，检查本次**整个压力包络下端**严格高于该区间饱和压力上端；同时保持实际 provider 的原饱和模糊带。例如 HEOS 当前模糊带规则为 max(0.01 Pa, 2e-8*p_sat)，必须在饱和区间上取保守最大值再做比较，不能删掉。

仅 `P > psat` 仍不足以认定任意高密度局部根是原 liquid 分支。须把饱和液体密度框连接到候选根框：对连续密度管全 T 范围验证 dp_native/drho>0，记录饱和端与局部框的包含/交叠；跨度大就细分密度管。这样固定 T 上 p(rho) 严格单调，已知液体饱和根与当前机械根位于同一连续分支。若细分不能证明正导数，不准跳过中间区段仅检查两端。

最先验收应是 **全 [295,310] K 上饱和压力上界加原模糊带 < 10^4 Pa** 的真实区间证明。此处不填写一个未经本程序认证的 psat 数值。之后认证到 10^7 Pa 的液体分支管。失败不会改变原压力范围，而是说明新接口尚不能覆盖请求域。固态排除依托官方稳定流体适用范围；若需要形式化越过熔化边界的证明，应另接官方熔化曲线，不能让局部 EOS 密度导数承担固液稳定性的证明。

## 5. public/native 转换及原误差必须原样进入最终接口

实际 descriptor 已显示 M_public 与 M_native 最末位不完全相同。必须保存两者原 hex，令 scale=M_public/M_native（精确值外包区间）：

```
rho_mass_native = rho_molar_native * M_native
v_public = M_public/rho_mass_native = scale/rho_molar_native
Vgas = Vbulk - sum(m_s*v_s) - Nl*scale/rho_molar_native
```

Nl 与气相水继续是项目 public mol 坐标，不改变库存以迎合 native 密度。pEOS 用 native EOS R；气相压力用原显式 Rg。`_heos_kernel._snapshot` 另用 public R_specific 检查压力残差，其容差是一次运算检查，不是允许默默替换数学 EOS R 的依据。

给最终 `pressure_radius` 的记录至少带：source JSON/PDF SHA、完整 provider descriptor/实现 SHA、M 两种 hex 与 scale、原状态/材料/参考身份、完整 inverse T 区间、原 bulk 与 Nl*liquid_v_error 体积预算、饱和/分支/机械根证书ID、原 fixed-T P 误差、全 T/V P 半径。所有区间和最终误差求和使用向外舍入。保持原 fixed-T 误差额外相加；不要因重复可能性而未经证明相减。

当前 `liquid_v_error_m3_mol` 和其他 envelope 值若仍属制造的数值声明，输出资格必须继续写 `conditional_on_original_manufactured_envelope`。即使数学分支已证明，也不能称实际 native 误差或材料不确定性通过。

## 6. 与实际 provider 相接的最小追加检验

- 精确匹配 JSON source、native二进制/版本、public形成参考、source资产、M/R 坐标；单独 Python IAPWS 与 HEOS 不能因为都叫 IAPWS95 就共用证书。
- 实际返回密度转换后落入已证液体分支管；对返回的精确 binary64 T/rho 用数学区间计算 EOS 残差，结合该局部区间的正斜率界约束密度偏差，不能把 native 自报 residual 当准确上界。
- U 反解温度误差的原来源和数值合同仍须成立。新压力证明不自动验证 Cp/U/du_dp；这与相稳定性不同，必须分别保留 failed/unavailable。

建议接口返回独立 flags，而不是一个泛化 `certified=true`：`mechanical_root_proved`、`saturation_box_proved`、`liquid_branch_connected`、`native_correspondence_checked`、`error_envelope_classification`。在只有前三项时允许研究导出，仍不准将 ordinary wet stage 伪装成全部误差门槛已认证。

## 本次已完成与下一步

本次建立了具体两变量残差/Jacobian和跨温区间求证接口依据，核对实际provider分支策略和public/native变换；未执行上述求证器，未声称范围认证成功。下一实际实现应首先补 `enclose_coexistence` 的区间Krawczyk与失败框记录，而非再跑16个点或直接调低现有P门槛。
