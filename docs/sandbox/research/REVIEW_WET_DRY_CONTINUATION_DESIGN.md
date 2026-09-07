# Independent design review: wet/dry continuation and water caloric join

**Final disposition: REQUEST CHANGES for the depletion implementation contract.** One substantive representation/error-budget choice remains open. The separate water caloric joining design may proceed to a bounded implementation and independent tests. Neither proposal is implemented or numerically verified by this review.

Reviewed the two final design files, the actual current SSPRK2 stage/update checks, and the current existing-liquid wrapper gate. No production code was changed and no heavy integration was executed. A small standalone binary64/Fraction arithmetic check below was run to verify the correction counterexample.

## Remaining finding

[HIGH] A generally usable depletion write-back policy has not yet been selected or validated

File: `LIQUID_DEPLETION_DESIGN.md:118` (final root decision; required next work at line 122).

Issue: the intermediate revision demanded that actual binary64 liquid loss and vapor gain equal the same delta exactly. This is not generally representable when the two initial inventories' exact sum cannot fit into the one remaining dry gas coordinate. It can reject ordinary physical depletion even when a bounded floating-point solution would be valid. Conversely, merely setting liquid to zero and recording an ideal paired source can hide an actual stored-mass residual. Generic amount atol alone does not establish an adequate cumulative error contract.

The final root decision correctly supersedes adoption of that intermediate rule, but does not yet provide either executable alternative. Before claiming a completed wet-to-dry continuation feature, choose and independently validate:

- A compensated/conserved-coordinate representation that actually carries the missing residual through state evaluation, serialization, restart and conservation diagnostics; or
- An exact paired event-extent ledger plus a separately defined, bounded and cumulatively audited state-storage rounding residual. Keep that residual distinct from physical transfer and from the proposed numerical phase correction. Register per-species/element/mass scales, ULP and absolute limits, cumulative prefix limits and failure behavior before testing. Do not count the storage residual a second time as evaporation.

This is a numerical implementation gate, not a requirement for new physical evaporation coefficients, not a demand for bit-exact conservation at every floating operation, and not a reason to abandon the full Goal. Returning unsupported for all otherwise normal unrepresentable exact-pair cases does not complete the intended wet/dry feature. The current integrator's `_check_update` already uses an explicit residual tolerance; the proposed event path needs a coherent extension and audit, not an unexplained stricter invariant.

## Review history and resolved design clarifications

The initial review was REQUEST CHANGES. Initial depletion hash `2391f15e21af99a38662819bef038c48d39b6e6b05765ae7872d6958ee8f7a66` and initial water-join hash `b0b0842e51ee777de8709151f395f0e374694bf9a0f61ea854ad5d533d0b0915` identify the inspected first versions. The authors retained the proposal text and added explicitly higher-priority amendments; no earlier proposal or numerical failure was reclassified as verified.

The first depletion amendment (hash `d2d6ec1b6433af6bd082ec9772a43535e73f9a839e49ca668d132581ca2ab37d`) added node limits for every fine subpanel, directional time rounding, a common post-event comparison time, phase-specific correction limits and independent correction records. The root then identified the exact-pair representability problem and appended the final unresolved two-option implementation decision. The final hashes below bind that latest disposition, not approval of the superseded exact-increment requirement.

### Event-map comparison and physical time

Comparing coarse and fine states at their respective depletion events is meaningful as an event-map comparison if event identity and transverse approach remain consistent. It is not the same quantity as a same-time RK local error estimate, and the original SSPRK2 1/3 factor cannot simply be reused. A small event-state difference alone does not control the consequences of different event times under continuing forcing.

The amendment therefore requires separate event-time and event-state indicators plus actual continuation of both candidates to a preselected common physical time. That resolves the conceptual omission. Both candidates must use the same declared dry branch and preserve every intervening boundary, reaction and face ledger; a time shift or unintegrated heat correction is insufficient. The common-time comparison remains empirical error/convergence evidence, not a rigorous global ODE bound. Its numerical scales, refinement rule, resource limits and sufficiently transverse-event qualification still have to be frozen with the implementation fixtures.

Every recomputed fine segment must obey the same next program node/final-time limit. One implementation caution remains attached to the prose about advancing to tb after a fine candidate crosses that node: coarse and fine estimates straddling a node do not prove that the true wet trajectory reaches tb. Only valid accepted wet steps may be committed; positivity failure or unresolved event approach must trigger further pre-node localization or a clearly unresolved result. Do not force a wet step through the event to satisfy that sentence. Likewise, another event during the common-time continuation requires explicitly handled compatible event ordering or an unresolved result; it cannot be hidden inside a comparison of different mode sequences.

### Positive terminal panel and full coupling

The present RK2 code evaluates and validates both forward Euler stages before convex averaging. For a constant liquid sink r, its full rk2 stage condition is N-2*h*r>=0 even though its final decrement is h*r. The ordinary integration also reevaluates the accepted state, while the wet wrapper rejects zero liquid. Thus the diagnosis of a genuine event-handling obstruction is correct; increasing step limits does not supply the missing phase-mode semantics.

A terminal Euler panel can be a defensible first event method, provided it is labelled lower order, controls all inventories and uses the actual represented time increment for all face mol/J, reaction mol and cell work. It must reclose total U/current inventories to T/P and retain solid occupancy and gas-pore feedback. No negative-inventory EOS calls, latent-heat subtraction or furnace-temperature reset is allowed. Rejected panels must leave state, interface modes, accepted trajectory and cumulative ledgers untouched. Modes change only on committed accepted events and survive restart/serialization.

The proposed first event is explicitly existing-interface evaporation depletion: r_evap>0 and net dNl/dt<0. It is not yet a generic liquid-removal event for reaction/outflow-driven disappearance with r_evap<=0. The source contributions remain separate, and all other inventory/domain limits and other cells share the same panel. No fluid host, active reaction or program forcing is replaced by a simplified dry-only demonstration.

### Numerical phase correction versus storage rounding

The amendment correctly restricts a proposed liquid-to-vapor correction to a residual from the represented event equation, with actual directional time rounding and a separately recorded event-time error. Its ULP scale uses the terminal panel's liquid terms, not the potentially huge gas inventory or a cumulative-flow scale chosen to make the correction pass. The additional delta<=eta*Eevap check ties it to independently accumulated positive phase evaporation, not net liquid removal that could instead come from a face or chemical reaction. Eta and ULP coefficients remain candidate numerical policies requiring preregistration and tests, not physical constants or proven global bounds.

The following standalone calculation reproduced the problem: panel liquid scale .01 mol, delta=ulp(.01)/2=8.673617379884035e-19 mol, vapor inventory .1 mol. The actual float increment `(0.1+delta)-0.1` is zero because ulp(.1)=1.3877787807814457e-17 mol. Setting residual liquid delta to zero leaves an exact stored-water deficit of delta, as confirmed by Fraction arithmetic. This does not prove every such rounding residual must be rejected: it proves it must be represented or explicitly budgeted and audited. It also shows why an ideal paired ledger alone cannot claim bit-exact stored-state conservation.

An event correction record and ordinary StepLedger must remain distinguishable. Accumulating saved binary64 values with Fraction makes their accumulation exact, not the original continuous solution or pre-rounding stage arithmetic. Corrected and uncorrected states, source-specific phase amount, numerical correction, storage residual, event-time quantization and total-prefix residuals must not be merged into a single unexplained source. Total U stays on its actual ledger; any T/P response to the changed composition must be recomputed and included in the numerical comparisons.

## Scientific dry-state limits

An explicit no-existing-interface/no-nucleation dry branch is a restricted scientific model, not chemical equilibrium or a condensation/wetting-front model. Keeping K unchanged while suppressing a nonexistent-interface contribution is a mode decision that must be recorded. It cannot silently ignore liquid inflow, liquid-producing reactions, supersaturation, unsupported S=0 mobility or missing constitutive domains. Reaction-produced liquid is not automatically the same mechanism as vapor nucleation.

Both amended documents now distinguish a calculable hypothetical-interface diagnostic from real existing-liquid chemical potential, and distinguish unknown out-of-domain condensation drive from evidence of no condensation. Strict mode must return unknown/unsupported there; an explicitly selected metastable no-nucleation branch may continue only inside all other active property domains. The current 500 K caloric endpoint is a separate limitation. A dry selection neither deletes water vapor nor extends its heat model, and a joined heat model does not create high-temperature liquid chemistry.

## Separate water-caloric design assessment

The 500 K differences are existing-model calculations: h/u jump +0.17481133254477754 J/mol and Cp/Cv jump -0.007918945959858092 J/(mol K). They are not real phase-transition heat, fitted experimental error, or a certificate of accuracy for either model.

Keeping the low branch through 500 K and integrating the original high-branch Cp from the low h anchor is a traceable derived caloric model. It can preserve continuous h and u while permitting source Cp jumps. All subsequent high-temperature Shomate seams must also be treated, and original h, offsets, coefficient/anchor versions and asset identities must remain observable. A heat-capacity seam must never be handled as a physical latent-heat or liquid-depletion event.

The revised contract now explicitly requires Cp>R throughout the joined domain so u is strictly increasing; Cp>0/h monotonicity alone would be insufficient. Its numerical gas_u_error contract must include the low anchor and high Cp integral/offset errors, separately from any material/source uncertainty. The endpoint discrepancy cannot serve as either model's true error bound. Identity binding, fixed R, molar basis, actual gas/solid temperature domains, reaction compatibility and manufacture gates must be tested through the existing whole-U host. This design can proceed independently to implementation, with the proposed derivative/identity/domain/constant-energy and real cross-seam integration tests; it is not an approved implementation yet.

## Minimum acceptance evidence before closing the depletion gate

Retain the independently solved constant and time-varying sink cases, event-time and common-post-event state convergence, constant-capacity energy oracle, actual coupled single- and two-cell continuations, explicit program-node ordering and original physics call/ledger checks. Add the demonstrated unequal-ULP storage case, tiny evaporation with liquid-outflow-dominated depletion, rounded time overshooting the proposed root, coarse/fine node straddling, another intervening event, condensation/liquid-reappearance and missing S=0 relations. The selected representation or bounded-storage-residual policy must pass its own per-step and all-prefix checks without changing tolerances after observing failures. A baseline exception or unsupported result is useful evidence of a remaining gap, not successful wet/dry continuation.

No new code or physical model has been verified by this design review. No heavy tests were run. Only this review file was written.

## Final document bindings

| Design | SHA256 |
|---|---|
| `docs/sandbox/research/LIQUID_DEPLETION_DESIGN.md` | `0527aab5e1aaebd879fbd6d64e5ad80db9faf140b018647eaba79b890c048eb2` |
| `docs/sandbox/research/WATER_CALORIC_JOIN_DESIGN.md` | `da6e80b28b59f6dd79eae92a203830e55fe89f6321302b4f1f20a6df3de9060c` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | open |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: REQUEST CHANGES — select and verify a usable compensated or explicitly bounded-roundoff event-state policy before approving depletion implementation. The independently separable caloric-joining design may proceed to bounded implementation and tests. Neither result completes the full Goal.
