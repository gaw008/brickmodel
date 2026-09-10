# Source-column liquid depletion versus old evaporation writeback

Read-only design review. No repository edits, EOS calls or numerical trajectory. Files reviewed: mass_wet_exact_terminal.py, mass_wet_writeback.py, exact_affine_depletion.py and current source-column/liquid face contracts. This is an implementation route, not a completed event admission or evidence that a numerical root is the exact physical event time.

## The old host cannot be directly reused

Old prepare_mixed_terminal uses two cells, a single face and A/B solid inventories. Its initial tangent is Nl/phase only for positive evaporation. Candidate liquid samples are `(0,0,-phase)`. MixedTerminalEvidence explicitly rejects nonzero liquid face terms, and state/panel layout requires exactly two A/B solids. ExactAffineEvidence itself includes a correction budget relative to positive evaporation. These are substantive contracts, not merely names or removable shape checks.

project_mixed_depletion sets the selected residual liquid delta to zero and adds delta to the same cell's vapor, at unchanged U. This is a numerical phase redistribution with local ulp, absolute correction, gross positive evaporation fraction, original liquid fraction, cumulative and vapor storage-rounding gates. It is not a generic drainage projection. Replacing 'evaporation' with net removal would violate both accounting and the intended safeguards. Keep all old gates and old behavior unchanged.

For the new source column:

Nl_i' = Jliquid_i - Jliquid_(i+1) - phase_i.

Positive face orientation is increasing cell index. Net depletion D_i=Jright-Jleft+phase can be positive even when phase<=0. A drainage-only event has zero gross positive evaporation, so any nonzero forced conversion to vapor fails the old fraction gate for a sound reason.

## Reusable numerical foundations

Reuse isolated exact Fraction polynomial evaluation/integration/minimum/root-enclosure/root-order primitives after separating them from any evaporation-correction admission. ExactEventTime arithmetic and exact schedule knot subdivision can also be reused. Preserve common-face samples and signed contributions once per face, rather than constructing separate per-cell flux histories.

A source-specific panel adapter should expose affine rates for every gas face, liquid face, total face energy, energy component and local phase term, including boundary terms. Form each cell's inventory polynomial by exact incidence aggregation. For sampled rates r0 and rm at separation hm, r(t)=r0+(rm-r0)t/hm, so N(t)=N0+r0*t+(rm-r0)t²/(2hm). This is a polynomial of the numerical panel. Its exact root is not automatically the exact root of the physical nonlinear ODE.

The predictor horizon may use Nl/D when D>0, not only evaporation. A nonnegative initial derivative does not prove no later affine root: the quadratic minimum/root test must also cover accelerating drainage. If no safe actual midpoint can be sampled, shorten/rebuild the panel within explicit resources; do not extrapolate from an invalid negative-inventory stage. Split before programme knots. Check competing gas/other liquid inventory roots over the whole panel and require all other admissibility gates, rather than relying on endpoint positivity alone.

A new root-evidence type must bind the full source host identity, source/geometry/transport programme, exact sample times and actual states/rates. Root isolation can use arbitrary adjacent rational lower/upper bounds and carry its own root residual certificate without a positive-evaporation precondition. Existing evaporation evidence is not such a generic type.

## Complete implementation sequence

1. Build the N-cell shared-face affine panel and exact inventory derivative/incidence mapping, preserving numerical rate/projection residuals and old-host regressions. Root's current planned foundation is the correct first dependency.
2. Add source-specific candidate and exclusion evidence using all wet cells and full Nl' terms. Prove first-root ordering or return unresolved; do not select by list order. Preserve unsupported/uncertain results and the accepted prefix. Simultaneous roots need a grouped atomic treatment or an explicit unsupported result, not arbitrary sequential mode switching.
3. Assemble one exact terminal ledger at the selected certified numerical time/enclosure using the same shared component integrals. Project each cell's combined quantities once to binary64 and record signed corrections. Keep numerical interpolation/truncation error distinct from exact polynomial arithmetic and binary projection.
4. Prefer an exactly representable zero residual whenever the numerical polynomial reaches zero at a representable exact time and state admission permits it. This needs no residual phase or transport correction. For a general nonzero residual, require an explicit new numerical writeback policy described below; never silently clamp.
5. Independently admit the entire corrected state tuple through source storage inverses and the event's permitted interface law before any global write. Check source bindings, conserved ledgers, correction budgets, competing events, and unchanged fixed dry masses. Commit event record/state/mode/config atomically only after every gate passes.
6. Continue under an explicit post-depletion constitutive/interface policy, not merely a changed phase mode. Bind the new operator identity and transition record. Retain event compare/time-step refinement and source-domain tests before claiming reliable event trajectories. Record/resume serialization requires a new source-column codec and replay checks; identical scalar clocks do not authorize reuse of the A/B codec.

## Residual policy choices must be explicit

The most conservative initial admission is zero-correction only, with nonzero unresolved residual returning a bounded unsupported projection result while preserving the last accepted state. This is an honest intermediate implementation, but not completion of the broader event objective.

To support general transport-induced depletion, introduce a separate, narrowly scoped conservative numerical drainage correction. If delta residual liquid is removed from the selected cell and assigned to a neighboring liquid receiver along an evidenced outgoing internal face, add delta to that receiver's liquid and move the same delta*h_donor energy from donor to receiver. Use the same frozen, source-bound donor enthalpy for both sides; evaluate a wet lower-end donor state if needed, never invent liquid h after the donor is dry. Record a shared numerical face correction separate from the physical integrated face ledger. No vapor is created, no external water loss is fabricated, and no extra latent/pQ source is added.

The transport correction needs its own predeclared absolute, local-ulp/root-residual, original-inventory fraction and cumulative budgets, plus a fraction of independently evidenced gross outward liquid throughput. Do not borrow or loosen the evaporation fraction policy. Choose any multi-face allocation rule deterministically before seeing residuals (for example restricted to a single evidenced outward face in the first version); if no eligible recipient exists or the full corrected tuple fails inversion/domain constraints, refuse the correction. A fresh arbitrary distribution of the residual is not physical evidence.

For mixed evaporation/drainage cases, keep phase and transport corrections separately classified and budgeted. One safe first policy may choose only the evidenced transport path for a tiny numerical residual, without claiming that allocation is an exact physical partition. A later partition policy must be explicit and source/identity-bound; do not reinterpret condensation as negative evaporation or substitute net depletion for gross positive evaporation. A pure evaporation extension may implement the same conservative phase-correction semantics and unchanged old thresholds in a new source-layout adapter, but cannot call the old A/B evidence object unmodified.

All nonzero writeback is a numerical perturbation to a localized numerical event. It must be disclosed and audited; neither a literature citation nor exact Fraction arithmetic makes the correction physical truth. Additional receiving-cell/vapor binary rounding and associated energy corrections must be recorded in full, with no clipping and no post-hoc tolerance expansion.

## Dry continuation is a separate physical boundary

Current liquid_face_exchange with connected nonzero mobility requires liquid on both sides. Marking a phase cell depleted_no_nucleation does not satisfy that liquid-face contract. The present manufactured frozen table has positive mobility at S=0, so a dry connected face will reject even if the phase mode is changed correctly.

Continuation therefore needs either (a) a previously declared constitutive zero-mobility dry limit supported by the actual table and interface policy, or (b) an explicit manufactured 'dry interface disabled/no rewetting' transition policy, with new identity, scope and source classification, or (c) a preserved domain exit until a rewetting/capillary law exists. Do not automatically disable a connected face and present it as measured sludge physics. Incoming liquid rewetting and vapor condensation/nucleation are distinct processes, neither already solved by a phase-only dry switch.

## Necessary independent tests

- Exact constant-rate drainage with phase=0, and drainage stronger than condensation with phase<0; verify event exists and no vapor is manufactured by event handling.
- Exact evaporation-only case preserving all old numerical correction thresholds and results; require nonzero drainage correction to be refused by old evaporation writeback unchanged.
- Initial net liquid gain followed by affine depletion; nonmonotonic polynomial/no-root/tangent-root cases, root at a schedule knot, large exact clock translation, and root-order ambiguity.
- Three or more cells with both adjacent liquid flows active; all shared internal water/energy terms telescope. Explicit open gas boundary remains the only external water exchange while liquid boundaries are zero.
- Constant liquid donor h/v drainage correction with exact expected paired molar and energy transfer; reverse donor direction, multiple-outflow ambiguity, receiver inversion failure, zero gross transport/evaporation budget, and malicious correction beyond any original/cumulative gate.
- Earlier gas depletion or another liquid root blocks the selected event; simultaneous liquid roots are grouped or explicitly rejected without partial state/mode writes.
- After event, connected positive-mobility dry face rejects; only a declared dry mobility/interface policy permits continuation. Test rewetting and condensation attempts stay unsupported when no law is declared.
- Short manufactured nonlinear trajectory with step/panel refinement against an independent ODE reference, reporting event-time differences separately from root-enclosure width and writeback magnitude. A polynomial root-width certificate alone is insufficient.
- Cancel/resource/source-mutation at every prepare/project/admit/commit stage leaves a complete valid prefix. Replay verifies exact clocks, physical versus numerical face corrections, energy coordinates, source identities and remaining original budgets.

No EOS or event trajectory was run in this review. Actual sludge liquid mobility/connectivity, dry-limit/rewetting law and full model qualification remain open requirements.

## Addendum: fixed dry mass with a four-fluid ConservedState adapter

Root's revised route (ExactSourceColumn translating existing source rates into generic Rates) is a legitimate reduction and avoids duplicating an integrator. When each dry mass is invariant and chemistry is explicitly disabled, dry kg are parameters, not dynamic state variables. It is correct for amounts_mol to contain only four actual molar inventories: liquid H2O, O2, N2, vapor H2O. U must continue to contain both fluid energy and fixed dry sensible energy. Omitting the constant solid inventory from the dynamic vector does not omit its heat capacity.

The adapter must bind ordered per-cell SourceWetStorage identities, exact binary64 dry masses, caloric anchors, layout, transport/geometry and programme into the non-None tuple energy_model_identity already supported by ConservedState. Reject unbound or foreign state identities before decoding, wrong cell/species shape/order, nonzero/unsupported mechanical stretches, or source/model mutation. Encode/decode must preserve all physical fluid amounts and U without introducing an unrecorded extra projection. Recovering fixed dry masses must use the bound storage for each corresponding cell.

Rates.face_species_mol_s columns then carry liquid transport and the three gas fluxes. Local source slot reaction_species_mol_s may numerically carry (-phase,0,0,+phase), but this is an existing generic local inventory-source storage convention: explicitly label it phase transfer and keep ReactionDisabled exact. Do not claim it is a chemical reaction or add chemical/latent cell power. face_energy_w remains the existing total enthalpy/conduction sum once. Preserve component diagnostics outside the generic total Rates if the latter cannot represent all liquid/gas distinctions.

Generic exact-time integration and polynomial tools may operate on this valid fixed-solid state. This does not authorize the mechanical-specific ExactFreeWaterTransfer driver, existing phase-only writeback, A/B records, or automatic resume; their gates still require explicit source-specific admission. No fictional molecular weight or dry-solid mole count is necessary.

Future reactive or transported solid mass is a different state contract. Once dm_dry/dt is nonzero, dry kg cannot remain hidden in fixed model parameters: otherwise the missing u*dm and composition changes break storage/energy interpretation. Add an explicit mixed kg/mol dynamic state (or another scientifically justified species basis), element/mass bookkeeping, source-compatible reaction/transfer energetics and identity migration. Never insert kg into amounts_mol or invent a dry pseudo-molecular weight solely for array compatibility. Arbitrary source sensible reference anchors are harmless only at fixed composition/mass; reactive formation/reference consistency requires new evidence and accounting. This restriction is a declared next-stage requirement, not a claim the overall firing-model objective has narrowed to nonreactive drying.

Necessary adapter checks: exact encode/decode roundtrip; compare one decoded evaluation with existing SourceWetColumn across N=1 and N>=3; verify phase source-column sum is zero in water and no chemical power; closed/open flux ledgers use the same liquid/gas/energy components; a changed dry mass or reference anchor rejects the old state identity; unsupported dynamic mechanics/solid conversion reject rather than silently disappear. These can be implemented without changing any old event threshold.
