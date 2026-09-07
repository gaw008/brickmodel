# Independent review: rigid planar water/gas mechanical closure

Reviewed 2026-09-07 UTC. Scope: `rigid_water_gas.py`, tests and `RIGID_WATER_GAS.md`; additionally reviewed `RIGID_STORAGE_DERIVATION.md` algebra and its separately scoped numerical identity artifact. No implementation edits by reviewer.

Source SHA-256: `e91ed3f840506d43686a15403e5aefb1b700f1415b8942883eed88ba706e50ab`.
Tests SHA-256: `9d851d805edb885a2e5fe6cf1b5f73ab09ce957cd487c2acabb533530aefd047`.

## Mechanical model

The explicitly selected planar-interface/no-capillary assumption equates liquid pressure to total gas mechanical pressure, not water-vapor partial pressure. Each trial evaluates liquid density at actual `(T,P)` through the gated water adapter, preserving its native constants. Gas volume is `Ng R_mix T/P`; fixed available fluid volume yields `F(P)=Vl+Vg-Vavailable`. Stable positive liquid compressibility and Ng>0 make F strictly decreasing on a continuous stable liquid branch. Invalid endpoints/saturation ambiguity/source or numerical errors are not repaired by substituting saturation density or clipping volume.

Solving F directly correctly permits trial low-pressure liquid volumes larger than the cavity; only the accepted closure requires positive remaining gas volume. Otherwise a legitimate compressed-liquid root could be rejected prematurely. All gas species must be present in the inventory map, zeros included; zero total gas is explicitly outside this model. Zero liquid bypasses liquid properties and uses an analytic ideal-gas pressure with the explicit bracket still enforced.

Final state preserves assumption, species inventories, actual mechanical and partial pressures, original bracket, explicit policies, residuals, representation budgets, iteration count and source metadata. Separate gas/native-liquid constants remain visible. Water asset hashes are not asserted to cover the separate constant declaration. No equilibrium, capillary material law, phase transfer or full brick qualification is inferred.

## Independent roots and defect recheck

Before reading implementation output, independently solved the liquid-EOS volume equation using SciPy brentq and the already gated WaterProperties source. Reference pressures:

| T K | liquid mol | total gas mol | available m³ | independent P Pa |
|---:|---:|---:|---:|---:|
| 300 | 1 | 0.01 | 1e-4 | 304469.3135400322 |
| 450 | 1 | 0.1 | 1e-4 | 4687356.680552809 |
| 300 | 10 | 0.1 | 2e-4 | 12345746.54129325 |

Independent equation residuals were <=4.1e-20 m³. Compared new module at volume tolerance 1e-13 m³ and pressure tolerance 1e-3 Pa: pressure differences about +8.66e-5, -1.71e-5, -4.60e-5 Pa, all accepted within unchanged policies. These references share the source EOS but use an independent numerical root algorithm; they are not brick experimental measurements.

Found and reproduced a genuine trace-partial-pressure defect: pure-gas numerical case T=300 K, bulk=1e50 mol, trace=1e-300 mol, cavity chosen for P=1e100 Pa. Computing `n/Ng*P` underflowed the intermediate ratio and returned zero although final partial pressure about 1e-250 Pa is representable. Implementer added a regression and exact Fraction ratio-product, with explicit error for an unrepresentable positive final value. Independently reran the original case: trace partial pressure now `9.999999999999999e-251 Pa`. This extreme case tests arithmetic only, not ideal-gas physical validity.

Reviewed subsequent NRT/total-inventory representation budget addition. Finite/positive gates, open-volume cancellation diagnostics, both volume and pressure residual checks, iteration limit and strict numerical failure paths remain intact. These budgets are clearly described as representation diagnostics, not full EOS algorithm-error or experimental uncertainty bounds.

Final focused suite independently executed: **17 passed in 1.66 s**. Read its root, compressibility-feedback, zero-liquid/high-temperature, bracket/domain, inventory, immutable output, extreme arithmetic and iteration-failure cases.

## Closed-storage derivative derivation

The companion derivation is algebraically sound under its explicitly stated fixed-N, common-T/P, fixed-total-volume and stable thermodynamically consistent contributions. Let `Ai=(dVi/dT)_P`, `Bi=-(dVi/dP)_T>0`. Then `dP/dT=sum(Ai)/sum(Bi)` and `dH=Cp_total dT+(V-T sum(Ai))dP`, giving `Cclosed=Cp_total-T*(sum Ai)^2/sum Bi`. Cauchy plus each contribution's `Cp_i-Cv_i=T Ai²/Bi` yields `Cclosed>=sum Cv_i>0`.

The ideal mixture is one gas-volume contribution, not duplicated full pore volume for each species. This proves strict increase only along an existing continuous stable closure branch; it does not supply an interval-wide numerical derivative bound or missing upstream error budget. The document preserves these caveats and excludes capillarity/deformable skeleton and phase transfer. Its three-case identity JSON labels itself as source-EOS/manufactured-carrier algebra verification, not validation of a new energy solver. Recorded derivative discrepancies are <=2.79e-7 J/K against the separately registered 1e-4 J/K gate and differ materially from naive sum Cv. No claim of implemented U-to-T closure follows from this derivation alone.

## Findings

No unresolved actionable issue above review confidence threshold after the partial-pressure correction. Full coupled energy closure, phase equilibrium and raw-sludge material admission remain separate work.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded planar rigid-cavity mechanical closure at final hashes and conditional derivative algebra; not full wet-brick or Goal completion.
