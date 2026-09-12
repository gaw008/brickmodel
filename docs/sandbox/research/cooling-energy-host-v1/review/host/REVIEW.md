# Native thermoelastic energy host review

Reviewed `candidate/thermoelastic_energy_host.py` against the installed native
`ConservedState`, `Rates`, and `CoolingThermoelasticPlate` contracts and repository
`docs/sandbox/research/cooling-spatial-v1/COUPLING_NEXT.md`. Repository baseline:
`3c61bf7`; `git diff --staged`, `git diff`, and final `git status --short` were empty.
No production or candidate files were modified. This is an internal independent
code review, not material validation or external expert certification.

No actionable host defects found with greater than 80% confidence.

The host binds all energy-law, reference-geometry, admissible-domain, and explicit
inventory inputs. Conductivity, boundary forcing, and inverse tolerances can
change without reinterpreting stored energy. Native immutable snapshots prevent
caller writes; each stage checks inventory shape and exact canonical float64
bytes. Explicit negative zero rejection is consistent with native zero-sum
updates, which otherwise replace negative zero with positive zero. No inventory
is supplied implicitly and no chemical mass qualification is asserted.

The successful inverse's actual `plate_evaluation` object is reused without a
second plate call. The single outward face array maps directly to native
left-to-right faces. Cell work is exactly the plate's `2 V sigma edot` output and
is exposed once as `mechanical_constraint`; there is no independently integrated
stretch, species source, or face species transport. Actual impossible-energy
targets raise `DomainExit`; actual iteration exhaustion and malformed input
remain `IntegrationError`.

Independent verification: `test_host_independent.py`, **14 passed in 0.08 s**.
These checks exercise energy identity changes, permitted boundary changes,
one-bit inventory changes, inventory column shape changes, byte immutability,
positive zero and minimum-subnormal zero updates, actual single-stage reuse,
extensive heat/work assembly, and real input/domain/numerical error paths.

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/brick-cooling-energy-v1/candidate /private/tmp/brick-cooling-thermoelastic-v1/installed-venv/bin/python -m pytest -q -p no:cacheprovider /private/tmp/brick-cooling-energy-v1/review/host/test_host_independent.py
```

Candidate SHA-256 at verification:

- Host: `3ecb8976bb1d0703d2845a1bf9522643f05f62fd80667b08ab6b264196b717bf`
- Storage dependency: `2db24a78bd9f356c4001492de26cd6dc81a4edc327520497b491574b1bda9481`

Scope limitation: storage's global inverse proof and uncertainty certification
belong to its separate numerical review. No time integration, trajectory,
accepted-step ledger, temporal convergence, source qualification, or full-cycle
acceptance was executed or claimed here. Candidates were still under parallel
development; later changes require review of the relevant delta.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — host interface only, at the recorded candidate hash.
