# Open source-column implementation: independent physical/numerical review

No blocking sign, half-cell, energy duplication, or exact-stage-time discrepancy found in the reviewed implementation. The wrapper replaces one closed right-face observation, uses the existing gas face with zero conductive coefficients, and adds only negative surface-to-cell conduction to outward energy. It retains source material qualification=false. Face-interpolated gas temperature is explicitly distinguished from solid surface temperature.

The shared integrator explicitly admits the wrapper type, queries first/mid/end at ExactEventTime, merges interior programme knots into nominal endpoints, and appends only fully admitted endpoints. Its documentation correctly states that subdivision may increase accepted ledger count and that projection/decomposition budgets exclude temporal integration error. The source-domain guard verifies programme gas temperatures before inversion; actual cell and phase queries retain their source-domain checks. Surface radiation temperature is distinct from a material caloric query.

## Predeclared independent experiment and result

OPEN_ORACLE_PLAN.md was saved before numerical execution. No conditions or tolerances were relaxed after inspecting results. The one executed check completed in 8.0574 s, within the 55 s cap. All four source hashes were unchanged during the run. Actual stdout is OPEN_ORACLE.log; machine-readable results and hashes are OPEN_RESULT.json; reproducer is check_open.py.

N=1, fixed 0.125 s programme with nodes at 0, 0.0625 and 0.125 s. Gas temperature, radiation temperature, reservoir pressure and composition all vary. Emissivity is 0.5 and bulk advection is inflowing. The test liquid remains explicitly artificial. Independent reference assembly uses the printed source Cp integral, artificial liquid U/v, brentq temperature inverse, direct chemical equilibrium and gas transport primitives, hand-assembled gas enthalpy, and a separate brentq surface convection/radiation balance. It never invokes the new wrapper, SourceWetStorage.evaluate/invert, or surface_balance helper to form reference rates. DOP853 is solved separately on the two smooth programme segments; it used 196 RHS calls. Programme interpolation is handwritten in the oracle.

| Midpoint steps | Energy difference from DOP853 (J) | Maximum inventory difference (mol) |
|---|---:|---:|
| 2 | 2.5653022420301568 | 7.453735867271605e-5 |
| 4 | 0.6445159586655791 | 1.8570600445799723e-5 |
| 8 | 0.1615533289150335 | 4.635173104644563e-6 |

Energy refinement ratios 3.98020 and 3.98949; inventory ratios 4.01373 and 4.00645. All meet the predeclared 3..5 criterion. This demonstrates second-order convergence for this bounded, knot-aligned case. It does not establish an arbitrary time-error tolerance: the eight-step energy difference remains 0.16155 J.

For every accepted step, exact Fraction arithmetic independently verifies body energy, O2, N2 and total-water changes equal negative outward boundary integrals plus accepted signed projection corrections. Conduction into the body is the negative outward conductive-face integral, and the signed surface defect equals conducted minus convective minus radiative heat. Convective/radiative terms are not added as a second body source. Reported surface residual remains within its declared algebraic tolerance.

## Hashes and scope

- programmed_source_wet_column.py: ad549f7d02fdc288640079069ffda66bcd2dc9d3275d60988e96f9cb54aca2e5
- source_wet_column.py: 8bbdcfb95630623fef218190d25705af93d560d2a4d5c7556621b3de06cc2de7
- surface_balance.py: cedbdc5587d9621d2386a1fba10052ed3b4bf6987f1b7a96237240cb8afb2e93
- mass_wet_transport.py: 4d2dc3518ad9d52a38029a72e032210a284da3cc25da2e99c54f204c17ab7503

The numerical comparison reuses source gas caloric, chemical equilibrium and gas transport primitives; it is independent aggregate/inverse/surface/ODE assembly, not independent validation of those primitive constitutive laws. This run uses a manufactured liquid and coefficients, not native EOS or matched material data. It tests aligned programme knots; the separate repository test covers knot insertion and large exact schedule translation, and was read but not rerun by this reviewer. No full firing-domain, event-localization or real-material claim follows.
