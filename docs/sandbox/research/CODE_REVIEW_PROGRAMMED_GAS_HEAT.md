# Independent review: programmed gas heat boundary

Reviewed 2026-09-07 UTC. Scope: `programmed_gas_heat.py`, its tests and `PROGRAMMED_GAS_HEAT.md`; existing gas/face/core code read for assembly contracts, not reapproved wholesale. Reviewer made no implementation edits.

Source SHA-256: `4f249494d434ce9bbc26a850fea37d3eaa2172fbf4811939b917273d4667d74c`.
Tests SHA-256: `e33b1205870c38ed4d839c1a6181e5c7ebb7c091676dde00814c4ae5786c4919`.

## Physics and assembly

For each actual trial state/time, wrapper checks the original base caloric signature, evaluates the current program and reservoir, and solves the surface balance before calling the existing model. It does not reuse a previous trial's surface or pressure. Existing outer boundary settings are rejected; full ordered species sets must match. Gas and radiation temperatures remain independent prescribed ambients, not imposed material surface temperatures.

Half-cell conductance per area is `G=2k/dx`. Balance `G(Ts-Tcell)=h(Tgas-Ts)+epsilon*sigma*(Trad^4-Ts^4)` is monotone in Ts, derivative `G+h+4 epsilon sigma Ts^3`; bracketing by the three temperatures is valid. Pure convection reduces to `qin/A=(Tgas-Tcell)/(dx/(2k)+1/h)`. Reviewed correct zero-k, all-zero transfer, and radiative/environment assumptions. The surface uses a declared W residual policy, not a falsely claimed temperature error guarantee.

The returned boundary face energy contains the actual half-cell conduction once and existing gas enthalpy transport once. No second film source is added. Checked both inflow and outward-flow donor enthalpy conventions against the original face contract. Reservoir temperature/composition participate in the face EOS; enthalpy donor temperature is selected by flow direction. They must not be conflated.

## Executed verification

Final focused suite: **15 passed in 0.54 s**. Tests include independent series-film solution, area scaling, nonlinear radiation reference, changing composition/pressure, zero conductance, full integration with piecewise analytic temperature response and every accepted energy ledger, invalid inputs, visible original composition/normalization diagnostics, numerical failure propagation and changed thermochemistry detection.

Independently evaluated **80 seeded random nonlinear surface cases**, varying cell/gas/radiation temperatures, k, cell width, area, h and emissivity. Roots obtained independently with SciPy brentq matched at maximum `1.93040250451304e-9 K`; assembled face heat matched the analytic conductance times the independent root with declared review tolerance `rtol=1e-8, atol=2e-7 W`.

Independent outward-flow check: cell 600 K/4800 Pa, boundary 800 K/4000 Pa, last half-cell 1 m, permeability/viscosity ratio 1e-5. Under the existing prescribed-face EOS-density convention the outgoing molar rate is 0.005 mol/s, with cell A enthalpy `30*(600-298.15)`. Expected outgoing heat is 45.2775 W; actual 45.27749999993831 W. The review initially used cell density rather than the existing face-density definition and corrected that oracle after reading `_face`; no implementation defect was inferred from that wrong reference. Inflow test independently uses boundary donor enthalpy and preserves formation terms.

## Findings and scope

No unresolved actionable issue above review confidence threshold. This is a fixed-geometry gas model boundary extension. It supplies no liquid/solid storage, full brick mechanics or material coefficient admission. Time knots still require explicit `breakpoints_s` integration argument. Tiny existing reservoir normalization is exposed alongside unchanged program composition. Numerical root/resource failure is not relabeled as material infeasibility.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — actual programmed rigid-gas boundary assembly at the hashes above, not full wet-brick or Goal completion.
