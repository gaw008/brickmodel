# Independent review: programmed solid/fluid boundary and phase composition

Verdict: **APPROVE within the documented conditional model scope**. No unresolved high-confidence implementation findings. This review covers the new programmed host, its integration into WaterPhaseTransfer, and the independent manufactured ramp benchmark. It does not qualify real brick material, transport coefficients, reaction kinetics, shrinkage, or a full firing model.

## Physics and implementation

The host evaluates SolidFluidHeat exactly once per trial. That call reconstructs each cell from total solid/liquid/gas internal energy and complete inventories, retaining the original conditional storage inverse and mechanical diagnostics. The programmed result returns the same state/inverse/gas tuples rather than recalculating or replacing them. Existing internal faces, reaction sources, cell power, and immobile inventory columns survive unchanged; only the outer gas face and outer heat ledger receive additions.

For zero radiation, independently eliminating the surface gives G=A*k/(dx/2), H=A*h, Ts=(G*Tc+H*Tg)/(G+H), and q=G*H/(G+H)*(Tg-Tc). The implementation's two quarter-cell distances sum to the correct half-cell resistance. With radiation, the residual derivative is G+A*h+4*A*epsilon*sigma*Ts^3, nonnegative and strictly positive for a coupled surface. The positive-temperature endpoint bracket contains the root. The k=0 case blocks conduction without suppressing gas transport or its enthalpy; the completely insulated surface is explicitly diagnosed. The recorded balance tolerance is a numerical residual at the decoded cell temperature, not a full physical temperature uncertainty certificate.

The gas reservoir uses the prescribed gas temperature, total pressure, and complete ordered composition. Its temperature is distinct from the solved solid surface temperature. Existing face transport and caloric identity checks are reused: advective donor enthalpy follows the actual donor gas temperature; diffusion uses the existing shared-face reference. The outer energy ledger adds enthalpy minus conductive heat into the cell, consistent with outward face orientation. Formation enthalpy can be negative, so flux correctness is judged by this algebra rather than an assumed energy sign. Existing external reservoirs/Dirichlet surfaces are rejected to prevent duplicate boundaries.

Coefficient identities, source IDs, immutable programs, complete gas order, and manufactured opt-in are checked. Opt-in covers film, underlying transport, solid/gas caloric fixtures, and manufactured geometry. A virtual geometry remains a design choice, not a material qualification. Known domain errors retain DomainExit behavior; numerical failures do not return an apparently valid state. Bare ConservedState arrays still depend on the documented inventory-layout contract; no nonexistent same-shape permutation detection is claimed.

## Phase composition and compatibility

The selected ordering is WaterPhaseTransfer -> ProgrammedSolidFluidHeat -> SolidFluidHeat. The wrapper unwraps only for layout/template identity and qualification checks. Actual evaluation stays on the outer programmed host, preserving the dynamic face flux and all inverse diagnostics without double decoding. Phase transfer retains the original equal/opposite liquid-water and gas-water source and does not add a second latent heat source to total U.

The wrapper forwards breakpoints_s for the dynamic host and returns an empty tuple for static hosts. Callers must still pass these values explicitly to integrate; the integrator does not automatically discover the method. The tests exercise this actual contract. Existing rigid and solid static compositions are included in the final regression. Early test-only API mistakes in knot/ledger field names were corrected before this final run; these are not hidden physics failures.

## Independent final regression

Reviewer executed, serially after worker processes ended:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_programmed_solid_fluid_heat.py tests/sandbox/test_water_phase_transfer.py tests/sandbox/test_solid_water_phase_transfer.py tests/sandbox/test_programmed_water_phase_transfer.py -q --junitxml=/private/tmp/programmed-solid-final-review.xml
32 passed in 68.29s; exit 0
```

The XML reports 32 tests, zero failures/errors/skips, 68.288 seconds. XML SHA256: `f3f725de550d0d9507935f9d41991cc743806e6d55110d3753d8898479952a90`.

The eight programmed-host cases include independent linear surface elimination, an independent nonlinear radiation root, actual ramp/hold/cool integration with nodes and energy ledger, prescribed atmosphere changes with donor enthalpy, k=0 gas inflow, source/order/domain/duplicate-boundary gates, and an actual dynamic gas-inventory integration. Five new phase cases include a real wet programmed integration with preserved solids/carrier, total water conservation, external face energy balance, and retained diagnostics. The other 19 cases protect the existing rigid and solid phase compositions. These are manufactured numerical cases; a short wet run is not a complete drying validation.

## Independent analytic benchmark review

Read-only review confirms the separate 60-digit Decimal reference imports neither the host nor the numerical integrator. It solves C*dT/dt=G*(Tb-T) piecewise for the specified ramp, hold, and cooling stages, with C=2*50+0.01*(30-R) and G=A/(dx/(2*k)+1/h). Its branch expression, endpoint propagation, weighted surface temperature, and Q=C*(T-300) are consistent. Conversion from the original binary-float inputs is explicit. The candidate assembles a manufactured fixture but compares actual integrate trajectories against this separate formula, not the candidate's inverse as its own temperature oracle. Every saved time is checked; node, shape, fixed-step, no-rejection, inventory, per-step, and prefix face-energy checks are separate.

The first decimal-step experiment (0.4/0.2/0.1 s) failed its actual uniform-step criterion. Repeated floating-point time addition left tiny node-remainder steps and subsequent step growth. Its archive is retained and it must not be described as a passing fixed-grid convergence test. A separately recorded amendment uses exactly representable 0.5/0.25/0.125 s steps, without changing physics, integrator, error thresholds, or convergence ratios. This is a valid bounded experimental redesign; it does not fix or qualify arbitrary decimal time grids.

The revised candidate records all actual surface residuals and limits. For this passive linear constant-C problem, 40*max(surface_limit)/C conservatively estimates the undamped accumulated temperature perturbation from surface residual alone. Requiring this and the inverse bound below 10% of the observed error helps distinguish time truncation error from local solver noise. It is not a general wet/nonlinear error theorem. Undefined refinement ratios are stored as null and fail rather than causing division by zero. Final numerical output is bound in the supplement below; it is parent-executed evidence independently inspected by this reviewer, not a second claimed run.

## Reviewed final implementation bindings

| File | SHA256 |
|---|---|
| `src/sludge_sandbox/programmed_solid_fluid_heat.py` | `1b044c413454686d547fa1caa2f086a2576991a3cda5bd3c6d15a690e7938d5e` |
| `src/sludge_sandbox/water_phase_transfer.py` | `2098387ddff71e39cac733bfef3ca49efbeaeadf82a9cc2c1c75d9ff6a365f3a` |
| `tests/sandbox/test_programmed_solid_fluid_heat.py` | `2c415624e1e00cb3169ed16c6e9d8e28efef49952d079fca22d0f9e5c360f797` |
| `tests/sandbox/test_water_phase_transfer.py` | `0499cbd72644889a6a1f76d25b466ea8dcdd1db4b80aa6db9fd29882e93f12b1` |
| `tests/sandbox/test_solid_water_phase_transfer.py` | `91a2cd0550f7eb5ef88fabdf5715d5df8b56fd0ca9cdaa3de193c5ceebbe3246` |
| `tests/sandbox/test_programmed_water_phase_transfer.py` | `4d098e98431f5a47d71b50c7f5e1126814afe6ab068de0b113eca04389e90bce` |
| `docs/sandbox/PROGRAMMED_SOLID_FLUID_HEAT.md` | `ab69f3e3b03cbafc69a368d4240a9f5b5f78d753e00c1b3be1939de569ecb55c` |
| `docs/sandbox/PROGRAMMED_WATER_PHASE_TRANSFER.md` | `5a13bc5d48681c8d87d7f56cfe25e43501d7abb33337219d267544a85c0071b5` |

## Final benchmark artifact inspection

The parent executed the amended benchmark; reviewer did not repeat the numerical integrations. Independently recomputed every recorded trajectory maximum and every prefix ledger discrepancy from JSON, verified all recorded dependency hashes against the current tree, checked the actual time increments, and recalculated the piecewise ODE using separate ordinary-math code. The latter agrees with the recorded Decimal reference within 1.14e-13 K. The retained ZIP contains the original plan, script, and failed JSON, whose three uniform-step flags remain false.

| Actual dt (s) | Maximum T error (K) | Maximum prefix energy discrepancy (J) |
|---|---|---|
| 0.5 | 0.0005201791474860329 | 9.444534043723252e-11 |
| 0.25 | 0.00012775850240132058 | 1.5131718100747094e-10 |
| 0.125 | 0.000031646373201965616 | 3.4927438719023485e-10 |

The adjacent error ratios are 4.071581442400001 and 4.037066161925477. All three runs complete with actual uniform steps, no rejected trials, exact inventories and nodes, and the prescribed heating/hold/cooling shape. The maximum conditional inverse temperature bound is 3.993568429829743e-9 K; the largest accumulated surface-residual temperature estimate is 5.946692601627056e-11 K. The amended predeclared checks pass. This supports the manufactured dry temporal convergence claim, independently of the short wet regression; it does not establish spatial or physical-material convergence.

| Evidence | SHA256 |
|---|---|
| `docs/sandbox/research/PROGRAMMED_SOLID_ANALYTIC_PLAN.md` | `6330b781f9dccaf9edf8153f5b99b1fee2eba15daa0b4ca26f1f546d2c71d96d` |
| `docs/sandbox/research/programmed_solid_analytic_reference.py` | `7faf91a86d7913e67b18baf954d6fd1f03d3a9611b6b0604cf44b4bff7e16726` |
| `docs/sandbox/research/programmed_solid_analytic_reference.json` | `5c7865509fa0a87a942ba82ea45d43b6d9511128a834b7ee06979f3110a28e52` |
| `docs/sandbox/research/programmed_solid_candidate_check.py` | `c584c203c8cdacdcadd19c6f140ddbcf07c50426f8b8ec4e9e28ce64789922f7` |
| `docs/sandbox/research/programmed_solid_candidate_check.json` | `39e3c628c6f03858beeb135016af4d271cfd273399ac7475a6e6cc41d635014f` |
| `docs/sandbox/research/programmed-solid-decimal-step-first-run.zip` | `5c78b48b36bac30edcd1acfe0ae23d6b8e8b761decd37c98fd0aa34d8e63068c` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded programmed solid/fluid and water-phase composition, with conditional inverse/source assumptions and manufactured validation limits retained.
