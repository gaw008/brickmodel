# Independent thermochemistry code and source review

Review date: 2026-09-07 UTC. Reviewer: separate Codex Python review agent. Scope: `src/sludge_sandbox/thermochemistry.py`, its tests, the NIST gas parameter pack, source records and source explanation. No production code, B2 source, B2 README or Git state was modified by this reviewer.

**Current decision after the repair recheck below: Approve for this ideal-gas thermochemistry implementation milestone.** Both initial numerical-boundary findings are resolved. The source/model and runtime-registry limitations remain unchanged.

## Initial decision: Warning

No CRITICAL/HIGH issue was found in the four-species NIST transcription or ordinary-domain caloric implementation. Two MEDIUM numerical boundary issues were independently reproduced and sent for repair. This is source-transcription/numerical review, not external material validation or qualification of a runtime material pack.

### [MEDIUM] Rounded zero residual bypasses the requested temperature precision

File: `src/sludge_sandbox/thermochemistry.py:330`

Issue: `residual == 0` stops bisection independently of the temperature interval width. For subnormal inventories, the stored total energy is quantized too coarsely to resolve the requested temperature precision. The method nevertheless reports a successful scalar temperature.

Reproduction with the initial implementation:

```python
from sludge_sandbox.thermochemistry import load_thermochemistry
t = load_thermochemistry('data/sandbox/thermochemistry/nist_gases_v1.json')
n = {'O2': 1e-320}
u = t.mixture_internal_energy_j(n, 1500.0)
print(t.temperature_from_internal_energy_j(u, n))
# 1500.0000104308128, with default temperature_tolerance_k=1e-9
n = {'O2': 5e-324}
u = t.mixture_internal_energy_j(n, 380.0)
print(t.temperature_from_internal_energy_j(u, n))
# 380.0048828125
```

These are deliberately extreme numerical inputs, not plausible continuum material inventories. The public API currently admits them, so it must either reject inadequate energy resolution explicitly or certify a temperature interval that accounts for that resolution. Do not simply replace the exact-zero exit with a small interval while retaining a quantized energy value that cannot support that interval. Preserve the ordinary `1e-30 mol` regression, which does have sufficient numeric resolution.

### [MEDIUM] Overflow of a finite mixture sum escapes the public exception type

File: `src/sludge_sandbox/thermochemistry.py:267`; analogous sums at `:270` and `:306`.

Issue: individual energy terms are checked for finiteness, but `math.fsum` itself can overflow when their sum is outside the finite range. Calling `mixture_internal_energy_j({'O2': 8e302, 'N2': 8e302}, 6000)` raises raw `OverflowError: intermediate overflow in fsum` instead of `ThermochemistryError`.

Fix: guard the summation operation as well as individual terms, and consistently translate arithmetic overflow/nonfinite results into the module's public domain exception. Apply the same policy to direct energy, total heat capacity and inverse branch evaluation. These are input/numerical failures, not evidence that a material is impossible.

## Independent source checks

The reviewer opened the current official [O2 Shomate page](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Mask=1&Type=JANAFG&Table=on), [N2 Shomate page](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7727379&Mask=1&Type=JANAFG&Table=on), [CO2 Shomate page](https://webbook.nist.gov/cgi/cbook.cgi?ID=C124389&Mask=1&Type=JANAFG&Table=on), [H2O Shomate page](https://webbook.nist.gov/cgi/cbook.cgi?ID=C7732185&Mask=1&Type=JANAFG&Table=on) and [CODATA constant listing](https://physics.nist.gov/cuu/Constants/Table/allascii.txt). The source extraction records were also read locally; they are explicitly extracted text, not original HTML bytes.

All 80 A–H coefficient scalars across 10 segments match the source tables, including signs, coefficient ordering, common formation reference and units. The source-supported temperature domains are:

| Species | Segments, K | Formation enthalpy reference, J/mol |
|---|---|---:|
| O2 | 100–700; 700–2000; 2000–6000 | 0 |
| N2 | 100–500; 500–2000; 2000–6000 | 0 |
| CO2 | 298–1200; 1200–6000 | -393522.4 |
| H2O(g) | 500–1700; 1700–6000 | -241826.4 |

The formation values are consistent with the H coefficient of the same fit. R is the product of exact SI defining constants, stored as `8.31446261815324 J/(mol K)`. No covariance or experimental uncertainty was invented for the fitted coefficients.

The reviewer independently parsed the cached source tables and compared **241 printed evaluation rows**, respecting each branch separately at duplicate seam temperatures. All rows meet the documented printed-precision tolerances. Maximum cp discrepancy was `0.005073393009595861 J/(mol K)`; maximum sensible-enthalpy discrepancy was `0.049896864583331535 kJ/mol` on the less precise high-temperature table rows. The 10 existing regression points use the two-decimal enthalpy subset and retain their `5.1 J/mol` threshold. No test tolerance was changed by the reviewer.

All five source cache files referenced in `sources.json` exist and match their stored SHA-256 values. This verifies those extracted artifacts, not an original-HTML hash or redistribution rights. The source document correctly distinguishes a readable web-tool extraction from the separately recorded direct-request HTTP 403 result.

## Physical and numerical verification

- Differentiating the Shomate enthalpy expression with `t=T/1000` gives cp in J/(mol K); the implementation correctly applies the factor of 1000 to the kJ/mol sensible primitive.
- Adding the same-fit formation reference once yields the declared total enthalpy convention. The ideal-gas relation gives `u=h-RT`, `cv=cp-R`. Reactions must change the species inventory without separately adding the same reaction heat to this total-energy convention.
- The interval lower bound for cv is mathematically appropriate for sums of monomials on positive temperature intervals: each monomial minimum is at an endpoint. Recursive subdivision resolves inconclusive bounds, while nonpositive/unresolved cases are refused. The existing interior-negative-cv regression covers a case that endpoint-only sampling would miss. This is floating-point numerical checking, not a formal directed-rounding interval proof for arbitrary extreme coefficients.
- Independent `scipy.integrate.quad` integration of the raw cp polynomial within each of the 10 segments agreed with the corresponding enthalpy change to a maximum `8.731149137020111e-11 J/mol`.
- Thirty interior derivative points across all 10 segments gave maximum `|dh/dT-cp|=1.4508806600588287e-08` and `|du/dT-cv|=1.6902262700568826e-08 J/(mol K)` using centered differences.
- Five four-species mixtures at 600, 900, 1500, 3000 and 5500 K were recalculated from raw coefficients with Decimal arithmetic, independently of the production energy function. Energy differences were below `1e-8 J`, and inversions of those independent energy values agreed within `1e-8 K`.
- At ordinary finite inventory and at `1e-30`/`1e-310 mol`, additional sampled inversions agreed with the requested temperatures to about `1e-10 K`. The subnormal-resolution failures above are outside those successful checks.
- Original seams are retained and reported. Additional actual four-species probes correctly rejected ambiguous inversions at 700, 1200 and 1700 K; 500, 2000 and 6000 K roundtrips succeeded for the tested composition. A gap or multiple inverse roots is a fit representation issue, not an unavailable real-world temperature.
- Positive H2O inventory below 500 K is rejected. A known zero H2O inventory does not constrain a different active species' temperature range; an unknown species at zero inventory still fails lookup. None of this supplies low-temperature steam or liquid-water properties for wet-brick drying.

## Executed tests and scope boundary

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_thermochemistry.py -q
37 passed in 0.03s
```

Static tools ruff, mypy, pylint and black were unavailable in the project environment/PATH; their results are not claimed. Manual review and the independent numerical/source checks above were performed.

Initial reviewed hashes:

```text
e511603451abb8951632ed79760dc301d71418513caebbb95a134500358c70c1  src/sludge_sandbox/thermochemistry.py
e26cd0fce0f1a288cb9764fb6bb0d2d12ae241c1775e7f2b202c4ec5ac879807  tests/sandbox/test_thermochemistry.py
b3ed8274b56fd773a01340308651c301f133dbd097cf4abcc0baed05e5ef7e53  data/sandbox/thermochemistry/nist_gases_v1.json
6d4efbd566475b3542573af1fcd7049f2df8080ca966a342c57c4bd6b396b742  data/sandbox/thermochemistry/sources.json
```

`provenance_status='source_links_declared_not_registry_validated'` is accurate: the loader validates structure and thermodynamic consistency but does not consult `EvidenceRegistry`. No runtime source admission, brick material applicability, condensed-phase model, pressure-domain qualification, chemical-equilibrium calculation, raw-sludge kinetics or full coupled-brick experimental validation is established by this review. The published NIST evaluation tables are evaluations of the fits, not independent experiments validating those fits.

## Repair recheck: numerical findings closed

The reviewer inspected the shared finite-sum helper and the repaired inverse exit/representability guard, then independently ran:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_thermochemistry.py -q
41 passed in 0.04s
git diff --check
passed
```

Twenty-three additional independent recheck cases passed:

- Six inversions at `1e-320` and `5e-324 mol`, covering approximately 301.12346, 380 and 1500 K, now explicitly return `insufficient_energy_resolution` instead of a misleading accurate temperature.
- Nine ordinary/low-inventory inversions at `1`, `1e-30` and `1e-310 mol` retain errors within `1e-9 K`.
- Direct energy, direct mixture cv and inverse-branch aggregate overflow each raise `ThermochemistryError` with the corresponding numerical diagnostic. No raw `OverflowError` escaped those probes.
- Five four-species independent Decimal reference energies still invert correctly, with maximum temperature error `9.094947017729282e-11 K`.

The inverse now requires its temperature bracket criterion even for a rounded-zero residual. It also compares the ULP spacing of the supplied energy and individual energy products against mixture cv and the requested temperature tolerance. The code correctly calls this a representability guard, not a complete bound on polynomial evaluation roundoff. The NIST coefficient pack was unchanged, so the earlier source/transcription and derivative evidence remains applicable.

Final reviewed hashes:

```text
d2934853eb9b720dc1beeaf16334cf7b8a5f0c0c918b5cea374e5b6a5467bdef  src/sludge_sandbox/thermochemistry.py
cf0847f0404aaa9e64f96e93a101b1ea90b228d92c0d7f0641568d017d28e5b0  tests/sandbox/test_thermochemistry.py
b3ed8274b56fd773a01340308651c301f133dbd097cf4abcc0baed05e5ef7e53  data/sandbox/thermochemistry/nist_gases_v1.json
```

No unresolved CRITICAL/HIGH/MEDIUM issue raised in this scoped review remains. The repaired module is suitable for the authorized local implementation milestone. It still supplies an explicitly limited ideal-gas caloric model; the native Shomate seams may reject continuous process states, low-temperature water/condensed phases remain missing, and actual runtime evidence-registry validation is not implemented by this module.
