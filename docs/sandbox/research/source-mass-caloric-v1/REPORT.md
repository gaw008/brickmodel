# Source dry-mass caloric adapter and explicit disabled chemistry

The new source_mass_caloric module calls the existing, source-pinned ArlabosseDryCaloric.cp and delta_h providers. It supplies conditional sensible storage for a fixed positive dry mass of the original mixed industrial/municipal feed, with no synthetic A/B reaction network, oxygen reference or dry-solid molecular mass. It does not yet replace WetMixedStorage or provide wet-cell geometry, transport, reactions, sintering or a PDE.

## Physical and coordinate contract

The explicitly selected model assumes fixed composition and an incompressible solid with temperature-independent specific volume and negligible pressure dependence of thermal properties. Under this approximation, source delta_h equals delta_u. A rigid container alone does not establish that relation, and the paper's measured Cp is not relabelled measured Cv. No numerical volume is supplied: intrinsic volume remains unknown, preventing unsupported wet mechanical closure.

The zero of relative u is placed at a reference temperature inside the source's 35–105°C interval. The energy target binds both the reference and the fixed dry mass. Changing either creates a different model identity; old targets are rejected until explicitly transformed. No absolute formation energy is assigned. ReactionDisabled is an explicit stage choice, emits chemical sources of the declared layout only, and does not disable a separately modelled liquid/vapor phase transfer.

For mass m, U(T)=m integral(T0,T) Cp(s) ds. For the pinned source's increasing affine Cp, the whole-bracket lower heat capacity is m Cp(Tlo). Bisection uses |U(T)-target|/Cmin and the original InversePolicy energy/temperature tolerances. Computations and returned temperatures are exact Fractions for the nominal printed relation and exact input target; zero numerical arithmetic error here is not zero fit uncertainty. Source fit error and the incompressibility approximation error remain unquantified. There is no implicit rounding of the output to float; a future float-valued host must account for its own representation error.

Finite float inputs mean their exact binary64 value, explicitly passed to the source provider as Fraction. Decimal and Fraction inputs retain their exact values. Thus binary64 308.15 K lies just outside the lower endpoint and is rejected; Decimal('308.15') is the exact endpoint. Nothing is clipped or extrapolated to force the old 298.15 K reference into the source domain.

## Verification and source trace

The first actual test run failed because the new module did not exist. Initial implementation then passed all 16 targeted tests in 0.51 seconds. Those include independent exact source-review energy/anchor values, inversion, full-domain heat-capacity lower bound, signed relative energies, fixed mass/source identity, endpoint/domain rejection, missing source refusal and explicit zero-chemistry layout. Further independent review and final installed results are recorded below after completion.

For 0.2 kg with T0=40°C and T=80°C, U=13051.2 J. Re-expressing the same physical state with T0=60°C gives U=6657.2 J; the coordinate shift is 6394 J. Both targets must return 80°C in their respective identities. The full source-interval heat-capacity lower bound is 309.83 J/K. These are evaluations of the source fit and selected fixed mass, not independent calorimeter validation.

The evidence registry retains the original Cp node and its integrated enthalpy node, then adds separate scenario/coordinate nodes for the incompressible approximation, reference temperature, fixed mass and disabled chemistry. The U equation depends on all of them. Unknown fit/model errors remain explicit. Raw source assets stay in the original legal ignored cache; no new publisher assets are redistributed.

## Remaining integration

The next substantive step is a source-specific mass-solid/actual-fluid storage path with independently supported available fluid volume or skeletal specific volume, followed by extracting the existing shared cell and face kernels for arbitrary N. Existing WetPair and exact-event/pressure/record layouts still impose manufactured A/B and two-cell constraints. None is silently relaxed by this point adapter. Material transport, source-compatible sorption/energy, reactions, full wet/fired/cooled brick validation and the complete original Goal remain required.


## Final independent review and installed run

The independent reviewer found a real runtime source-binding defect: replacing a constructed provider or caloric adapter could preserve the previous identity while returning forged values. The original source/test versions and independent RED are retained. Both binding layers now revalidate exact supported collaborator types before invoking callbacks, and recheck the declared reference/domain, mass and chemistry layout. No formula, physical interval or numerical acceptance tolerance changed. Final source tests: 19 passed in 0.64 seconds; independent tests: 4 passed in 0.78 seconds, including both substitution failures and near-endpoint/1e-200 J outside-domain targets.

Independent physical review used 80-digit Decimal integration and the quadratic inverse, confirming the two energy coordinates and 309.83 J/K whole-domain lower bound. Its original reviewed source snapshot preceded the binding-only fix; the final code review separately verifies unchanged mathematics and the runtime guard fix.

The final noneditable installed selection includes all 19 source-mass tests, all 5 new water behavior tests and the full 9-case deforming-wet-admission file: **33 passed in 4.70 seconds**, zero failures/errors/skips (session35120 terminal exit0). This closes the former stale AST test failure by testing real behavior; it is not a new full-repository suite. Actual imports came from site-packages with cwd=/private/tmp and no PYTHONPATH. All 108 modules byte-matched source, and final reviewed source/test hashes were rechecked.

`installed-example.json` records the actual 0.2 kg/40→80°C case, exact rational fields, model identity, inverse bound and seven-node evidence trace. U=13051.2 J; recovered T approximately353.1499999999997 K with nominal numerical bound3.1137930636337134e-13 K. The physical fit error and specific volume are null. The bound describes the conditional nominal polynomial and exact target, not experimental prediction accuracy.

A direct Python reproduction uses ArlabosseDryCaloric with the original data/sandbox/research/arlabosse2005/source.json and repository-root arguments, ArlabosseMassCaloric(reference_temperature_k=Fraction('313.15')), a matching ReactionDisabled layout and FixedMassCaloricStorage(dry_mass_kg=Fraction(1,5)). Evaluate Fraction('353.15'), create the model-bound target and invert with InversePolicy(1e-10,1e-8,100). EvidenceRegistry.from_dict(model.registry_payload()).trace(ENERGY_NODE_ID) returns the saved dependency chain.
