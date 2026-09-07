# Independent review: explicit deforming wet-host admission

Verdict: APPROVE for the bounded software admission/wiring change only. No actionable CRITICAL or HIGH finding. This is not approval of active wet phase numerics, wet depletion, full 10% deformation accuracy, or free-sintering/material applicability.

Reviewed the three proposed module diffs against retained baseline, surrounding storage/inverse and wrapper call paths, complete seven tests and author history. Repository staged/unstaged diff was empty when review began; review used the isolated candidate, not a claim that it was applied.

## Verified behavior

- Exact `DeformingSolidHeat` admission preserves the original tagged-total-state checker. Configuration unwrapping is restricted to explicit known types; actual execution still invokes the canonical total-energy host. Point mechanical error identity changes are rejected by the original host.
- Program boundary work uses `base.current_host.transport` produced by the same total inverse. Current face area and half-cell distance apply to convection/conduction and gas enthalpy exchange. The configuration transport is used for construction/source gates, not as current geometry in evaluation. Existing fixed-solid route remains unchanged; actual old/new evaluate golden arrays match in the author test independently rerun here.
- Thermal projections retain the original `thermal_inverse` objects and storage states; `total_inverses` remain in the base evaluation. No extra inverse is called, no total E is relabelled thermal, and all five power components survive. Added mechanical uncertainty reaches the thermal target rather than being discarded by projection.
- Program and motion knot union validates both domains. Independent values at two distinct boundary knots use current motion geometry; author test separately places a motion-only knot at .5 between program-only .25/.75 knots and rejects either shortened domain.
- Water matching/source loop including `JoinedWaterVapor.low_model`, active evaluate, dry strict/metastable diagnostic, and mode switch AST are unchanged. New branches only select the legitimate fixed configuration host while preserving execution of the outer program/deformation chain. Layout-based liquid/water columns and manufactured opt-in remain.

## Actual independent evidence

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/brick-deforming-wet-admission/candidate:tests/sandbox .venv/bin/python -m pytest /private/tmp/brick-deforming-wet-admission/tests -q --junitxml=/private/tmp/brick-deforming-wet-admission/review-tests.xml`

**7 passed in 0.37 s**, XML retained. These are no-EOS tests; no wet integration was performed.

Independent `review_probe.py`, executed with candidate/tests plus repository test helpers on PYTHONPATH, forbids `WaterProperties.state_tp` globally. A nonzero additional mechanical error of 1e-7 J is propagated to 1.0000900810515163e-7 J thermal target error; the original inverse projects a 4.903288832780737e-8 K bound. Exact inverse object identity is asserted, and the previous host rejects the changed error-bound energy identity. At t=.25/.75, independent half-cell + film heat uses current A=.01356591796875/.01173716796875 m2 and d=.00984375/.00915625 m. Errors are −7.37677e-11/−9.54614e-12 W, below 1e-8 W. Full probe output retained.

## Scope limits and next evidence

The K=0 tests explicitly use a constructor-bypassed, unused chemical sentinel. They test routing and unchanged power, not genuine chemical-provider admission or phase dynamics. Nonzero K on the manufactured H2O caloric is correctly rejected. A separate actual source-linked compatible IdealWaterVapor/Joined.low + WaterChemicalPotential **nonzero K callback** is still required, then independently budgeted active wet integration as appropriate. Existing chemical logic being unchanged is useful regression evidence, not a substitute for this next actual callback.

The original `DeformingSolidHeatEvaluation.qualification` text still says `not_wrapper_admitted`; it predates these diff lines. This conservative stale description does not grant scientific capability; documentation should distinguish the new bounded admission from still-unverified wet trajectories. No source edits were made by this reviewer.

## Bound hashes

| Artifact | SHA256 |
|---|---|
| `candidate/sludge_sandbox/deforming_solid_heat.py` | `510211198c55ba328d505c9304f4393f4d9eb97330fd5754b4654c31e6b9a7d4` |
| `candidate/sludge_sandbox/programmed_solid_fluid_heat.py` | `a2e3136ee3a62d102f1fb5b36816e97942ffd484fa3939ad06d0e300fe19e2da` |
| `candidate/sludge_sandbox/water_phase_transfer.py` | `0463ed85ad4719e65c5c617526dd8520f46f9511426a6f0c69ff95ef0f9c2fb1` |
| `tests/test_admission.py` | `efa2fdf85a8650106f6e843220621a471e64efcb7d4f402f1d0301dc5aef3441` |
| `review-tests.xml` | `7d3d10e589ad20ef4c78ba2f6ae4e87aa94532b20f0025de9e487ab35d2a6d34` |
| `review_probe.py` | `9e570c77f17d0566a8956720348ebd042a9a63f0d6cd47fd283d9cea61fdc4ed` |
| `review-probe.json` | `c287acadde73dc06d7c3489dff7cbc520464cb20f5ecfd77347ec2a0b17db804` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — explicit bounded software admission only; active source-linked wet validation remains outstanding.
