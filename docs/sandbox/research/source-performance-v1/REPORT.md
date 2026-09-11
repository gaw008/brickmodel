# Source execution performance

This phase starts at 86d9733. The complete Goal remains active. It addresses the
measured ordinary-segment resource failure without changing its physical inputs,
numerical tolerances or acceptance requirements. Neither a single RHS nor a
passive decode is an accepted integration step or a full material prediction.

## Measured original implementation

- `passive01`: one installed full parent read, 13.151049542 s including profiler
  overhead, no live physics. The 63 sample audits performed 126 decodes. The
  original record SHA remains 78aec3da52f175487dd9fa2a9a6d9cda943f9bb961afeb4ef4ed1b35428ba77d.
- `rhs01`: one original saved numerical query after actual reconstruction,
  6.034868291 s reconstruction and 6.382242000 s profiled RHS. Four actual new
  HEOS constructors and one new RHS, zero initial-U work or supplementary wet
  queries. The full returned payload equals the original native02 continuous
  first return. No integration was attempted.
- `supervised-rhs01`: terminal exit 0, 13.727477250 s, all monitored inputs
  unchanged, child reaped. The passive read was separately bounded; it did not
  use this supervisor.

The RHS contains 2,045 `state_tp` operations. The profiler's 4,090 transaction
entries count the generator's entry and exit resumptions, not 4,090 complete
transactions. Their cumulative 4.613 s is dominated by retrieving native Water
JSON for integrity checks. Separate 32-sample getter measurements put Water JSON
retrieval at 93.3% of one integrity-check side. These are measurements of the
original implementation, not achieved optimization results.

## Completed passive change

`create_source_sample_record` returns the existing decoder's checked record;
the public encoder returns that record's original canonical bytes. Study audit
reuses the checked record without decoding it again. Every semantic validator,
expected context and source/material qualifier remains active. There is no
cross-call cache.

Six focused tests passed in 2.03 s. An independent reviewer compared two saved
native observations against the original encoder extracted from 86d9733:
25 checks in 0.576 s, including owned immutable snapshots and error behavior,
zero EOS calls. The related source test run passed 93 tests in 40.45 s. The
initial missing-interface RED is preserved alongside the actual outputs.

The post-change installed passive read completed in 7.731053750 s with the same
source study SHA and no live physics. The profile confirms exactly 63 decodes,
down from 126. The observed read time decreased by 41.2%; these are two single
profiled observations, not a repeated statistical benchmark.

## Versioned runtime optimization

The backend retains the original kernel byte-for-byte as
`_heos_kernel_v1.py`, selected by the original manifest. A separate manifest and
source profile select the new kernel. Both default to per-operation integrity
checks. An explicitly isolated, installed `python -I -m` data worker may admit
one closed source RHS with complete integrity checks at entry and exit, before
publishing rates. Numerical arithmetic, local warnings and phase reset remain.

This boundary contract relies on the worker's closed execution graph. It does
not claim to detect arbitrary transient changes restored inside a foreign
callback, nor attest against hostile native code. No caller callback enters the
worker. New implementation and dependent configuration identities are explicit;
the saved old source run is never relabeled or treated as a cross-version resume.

The final implementation and manifest passed independent code review. All
150 installed Python modules and 157 package files match source bytes. The
installed related regression passed 228 tests in 49.41 s. A separate existing
nine-point native TP regression passed in 0.96 s through the original manifest
and retained kernel; its native calls are separate from the one-RHS experiment.
The worker's three independently found failure cases were actually reproduced
and fixed: false completion after profile I/O failure, lost primary failure
record when secondary audit fails, and noncanonical exact time admission.

## Actual new execution

The preregistered `rhs02` worker and `supervised-rhs02` completed successfully.
The supervisor took 4.342557291 s, confirmed all frozen inputs unchanged and
reaped its child. The worker took 3.233241791 s. It made four actual HEOS
constructions, one RHS, and zero initial-U, supplementary wet or integration
requests. Its admission was closed and its single scope verified all four
actual kernels at entry and exit.

| Same profiled RHS region | Original | Managed |
| --- | ---: | ---: |
| Elapsed seconds | 6.382242000 | 1.719229833 |
| Actual state operations | 2,045 | 2,045 |
| Full config reads | 4,090 | 8 |
| Full Water JSON reads | 4,090 | 8 |
| Accepted integration steps | 0 | 0 |

The observed RHS elapsed time decreased by 73.1%. Getter counts are supported by
the profile's actual caller edges plus the eight complete recorded checks;
constructors are outside the profiled region. New reconstruction is 1.461461083 s,
but it uses explicit saved query data instead of opening an old source trajectory.
Its reconstruction time is therefore not an equivalent before/after comparison.

The independent full comparison passed in 0.012843 s with zero new physics:
200 nodes, 229 references, six arrays, 456 binary64 values, 24 Fractions and 41
qualification fields retain their complete structure and values. Exactly 18
declared metadata leaves differ. Their finite mapping includes independently
recomputed implementation, config, storage/energy and column/operator identities;
the nested descriptor is checked field by field. Nothing is excluded by a broad
hash/identity wildcard. A one-ULP pressure change, qualification upgrade and
forged energy identity each fail the comparator. Its initial configuration-field
assertion failure and corrected four-path comparison are both preserved.

See `managed-comparison/COMPARISON.json` and `review/MANAGED_RUN_BOUNDARY_REVIEW.md`
for the separate full-value and execution-boundary checks. The raw profiler/test
outputs retain original whitespace; the exact exceptions and clean check of all
other authored files are recorded in `execution/WHITESPACE_CHECK.json`.

This single-query measurement never establishes a
successful ordinary segment, source-session recovery, full brick firing cycle
or material/external validation. See [NEXT_STEP.md](NEXT_STEP.md) for the actual
remaining trajectory gate and the original complete Goal requirements.
