# PrescribedSlabMotion independent review

Scope: isolated candidate under `/private/tmp/brick-deformation-motion-candidate/`, not yet installed. Read complete source, tests, README, verification history and the actual `ReferenceSlab` implementation. No author source or test was changed by the reviewer; no EOS or gas-host run was performed.

## Initial finding

[MEDIUM] Nonzero exact time silently underflows into the supported domain.
`_number` accepts Real values including Fraction, but converts them without a nonzero-underflow check. Independently reproduced `program().sample(-Fraction(1, 10**400))` returning a snapshot at `-0.0`, although the exact input is outside the [0,4] s domain. The same conversion is used by breakpoint inputs. Requested an explicit conversion failure and a regression from the author; do not treat this as successful negative-time extrapolation.

## Mathematical and representation review

For q in [0,1], h=q²(3−2q) has h′=6q(1−q)≥0 and endpoint values 0,1. Every normal and common tangential stretch is therefore a convex blend of strictly positive endpoints for the whole interval, even when their directions differ. Its endpoint velocity is exactly zero, giving C1 motion across program nodes. This proves mathematical stretch positivity, not representability of every intermediate geometry. Products n*h_tangent² may have interior extrema when stretches move oppositely, so merely checking endpoint volumes would not prove a global float-range certificate.

The actual implementation and README correctly use **per-sample** finite/positive geometry and velocity gates. For example, a constant tangential stretch 1e308 can be constructed but sampling explicitly fails; this is not clipping or a claim of a globally executable schedule. Unresolved face spacing/centers are rejected. No interval-wide floating-point or experimental error bound is supplied.

Independent Decimal70 calculations at seven times, two cells each, evaluated Vdot=A0*dX*(normal_dot*tangent²+2*normal*tangent*tangent_dot), without calling candidate derivative helpers. Maximum discrepancy across 14 values was 2.710505431213761e-20 m³/s. The full tangential contribution is present. Fraction interpolation uses the binary64 input values exactly, then explicitly checks rounded derivatives; products use the actual sampled geometry consistently up to declared numerical rounding. Sampling always returns to the reference configuration, not an incrementally compounded geometry.

All CurrentSlab and exposed derivative arrays are copied into immutable bytes-backed arrays; caller knot/source lists are detached into tuples. Geometry count is exact, and area, every width and every gas volume are separately checked with zero relative tolerance and at most 2 max-ULP absolute allowance. Equal volumes with wrong area/width do not pass. A 2-ULP accepted alignment is explicitly numerical tolerance, not exact bitwise identity or physical shape uncertainty. Source/hash labels form immutable identities; literature-class hashes are required but source content is not fetched or admitted.

## Initial actual validation

Independent candidate suite: **24 passed in 0.06 s**, XML `/private/tmp/deformation-motion-review.xml`. This uses the test's explicit importlib loading of the isolated sibling module and the repository geometry implementation. Initial source SHA256 `128e74ef8f68ec7e7a2bd0587cc331de41cc2881dc89601896d0a41eb00afd35`; test `8260358f3246c19f06c16bf5e1e4743c030700a016c23b851ae5d498bc5760a1`. The new underflow finding was reproduced separately after those 24 tests passed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | pending repair |
| LOW | 0 | pass |

Verdict: pending final binding after the requested input-conversion regression. No physical/kinematic formula blocker was found for the explicitly prescribed, per-sample validated motion scope.

## Final repair review and independent verification

The author first reproduced the exact negative-time underflow as RED, then added the explicit nonzero-input-to-zero rejection in `_number`. The new regression includes `sample` and breakpoint conversion. The initial finding is resolved.

A separate root-requested ordinary 16/32/64-cell probe exposed over-restrictive face-spacing validation: subtracting two accumulated coordinates inherits their ULP scale, not merely the small width's ULP. The author preserved actual RED evidence for those three valid grids and one missing invalid-knot check (4 failed / 25 passed), then changed the local allowance to `ulp(left)+ulp(right)+ulp(width)+ulp(right-left)`. Independently reviewed the derivation: each right face is formed by a rounded `left+width`; the coordinate-addition/subtraction allowance is a conservative local representation check. It is not a proof of the total accumulated position error from the origin. The allowance must remain smaller than the width, and faces/centers must remain strictly distinguishable; the old giant-coordinate/thin-cell rejection remains covered. This fixes a practical spatial-refinement blocker without an arbitrary physical tolerance.

Construction now samples every knot, so the previous overflow-knot example fails construction. Mathematical positivity still holds throughout each interval; interior float representability remains checked at sampling, not certified globally. The final README explicitly preserves both that limitation and the local-versus-accumulated coordinate distinction.

Independent final isolated run: **29 passed in 0.09 s**, XML `/private/tmp/deformation-motion-final-review.xml`. No gas host or EOS test was run. Final source SHA256 `2be5fcf036287143bfbb7b5694d5fa39916cd3f8105715b2068750a4047ec8e0`; final test SHA256 `028ccc7231a0f9d087879c7a92116fcfa07dd941bedb098b3671393a6138b419`.

## Final Review Summary

| Severity | Unresolved count | Status |
|----------|------------------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | repaired |
| LOW | 0 | pass |

Verdict: APPROVE — the frozen isolated candidate may be applied for subsequent gas-host testing under its prescribed-kinematics, per-sample representability scope. This is not a sintering constitutive law or global geometry-error certificate.

## Repository application binding

Independently compared the applied files bytewise against the reviewed isolated files. Production source changes only its opening docstring, removing “Isolated”; all executable logic is unchanged. The test changes only its docstring and replaces the temporary importlib loader with direct imports from `sludge_sandbox.deformation_program`. All test bodies and assertions are unchanged. Root reports the actual applied 29-test run passed in 0.10 s; the reviewer did not duplicate that run, and the independent isolated 29-test XML above remains separate evidence.

- Applied `src/sludge_sandbox/deformation_program.py`: `bed652b4c5b1670cd7122d08d331fd7b15f970b0f12fcba2eff37095249253dd`.
- Applied `tests/sandbox/test_deformation_program.py`: `b7cad8fd76c9524af1961c5ec1b4e6f84ca62b0d8bce3a938a99b6863d688269`.

The bounded APPROVE remains valid for this application. Host integration is a separate pending review.
