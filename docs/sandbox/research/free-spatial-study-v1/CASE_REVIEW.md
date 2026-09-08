# Independent eight-cell admission review

Verdict: **APPROVE** for the frozen bounded candidate. No blocking findings. The supplied before.py matches actual production byte-for-byte, and the repository diff/staged diff were empty during inspection. No EOS, tests, installs, or repository edits were performed.

## Inspected SHA-256

| File | SHA-256 |
|---|---|
| verification_case.py | c0b57e8c3de1d8efd5eaa10c07b30210342c8dfe0b32e385aade457b276c1913 |
| free-wet-slab-equations-v1.json | c13db2dd9dc13f930d82e9fe41c5207bcecb223bef5eb690ac0c5b8740ce5c72 |
| test_eight_case.py | 783f29f13bfd2b9ae97f090e938715a09741d7e3dc7c447a5b17e5d1c0ac4a64 |

## Source and scope

The only Python change is verification_case.py:155: explicit free model admission expands from cells (2,4) to (2,4,8), retaining exact integer validation, two fixed parent cells, fixed physical domain, and the prescribed model's original (2,4) restriction. Existing builders already use parent_cells/cells, cells//2, and complete normal-vector reconstruction; eight cells give exactly four children per parent without a new rounding/non-power-of-two partition path.

The catalog changes only its two supported-cell-count statements. No physical coefficients, case JSON, numerical tolerance, horizon, free equation, prescribed motion behavior, or material qualification is changed by the patch.

## Tests

The tests execute actual dry builder wiring with the existing explicitly disclosed zero-water caloric substitute and EOS prohibition. They cover free eight-cell acceptance, rejection of six cells and prescribed eight cells, distinct-parent and uniform normal mapping, the nine-component mechanical state, exact extensive inventory and energy sums, fourfold composition-weight scaling, micro-interface area and additional mechanical error scaling, nonzero later B current-q/interface-energy checks, additional/reference bulk-error scaling, inherited policy equality, current widths, and nine face positions.

The later composition test retains initial B=0 and evaluates current A=1.5/B=0.5 with exactly quartered children; it does not relax the initial schema. Face-coordinate tolerance is only a direct geometry arithmetic check, not a trajectory or physical acceptance tolerance.

Evidence limits remain as in the preceding two/four-cell review: q*eta equality compares declared coefficients, while skeleton evaluations use zero rates. It does not test a nonzero viscous response or solved-rate denominator. The new geometry assertions directly check widths and face positions, not an independent current-volume/face-area oracle. Initial extensive checks and unchanged existing geometry code support this admission change, but a native eight-cell trajectory, coupled spatial convergence, and material accuracy are not established. The four-cell native outcome reported by the parent is outside this candidate's evidence and was not rerun here.

Preserved red/intermediate-failure history is described in IMPLEMENTATION.md; this reviewer inspected the final tests but did not execute or independently reproduce those historical runs. When applying the tests, replace the temporary candidate import and hard-coded root with the established production import and test-root fixture convention.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **APPROVE** for the exact candidate and stated admission scope.
