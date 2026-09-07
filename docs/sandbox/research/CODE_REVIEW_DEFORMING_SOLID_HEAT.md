# DeformingSolidHeat independent code/integration review

Status: pre-review complete; final frozen test validation pending. Candidate lives under `/private/tmp/brick-deforming-solid-host-candidate`. This report does not yet approve its physical/integrated acceptance gates.

Read the three changed candidate modules and all initial host tests against current repository source. The assembler extraction keeps the existing face/enthalpy/conduction calculations and uses the original thermal inverse objects; it neither reconstructs a thermal target nor invokes decode_inverse. Point results now expose the actual current_storage instance used by closure, allowing the instantaneous host to bind that exact object and its fluid template while updating current common area and every width.

The new host requires explicit total-energy identity, full layout shape, fixed complete Ns, exact point-template object binding, cell index and common motion identity. It rejects solid reactions and unqualified moving transport. Original base scientific settings are digested before point inversion; the point implementation separately rechecks complete template identity. Private assembler source-label/inventory/volume checks are additional consistency checks, not proof of arbitrary provider equivalence; safety depends on the caller supplying the actual bound context and original inverse, as this host does. The total inverse retains its mechanical target-error contribution and original thermal radius through face assembly.

Mechanical/source components are separately assembled as elastic, interface, dissipation, pore and body; their total is the correctly rounded exact Fraction sum of represented component powers. The original face energy remains distinct. No second mechanical-energy subtraction or separate unrecorded dissipation heat is added. Independent physical-oracle review is being coordinated separately; this code review will additionally verify old-path behavior and actual accepted component bookkeeping.

## Initial finding and retained test failure

[MEDIUM, repair requested] `DeformingSolidState.current_storage` was initially inserted before the old `qualification` field. This broke callers passing the old final scope/qualification positionally. Requested appending it after all existing fields and a positional-construction regression. The author has added that regression; final source/test verification remains pending.

Read actual attempt05 XML/log: **1 failed, 5 passed in 5.00 s**. Finest dt=1/128 had T error 1.8114890167453268e-5 K but cumulative pore-work oracle error 0.0001849691513893248 J, exceeding the unchanged 1e-6 J gate. This is not a complete passing component-work validation. The failure is retained; any later refined grid must be reported separately without changing that physical/error gate or claiming these coarse runs passed it.

## Review Summary

| Severity | Unresolved count | Status |
|----------|------------------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | final repair verification pending |
| LOW | 0 | pass |

Verdict: PENDING — final frozen code, regression verification and original integrated component-work gate are still required.

## Repairs and final independent code validation

The point-state compatibility issue is resolved by appending current_storage after the original qualification field; an actual old positional-construction regression passes. A further root/reviewer finding was initializer coercion: direct float(t) admitted numeric strings and len(scalar) raised an unclassified TypeError. The author preserved a string-input DID NOT RAISE failure, then reused the established `_column` validator. String, bool, scalar, NaN, mapping and missing temperatures now reject under the existing integration error contract. A regression executes the saved attempt06 initializer AST with its valid actual fixture and confirms identical represented initial N/E and energy tag; this prevents the validation repair from changing the previously tested trajectory's starting state.

Independent final bounded suite excluding the long compression scan: **13 passed, 1 deselected in 0.38 s**, XML `/private/tmp/deforming-solid-host-light-review.xml`. This includes the original six short cases, six malformed initializer cases and the valid old/new initializer comparison. No 72-second scan was duplicated.

For a separate old-path oracle, saved and compiled actual HEAD `SolidFluidHeat.evaluate` (complete source SHA256 `9b9b69f51d9963da799096260b5a3f5483b22d27b47abbb4435c6e334d606be2`) against unchanged helpers. Compared it to the candidate extracted assembler on a two-cell dry fixture with nonzero heat transfer, gas transport and solid reaction sources. **All four Rates arrays and original thermal-inverse diagnostic objects' values were identical.** This is a real pre-extraction method comparison, not evaluation/assembly self-comparison within the new implementation. The original solid-reaction path remains available for the unchanged fixed host while the new fixed-Ns deforming host correctly rejects it.

An additional reviewer dry point supplied 1e-7 J extra mechanical error and verified that the exact original thermal_inverse, including that target uncertainty, is the one retained by thermal_evaluation, and the exact current_storage object is reused by current_host. Independently summed all five represented component powers with Fraction: its rounded value equals authoritative total power and its exact residual equals Rates.component_sum_residual_w. Together with one-/two-cell call-count tests, this supports no duplicate thermal decode or error loss. It is not a proof that arbitrary user-constructed private inverse objects are authentic.

## Preserved actual scan and applicability to final source

Independently parsed attempt06 XML and the saved metrics JSON: identical rows. The author/root executed this scan once; the reviewer audited its persisted results rather than reintegrating. Actual scan status is successful, 72.617779 s externally timed, with 1 passed / 6 deselected in 72.39 s reported by pytest. All three grids have min_dt=max_dt=cap, zero rejected trials and actual accepted counts 512/1024/2048 over 1 s.

| Actual cap | Accepted | Max T error (K) | Max elastic prefix error (J) | Max interface prefix error (J) | Max pore prefix error (J) |
|---|---:|---:|---:|---:|---:|
| 1/512 | 512 | 1.1321531019348186e-6 | 7.033573869164034e-9 | 2.7179718019429075e-10 | 1.1560369269858484e-5 |
| 1/1024 | 1024 | 2.830424250532815e-7 | 1.7583933501971738e-9 | 6.794929506212521e-11 | 2.8900834365686023e-6 |
| 1/2048 | 2048 | 7.078398311932688e-8 | 4.3959832995987824e-10 | 1.6987323765531304e-11 | 7.225205731486994e-7 |

The finest case passes the original T≤2e-5 K and each nonzero component-prefix error≤1e-6 J gates. Coarse failures remain visible. Step caps were refined and per-integrate resource allowance explicitly increased from 20 to 90 s under a 150 s outer scan timeout; physical/error acceptance gates were not relaxed. The dry fixture makes water.state_tp fail if called. Component quadratures are measured against independent potential/thermal energy differences, not generated from those endpoint differences. This verifies this particular smooth manufactured compression; net-energy error control alone is still not a general component truncation-error certificate.

The saved attempt06-frozen base assembler and point-storage source are byte-identical to the final candidate. Independent AST comparison of the old/final deforming host finds only state_from_temperatures changed; the actual valid initial state is shown identical by the short regression. Final test caps and wall allowance are explicitly fixed to the executed configuration rather than depending on a hidden opt-in environment. Thus applicability of saved scan evidence to the final initializer repair is documented, not falsely presented as a fresh long run.

## Final isolated bindings and limits

- `deforming_solid_heat.py`: `e1b987ce0d544d8bbcf5982aa6ae4a5d0e6aee04fd925fd14c209b2fedc7ca29`.
- `solid_fluid_heat.py`: `241cc388a4fd83f957faf77760bf74b605963976b3ed0754df01592757b756e7`.
- `deforming_solid_storage.py`: `b4d9fcc5e71b270643b1953b228f80449d84ad177730dd65d78506e8bb3593b8`.
- Host test: `fb6d0825ef70c185a4b61fe913b867fc3ec7ad1d2c7c844f2299d12bc92b22e3`.
- Attempt06 XML: `5a9ea967770a55ac8b1e00bec3d7912d902a01b648a78c4d2d18350e31774cc8`.
- Attempt06 metrics: `4edb95ef52695b60f4695d2dc0450013095924b782761ae00752bf9bbac381c5`.

The actual demonstrated integration is a dry fixed-solid manufactured compression; the two-cell shared-face case is a point evaluation, not a long coupled moving wet run. The viscous term has a point check here, not a full dissipative trajectory oracle. Water/depletion wrappers and material sintering are explicitly not admitted. No production source/tests were edited or committed by this reviewer.

## Final Review Summary

| Severity | Unresolved count | Status |
|----------|------------------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | repairs verified |
| LOW | 0 | pass |

Verdict: APPROVE — bounded total-energy deforming host, actual decoded-context reuse and manufactured dry component-work validation. Apply only with the stated source/scope identities and preserved evidence; this is not real sintering or general wet/depletion support.

## Repository application audit

Independently compared all three applied production files with their approved candidate files using byte comparisons: identical. Their hashes remain e1b987… (host), 241cc3… (private assembler) and b4d9fc… (point context), as fully bound above. The applied test differs in exactly one line: the saved historical initializer source path now resolves to `docs/sandbox/research/deforming-solid-host-attempt06.py` relative to the repository root. All test bodies, numerical gates and configured scan caps remain otherwise identical.

The repository historical fixture is byte-identical to the actual attempt06-frozen source, SHA256 `53ef7aa7b649fa006504b8a0ceaf83e9059ce59b644eecac040f609e7c2d4cb4`. Thus the initializer regression retains the same historical oracle rather than silently switching to current code. Applied test SHA256 is `c48167d6aa293872dc41d3502438b602c8797541bf462e5d7b85f02a7d782947`.

Root reports the applied 13-light-test run passed in 0.41 s; the reviewer checked the exact application differences and did not repeat either that unchanged short run or the 72 s scan. The bounded APPROVE remains valid for the application. A forthcoming full installation suite is separate integration evidence, not already completed by this review.
