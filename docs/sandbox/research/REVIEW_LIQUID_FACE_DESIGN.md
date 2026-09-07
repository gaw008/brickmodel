# Independent review: liquid face design

Reviewed `LIQUID_FACE_DESIGN.md`, the retained MOOSE Advection and Heat flux equations, and current rigid/solid-fluid storage/host interfaces. No implementation or experiment was added. MOOSE snapshot SHA256 independently matches `3215ecc012b321062a2470f032ec480a2569fe3511146adc81110ecc512fa0c8`. No broader search or current-version claim was made.

## Physical and numerical assessment

For a horizontal scalar-permeability face, phase mobility λ=k kr,l/μ has units m²/(Pa s). The two half-cell resistances give `Q=A(Pleft−Pright)/(dleft/λleft+dright/λright)` in m³/s, where each d is its cell width/2. Sign is left-to-right for positive pressure difference. Either zero mobility gives exactly zero; zero pressure difference needs no arbitrary donor selection. The bulk-area Darcy definition already accounts for porous resistance; multiplying Q again by porosity would be incorrect.

`Ndot=Q/vmol,donor` is equivalent to a single upwind density conversion `mdot=rho_donor Q` followed by division by M. Positive Q selects left, negative Q selects right. The energy carried across the same face is `Ndot hmol,donor` in J/s. It must use real liquid h at the actual donor T and liquid mechanical pressure and the same common energy reference as storage. h includes flow work u+pv: adding pQ again double counts this contribution. No additional latent-heat source is involved in liquid advection. With opposite signs from a single shared face value, extensive water and energy conserve algebraically; different receiving density means the receiver volume change per transferred mol may differ, which the next storage closure must resolve.

One clarification was sent to root: harmonic frozen mobility plus one donor density is an explicitly chosen finite-volume/upwind discretization. It is not an exact steady compressible two-half-cell solution when density varies appreciably along pressure/temperature. An exact steady mass-flow derivation would conserve mass flow through each half and account for the density dependence there. The proposed scheme remains a valid bounded first discretization, but its consistency and mesh refinement need testing; no claim of exact arbitrary compressible-flow integration is justified.

Pliq=Pgas can support this restricted pressure-driven, connected-liquid branch with rigid bulk and existing stable pure liquid. It cannot supply a capillary saturation curve, phase connectivity, wetting front, hysteresis, crystal-surface adsorption or effective transport law. Current mechanical states expose liquid pressure, liquid/gas amounts and volumes; all temperature inversions use total U and current inventory. Liquid donor h is not stored on the mechanical state, so the face must obtain it through the same source-gated water provider at decoded T/P (or a verified state exposed by storage). Do not substitute total cell enthalpy, gas caloric h, saturation h or h=u.

## Minimal integration recommendations

- Add one explicit optional liquid-face configuration to SolidFluidHeat and reuse its single decoded states. Populate the layout's liquid column, add the liquid enthalpy contribution to the existing shared face energy, and leave existing gas/conduction terms intact. Preserve separate liquid diagnostics and source/qualification metadata in the evaluation chain. ProgrammedSolidFluidHeat and WaterPhaseTransfer must retain these diagnostics when adding outer heat or reactions.
- Validate the declared coefficient identity/classification, liquid-specific relative permeability, viscosities, scalar directional permeability and connected-face condition before an active flow. A disabled/zero-mobility face should have an explicit zero status; it need not invent a liquid state in a dry cell. An active face involving dry/unknown-connectivity state must exit or declare missing support rather than silently infer wetting.
- Use actual donor state, not independent left/right density conversions followed by averaging. Test unequal molar volumes/enthalpies and reversed pressure sign to catch incorrect receiver selection. Test exact zero mobility and pressure difference separately.
- Account honestly for pressure-root resolution: near-equal decoded pressures can have an unresolved physical flow direction within their numerical envelopes. Nominal floating-point sign is a numerical approximation, not a certified directional statement. State the policy explicitly; do not use epsilon clipping to create a direction. Protect harmonic-resistance arithmetic and Q/v/h products against overflow/underflow without changing the physical zero cases.
- Keep external liquid reservoirs separate from atmospheric gas reservoirs. A gas-reservoir temperature/composition is not a liquid boundary state. Capillary work or pressure corrections require a new mechanical/energy derivation before being mixed into this branch.

Independent analytical half-cell tests should verify resistance and donor choices. Then actual source-gated liquid states can test interface wiring, and two-cell integration should verify each accepted prefix of total water/U, unchanged solids and sealed gas amounts, plus P/T response. Large trial transfers must be rejected by the integrator's existing inventory/domain rules, not clipped or compensated. Numerical conservation is not validation of a real sludge mobility law.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE as a restricted next-step design. The frozen-coefficient/upwind compressible-flow limitation must remain explicit; no liquid migration implementation or real-material qualification is approved by this review.

Final follow-up: root incorporated the frozen-coefficient finite-volume/upwind limitation directly into the design (line11). Reviewer read that final wording. Reviewed `LIQUID_FACE_DESIGN.md` SHA256: `1b70c4c50b7db8f37b4e576821f774520f26aae3ed55b4b8575563bc164fb4b5`. No heavy tests were required or run for this read-only design review.
