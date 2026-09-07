# Independent review: fixed-bulk solid/fluid storage

Scope: `solid_fluid_storage.py`, its tests/documentation, and the existing solid and fluid contracts it composes. Full source and final increments were inspected. No implementation files were changed by this reviewer.

## Physical and numerical audit

Every forward call validates complete solid inventory keys and computes `Vs=sum(Ns*vs)` and `available=Vbulk-Vs` from exact represented inputs. It replaces the template fluid cavity for this call, so changing Ns affects both pressure and stored solid energy. No old fluid-only inverse receives the total U target. Every overall inverse trial evaluates all active solids and the actual fluid mechanical closure at the trial temperature.

The total energy is fluid U plus each `Ns*(h0-P0*vs)`; enthalpy includes the consistent pressure-volume term. At fixed inventories and constant solid volumes, total closed-path heat capacity is the actual fluid closed-path capacity plus solid Cv. The lower bound adds the downward-rounded original fluid bound and the certified positive single-branch solid bounds. Local capacity only proposes a safeguarded Newton step; acceptance uses outward energy/error intervals and the global conditional lower bound.

Solid-volume uncertainty, declared bulk uncertainty and available-volume representation error enter the additional pressure budget using `Bmin=Ng*R*T/Pmax²`. This is a conservative analytic lower bound on the magnitude of the pressure residual derivative for the stable liquid plus ideal-gas closure. It applies in the pure-gas branch too. The existing fluid pressure/error budget is retained, then the added pressure error contributes `Nl*sup|du_liquid/dP|*extra_epsilon_P` to U. Solid u declarations and per-term/sum roundoff are added separately; the solid declarations already include their reference-pressure volume contribution. Correlated errors are conservatively added, not cancelled.

The code rejects overfilled nominal volume and volume uncertainty that excludes a positive available cavity, and requires the complete pressure-error interval to remain within the mechanical bracket. Construction requires that bracket to fit every solid's pressure domain. Zero solid inventories preserve keys without querying inactive phase domains; zero total gas remains rejected rather than patched with epsilon. Cross-phase shared species must use the same molar mass, including the water convention. All geometry identities/classifications and manufactured inputs remain explicit.

The state retains the original fluid state and its narrower error contract separately from the total solid/fluid fields, immutable solid inventory/point maps, and complete inverse diagnostics. The resulting error conclusions are still conditional on declared global fluid and solid model-error envelopes; they are not independent physical error certificates or material validation.

## Independent execution

Initial inspected suite: 20 passed in 0.62 s. After the final mass-identity and active-solid-domain additions, the reviewer ran:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_solid_fluid_storage.py -q
```

Final result: **22 passed in 0.62 s**. Coverage includes independent pure-gas/constant-Cp formulas, real whole-inventory constant-power integration, immutable/complete inventory maps, zero-solid fluid regression, changed solid occupancy and energy, budget failure and explicit source/domain gates. The volume-uncertainty tests independently solve perturbed pressure roots with SciPy and the original water EOS, then check both pressure and energy inclusion, with and without liquid.

An additional reviewer calculation held solid inventory at 2 mol and gas at 0.01 mol, then evaluated the actual coupled forward at 300 K and T±0.01 K for liquid inventories 0, 1 and 2 mol. Central dU/dT matched the returned closed-path capacities within the preselected 1e-4 J/K threshold. Maximum observed residual was 2.54e-8 J/K; capacities were approximately 10.216855, 85.518740 and 160.810023 J/K, each above the conservative 10.2 J/K lower bound. This is a local numerical consistency check, not a replacement for the global-bound derivation.

## Independent two-solid/two-gas reference audit

The reviewer also read `solid_fluid_analytic_oracle.py` and its preregistration. Its 60-digit Decimal reference has no candidate-solver dependency: occupied volume, remaining gas volume and ideal pressure are computed directly; solid u uses h0-P0*v, gas u uses h-R*T, total C sums solid Cp and gas Cp-R, and a 250 J input gives 300+250/C. `H=U+P*Vbulk` is correct because all phases share P and their volumes sum to the fixed bulk volume. The initial output accurately states that runtime comparison has not yet been performed. Any later parent-run comparison is separate evidence and is not falsely attributed to this initial reference generation.

The subsequent `solid_fluid_candidate_check.py` was also independently read. Its three forward states are compared to the separate Decimal JSON using the preregistered absolute thresholds; inverse target U and expected T likewise come from that reference. Each actual 25 W, 10 s integration operator call evaluates the complete inventory inverse. Saved inventories, `U-U0-25*t`, completion status and final independently predicted temperature all enter the pass condition. Initial U is obtained from the candidate only after the separate forward comparison checks it; the final oracle is not generated by the inverse under test. Root path resolution is correct, JSON disallows nonfinite values, and failed criteria produce a nonzero exit. This is an audit of candidate-comparison independence and checks, not an independent rerun attributed to this reviewer.

## Final SHA-256 binding

| File | SHA-256 |
|---|---|
| `src/sludge_sandbox/solid_fluid_storage.py` | `8ff5663f311a93f03b095e407f07b425f85ed23626102b7ccacd14200495220e` |
| `tests/sandbox/test_solid_fluid_storage.py` | `f30838de9007ee14e03cd5872478a01d00f9183663ebb53df0e74ddc9f4417e4` |
| `docs/sandbox/SOLID_FLUID_STORAGE.md` | `634a74234d0ffdd80a5481afe6f4c4194eed2d5751cf79f1094422aad4aad924` |

Final geometry-only follow-up: `virtual_design_choice` was added solely to the geometry classification whitelist. Required geometry ID/version/sources remain enforced, material provider classifications are unchanged, and manufactured material opt-in remains required. The reviewer inspected the new regression/documentation and reran the storage suite: **23 passed in 0.63 s**. This adds an explicit sandbox design category, not a new material qualification or changed physical/numerical model. Final hashes supersede the historical table above:

- Source: `a592373dcc365ee121926eee2330ccad93b1d300822ab0eebcd7be2b1f45508c`.
- Tests: `b008e80afa63dc607667c1ab763525a3ebed187fc30ac870f2570e0554df7b59`.
- Document: `d3a5ed215f6596b6fb4543a49e4787fb4b4c31afebfa4dea207f11964bebdbf9`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — fixed-bulk inert solid/fluid storage and its conditional inverse are consistent within this bounded scope. Transport-host adaptation, reactions, phase transitions, shrinkage and complete brick-model qualification are separate work.
