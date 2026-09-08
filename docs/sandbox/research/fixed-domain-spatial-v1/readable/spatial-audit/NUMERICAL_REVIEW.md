# Fixed-domain spatial refinement: numerical review contract

Preparation only; final worker files are pending. No EOS/tests/source edits. Root owns the independent scaling script; this report does not duplicate that implementation. Execution approval remains pending frozen scripts and source-bound initialization evidence.

## Initial extensive energy gate derived from provider bounds

DeformingSolidStorage.forward(T,...) returns DeformingSolidState with total_energy_j and energy_error_bound_j. The latter is the outward sum of thermal.energy_error_bound_j, mechanical error (elastic/interface numerical enclosures, reference-volume geometric contribution, additional declared mechanical error), and exact total-addition rounding. Using only thermal.error omits part of the total energy model. state_from_temperatures returns the represented energies but discards these bound records, so the experimental fixture must retain corresponding forward evidence explicitly.

For a parent and its two correctly scaled children at the SAME represented nominal temperature, time, intensive composition and deformation, record Ep,Bp and E1,B1,E2,B2 from the actual forward provider. The acceptance inequality is:

abs(Fraction(Ep)-Fraction(E1)-Fraction(E2)) <= Fraction(Bp)+Fraction(B1)+Fraction(B2).

No unexplained absolute tolerance is required. Use exact Fraction sums; if output displays float sums, store the display rounding separately and do not feed it back into the exact test. This is compatibility within declared source/numerical uncertainty, not equality of two independent noisy material measurements or proof that the provider law is correct. The analytic no-EOS extensivity checks remain necessary to show the intended model did not change.

Any new forward evaluations are actual provider work and must fit the unchanged callback/supervisor budget. Do not call this read-only script preparation zero native cost after execution. Full DeformingSolidState evidence may be large but its relevant total bounds, components, geometry and identity must be retained.

## Old inherited energy versus new same-temperature evidence

The actual archived two-cell callback initial state supplies the conservative N/E parent values. Its stored decoded thermal temperature differs slightly from nominal requested 300/301 K because of inverse error. Comparing a child forward at nominal T against a parent state evaluated at this slightly different decoded T is NOT a same-T extensivity test unless the temperature mismatch is propagated with a valid energy sensitivity bound. Prefer recording parent and child forwards at the same nominal T, and keeping that test separate from the archived initial-energy binding check.

For conservative prolongation require each child's amount and represented E equal parent/2, and require exact Fraction parent-pair sums. Reject unrepresentable division/underflow. Decode that inherited target through each fine point, preserving the fine model identity and original inverse gates. A declared nominal-temperature consistency test can use the actual returned inverse temperature bounds; it cannot assume that a source-energy uncertainty is a zero-width temperature constraint.

Archive and verify the original callback input bytes/hash and its original source identity. If same-source parent forward replay does not reproduce the archived target exactly, record the discrepancy and source/numerical bound evidence explicitly; do not silently replace the inherited energy or declare an arbitrary tolerance. Parent replay and child-extent checks should remain distinguishable in output.

## Scaling invariants to review in final fixture

Hold the .02 m half-domain and .01 m2 reference face area. Two-to-four width and Vref are halved; reference microscopic interface area .003->.0015, phase-transfer coefficient1e-6->5e-7, all inventories/geometry absolute volume bounds halved. Keep K/G/eta/gamma and gas conductivity/diffusivity intensive constants unchanged. q0 stays1; wB becomes20 because invariant betaB=wB*Vref=.001 m3/mol. Reaction k remains.1/s with current-bulk-volume concentration basis; no rate constant halving. Test nonzero B to reveal accidental q scaling defects. Interface microscopic area is distinct from computational face area, which is not halved.

Use the same piecewise initial physical field [left,left,right,right]; do not introduce a smooth four-cell profile and call it the same initial-value problem. The middle jump's initial face distance changes with mesh, so its discrete initial heat/diffusion flux need not equal the coarse one. Native comparison must use fixed-domain conservative cell aggregation at a common time and disclose time-cap error separately. Two grids alone do not establish asymptotic convergence.

## Uniform control qualification

A uniform zero-gradient callback is useful to verify zero internal face transport on the fine grid, correct extensive sources and binding. If only a callback is executed, state exactly that: uniform time histories and cross-grid trajectory parity remain pending. Do not promote a zero initial gradient into a proof of equal histories, especially with cell-indexed geometry or constitutive identity mistakes. A/B and imposed uniform deformation should be identical intensively, but that expectation still needs explicit evidence when claimed.

## Frozen execution boundary

Retain120 s internal and150 s wet supervisor budgets; no source/install/EOS changes during another live job. All steps require fresh actual callback/source bindings and terminal evidence before progression. Known .005 ordinary-knot failure remains a separate unresolved issue. This extension supplies numerical manufactured-model evidence, not raw material admission, free sintering or full spatial convergence.

## Frozen final script review

APPROVE the first bounded four-cell gradient callback and the explicitly sequential continuation after each actual result passes its registered checks/audits. No EOS or tests were executed by this reviewer. Actual reviewed hashes:

- PLAN.json: 4c045829c908adc9b7fcaac0f4ab6aa03aae63d68555ec3b3e38031da46c01c2
- fixture.py: 92bce245bafe31b4364384a41aee277aee3db695c638771fa6783945ae3d4129
- callback.py: 049d4eb4c23ab4666684b33b1b2481d85e280afe1f785da56594bda3ad13bd96
- wet_run.py: 0a5304cdd1659889b030b4aa81b26f473aca19b7f9f163f50ffc6b939fdcb9f9
- run.py: 1f02980049a6fa49765f51e506b0fab3297b2a13c89c9774bd2ff96c4f495a5d

All four scripts parse and match PLAN hashes. Independently checked all43 registered source files against installed bytes/hash and all16 water assets. Read the root's existing scaling-result.json status passed; it explicitly limits itself to manufactured extensive API scaling without phase/reaction EOS validation. This report does not represent that script as reviewer-executed.

The final fixture scales Vref, width, inventories, declared absolute bulk-volume error, microscopic interface area and lumped phase coefficient by2/cells; scales wB inversely, with q0, K/G/eta/gamma, k, conductivity and diffusivity unchanged. Skeleton indices and reference geometry are complete, physical domain fixed, computational face area unchanged. The registered piecewise profile is conservatively duplicated. Uniform mode constructs a separate genuinely uniform parent, rather than reusing the gradient parent's right-hand energy.

forward_evidence first constructs the temperature state and then separately evaluates each point.forward to retain its documented full energy bound and mechanical/thermal/addition constituents. Exact repeated forward energy equality is required; disagreement fails rather than broadening tolerance. For four cells the same process reconstructs the two nominal-temperature parents. Gradient initialization additionally requires exact encoded parent state N/E/identity equality with the archived actual two-cell coupled callback. Thus its original parent energies are genuinely bound, not merely approximated from decoded temperatures.

Every child target E is parent represented E divided by the integer child count; exact Fraction checks enforce all parent-pair N/E sums. Independent forward pair comparison uses exactly Bparent+sum Bchildren with no added atol. The per-child forward-versus-conservative gate uses Bchild+Bparent/childcount. The nominal-temperature diagnostic uses its actual conservative target discrepancy plus those bounds divided by the documented positive minimum heat-capacity bound, then adds the actual inverse-temperature error. This is conservatively qualified source/reconstruction consistency, not a trajectory error bound. The skeleton is temperature-independent in this fixture, so using the closed thermal minimum capacity for that total-energy difference is consistent. It does not compare nominal-T forward energies with a different decoded parent temperature.

The callback retains initialization before assertions, verifies enclosure gates, exact external-face conditions, current reaction/storage and inverse reuse, source-qualified wet transfer and extensive reaction rates. Internal faces are sampled with face-temperature enthalpies, not treated as an independent face oracle. Gradient mode requires the central vapor exchange; uniform mode requires all internal fluxes zero. The latter, if executed, is only a callback check. No uniform time-history claim is authorized.

The wet script requires fresh same-cells/profile callback and exact initial/initialization/energy identity equality, records full run before completion checks and leaves ledger audit explicitly pending. All stored states must remain wet. The supervisor refuses existing outputs, records old parent callback and same-grid callback inputs, uses30 s callbacks and150 s wet limits with120 s internal integrator budget. Repeated parent/child forwards and the four actual fine inverses are disclosed inside these original limits. No budget increase is assumed from this approval.

No blocking numerical/setup issue found. Actual first callback may still fail an exact replay, source-domain or runtime gate; preserve such failure. Two spatial grids remain preliminary resolution evidence, and source/raw-material/free-sintering admission remains unfulfilled. All previous known-bug and qualification statements above still apply.

## Required preflight correction supersedes original script approval

The other reviewer found a real construction-order blocker that this numerical review initially missed: RigidFluidHeat.__post_init__ requires each initial fluid-template available volume <= face_area*cell_width. The old four-cell fixture narrowed cells to .005 m but passed a one-cell 1e-4 m3 fluid template into the transport constructor, exceeding the new5e-5 m3 bulk volume. This would reject construction before current solid/deformation closure. No native attempt was required to discover it. The earlier original-script approval is superseded by this corrected snapshot; original files are retained in preflight-original/.

Reviewed exact diff: before transport replace, create a fluid template with mechanical.available_pore_volume_m3 multiplied by scale=2/cells, then supply that template for all transport cells. No other fixture numerical formula changed. For two cells scale=1 preserves original field values and parent replay identity. For four cells reference template volume becomes5e-5 and passes the actual area*width constraint. DeformingSolidStorage._prepare still later computes current available volume from current_bulk minus actual solid inventory and replaces the fluid mechanical volume with that value exactly once. There is no second scaling of the dynamic pore volume or altered solid energy/geometry law.

Final corrected fixture SHA256: 66639ad99b1996a83a1836c58a4b6ca01b59ebcbe88de13a3ae899b973972e77.
Final corrected PLAN SHA256: 1ad81a3b7f656bef00218abd29ef72441e76d4d907754e2f1c6e06b95817d81d.
Callback, wet and runner hashes remain049d4eb4...,0a5304cd...,1f029800... as listed above. All actual script hashes match corrected PLAN, and all parse. APPROVE this corrected version for the previously bounded first callback after the other review closes its blocker. No EOS or test execution by this reviewer. Source-derived initial energy gates, original30/120/150 s budgets and all scientific limitations remain unchanged.
