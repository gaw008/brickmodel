# Independent material accounting review

Review date: 2026-09-07 UTC. Reviewer: separate Codex Python review agent. Scope: `src/sludge_sandbox/materials.py` and `tests/sandbox/test_materials.py`. The reviewer did not change production code, stage files, commit, or alter the concurrent B2 validation work.

**Current decision after the repair recheck below: Approve for the material-accounting implementation milestone.** Both initial findings are resolved; their original evidence is retained below. No scientific source admission or material-property validation is implied.

## Initial decision: Block on analysis-category admission

Native/added-water bookkeeping and unknown-value rejection are correct for the inspected cases. One HIGH category-admission gap and one MEDIUM exception boundary were independently reproduced. This report concerns schema/accounting behavior, not external scientific validation of a real sludge or brick material.

### [HIGH] Analysis labels can conceal cross-category quantities

File: `src/sludge_sandbox/materials.py:87`

Issue: only the analysis-level `kind/basis` pair is checked. Each analyte name only needs to be nonempty text, so an apparently complete oxide analysis may include loss on ignition or a mineral phase, and an elemental analysis may include an oxide mass. These quantities have distinct meanings and cannot be treated as interchangeable mass fractions merely because their sum is one.

Reproductions accepted by the initial implementation:

```python
MassAnalysis('oxide', 'dry_solid', {'SiO2': .6, 'LOI': .4},
             'complete', 'fixture:analysis')
MassAnalysis('oxide', 'dry_solid', {'SiO2': .6, 'quartz': .4},
             'complete', 'fixture:analysis')
MassAnalysis('elemental', 'dry_solid', {'C': .6, 'SiO2': .4},
             'complete', 'fixture:analysis')
MassAnalysis('mineral_phase', 'dry_solid', {'quartz': .6, 'LOI': .4},
             'complete', 'fixture:analysis')
```

The existing `oxide/LOI` rejection test uses `.7+.4>1`; it fails because the total exceeds one and does not verify category separation.

Fix: give analytes explicit resolved types or apply an appropriate category-specific validation contract. Element and oxide identities need consistent chemical meaning; arbitrary mineral labels must retain source-resolved identities rather than being guessed from XRF. Known LOI/proximate fields must not be silently included as oxide, elemental or mineral-phase constituents. Add tests whose totals equal one so closure checks cannot conceal this admission gap.

### [MEDIUM] Mass-analysis summation overflow escapes `MaterialError`

File: `src/sludge_sandbox/materials.py:90`

Issue: individual fractions are only constrained to finite nonnegative numbers. `MassAnalysis('elemental', 'dry_solid', {'C': 1e308, 'N': 1e308}, 'partial', 'fixture:analysis')` raises raw `OverflowError: intermediate overflow in fsum`, bypassing the declared `MaterialError` contract. Batch aggregation already translates overflow; analysis aggregation does not.

Fix: reject individually impossible fractions and/or guard `fsum` so invalid assay data consistently produces `MaterialError`. Keep the measured values unchanged; rejection must not be implemented by renormalizing the input.

## Verified behavior

- Explicit material classes distinguish `raw_sewage_sludge` from `sewage_sludge_ash`. The ambiguous label `Raw SSA` is rejected rather than inferred as raw sludge. Batch/source IDs are retained. These are declared identities; their authenticity is not established here.
- Basis families are declared separately for elemental, oxide, mineral-phase, proximate and loss-on-ignition analyses. The category-admission finding above concerns the contents of each table.
- A partial oxide example `{SiO2: 0.51, Al2O3: 0.27}` remains unchanged with an arithmetic unassigned fraction of 0.22. Input mapping mutation does not change the captured analysis, and returned fraction mappings reject writes. No mineral-phase inverse or silent normalization is performed.
- For dry solid mass `m_d` and native wet-basis fraction `w`, native water is `m_d*w/(1-w)`. Converting a supplied wet feed uses `m_d=m_wet*(1-w)`. Added forming water is a separate explicit mass. Total water and wet mass are computed once from these terms.
- A manufactured two-material batch with 2 kg dry sludge at 80% native water, 6 kg dry clay at 10% native water, and 1 kg extra forming water gives 8 kg dry mass, 8 + 2/3 kg native water, 9 + 2/3 kg total water and 17 + 2/3 kg wet mass. Dry mass fractions are 0.25/0.75.
- An independent Decimal calculation checked **30** one-material cases: dry mass 0.125/2/1000 kg, native wet-basis fraction 0/0.01/0.4/0.8/0.95, and 0/1.5 kg additional water. Maximum relative wet-mass error was `9.094947017729283e-16`.
- Null, NaN, boolean, negative and unrepresentably large native-water values are rejected. Native water is not defaulted to zero; dry mass must be positive and wet-basis water fraction must be below one. Explicit zero water is allowed.
- Duplicate material IDs are rejected before they could overwrite dry-fraction contributions. This is an explicit current API restriction, not automatic aggregation of separate batches.
- `scientific_status='bookkeeping_only_sources_not_resolved'` accurately describes the result. Source node IDs are retained for later resolver checks and do not imply evidence eligibility or applicability.

## Executed evidence

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_materials.py -q
20 passed in 0.02s
```

The category-mixing and overflow reproductions above are independent of those tests. No material parameters were added or inferred by this reviewer. Static analyzers were unavailable in the project environment; manual inspection and executed probes were used.

Initial hashes:

```text
1c2434d6784c589e57665e8b9c72ca3c26fcaef1df08761ee464de1137a52d43  src/sludge_sandbox/materials.py
62d7d1f289f17ea73cdc627dc3766ebe67145f5af4db365b0eb63a5b169ad78d  tests/sandbox/test_materials.py
```

## Repair recheck: both findings closed

The reviewer independently inspected the repaired analyte contract and executed:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_materials.py -q
25 passed in 0.02s
git diff --check
passed
```

Fourteen additional independent probes passed: the four original cross-category cases and the huge-fraction case now raise `MaterialError`; water-as-oxide, LOI-as-proximate and ash-as-LOI are rejected; valid elemental, oxide, proximate and LOI tables retain their input values; per-phase source mapping is snapshotted; mismatched phase identity keys are rejected.

The implementation now validates elemental symbols, a declared binary-oxide formula syntax, dedicated proximate/LOI labels and individual fractions at most one. Mineral-phase analyses require a separate identity node for each phase rather than inferring phases from an oxide label. The mappings are preserved as declared evidence links for a later resolver.

The oxide check is syntactic classification. It does **not** establish chemical valence, electroneutrality, a stable phase, or real mineral occurrence. Likewise, a mineral phase ID is not scientific proof until the resolver and source review verify its referenced node. These boundaries are consistent with this module's bookkeeping-only status.

Final reviewed hashes:

```text
4fd1ea01d49f345b3cd4745f4a3e44da747ee7ebd2bcc16e6ed4d7f3e833e591  src/sludge_sandbox/materials.py
2ca0fdeb09c81e143b432f5722dc1c7eeb18991a3b9d784425e271dcd6a33467  tests/sandbox/test_materials.py
```

No unresolved CRITICAL/HIGH/MEDIUM issue raised in this scoped material-accounting review remains. The module is suitable for the authorized local implementation milestone; full real-material source resolution, mixing physics and the coupled sandbox remain separate requirements.
