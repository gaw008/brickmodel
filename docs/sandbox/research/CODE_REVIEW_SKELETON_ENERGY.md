# DiagonalSkeletonEnergy independent review

Verdict: APPROVE for the isolated manufactured diagonal potential provider. Not applied to the repository at review time; no total-energy host, actual material admission or pore-pressure mechanics is thereby verified.

Read complete candidate source, tests, README and the associated energy design. Reference cell identity, exact fixed solid inventory, opaque provider identity, coefficients, source/version, stretch/log-rate domain and manufactured permission are mandatory. Caller inventories cannot change or omit a species. Frozen tuples and mapping-proxy numerical bounds prevent ordinary mutation. The opaque provider tuple is a declaration; a later host must bind the actual solid caloric model, as the README expressly requires.

## Physical derivation

With diagonal stretches lambda_i, theta=sum(log lambda_i) and d_i=log(lambda_i)−theta/3, Eel=V0*(K theta²/2+G sum d_i²). Differentiating Eel/V0 gives first Piola P_i=(K theta+2G d_i)/lambda_i because sum d_i=0. The two tangential components represent separate directions evaluated at equal stretch/rate, so a derivative with respect to their common scalar must count both. The oriented internal interface area has Eint=gamma*Aint0*lambda_y*lambda_z, whose y/z gradients are correctly divided by V0; no exterior heat-transfer area is substituted.

Phi=(eta V0/2)*sum((lambda_dot_i/lambda_i)²) differentiates with respect to lambda_dot to give viscous Piola eta*lambda_dot_i/lambda_i². Its work V0 sum(Pvis_i*lambda_dot_i) is D=2Phi≥0. Elastic/interface rates use their own gradients and share this reference-volume Piola-power convention. Units are J, Pa and W as declared. Temperature-independent stored internal potentials supply no unmodeled entropy derivative; the same formulas must not be used for a temperature-dependent surface free energy without the additional thermodynamics. No gas-pressure work or total applied stress is added by this standalone provider.

## Numerical bounds

The private Decimal80 logarithm primitive uses the documented correctly rounded HALF_EVEN result and its neighboring Decimal values. Exact conversion of those endpoints to Fraction encloses ln for each represented binary64 input. Interval addition, signed multiplication, square (including intervals crossing zero) and division by a sign-definite denominator correctly propagate this enclosure. Final error is the outward-rounded maximum distance from the represented midpoint output to both rational endpoints, including output rounding. This is not an arbitrary epsilon tolerance. Explicit failures reject nonfinite or nonzero-underflowed outputs and unrepresentable bounds.

Reference V0 is explicitly the geometry's represented A0*(half_thickness/cells), not an enclosure of physical reference-volume error. Source/parameter uncertainty, interpolation/geometry uncertainty and model discrepancy remain excluded and must be separately propagated by a future host. The potential is a manufactured diagonal law, not proof of general finite-strain stability, arbitrary rotations/shears or real sludge mechanics.

## Independent execution

Actual isolated suite: **23 passed in 0.08 s**, XML `/private/tmp/skeleton-energy-review.xml`. It includes finite-difference potential gradients, separate work identities, the isochoric analytic limit, all-field Decimal160 checks and failure/immutability gates.

Additionally recomputed all 15 scalar outputs at five independently selected states (domain endpoints, identity/rest, adjacent-to-one stretches, mixed compression/expansion and nonzero rates) using exact Fraction algebra and a separate 240-term atanh-series logarithm:
`ln x = 2*sum(z^(2k+1)/(2k+1)), z=(x−1)/(x+1)`.
This uses neither candidate interval helpers nor Decimal.ln. Here |z|≤1/3, so the logarithm truncation remainder is below 1e-230. All **75** reconstructed outputs fall within their returned numerical bounds. This finite independent check supports, but does not replace, the analytical interval argument or confer a physical uncertainty certificate. An optional mpmath check could not run because that package was absent; nothing was installed, and the independent rational check above completed instead.

Final isolated bindings:

- `skeleton_energy.py`: `c268883c6f10816f802c01508e1fa654ec7fb72a201365df133dfb1843e25bab`.
- `test_skeleton_energy.py`: `235b54f3840746fec37757a38897840a96d7abba5561b1840bb1967e8fdf9c2b`.

No candidate/production source or tests were edited by this reviewer, no EOS experiment was run and no Git commit was made.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded manufactured energy/stress/dissipation provider with numerical enclosures for its represented inputs; future host coupling remains separate work.

## Repository application audit

Independently diffed final repository files against the reviewed isolated versions. Source differs only by removing “isolated” from its opening docstring. Test differences only remove the temporary importlib/path loader and import the production module; all test bodies remain identical and `sys` is retained for the extreme-output test. Root reports an actual first application run of 1 failed / 22 passed because that still-required sys import was initially removed; its failure XML was preserved, then sys restored and a separate 23 passed / 0.08 s application XML saved. The reviewer confirms the final diff closes this import mistake and did not repeat the unchanged 23 tests.

- Applied source SHA256: `d6bd0b76ba5dd8629229ac7747d6ae8545d56c25859748ef34b66fb0161fafe7`.
- Applied test SHA256: `d9eb11843efac06969bcbcf439b49c1f7ee7ae833f656a05043616cf8664f3da`.

The bounded APPROVE remains valid for this application. It remains a standalone potential provider until the total-energy host and accepted component ledger are actually connected and validated.
