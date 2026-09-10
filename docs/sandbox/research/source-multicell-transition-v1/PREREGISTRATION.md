# N3 selected-cell source wet/dry transition — preregistered once

Implementation baseline `3fdea98`. This is a new three-cell HEOS experiment,
prepared before execution. Root will run it once only after source/installed
checks, package identity verification and independent runner/code/physics review.
There is no result assertion, automatic rerun or post-failure budget increase.
All earlier N1 runs and their accepted/rejected numerical evidence remain intact.

## Sources and construction

[run_native.py](run_native.py) derives its atomic saving, callback capture,
returned-candidate retention and exception-chain logic from the preceding
[source-dry-shared-pressure runner](../source-dry-shared-pressure-v1/run_native.py),
SHA-256 `f0c8a659053630ccad55901b0a7f6bf16c07b35313f54ce596087f54f277196b`.
Before constructing any backend it verifies that file and these original helpers:

- [source-wet-storage constructor](../source-wet-storage-v1/run_native.py):
  `9a8bbf40651c7dfc31e81c85e8367904e441e210f1c7b1666c9080dbc81b93a6`.
- [exact-source-column serializer](../exact-source-column-v1/run_native.py):
  `b0b873960bdc8bc9f2299fc3d0d008fd5fa5a9d3f7a972eb0f080ec3a2d39ab5`.

Call the original `make_case` once, then build three distinct SourceWetStorage
instances and three distinct available-volume objects by copying its checked
storage/volume values. The actual water/gas providers, source Cp, fixed dry mass
0.2 kg per cell, chemical convention, caloric reference, source errors and
V=0.001 m3 with eV=1e-12 m3 are retained. The three spatial uncertainty parameters
are separate even though their numerical values are equal. Use the original
HEOS manifest/backend and a separately constructed HEOS WaterChemicalPotential.

Count the actual four successful HEOS provider constructors/reference-anchor
checks: two in the shared storage template and two in the chemical provider.
The three storage copies are not counted as extra native constructors. These
counts describe constructor/anchor invocations, not every internal native update.
Forward initial U is evaluated separately for each of the three cells; save
three before/after attempts, three actual points and three resulting U values,
or the exact partial list and failure if construction/initialization stops early.

## Fixed new numerical scenario

Use actual SourceWetColumn and ExactSourceColumn with N=3. All cells start at
325 K in `existing_liquid` mode; intended first event cell is k=1 (zero-based).
The same values were declared before the manufactured terminal fixture was run:

| Cell | Liquid mol | O2 mol | N2 mol | H2O vapor mol | Phase coefficient mol/s/Pa |
|---|---:|---:|---:|---:|---:|
| 0 | 0.25 | 0.125 | 0.25 | 1e-12 | 0 |
| 1 | 1e-11 | 0.1875 | 0.25 | 1e-12 | 1e-9 |
| 2 | 0.25 | 0.125 | 0.25 | 1e-12 | 0 |

Closed boundaries; widths (0.25, 0.3125, 0.375) m, face area 0.01 m2.
Keep actual face half-widths derived from those widths. Set gas diffusivities,
gas permeability and thermal conductivities to zero to isolate paired liquid
transport and its donor enthalpy. Retain gas viscosity 1.8e-5 Pa s in the face
configuration. Internal face 1 (cells 0/1) is explicitly disabled at construction;
internal face 2 (cells 1/2) is connected. No connection changes after depletion.

Liquid transport is a declared manufactured numerical table, not measured sludge
mobility: saturation knots (0, 1e-18, 1), permeability (1e-18, 1e-18, 1e-18) m2,
relative permeability (0, 0.5, 0.5), viscosity (0.001, 0.001, 0.001) Pa s,
T domain [310,350] K and P domain [1e4,1e7] Pa, tabulated saturation relation.
The tiny positive knot gives the wet samples a plateau while declaring exact
zero mobility at zero saturation. This law is fixed in advance and remains in
the dry adapter. The native run's table source asset is the actual runner path
and SHA-256, rather than a dummy test digest. Geometry, transfer coefficients,
initial compositions and mobility remain explicit virtual/manufactured inputs;
real water/source thermochemistry does not turn them into material calibration.

The actual initial callback must show positive selected-cell evaporation and
net loss, zero left liquid flow, positive right liquid flow and nonzero actual
liquid enthalpy power. Define H=(3/2)Nl_1/(E_1+J_right−J_left) using Fractions of
the actual saved binary64 rates. Transport is not counted as gross evaporation.
The first unique root must be ('liquid',1,0) on both independently executed
coarse/shifted paths; otherwise preserve the actual failure and stop.

## Unchanged scientific gates and path controls

Use InversePolicy(1e-5,1e-6,100) in every cell. Retain initial/max integration step
float(H), minimum step 2^-30 s, relative tolerance 1e-8, amount absolute tolerance
1e-7 mol, energy absolute tolerance 1e-3 J, scales 1 mol and 1e5 J, maximum 4
accepted steps/4 rejections, and 180 s per original path policy. These positional
IntegrationPolicy values retain their original meanings.

Event thresholds: time 1e-8 s, N 1e-11 mol, U 1e-7 J, T 1e-5 K, P 1e-4 Pa;
terminal window 0.001 s, maximum refinements 32, explicit affine_midpoint,
existing default common horizon 0.01 s and safe fraction 0.25. Keep all original
roundoff budgets: correction absolute 1e-15 mol; correction/actual positive
evaporation fraction 1e-8; storage absolute/cumulative 1e-15/1e-14 mol;
element absolute/cumulative 2e-15/2e-14 mol; mass absolute/cumulative
1e-16/1e-15 kg; cumulative correction 1e-14 mol. Bind water molar mass to the
actual chemical reference and all three storage water references. The saved
comparison with old test literal 0.018015268 kg/mol reports its representational
ULP difference; it does not loosen a threshold.

Run the actual initial probe, two-sample seed, positive approach, shifted seed,
and two existing terminal/writeback/mixed dry-reference candidates to the
original seed.end. Only cell 1 may switch to depleted_no_nucleation. Retain all
other inventories, all cell energies and the original liquid configuration;
actual dry evaluation must follow that configuration rather than invent a new
transport boundary. The existing kernel may refuse a state/domain, and that
failure remains evidence.

Declare shared volume explicitly for the actual cell-1 storage/volume object
only. Every callback must retain all three original storage/volume objects,
complete N-cell modes and energy identities. The two path adapters can differ,
but share corresponding original parameters. Cells 0 and 2 remain wet and use
their original full-temperature wet pressure enclosures. Save all per-cell
reported/independent/selected pressure values and gates, including any wet-cell
failure. The selected dry cell alone may use the joint full-T/shared-V dry
bound. Do not apply its correlation to different spatial cells or take a min
across the older independent and new machine-error targets.

Numerical comparison completion and numerical event acceptance are separate
saved outcomes. Original clock, all-cell N/U/T/P and cumulative ledgers must
all pass to accept numerically; no acceptance is asserted or forced. Shared dry
P success cannot override wet-cell P failure. Source/material/event-certificate
flags retain their original false values. This experiment addresses one
manufactured single-event N3 execution, not general drainage-only writeback,
repeated depletion/rewetting or validation of a real sludge material.

## Predetermined resource limit and retained evidence

Caps remain 16 actual callbacks per seed/approach/shifted trial and 24 per dry
path, with total 97=1+3×16+2×24. A previous 32-call path is only a planning
estimate; report this run's measured attempts, including failed callbacks.
Original adaptive step rejections remain within their existing policy; there
is no automatic external rerun.

Set the new experiment's outer SIGALRM budget to **510 s in advance**. This is
not a modification of the previous N1 210 s budget. It uses documented N3 costs
as context: [exact-source-column](../exact-source-column-v1/REPORT.md) recorded
448.601522 s for 47 evaluations, while the earlier
[source-liquid-column](../source-liquid-column-v1/REPORT.md) run took about
23.68 s for three evaluations. These are different scenarios and do not promise
completion here. The signal requests a stop at the Python boundary; it cannot
guarantee interruption inside a native backend call. Never increase the budget
after failure.

Save atomic JSON before and after each actual callback and each initial U
attempt. Retain full packed N-cell input, exact time, modes, operator/energy
identity, per-cell same-object checks, every complete returned source observation,
returned candidates before postprocessing, partial pressure rows, comparison
failures and chained causes. The existing recursive serializer retains nested
types, Fractions and ndarray data, omitting only live adapter/dry_adapter/storage
fields; source identities and provenance remain. Save process-local object IDs
as runtime admission evidence, not an offline permission to reconstruct shared
objects. Root records final source/installed byte identity separately before
execution. Audit the saved raw output without starting another native run.
