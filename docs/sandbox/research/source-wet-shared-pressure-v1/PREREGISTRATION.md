# Source wet shared-pressure stage: actual execution registration

Baseline fe9d684. The previous record-persistence stage was progress. This stage
implements the strict `physics/CONTRACT.md` and a new explicit wet-cell pressure
strategy. Original physical inputs, volume error, event gates and independent
pressure failures are retained. Root contributes transition wiring and the native
study wrapper; implementation and independent review are separately owned.

Before native execution freeze the final reviewed production/test files, this
runner and the physics contract. Run relevant source and noneditable installed
tests once per final version, including the existing paired-pressure golden,
source wet/dry comparison and new wet root/roundoff/qualification tests. Check
actual XML and installed file identity. No changed tolerance is allowed.

The new native study is one actual N3 run using the frozen previous orchestrator
`source-multicell-transition-v1/run_native.py` (SHA
1250733f5eddb41f4c4bbdb1bdbad235d553ecb79c98c12a7c848362774c556c).
Importing it performs no simulation. Its original material/geometry/transport
settings, helper file identities, `.001 +/- 1e-12 m3` per-cell volumes, physical
program, integration/event policy and callback caps remain unchanged. These
include an explicitly manufactured geometry/transport envelope, not a qualified
raw-sludge material. Retain its original 510 s hard runtime limit, 97 maximum
source callbacks, four provider constructors/reference checks and three initial
U evaluations. Prior measured source callbacks were 32 and wall time 71.77 s;
these are cost estimates for planning, not assertions about the new run.

Only the newly opt-in pressure comparison changes. Each remaining wet cell gets
its own live shared-volume declaration, tied to the exact storage/volume used by
both new candidates; spatially distinct parameters remain distinct. Original
selected dry-cell declaration remains as before. Four wet pairs (two cells at
event/common) each collect at most four real T/P/phase points, so at most 16 new
public EOS requests. Exact within-pair duplicates may be reused; identical keys
across different pairs are reported honestly as repeated observations unless a
reviewed shared cache actually avoids them. No approximate-key merging or
post-failure widening of the support interval.

Record each request before calling state_tp, its complete returned WaterState
before collector validation, and any failure. Save every pair's returned status,
support/root signs, full Gamma/temperature contributions and source binding.
The wrapper records these extra requests separately from the orchestrator's
source callbacks and provider reference anchors. Pair checks must perform no EOS.

Completion of the run, conditional numerical event acceptance and material
qualification are distinct. Require preserving the full old independent bounds
and N/U/T/time gates; select only the newly proven joint wet bounds where supplied.
All cells must pass; a missing or unresolved wet pair cannot use a convenient
fallback to pass the event. Original pressure threshold is 1e-4 Pa. A failed
result is a valid saved outcome, not grounds to change the policy or rerun blindly.

Keep the frozen orchestrator's raw output and stdout untouched. The wrapper's
final result adds its execution identity, actual new strategy and an explicit
label for the parent's inherited initial strategy metadata. It does not change
the nested numerical outcomes or observations. Independently audit saved new
pressure fields/whole-cell acceptance and compare the original numeric inputs,
policies and physics observations with the old N3 where meaningful. Matching old
observations is compatibility evidence, not external material validation.
