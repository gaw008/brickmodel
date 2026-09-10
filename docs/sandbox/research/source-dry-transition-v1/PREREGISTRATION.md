# One actual source N1 wet-to-dry study — prepared, not executed

Baseline `fb799fd`. Execute once only after the parent confirms final source and
installed identities, tests, and independent runner/code review. This file and
`run_native.py` prepare an experiment; they contain no observed native result.

## Fixed sources and new virtual scenario

The predecessor is `source-root-comparison-v1/run_native.py`, SHA-256
`5b8c0e650e051a0ab4eb36e919eaaef18b271f51bb499add23f5e534c8434f28`.
Reuse its two helpers, checked against their original hashes before construction:

- `source-wet-storage-v1/run_native.py`:
  `9a8bbf40651c7dfc31e81c85e8367904e441e210f1c7b1666c9080dbc81b93a6`.
- `exact-source-column-v1/run_native.py`:
  `b0b873960bdc8bc9f2299fc3d0d008fd5fa5a9d3f7a972eb0f080ec3a2d39ab5`.

Use the original `make_case` without changing available fluid volume (0.001 m3),
its declared error (1e-12 m3), source dry mass/Cp, actual O2/N2 caloric providers,
manifest-checked HEOS liquid/ideal-water-vapor providers, any EOS/caloric envelope,
or pressure bracket. Four provider constructors and their successful reference
anchor checks are counted separately. These are not counts of all internal EOS
updates. The constructors themselves perform native reference checks.

The explicitly new virtual numerical scenario starts with **Nl=1e-11 mol**,
gas amounts **(0.125, 0.25, 1e-12) mol**, and **325 K**. One actual forward source
evaluation determines initial total U. Prior Nl=1e-6 scenarios, their retained
failed seeds, and their pressure failures remain unchanged. This new inventory
is not fitted sludge material data and does not retroactively qualify an older
experiment.

Use `SourceWetColumn` with one cell, closed boundaries, no internal face and no
liquid_transport, original cell width 0.25 m and face area 0.01 m2. The nonzero
phase-transfer coefficient remains 1e-9 mol/s/Pa. Initial mode is existing_liquid;
dry mode can arise only from the checked terminal writeback. Use exactly
`InversePolicy(1e-5, 1e-6, 100)` and the existing disabled chemical reactions.

## Frozen numerical controls and sequence

One actual positive finite initial evaporation probe E determines exact
`H=(3/2)*Nl/E`. Initial/max reference step is the binary64 value of that actual
H; minimum step 2^-30 s, relative tolerance 1e-8, amount tolerance 1e-7 mol,
energy tolerance 1e-3 J, amount scale 1 mol, energy scale 1e5 J, maximum four
accepted steps and four rejects, and 180 s per-trial/path wall policy are retained.
These controls are saved in full, including the actual derived H.

Keep all original DepletionPolicy gates: time 1e-8 s, N 1e-11 mol, U 1e-7 J,
T 1e-5 K, P 1e-4 Pa; terminal window 0.001 s, 32 total refinement rounds,
common-time horizon 0.01 s and safe inventory fraction 0.25. Explicitly select
`terminal_method='affine_midpoint'` for this new terminal execution. No ordered,
nested-approach or alternative pressure-comparison policy is enabled.

Original roundoff budgets remain: local correction 1e-15 mol, correction fraction
1e-8, local/cumulative vapor storage 1e-15/1e-14 mol, local/cumulative element
2e-15/2e-14 mol, local/cumulative mass 1e-16/1e-15 kg, and cumulative correction
1e-14 mol. Set its water molar mass from the **actual constructed
`chemical.reference.molar_mass_kg_mol`**, matching the storage water reference.
The former `.018015268` test literal differs by one binary64 ULP from that source
value; using the source value repairs the species identity, not an error threshold.
Both values, their exact Fraction difference, and ULP difference are saved; no
old policy record is edited and no scientific tolerance is relaxed.

Run the following once, saving each returned record before later assessment:

1. Initial source probe, then a SourcePrefixTrial from the initial state to H.
   Require the actual first/midpoint observations and retained negative-inventory
   full-prefix failure; do not manufacture a seed or reuse another scenario.
2. Propose and execute the actual positive approach with the original controls,
   requiring its completed original reference.
3. Execute the shifted-root trial from that actual reference endpoint to H.
   Preserve its failed full prefix if present. Require available independent
   actual root comparison; keep its original shared refinement budgets.
4. Call `evaluate_source_dry_transition(refinement, end=seed.end,
   maximum_callbacks_per_path=24)`. Execute both source terminal/writeback/dry
   reference candidates through the production entry. Each actual dry adapter
   may be a different object, but must retain the original column data, source
   storages, energy identity, fixed dry kg masses and explicit depleted_no_nucleation
   mode. Do not route dry calls through the original wet object.

Candidate execution, completion of numerical comparison, conditional numerical
event acceptance, and material qualification are distinct. Save both original
N/U/T/reported-P and conditional dry pressure gates at the event and common end,
the clock gate, full cumulative balances, writeback/roundoff evidence, and actual
dry reference steps. Pressure can still fail under the original volume/error
declaration; **do not assert event acceptance**, lower eV, cancel common uncertainty,
or enlarge the 1e-4 Pa threshold. Material qualification remains false. Existing
candidate/terminal/pressure event flags retain their meanings; the new transition's
`numerical_event_accepted` is saved separately rather than relabeling old objects.

## Resources, failure retention and persistence

Each seed/approach/shifted trial allows at most 16 actual source callbacks; each
dry path at most 24. Whole-study cap is **97 = 1+3*16+2*24**. A 32-call minimal
path is a planning estimate only, never a forced or asserted observation. Report
the actual attempts and wall time. Keep the 210 s outer SIGALRM request over
construction, execution, checking and writing; native calls may observe the
signal only when they return to Python. This is not a hard native interrupt.
There is no automatic native retry or budget increase.

Before every actual source callback, atomically save its ordinal, phase, exact
time, packed input and actual operator/mode/energy identity. Save returned values
or real exception afterward. Returned candidates are also saved before transition
postprocessing, and SourceApproachAssessmentError/SourceRootStudyError/
SourceDryTransitionError context and nested exception causes preserve all already
returned trials, partial comparisons and candidate evidence.

The recursive serializer preserves nested dataclass type/fields, exact Fraction
numerator/denominator and ndarray dtype/shape/values. Only live adapter, dry_adapter
and storage fields are omitted; original source/identity fields remain. Wet and
actual dry adapter provenance is saved separately. Nonfinite values in failed
observations are explicitly tagged, not silently converted to finite data or
written as invalid JSON. JSON updates use a sibling pending file and atomic
replacement; actual constructor/anchor and initial-U counts are saved separately.

This N1 closed candidate study does not complete nonzero heated dry continuation,
program-node handling, mult cell drainage/paired donor enthalpy, rewetting, material
validation, full kiln reaction/sintering/cooling, public mechanism holdouts or
application/multigeneration goals. It is one bounded native experiment within the
remaining authorized work. Review and preparation do not establish its outcome.
