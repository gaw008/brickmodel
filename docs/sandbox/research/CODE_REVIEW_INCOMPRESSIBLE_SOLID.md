# Independent review: incompressible single-branch solid

Scope: `incompressible_solid.py`, `test_incompressible_solid.py`, `INCOMPRESSIBLE_SOLID.md`, and the actual `PhaseStorage` assembly/inverse test. The complete new source and existing phase-point/storage contracts were inspected. No rigid solid/fluid coupling or material admission is implied.

## Physical and source checks

For a declared constant molar volume v and reference-pressure enthalpy h0(T), the implementation correctly uses `u=h0-P0*v` and `h=u+P*v`. Consequently u has no pressure dependence and `du/dT=Cp0=Cv` under this explicitly nonexpanding, incompressible approximation. It does not apply ideal-gas `u=h-R*T` or require solid Cp to exceed a gas constant. The 5 J/mol/K fixture is therefore legitimate as a manufactured solid caloric example.

The Shomate enthalpy and its temperature-difference integral retain the original eight coefficients, including the correct E reciprocal-temperature term. Fraction arithmetic avoids subtracting rounded large formation energies for tiny temperature differences. Formation-reference consistency is checked; generic supplied asset identifiers/hashes are recorded, not independently opened or approved by this provider. Molar volume and its provenance remain separate from caloric data.

Only one explicit temperature branch is represented. The quartz test reads the archived first source segment, independently evaluates its original decimal-coefficient enthalpy increment and rejects the next representable temperature above 847 K. No interpolation or artificial continuity is introduced across the quartz source seam. This review does not certify actual phase stability throughout the user-declared pressure range or derive density from the caloric asset. The quartz assembly uses manufactured volume/error inputs and remains manufactured.

## Positivity, precision and error qualification

The global lower-bound construction is mathematically conservative for the represented coefficients: on a positive-temperature interval each individual term `B*t`, `C*t²`, `D*t³`, and `E/t²` has its minimum at one endpoint, including negative coefficients. The exact sum of those minima is therefore a lower bound for Cp on that interval. Recursive subdivision covers the original interval; every accepted leaf has a strictly positive exact bound, and the exposed minimum is rounded downward. Failure to certify within the bounded depth is rejected. Dense samples are not used as the proof.

The declared u-error minimum is checked against exact represented `P0*declared_v_error`. Documentation correctly requires additional h0/reference/arithmetic error coverage while acknowledging that the constructor does not independently certify that entire declaration. Manufacturing any caloric, volume or error component propagates through metadata and requires explicit opt-in. The provider does not pass these declared u/v errors into the preexisting PhaseStorage inverse and does not relabel its conditional monotonic-path result as a rigorous full material bound.

Unrepresentable nonzero outputs, invalid/nonpositive domains, invalid identities and unsupported classifications are rejected. Coefficients, volume identities, source records and declarations are immutable semantic values. No source file or existing water/cache implementation was edited by the reviewer.

## Independent execution

The reviewer ran the 29 new cases independently: **29 passed in 0.04 s**. Combined with the existing phase-storage tests:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_incompressible_solid.py tests/sandbox/test_phase_storage.py -q
```

Result: **51 passed in 0.84 s**. This includes actual PhaseStorage total-energy/volume assembly and temperature inversion to 320 K, retaining the original conditional inverse status; it is not only a standalone provider mock. Existing source, manufactured-error, nonpositive-Cp, finite-value and domain tests also passed. `git diff --check` passed.

An additional independent numerical probe generated 50 mixed-sign coefficient sets with seed 59317. It found candidate Cp minima using roots of the independent derivative polynomial `3D*t^5+2C*t^4+B*t^3-2E=0` plus endpoints, and checked the exposed lower bound against those minima with a preselected 1e-10 J/mol/K numerical allowance. All passed. For those same curves, central differences of actual u at 370 K and 200000 Pa with dT=0.001 K matched Cp within the preselected 1e-6 J/mol/K threshold; maximum observed error was 7.25e-9 J/mol/K. These numerical probes supplement the interval-algebra audit; polynomial root numerics are not claimed as a proof of physical Cp accuracy.

The documented early fixture failures concerned a declared budget smaller than the exact binary-input product P0*epsilon_v. The implementation comparison was not loosened; the manufactured fixture was given explicit margin. This history is distinct from the final reviewer runs above.

## Final SHA-256 binding

| File | SHA-256 |
|---|---|
| `src/sludge_sandbox/incompressible_solid.py` | `b20d369a15892dd5b8284a1ede26d11bc29397f83137e033f15632b0f0111066` |
| `tests/sandbox/test_incompressible_solid.py` | `d80cb150340661feaa66f49d41dce148397db09d0dcb16ca79726edec297b7e6` |
| `docs/sandbox/INCOMPRESSIBLE_SOLID.md` | `6caa7c918ecb6e145d6d92be3a4d44535b2f029dc5e183aef4170651721f9e23` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — this is a bounded inert single-branch solid caloric/volume provider. Actual solid inventories and occupied volume are not yet coupled to the rigid fluid pressure/energy inverse; shrinkage, transitions, reactions and brick qualification remain outside this implementation.
