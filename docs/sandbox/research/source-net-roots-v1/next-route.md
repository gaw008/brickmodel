# Next bounded step: source-panel quadrature and signed ledger, before event commit

Read-only route, 2026-09-09. No EOS, tests, production changes or event admission performed for this route. This step should produce a checked numerical prefix and its arithmetic ledger, not a dry-mode transition.

## Concrete reuse and smallest extraction

1. `source_net_panel.py:131 build_source_panel` already binds both complete saved observations, exact times, operator/energy identities and fixed dry kg. Its `shared_rate_history` contains each of the N+1 faces exactly once: four fluid molar rates, one total-U rate, and per-cell local phase terms. `SourceAffinePanel.check` (106) rebuilds derived data; call it before quadrature. Do not use the two-cell `mass_wet_exact_stage.components` (265), `inventory_derivatives` (283), or `advance` (335): those encode A/B chemistry and liquid=-phase without liquid face migration.

2. The closest existing generic implementation is `exact_terminal_panel.py:36 build_exact_affine_panel`, not the old mixed-pair stepper. Extract only its nested `integral(a,b)` and `update(before,terms,tolerance)` into shared pure helpers in that same module. Keep the old wrapper calling them with unchanged ordering, errors and budgets. `integral` returns both represented arrays and exact Fraction integrals; `update` should expose its per-entry signed projection residual without changing the old result. Reuse `rounded` (26) for finite/underflow refusal. Do not import the entire terminal wrapper into the source route: it requires selected liquid/wet-cell semantics and its own positivity policy. Do not duplicate its array quadrature or implement another solver.

3. New source-prefix assembly can consume checked panel histories and the two actual Rates arrays, with exact duration h=end-start in (0,H]. For every shared component I(h)=r0*h+a*h*h/2, a=(rm-r0)/hm. Cross-check integrated inventories/U against `InventoryPolynomial` evaluation from the same panel. Reuse `InventoryPolynomial.minimum` (`mass_wet_exact_stage.py:140`) for the chosen prefix, not only panel.upper. Root order may be consulted but cannot replace independent all-fluid minimum checks.

4. Reuse `ExactStepLedger` (`exact_integration.py:45`) for represented face/local integrals and ordinary packed state shape. It does not expose every exact fluid/face projection residual; retain those in a small source-prefix result alongside exact integrals, represented integrals and state projection residuals. `ExactMixedLedger` (`mass_wet_exact_stage.py:166`, `make_ledger:328`) is the existing exact/represented/error pattern but its producer is constant-rate/two-cell. No need to widen that legacy producer or create a new provenance framework: retain original panel and invoke its check, then rebuild the derived prefix when checking returned records.

## Arithmetic contract that must be explicit

Choose the existing terminal once-rounded-component contract for this prospective packed source prefix. For each shared exact integral I, record Ihat=rounded(I), eI=F(Ihat)-I exactly. Apply incidence to those same represented face values on both sides, not separately integrated cell rates. For species j in cell i,

    nexact = F(n0) + Ileft - Iright + Ilocal
    nrepresented_sum = F(n0) + F(Ihat_left) - F(Ihat_right) + F(Ihat_local)
    nout = rounded(nrepresented_sum)
    estate = F(nout) - nrepresented_sum
    F(nout) - nexact = eleft - eright + elocal + estate.

Use the identical formula for U with total face-energy integrals and zero cell power for this source model. Each internal face cancels exactly in global represented and exact ledgers. Sum cell residuals as Fractions; never claim float global sums are exactly conservative. Preserve original amount/U absolute budgets; expose integral projection, aggregation projection and full residual separately and gate each contract actually required, rather than silently treating a state-only check as bounding all projections.

This differs from `source_wet_column._advance:358`: that routine aggregates exact face integrals first and rounds only each final cell quantity. Preserve that existing midpoint integrator unchanged; the two arithmetic paths can differ by ulps legitimately. `exact_integration._scaled:16` handles constant-rate projection only. Its nested `accumulated_exchange:157` is the reusable cumulative pattern: sum original represented terms in Fractions and compare actual state to initial plus ledger. `integration._updated:67/_check_update:73` do not supply exact affine integral errors themselves.

Physical decomposition comes from original saved `source_rates.faces`. Reuse `ColumnFaceIntegral`/`LiquidColumnFaceIntegral` (`source_wet_column.py:268/279`) and the decomposition in `_integrals:337`, but integrate both samples affinely using the same shared quadrature. Total U is authoritative; conduction, each gas diffusive/advective enthalpy, liquid donor enthalpy, and the existing liquid-enthalpy projection are diagnostics. Record the integrated discrepancy between total and decomposition rather than reconstructing total from rounded parts. Signed liquid and donor-enthalpy histories must remain paired by face and source sample; if liquid direction changes, two samples do not establish the correct physical donor between samples. A numerical interpolation may report that limitation but cannot certify the transport path.

## Prefix boundary and what remains forbidden

For strictly positive initial fluids require minima>=0 on [0,h], and require strictly positive endpoints when returning an ordinary wet host state. Tangency or endpoint zero needs explicit boundary-only status, not implicit event acceptance. Current root ordering explicitly returns incomplete for any zero initial inventory. A prefix API must either preserve that unsupported status or explicitly implement only a closed numerical boundary case: the declared zero component has an identically zero polynomial and compatible fixed interface mode; no omitted competitor, negative excursion, nucleation or rewetting inference. Nonzero derivatives from zero remain unsupported at this step.

`exact_terminal_executor.execute_exact_terminal:63` is explicitly ExactFreeWaterTransfer-only. It builds an actual predictor, evaluates again, orders evaporation-qualified roots, constructs a panel, performs `exact_depletion_writeback`, switches modes and evaluates the endpoint. `exact_depletion_integration.terminal:208` commits only its successful speculative result. None of that becomes source-authorized merely because source roots are completely ordered. Exact roots of an affine approximation establish neither RHS accuracy nor physical event-time error. Keep original evaporation/ULP/fraction correction gates unchanged. Net drainage residual cannot be relabeled evaporation: any eventual transfer must conserve paired liquid inventory across its actual face and the same donor enthalpy with a justified error bound. That bound and physical event writeback are still unauthorized by current evidence.

## Focused tests before this step is accepted

- N=3 signed affine faces, nonzero open gas/U boundaries: independently derive every exact integral, local incidence, global water and U telescoping; local phase cancels liquid/vapor.
- Binary64 cancellation example: independently compute eI and estate, verify their exact residual identity and original budgets; also expose the expected difference from source-column exact-first aggregation.
- Recovery polynomial with positive endpoint but negative interior; tangent at h; earlier gas zero; zero-initial identically closed versus zero-initial outflow. Reject forbidden prefixes without clipping.
- Pure drainage and drainage exceeding condensation, including donor-energy and decomposition projection diagnostics; demonstrate that these do not grant physical event permission.
- Exact clock translation, arbitrary h<=H, and tampered prefix/ledger/derived residuals. Checks must rebuild from the original bound samples without a provider call.
- Frozen legacy terminal panel result/ledger regression after the two small helper extractions. No numerical tolerance changes and no new EOS needed.
