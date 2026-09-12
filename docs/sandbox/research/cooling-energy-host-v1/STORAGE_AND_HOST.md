# 储能反演与原生能量宿主

以下储能推导和候选测试说明来自已独审的候选文档，候选阶段的“未积分”陈述只描述该阶段。后续正式执行结论以本研究REPORT为准。生产storage与最终候选逐字相同；host仅改包导入路径；见PORT.json和审查报告。

# Pure reference thermoelastic energy storage and global inverse

Scope: the already frozen `CoolingThermoelasticPlate` potential, constant explicit M/alpha/C, uniform reference half-plate, free symmetric plane stress and zero membrane force. This module adds the extensive energy state needed by a future native host. It performs no time integration, adds no inventory/fluid/reaction law, and supplies no material parameter. `material_qualified=false` remains mandatory. The frozen plate source is SHA-256 `33851857946f16b560529ad8a9d3ab1bc4fec6c1a18ae63bb9897d77a03746d7`.

## Mathematical state and units

M is Pa, alpha is K^-1, C is J m^-3 K^-1, T and Tr are K, and V is the fixed reference cell volume in m^3. E is **total internal energy in J per cell**, including thermoelastic internal energy; it is neither temperature nor Helmholtz energy. Let b=M alpha^2, N be the number of cells and mu=sum(T_i)/N. The supplied potential gives

```
e = alpha (mu - Tr)
E_i(T,e) = V [C (T_i-Tr) + M (e+alpha Tr)^2 - b T_i^2]
E_i(T)   = V [C (T_i-Tr) + b (mu^2 - T_i^2)]
J_E      = diag(V (C-2b T_i)) + (2b mu V/N) 1 1^T
```

`at_strain(T,e)` exposes the first relation without force elimination. `forward(T)` uses the second and reports the free common strain. The symmetric J_E is the energy inverse Jacobian. It is **different** from the thermal rate matrix `A_rate=diag(V(C-2bT_i))+2bV diag(T)1 w^T`. Indeed `(J_E-A_rate) Tdot` is local mechanical power `2Vb(mu-T_i) mean(Tdot)`. Using A_rate as the inverse Jacobian, or replacing u by psi, changes the energy map; separate tests demonstrate both errors.

The declared positive temperature interval [Tl,Th] must obey C-2bTh>0 in exact represented-input arithmetic. For this first inverse, the entire rectangular temperature domain must also satisfy the existing common/eigen/mismatch strain limits: check alpha(Tl-Tr), alpha(Th-Tr) and +/-alpha(Th-Tl). Unsupported narrower correlated strain domains raise a configuration `EnergyStorageError`; that is not a claim that all original plate states lack a root. This restriction prevents intermediate scalar trials from being misclassified as physical domain exits.

## Uniqueness and domain existence are different proofs

J_E is symmetric positive definite throughout this admitted convex box. Its uniform eigenvalue lower bound is dmin=V(C-2bTh)>0, which proves strong monotonicity and at most one temperature vector for a specified energy. It does not prove a root lies inside the box.

For b>0, let x_i=E_i/V+CTr, h(T)=CT-bT^2 and q=mu^2. Because h is strictly increasing on the positive temperature interval,

```
T_i(q) = h^-1(x_i-bq)
F(q) = sum(T_i(q))/N - sqrt(q)
qlo = max(Tl^2, max_i (x_i-h(Th))/b)
qhi = min(Th^2, min_i (x_i-h(Tl))/b)
```

The exact interval [qlo,qhi] is necessary and sufficient for every auxiliary T_i(q) to be in the temperature box. F is continuous and strictly decreasing: `F'(q)=-mean(b/(C-2bT_i))-1/(2sqrt(q))<0`. An empty interval or certified wrong endpoint signs proves no domain root. Otherwise strictly opposing certified signs (or an exact endpoint zero) prove domain existence before bisection. An unresolved initial endpoint sign is a numerical failure, never an asserted physical no-root event. For b=0, solve each linear energy equation directly and check its exact root against the same box.

The stable positive inverse is `h^-1(y)=2y/(C+sqrt(C^2-4by))`. Exact h(Tl)/h(Th) cases return their known endpoints; this is not clipping. The denominator and feasible interval are positive by the declared domain. The tests include an exact nonuniform boundary root and a nonempty feasible q interval with wrong F signs.

## Certified scalar acceleration with bisection fallback

After the endpoint proof establishes a root r in I=[qlo,qhi], choose m at the interval midpoint and compute the existing exact rational enclosure [flo,fhi] of F(m). Let Ce_min=C-2bTh, Ce_max=C-2bTl, ml=max(Tl,sqrt_lower(qlo)), mh=min(Th,sqrt_upper(qhi)). These bounds remain valid and strictly positive even if a low-resolution dyadic square-root lower bound is zero. On all I,

```
D(q)=-F'(q)=b*mean(1/Ce_i(q))+1/(2sqrt(q))
0 < L=b/Ce_max+1/(2mh) <= D(q) <= H=b/Ce_min+1/(2ml)
```

The mean value theorem gives r=m+F(m)/D(xi). Form all four endpoint quotients of [flo,fhi]/[L,H], including when [flo,fhi] crosses zero, and enclose their min/max. Intersect the resulting root interval with I. An exact empty intersection violates the inherited root certificate and raises a numerical ResolutionError, never a physical no-root claim.

Before intersection, round the new rational lower/upper bounds outward to a dyadic q grid with spacing 2^-square_root_bits in the numeric K^2 coordinate. This retains the enclosure while bounding Newton-generated denominator growth. It is an arithmetic enclosure of the root, not a projection of T or a modification of target E. The original signed half-interval is also intersected whenever F(m) has a certified sign, so bisection remains available even if Newton does not contract usefully. If F(m)'s sign is unresolved, a strict inherited Newton contraction can continue; otherwise return numerical unknown. No new physical constant, tolerance, cache or public-interface field is introduced. `iterations` counts actual tested midpoints. All final returned-T residual/domain/uncertainty gates remain unchanged.

## Arithmetic and policy meaning

All supplied numeric values are decoded as finite binary64, then interpreted as exact rational numbers for this algebraic model. The represented V is exactly the same binary64 computation `(L/N)*A` used by the frozen plate, then decoded as a rational. This convention is not a zero uncertainty assertion about physical dimensions or coefficients. Squared coefficients and the algebraic mean are evaluated exactly; no material value or target energy is adjusted.

Square roots use integer `isqrt` to enclose a rational radicand between exact dyadics at spacing 2^-square_root_bits. `square_root_bits` is an explicit absolute square-root resolution, not a decimal significant-digit claim. Finite bisection, precision exhaustion, inadequate representability and unavailable final core stages raise `EnergyResolutionError`. The algorithm does not claim to search all possible binary64 temperature vectors or to prove that a stricter requested error is impossible over that discrete set.

`EnergyTarget(cell_energy_j, absolute_error_j)` copies two immutable equal-length vectors. The nominal target is the exact represented energy, and each nonnegative error is an independently explicit absolute J bound. All-zero errors decode the current represented conserved state; they say nothing about integration truncation or material uncertainty. Nominal domain existence is always required. A nonzero error interval cannot rescue a nominal target with no domain root.

`EnergyInversePolicy(energy_tolerance_j, temperature_tolerance_k, maximum_iterations, square_root_bits)` has **scalar** positive tolerances: absolute J per cell and Euclidean K error of the whole temperature vector. Policy is numerical configuration, not physical energy identity. Integers are explicit and bounded; bool/nonfinite/shape-invalid inputs are rejected.

At every candidate the actual returned binary64 T is decoded and its exact E(T) is recomputed. With exact residual r_i=E_i(T)-target_i and explicit target error d_i, use c_i=abs(r_i)+d_i. Both gates must hold: every c_i<=energy_tolerance_j and `R=upper_sqrt(sum(c_i^2))/d_report<=temperature_tolerance_k`, where d_report is the positive binary64 **downward** enclosure of dmin. The reported radius is rounded upward. Thus the returned public fields compose directly: `sum(c_i^2) <= (R_report*d_report)^2`. A nonrepresentable positive lower bound is a resolution failure.

For zero target errors, existence was already proved by the scalar root bracket. For nonzero errors, additionally require the entire Euclidean radius-R ball around the returned T to fit the temperature/strain domain. Common/eigenstrain perturbations are bounded by abs(alpha)R; mismatch perturbations by 2abs(alpha)R. Strong monotonicity gives an outward boundary condition for every target in the energy-error box, so every such target has a unique domain root inside this ball. Failing this sufficient admission proof is an unresolved uncertainty/domain certificate, not proof of physical nonexistence.

A boundary forward energy may round to a nominal binary64 E just outside the exact image of the temperature box. Its subsequent strict nominal inverse can therefore reject it. The module neither snaps that energy back to the boundary nor silently reinterprets it as an interval target. The tests use separately explicit exactly representable endpoint fixtures to verify actual endpoint support.

## API and core reuse

- `ThermoelasticEnergyStorage(plate)` is immutable and requires the explicit frozen plate type; `cells` and `reference_cell_volume_m3` describe its fixed half-plate discretization.
- `at_strain(T,e) -> StrainEnergyState`: immutable T/e, E, forward rounding bounds and actual constituent points at explicit common strain.
- `forward(T) -> FreeEnergyState`: immutable T/mu/e, E, forward rounding bounds and the actual final `plate_evaluation`. This calls the frozen plate exactly once.
- `inverse(target,policy) -> EnergyInverse`: unchanged target/policy, actual final state, exact-residual outward bounds, combined bounds, K radius, dmin lower bound, scalar bracket/sign evidence, iteration count, existence classification and elapsed wall time. All success results explicitly retain false material qualification through the state.

The scalar residual interval concerns the tested auxiliary q, not a substituted residual at the returned mean. `mean_temperature_bracket_k` encloses the nominal exact root mean; final energy residuals are independently recomputed from the returned T.

Inverse iterations do not evaluate the core rate solver. On success, `forward` evaluates the actual frozen plate once and that object is available as `result.state.plate_evaluation` for native Q/P rates. Core intermediate rounded arithmetic can differ from the exact binary-input algebra: `plate_energy_difference_bound_j` bounds exact V times the actual core point u minus the algebraic E; `plate_strain_difference_bound` bounds the actual core strain minus the exact algebraic free strain. These are separate from forward rounding and from inverse residuals. The reported mean/strain are nearest binary64 algebraic values; actual core stress/strain outputs remain in the evaluation object. No agreement is manufactured by overwriting either result.

Error classification is explicit: `EnergyDomainError` only for actual input outside the declared domain or proven absence of a nominal domain root; `EnergyResolutionError` for unresolved existence/precision/representation; base `EnergyStorageError` for invalid or unsupported configuration. A host can map only the first to a native shrinkable DomainExit.

## Short validation and frozen candidate evidence

No time integration, fitting, new dependency or material admission was performed. The existing installed Python 3.12.13 environment was used.

- Original author suite: 56 pure algebra/input/domain tests. N=1/2/4/16 nonuniform round trips, exact dyadic endpoints and alpha=0/negative-alpha cases, two distinct nonlinear no-root conditions, explicit restrained points, psi and A_rate negative cases, independent exact returned-energy/roundoff checks, target uncertainty, iteration/representation failures, immutable snapshots and actual one-core-evaluation behavior.
- Baseline combined run: author 56 plus root-owned host 18 = **74 passed in 0.17 s**, `/private/tmp/brick-cooling-energy-v1/storage-host-second.log`.
- First run retained at `storage-author-first.log`: 50 passed/6 failures of the same public-certificate composition check. Original exact-dmin radius was mathematically valid, but independently combining its rounded public radius with the separately downward-rounded dmin could fail by rounding. The narrow correction divides by the reported downward dmin before rounding the radius; no policy threshold or physical coefficient changed.
- Baseline one actual pure inverse for the declared B point T=(304,304), E=(40,40) J, explicit zero target error: 35 scalar iterations, external wall time **0.004358917 s**, reported elapsed 0.004344958 s, per-cell energy residual bound 9.096863887170238e-12 J and temperature-vector bound 1.3715254034433032e-12 K. This is one measurement, not an integration-runtime guarantee. Full data: `storage-single-inverse.json`.

The approved pre-optimization source/tests/description are preserved unchanged under `/private/tmp/brick-cooling-energy-v1/baseline-storage-bisection-v1/`; `BASELINE.json` records original SHAs 68d3f6b…/0785c23…/11b2ebc….

The accelerated author suite adds seven cases: independent exact-root containment on both F signs and at a centered root, signed division across zero, a tiny positive domain with an unresolved dyadic sqrt lower bound, explicit invariant-error classification, and unchanged-Newton fallback with exact successive interval halving. **63 author plus 18 host tests = 81 passed in 0.13 s**, `storage-newton-final.log`. The first expanded run is retained as `storage-newton-second.log`: its only failure was a test's unjustified expectation of more than 20 fallback steps; the selected exactly representable mean already completed original bisection in seven. That performance assertion was replaced with direct rational verification that each fallback interval halves. Solver code and scientific thresholds were unchanged by this test correction.

Only the same three existing B points from `root-three-point-cost01.json` were each timed once, with policy 1e-10 J / 1e-9 K / 200 / 160 and explicit zero target error. Results in `storage-three-point-newton01.json`: 4/4/4 midpoint trials, external inverse wall times **1.004542 / 1.037584 / 1.265750 ms**, compared with original 35/35/36 trials and 4.110333 / 4.504292 / 4.611833 ms. Maximum cell residual bounds were 1.08022e-11 / 3.97867e-12 / 1.13786e-12 J. These three algebraic measurements are not an integrated-runtime guarantee; no time integration was run.

Frozen accelerated candidate SHA-256:

```
thermoelastic_energy_storage.py
d98d6dccff4e31895da642ffa170ecd208c60e6e55b27ac5e314c36ace3f4579

test_thermoelastic_energy_storage.py
31ec6280dc1d97c648bddea9b508b651f2e6d439f2dc8b518ad814dc2d66e4fc
```

Independent review is separate evidence owned by the review agent. Root controls source integration, installation, any native time run and Git archival. This candidate closes the algebraic extensive-energy decoding gap only; reactive solid/liquid/gas material closure and full-cycle qualification remain outside its scope.

## 原生宿主接口

生产 `ThermoelasticEnergyHost` 使用显式、非空、不可变的每格物质的量库存；此库存只为原生状态接口记账，不进入常C热弹体积内能。宿主不引入摩尔质量、真实组成、气体EOS或反应。每次调用检查同一能量模型身份、库存形状与原字节，拒绝把共同面内应变当成积分伸长。负零库存会在原生零增量中变成正零，故准入时明确拒绝；正零及最小正次正规数通过纯接口测试。

`state_from_temperatures` 同时返回原生总E状态和初始化函数求值证书。每次 `evaluate` 全局反演当前E，再复用该反演最终一次实际plate求值中的面热与逐格机械功。Rates包含实际面热、零物流与反应源、实际局部功，功分量名为mechanical_constraint。只将已证明域外/无根映射为DomainExit；数值解码未解决仍为IntegrationError，不伪装成可通过缩步消除的物理事件。

能量身份绑定M、α、C、Tr、参考几何、适用域、机械定义、制造分类和显式库存。导热率与外边界只影响演化，不定义U，因此无需因这些变化重定义当前内能。改变储能定义的旧状态不能直接送入新宿主。

V1移植时，源与非editable安装各执行168项受影响测试，均通过，分别1.34/1.31秒；包括新81项、既有热弹与原生能量/机械积分回归。该时点安装158个Python模块/165个包文件与源逐字相同；先前163文件未修改，只新增storage/host。依赖版本保持Python3.12.13、NumPy2.5.2、SciPy1.18.1。

原168项回归含既有短制造测试；它们没有执行本研究新登记的两条0–10秒B轨迹，不能用于代替本研究正式运行。包位置核查由/private/tmp运行，无PYTHONPATH，确认实际从site-packages导入。

V1正式运行随后暴露原生时钟尾段缺陷，修复与V2执行另见[CLOCK_REPAIR_PREREGISTRATION.md](CLOCK_REPAIR_PREREGISTRATION.md)和[最终报告](REPORT.md)。最终183项源码/安装回归通过；相对V1只有integration.py变化，其余164包文件不变。原168项的历史源码身份不能代替V2冻结。
