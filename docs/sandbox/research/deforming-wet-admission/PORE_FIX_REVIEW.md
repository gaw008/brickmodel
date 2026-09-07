# Independent current-pore context fix review

Reviewed 2026-09-07. **APPROVE the isolated current-pore configuration repair only.** No actionable CRITICAL/HIGH/MEDIUM finding in the reviewed change. This does not approve production promotion, wet chemical callback correctness, phase transfer or a full wet trajectory.

Scope: diff of `candidate/sludge_sandbox/deforming_solid_storage.py` against `pre-pore-fix/deforming_solid_storage.py` (one error import plus the current-context block), corresponding two new tests, existing seven admission tests, prior CODE_REVIEW.md and surrounding solid/skeleton validation. No EOS or production source edit was performed.

## Actual independent verification

Command from repository root:

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/brick-deforming-wet-admission/candidate:tests/sandbox .venv/bin/python -m pytest /private/tmp/brick-deforming-wet-admission/tests -q --tb=short -o cache_dir=/private/tmp/brick-deforming-wet-admission/review-pore-cache --junitxml=/private/tmp/brick-deforming-wet-admission/review-pore-tests.xml`

**9 passed in 0.38 s**, exit 0. review-pore-tests.log and XML retain the independent run. New tests explicitly forbid WaterProperties.state_tp. All ten entries of pore-fix-manifest.json match the current files. Prior three-module approval is retained in CODE_REVIEW.md; it is not expanded into wet numerical approval by this follow-up.

## Assessment

The previous current_storage changed bulk volume while retaining the reference fluid-template pore volume. Under compression that stale context could exceed the current bulk and fail transport construction even after a valid total inverse. The repair constructs the fluid template using `Fraction(current_bulk) - sum(Fraction(Ns)*Fraction(vs))`, converts that positive volume once to the normal represented float and attaches the resulting template to the same returned current_storage. Inventory is mol and intrinsic molar volume is m3/mol, yielding m3. The calculation matches SolidFluidStorage.evaluate_at_temperature's independent available-volume formula.

There is no second subtraction from a pre-subtracted pore volume: thermal storage continues deriving pore volume from its bulk and solids. It also retains the original volume-error accumulation, conversion-roundoff contribution, intrinsic-volume uncertainty and positive-domain rejection. The geometry and mechanical error computations surrounding the new block are unchanged. No energy, pressure or tolerance gate was weakened.

Skeleton evaluation precedes the new indexing/conversion and verifies the complete fixed inventory keys and finite nonnegative values against the declared fixed inventory. Invalid key sets/inventories therefore do not enter the new pore sum as unvalidated user input. The exact nonpositive-pore guard uses the existing SolidFluidStorageError and established message. The underlying thermal uncertainty guard remains active; the added collapsed and uncertain-domain tests both verify refusal without EOS.

The compressed-context regression reproduces the problematic reference/current geometry relationship, asserts an independently calculated exact pore volume, verifies one total inverse, and checks object identity through current_host storage and transport plus the resulting dry gas volume. It verifies the original template remains unchanged, solid phases are preserved and the error envelope is the same object. This is behavioral regression coverage, not merely an assertion about implementation syntax.

No source binding, manufactured opt-in, current-state identity or thermodynamic reference convention is changed. The retained actual callback attempt still failed before reaching chemistry; these no-EOS tests do not retrospectively turn it into a pass. Any next actual callback or integration requires its own bounded preregistered run and independent result audit.

## Frozen bindings

- `candidate/sludge_sandbox/deforming_solid_storage.py`: `8ee7490c1b46616efc404689ce74b40dd62d9d18e23c4966e636702f99592603`
- `tests/test_admission.py`: `257cfb4c037c8b3312ccca291076687c9f1756e4a7f0e9d0ffa7ce1bd79b15b2`
- `review-pore-tests.log`: `f1a9665036b680a4bebda68071fe5683a2a7fbfba9b368d6ce086654f3d6ca51`
- `review-pore-tests.xml`: `48490a9255da0358cb805bc10c90c985250a9b7e3076705e08c0f8d7b13ee84c`
- `pore-fix-manifest.json`: `9ef08cb8d4d4a85c85cc39242e040aae92ddd08312dfb0c7ca44ac9345d9048a`
