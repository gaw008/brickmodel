# TP equilibrium mathematics / standard-state review

APPROVE for this restricted implementation direction. The convex formulation and proposed partition lower bound are correct under the conditions below. Two small design clarifications should be explicit before interpreting the acceptance gap. This review read the frozen design, source-admission report, candidate definitions, graphite definition and `NasaPoly2.h`; it did not import Cantera, execute EOS or optimization, or repeat the source agent's NASA-page validation. Identities are in `DESIGN_READ01.json` (design `7d634532…d7d1e4a`).

At fixed T > 0 and P, with finite composition-independent ideal-gas standard potentials, the gas Hessian is positive semidefinite by weighted Cauchy–Schwarz:

`vᵀHv = RT[Σ(v_i²/n_i) − (Σv_i)²/N_g] ≥ 0`.

The pure-graphite term is linear. The `0 log 0` extension preserves convexity; a no-gas degenerate pool may be explicitly refused as proposed. This does not imply general nonideal-mixture convexity or prove absent phases unimportant.

Let `q_i=exp[(a_i·λ−g_i_std)/(RT)]`, `Z=Σq_i`, and `d_C=(g_C−λ_C)/(RT)`. For any exactly feasible pool b, Gibbs' inequality gives

`G−λ·b = RT N_g[D_KL(y || q/Z)−log Z] + RT n_C d_C`

`≥ −RT(N_g+n_C)δ ≥ −RT Bδ`, where `δ=max(0,log Z,−d_C)` and `B=Σb_e`.

The last step requires nonnegative atom counts and **at least one atom in every candidate**, true for these 18 gases and C(gr); there must be no electron/empty-composition column. Include every structurally allowed gas in logsumexp, regardless of fit threshold or reported zero trace. Remove graphite's term only when exactly excluded by zero requested carbon. T, R and B must be positive, all potentials/λ finite. Fit λ only in the subspace of positive-element constraints after structural exclusions; otherwise legitimate zero-element rows create artificial rank failure. A rank-deficient active fit remains unresolved. B_out=0 or an empty admissible gas set needs a named unsupported branch, not epsilon inventory.

[MEDIUM] Make the gap's element pool explicit.

File: `TP_EQUILIBRIUM_DESIGN.md`, §5. Keeping b_out and b_requested as separate fields is necessary but the acceptance gap also needs an explicit argument. Define `L(b)=λ·b−RT δΣb`, and gate/report the same-pool nominal gap `G_out−L(b_out)` using B_out. Separately retain L(b_requested), its requested-pool diagnostic, and the elemental residual `r=b_out−b_requested`. The exact connection is

`gap_requested−gap_out = λ·r − RT δΣr`.

An accepted element tolerance does not make n_out exactly feasible for the requested pool. Without this distinction the requested-pool gap also changes under an elemental reference shift by `c·r`; it cannot be advertised as a nonnegative suboptimality bound for the original pool. No second optimizer or feasibility repair is needed.

[LOW] Clarify the graphite loading phrase.

File: `TP_EQUILIBRIUM_DESIGN.md`, §4 (“另载原 graphite phase”). Reuse the original fixed-stoichiometry/constant-volume **model**, but instantiate the derived C(gr) species with actual reference pressure 100000 Pa. Loading the untouched original graphite YAML directly would restore the omitted-reference default and conflict with §3. Verify the loaded solid species reference pressure as well as all gas species.

The standard-state and unit algebra otherwise agree: mol amounts are divided by 1000 for kmol and read back multiplied by 1000; J/kmol properties divide by 1000 before combining with mol. Current-P gas standard Gibbs already contains the pressure contribution, so add only RT log(y). The explicit 1-bar branch changes interpretation of original coefficients, not entropy constants while claiming equivalent 1-atm semantics. A genuinely equivalent alternative reference would require the stated gas entropy shift and, for this temperature-independent solid molar volume, solid h/g shift. Formation enthalpy is already in NASA7. The saved v3.2.0 header explicitly uses `T <= Tmid` for the low segment; exactly 1000 K must follow it in independent arithmetic.

One targeted manufactured pressure check is useful: use a mock current-P standard potential at non-reference P to catch an extra RT log(P/p_ref). Actual P=p_ref=100000 alone cannot reveal that double addition because the term is zero. This need not expand the admitted physical domain or run EOS. Retain the source review's limited three-row original-page scope, historical-R distinction, finite-phase candidate limitation, nominal numerical gaps and unknown material/thermochemical errors.

## Review Summary

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | explicit gap-pool clarification |
| LOW | 1 | graphite loading wording |

Verdict: APPROVE — mathematics supports implementation; apply the two small clarifications before numerical acceptance claims.
