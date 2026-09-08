# Final applied free-case lifecycle review

Verdict: **APPROVE** for the reviewed free case, catalog/service seam, and saved bounded lifecycle evidence. No outstanding blocking findings. UI and ongoing local socket tests are outside this review.

## Exact applied source and tests

| File | SHA-256 |
|---|---|
| verification_case.py | e471398ba380a941aa4864ad7b7fd6b9342d660a47ddac897d9f7ccdb4642a34 |
| run_service.py | a51fba08e8695fe69289647decc2e4177d4ec6c77798c5151e938311bfd991e3 |
| run_provenance.py | 6a31f32b768298308c941e5e89b010d0e92f4213a210b9212e5e42b0b3c467e4 |
| catalogs/free-wet-slab-equations-v1.json | 5f5374f7cb1d84ed94f40fdc57ef4d59bc7c039299223ff0d4e00de688debb5d |
| tests/sandbox/test_free_case_build.py | 006e6d06dafcd398a9b8cf144de72c77b461baeaf61a47fbe342731fb3d98dcb |
| tests/sandbox/test_free_catalog_service.py | 627b1bee0d08acb78b5635759cec9b50e6d1c845c8a4ca7efcfd38538c559fa0 |

The four production files match the previously approved frozen snapshots. Applied tests import actual production modules and resolve fixture paths from the test-file root. Model selection, synthetic sealed trace fixtures, malformed selection rejection, and model-specific resume checks retain their earlier reviewed semantics. The case-test current-B and viscosity/trajectory evidence limits recorded in APPLIED_REVIEW.md remain applicable.

## Independently inspected saved artifacts

This reviewer read the original and second lifecycle scripts, summaries, launch statuses, and saved run bundles. A standard-library-only audit recomputed every listed manifest file hash in attempt01, replay01, cancel01, cancel02, and resume02. All matched. No native provider or model code was invoked.

All five bundles contain the same original case bytes, the explicit free model ID, and catalog hash `5f5374f7cb1d84ed94f40fdc57ef4d59bc7c039299223ff0d4e00de688debb5d`. That hash matches each bundle's runtime catalog entry and actual catalog bytes. Each runtime_before equals runtime_after. Original, cancelled, and resumed policies are identical.

- **attempt01:** completed, three states and two accepted steps. Saved launch status is exit 0 with source_unchanged=true.
- **replay01:** completed, three states and two steps. Every integration field except elapsed_seconds is identical to attempt01; therefore the states, steps, times, counters, and residual summaries reproduce exactly. This is not a claim that timing metadata is identical.
- **cancel01:** correctly cancelled with one initial state and zero accepted steps. The original lifecycle process exited 1 because its intended accepted-prefix test was not reached. This preserved failure must not be described as a successful resume test.
- **cancel02:** callback schedule changed to 19 after guard inspection, yielding exactly one accepted step and two states. Its accepted times are 0.5 and 0.5000076293945312. Physics, case bytes, and numerical policy remain unchanged.
- **resume02:** completed with three states and two steps, ending at 0.5000152587890625. The full original two-state, one-step, two-time prefix is exactly equal, including every amount, total energy, energy identity, mechanical vector, face/reaction/work ledger, local work component, stretch increment, and recorded roundoff field. Saved parent/result.json and parent/manifest.json are byte-identical to cancel02 originals. The second lifecycle status records exit 0, source_unchanged=true, and 19.33386149999569 s.

The retained mechanical vector changes from [1,1,1] to [0.9999995441349,0.9999995451955908,0.9999995217770835] in the accepted cancelled prefix, confirming the preservation check includes an evolved mechanical state rather than an unchanged placeholder.

## Scope

The read-only audit confirms integrity and preservation of these actual bounded saved lifecycle outputs. It did not rerun EOS, tests, installs, services, or sockets, and did not edit repository source/tests. It does not establish material qualification, full firing-cycle capability, spatial convergence, or equivalence of all possible adaptive restart trajectories. Parent-reported installed test counts and the ongoing local-app rerun are not independently certified by this report.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **APPROVE** for the exact reviewed local stage and saved lifecycle evidence.
