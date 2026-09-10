# D1 independent mathematical review

Verdict: APPROVE the stated finite effective-MR model and numerical validation strategy, with the implementation checks below. This is a mathematical review, not approval of a fitted parameter set or of a material constitutive law. Read only PREREGISTRATION_DRAFT.md and source_review/REVIEW.md. No experimental CSV, 50°C observations, fitted parameters, prediction or EOS was accessed/executed.

## PDE, geometry and modes

Use y=x/L with L=0.002 m the entire exposed layer thickness, and s=Dt/L². Then u_s=u_yy, u_y(0)=0, u_y(1)=-Bi u(1), Bi=kL/D>0. The flux sign is correct. Integrating gives dMR/dt=-k u(1,t)/L; water leaves only the exposed top. With uniform initial concentration and fixed uniform dry-solid basis, MR is the spatial average. None of this asserts the actual interior is isothermal: Tair remains the effective experimental coefficient label.

The maximum principle gives 0<=u<=1. The positive self-adjoint diffusion operator with this dissipative Robin boundary generates the unique weak solution from u(y,0)=1. The initial trace does not satisfy the classical Robin derivative when k>0, but this is normal initial-boundary incompatibility, not an invalid PDE. For positive times the boundary is satisfied; do not delay t0, change initial shape or discard initial positive observations. MR(0)=1 exactly. Its initial right slope is -k/L; higher derivatives need not stay finite at zero.

Eigenfunctions cos(mu_n y) have mu_n tan(mu_n)=Bi, n=0,1,..., in (n*pi,n*pi+pi/2). Orthogonal projection of the constant initial function, followed by averaging, gives
A_n = [sin(mu_n)/mu_n]^2 / [1/2+sin(2mu_n)/(4mu_n)]
    = 4 sin²(mu_n)/[mu_n(2mu_n+sin(2mu_n))].
All coefficients are positive and sum to 1. MR(s)=sum A_n exp(-mu_n² s) is decreasing and convex at positive times. Thus the effective model cannot reproduce a genuinely increasing initial drying rate by adjusting these three parameters. This is a predeclared possible failure mechanism, not a reason to suppress the finite holdout check.

## Tail bound: indexing and conditions

If N terms means indices 0 through N-1, then the omitted indices are n>=N. On each allowed interval sin(2mu_n)>=0, hence A_n<=2/mu_n²<=2/(n*pi)² for n>=1. For Fo>=0,
 tail <= (2/pi²) exp[-(N*pi)² Fo] sum_{n=N}^infinity 1/n²
      <= 2/[pi²(N-1)] exp[-(N*pi)² Fo], N>=2.
The proposed factor 4 is therefore conservative and valid. It requires positive finite Bi, Fo>=0 and correct zero-based indexing; it does not cover root-location, coefficient, exponential, summation or time/parameter conversion errors. Underflow of a machine exponential is not a literal mathematical zero tail. Use a logarithmic comparison, outward enclosure, or explicitly conservative remaining error allowance. At t=0 return the exact initial mean instead of a truncated sum.

## Stability and minimum tests

A tangent residual near a pole is avoidable: solve (n*pi+d) sin(d)-Bi cos(d)=0 for d in (0,pi/2). Preserve a bracket and do not accept the pole or interval endpoint as an exact root. For very small Bi, mu_0~sqrt(Bi), A_0~1 and leading rate D*Bi/L²=k/L. Direct differences of nearly equal trigonometric expressions should be avoided. A useful equivalent coefficient is 2 Bi²/[mu²(mu²+Bi²+Bi)], with scaled evaluation if Bi² might overflow. For large Bi, mu_n tends to (n+1/2)pi and A_n tends to 2/mu_n². These are numerical/asymptotic tests, not replacements for solving finite Bi.

Across the declared parameters and RH=0.3..0.6, conservative D limits are about 1.68168e-13..5.34288e-7 m²/s and Bi limits about 2.72240e-7..1.51364e6. At a hypothetical first 600-second sample the smallest Fo is about 2.52252e-5; arbitrary positive times may be much smaller. A fixed mode cap must explicitly fail if it cannot meet its tail target; do not silently return the capped series. Verify the actual evaluation times and every locked-parameter curve against an independent high-precision calculation, including numerical error allowance, before labeling the 1e-6 numerical target satisfied. No claim of a rigorous global floating-point bound follows from a handful of cases.

Minimum code tests: zero time exact 1; negative/nonfinite domains rejected; separate roots and positive coefficients; small/large Bi limits; monotonic and bounded MR; retained-mode indexing and tail failure at tiny Fo; root tolerance tightened without materially changing MR; L as full thickness and minutes-to-seconds conversion; independent cell-centred FV flux balance; parameter boundaries/Arrhenius units; no holdout values in optimization or start selection. Numerical failure must remain separate from model-data discrepancy. Nine fixed starts and locked training-only choice are statistical execution rules, not mathematical guarantees of global identifiability.

## Independent manufactured evidence

`oracle.py` implements a separate cell-centred conservative FV operator, with top-face conductance g=Bi/(1+Bi*h/2), including the half-cell diffusive resistance. Its last row is -(1/h²+g/h), the first row -1/h², and adjacent couplings 1/h². Telescoping gives d(mean)/ds=-g*u_last, while symmetry gives a spectral exact-in-time semidiscrete evaluation; there is no time-stepping stability error. Omitting the half-cell resistance changes the finite-grid boundary model and degrades convergence.

Nine synthetic cases Bi={1e-6,1,1e6}, Fo={.01,.1,1} used grids 256/512/1024/2048. All passed; largest finest-grid absolute MR discrepancy was 1.681308980927554e-7. The initial 64/128/256/512 attempt failed the research script's 2e-6 finest comparison; source/log are retained as oracle-before-grid-refinement.py and oracle-first-failure.log. We refined only the artificial FV grid and tightened its check to 1e-6; no data, model or scientific gate changed. Roundoff dominates some very-small-Bi grid differences, so observed second-order ratios are asserted only when the coarse discrepancy exceeds 1e-8.

`high_precision.py` independently uses 65-digit arithmetic, 190 bracket bisections and the unsimplified integral projection coefficient. Three synthetic Bi values at Fo=.01 agree with the float64 modal calculation within 1e-13, with 32-mode theoretical tails below 1e-40. This is independent consistency evidence, not an interval certificate for all parameter inputs. These scripts import neither the candidate implementation nor any experimental data. mpmath was installed by root after an initial availability probe found it missing; no dependency was installed by this task.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — D1 mathematics and bounded validation plan. Frozen implementation and fitted outcome require their separate checks; no real material qualification is granted.
