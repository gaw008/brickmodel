# Independent review: liquid transport and actual solid/fluid integration

Verdict: **APPROVE for the declared horizontal, planar-interface, connected-liquid finite-volume branch**. No unresolved high-confidence implementation findings. This review does not admit a real sludge mobility, capillary relation, connectivity law, full drying model, or sintering prediction.

## Physical and interface audit

The scalar liquid mobility is k*kr_liquid/mu_liquid in m²/(Pa s). It comes from a separate explicit per-cell relation, never from the gas relative permeability or gas viscosity. The face uses Q=A*(PL-PR)/(dL/lambdaL+dR/lambdaR), where distances are the respective half-cell widths and A is bulk area. There is no extra porosity multiplier. A single nominal donor supplies v and h, giving Ndot=Q/vdonor and Edot=Ndot*hdonor. Enthalpy includes the pressure-flow work; no additional pQ or latent heat is added. For unequal densities this is the stated frozen-face upwind finite-volume discretization, not an exact compressible steady half-cell solution.

Frozen-manufactured relations are explicitly restricted to manufactured fixtures. The root clarified that the separate source-labelled tabulated constitutive contract can contain plateaus or a completely constant relation: requiring artificial numerical variation would not establish physical provenance. Table data, T/P/S domain, interpolation method, identities and asset hashes remain caller declarations, and material_qualified remains false. No actual unknown material coefficient is filled by a default. This resolves the initial API-message ambiguity without manufacturing fake variation or treating a label as material admission.

Tables validate finite nonnegative k, 0<=kr<=1, positive viscosity, strictly ordered saturation knots, and finite positive T/P domains. Interpolation uses the actual supplied saturation with no extrapolation. Source and caloric identity are checked across the face, including the liquid energy reference, provider identity/version and assets; different physical T/P/v/h are permitted. Public LiquidTransportState values are caller-supplied contracts, not automatically verified EOS observations. The host is the concrete source-gated assembly path.

Validation precedes a disabled zero result. For other faces, both relations are evaluated before the zero-mobility limit. A true zero mobility can close a dry face without inventing liquid v/h. Positive mobility requires explicitly connected and existing liquid on both sides; unsupported connectivity and dry active faces exit the domain. Zero nominal pressure difference has its own status. No epsilon replaces zero permeability, clips inventories, forces a flow direction, or hides a nonrepresentable nonzero flux. Fraction arithmetic protects pressure differences, series resistance and products; final nonfinite/underflow outputs are rejected. An independently probed pressure-error sum of max_float+1 correctly raises LiquidTransportError when its upward-rounded finite bound cannot be represented.

## Pressure uncertainty limitation

The state pressure bound is conditional on the fixed decoded temperature. It does not include temperature-inverse uncertainty propagated through the mechanical response. Both face and host diagnostics explicitly retain fixed_decoded_temperature scope and full_inverse_direction_certified=false, and the complete storage inverse remains accessible. Near-equal pressures keep their nominal signed flux with nominal_direction_not_certified; a nominal zero is not a certificate of zero physical flow. The code does not invent a global dP/dT bound from a local water derivative. Conditional_direction_resolved is only meaningful inside this explicit fixed-temperature scope.

## Actual host wiring and wrapper compatibility

SolidFluidHeat adds an optional LiquidTransportConfig with one relation per cell and one connection per internal face. Defaults preserve the previous zero-liquid-face behavior. Each evaluation still performs exactly one complete U/inventory decode. Liquid saturation is Vl/(Vbulk-sum Ns*vs), using the actual storage-available volume rather than bulk volume. Wet cells obtain v and h from the same source-gated liquid water provider at the decoded T/P; dry cells do not call liquid state_tp. No second pressure or temperature inversion is inserted.

One shared liquid molar flux is placed in inventory_layout.liquid_index, and its enthalpy flux is added to the existing gas and conduction energy face. The integrator applies that one face oppositely to its adjacent cells. Solid inventory and sealed gas columns remain immobile in the test configuration; the next trial re-solves total energy and mechanical pressure after liquid inventory changes. External gas reservoirs are not reused as liquid reservoirs. New evaluation fields follow the old default fields, preserving previous positional construction.

ProgrammedSolidFluidHeat and WaterPhaseTransfer each add the explicit liquid-manufactured gate. The classification-control test isolates only the new liquid flag and removes only the liquid configuration as a negative control. Its synthetic relabelling is plainly a gate-logic test, not a change to scientific source facts. Composition retains the nested liquid face diagnostics, full inverse chain, dynamic outer boundary and explicit program nodes. Actual gas/conduction terms and phase sources continue through their existing paths.

## Independent numerical checks

Reviewer-selected exact-rational example: A=.02 m², dL=.003 m, dR=.007 m, lambdaL=2e-12 and lambdaR=5e-12 m²/(Pa s), abs(deltaP)=20000 Pa. The independently calculated Q is +/-1.3793103448275863e-7 m³/s. With vL=1.8e-5, hL=1200 and vR=1.9e-5, hR=1800 (SI molar units), the forward result is 0.007662835249042145 mol/s and 9.195402298850574 W; the reversed-pressure result is -0.007259528130671506 mol/s and -13.067150635208712 W. The implementation matches all three quantities within 3e-15 relative error. Unequal forward/reverse magnitudes specifically check actual donor conversion rather than receiver averaging.

Reviewer independently executed the frozen final tests serially:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_liquid_transport.py -q --junitxml=/private/tmp/liquid-transport-review.xml
20 passed in 0.04s
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_liquid_solid_fluid_heat.py -q --junitxml=/private/tmp/liquid-solid-host-review.xml
6 passed in 22.89s
```

Both exited zero. XML SHA256 respectively: `041e2788eb2dc2256bc0241faef39bb919cab59c97d648d0fed4e0a53971ccda`, `82d0395ddd39cdf0cf0c3431ac8a9dbf4b3e6e5aa24c994ad195484db535c807`.

The six host cases include actual source-gated donor h, arbitrary liquid-column placement, a real two-wet-cell integration with accepted-prefix water and total-U conservation and per-cell face ledger, nominal pressure feedback, isolated outer manufacture gates, nested program/phase diagnostics, a one-decode count, and a disabled dry face that must not query liquid TP. The final test snapshot includes the new nominal temperature-change assertion. It does not establish separation of the before/after temperature uncertainty intervals; the documentation explicitly avoids that claim. This review does not promote a floating-point inequality to a resolved thermal effect. The short 0.001 s manufactured integral does not establish wet temporal convergence or inventory-exhaustion/wetting-front handling; source inspection confirms no new clipping or compensating source is introduced, and existing integration domain/positivity controls remain in use.

## Independent continuum reference and candidate audit

Read both root-authored scripts and their plan and saved outputs. For isothermal horizontal steady flow, J=-(lambda/v(P))*dP/dx, so Ndot=A*lambda/L*integral(1/v dP). The cumulative integral from P(x) to inlet pressure gives x/L of the total. The independent reference uses source-gated water plus Gauss-Legendre quadrature and brentq, without calling the new face or host. The candidate applies the actual face function on 4/8/16/32 equal intervals using independently stored pressure profiles and donor properties. Reversing the complete left/right states places the same high-pressure physical donor on the opposite side, correctly reversing the flow. The separate unequal-donor probe above tests a different pressure-reversal scenario. The artificial 1 Pa perturbation case checks uncertainty diagnostics, not an independently recomputed EOS state.

Root executed the reference (2353 actual water-state cache misses, 9.349773 s) and the candidate. Reviewer did not repeat those integrations. The reference molar flow is 0.002740522051133881 mol/s. Gauss16/32 relative agreement is 3.5634177787255925e-16: this is a consistency observation, not a rigorous quadrature bound. The root solver's partial integrals use order16 while total uses order32; their measured agreement supports this numerical test at its stated tolerance without providing a general proof. Water EOS is shared, so independence applies to Darcy/upwind discretization, not EOS validation. External isothermal forcing is explicit; this is not an adiabatic energy steady state.

Reviewer independently recomputed every maximum relative flow error from the stored face values, checked artifact dependency hashes against current files, and inspected candidate thresholds and donor/enthalpy/uncertainty checks. The saved result is PASS:

| Intervals | Maximum relative molar-flow error |
|---|---|
| 4 | 0.002719757453300827 |
| 8 | 0.0013753405510284276 |
| 16 | 0.0006916049857179565 |
| 32 | 0.00034679506965380204 |

Adjacent ratios are 1.9775156424109617, 1.9886215100093354 and 1.99427571565066, consistent with the separately declared first-order upwind limit. This checks the chosen steady face discretization, not full-host spatial convergence or material predictivity. The reference script currently raises directly on quadrature/budget failure and does not guarantee a failure JSON on every exception; only its actual successful output is claimed here.

## Final reviewed bindings

| File | SHA256 |
|---|---|
| `src/sludge_sandbox/liquid_transport.py` | `8cac540401fff281d8b5857ce7ad8096d346249fb9bfe5ff0f90f770f8eb00e3` |
| `src/sludge_sandbox/solid_fluid_heat.py` | `fc36774e3ac35beaf696dd7daa7c6c3b67d9a7de7e63243818e95641c4514e60` |
| `src/sludge_sandbox/programmed_solid_fluid_heat.py` | `d99166c8236e36dda0fc13fdcfd197368e61ea9d12442b233b1a9d3285e7fc5d` |
| `src/sludge_sandbox/water_phase_transfer.py` | `c82977b3c351152a8c5f9fcf346f8fe7f6627f7356c1be5c6c9ce7ea8ecaf9aa` |
| `tests/sandbox/test_liquid_transport.py` | `910b1010da517820149340ba7b4ec82a730a2e57b4cbdb73baaaaa0ca4ab603b` |
| `tests/sandbox/test_liquid_solid_fluid_heat.py` | `6b551e234b1565aa684914d551d3e97a04ed814dd0edf42d2b54742162813ce8` |
| `docs/sandbox/LIQUID_TRANSPORT.md` | `814df34c216f0ef19f771b4f65e579457e1733f57ee2369317b2e4ecdf7b8d33` |
| `docs/sandbox/LIQUID_SOLID_FLUID_HEAT.md` | `bf4031e46884f30da488a13d406e0154aa2f12c1814e84f6f120c0951bdaeeab` |
| `docs/sandbox/research/LIQUID_FACE_CONTINUUM_PLAN.md` | `64f6941e39dc8b7849d8d59f1bca9e8c158ed958e108a776373ebc826d82e2e4` |
| `docs/sandbox/research/liquid_face_continuum_reference.py` | `5ae572878a736f218bfcc0dc1e2cc164de8db58f85e8c48886a93071d7174909` |
| `docs/sandbox/research/liquid_face_continuum_reference.json` | `5f5015b0029db7b32869b2c0e4e5215d95a79f6a11c89590b00d50f7b237aba9` |
| `docs/sandbox/research/liquid_face_continuum_candidate.py` | `e68ecc6500103c24ce4ec2a0794d4216bb0de44f1729c80e24b440cea4f87979` |
| `docs/sandbox/research/liquid_face_continuum_candidate.json` | `c2b7d8c40b3fe7f1114051f278bf24d7cbd65c4aebacb38bfb6f5490757c58db` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded liquid Darcy/upwind operator and actual solid/fluid host coupling, with explicit source, uncertainty, connectivity and material-qualification limitations.
