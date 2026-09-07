# Joined water vapor: pre-registered numerical verification

Model scope:293–6000K ideal-water caloric only, low293–500 exact existing IdealWaterVapor calls; high original NIST H2O Cp integration from low h500. No liquid/EOS/chemical domain extension.

Pre-registered checks: low h/u/Cp/Cv equality exact to existing branch; independent Decimal60 integral at501/1000/1700/3000/6000K absolute h/u error≤1e-8J/mol; h−u−RT absolute residual≤2e-10J/mol; each500/1700 seam branch h difference≤1e-9J/mol, nextafter increments may quantize but must not decrease; Cp at500 is low and above500/at1700 original selected high branch, with source Cp jump retained. Finite-difference dh/dT=Cp away seams, dT=.01K, abs≤1e-6J/mol/K. Analytic positive Cv proof with exact Fraction interval arithmetic for high branch; no dense-sampling positivity claim. Domain/nonfinite/wrongsource/negative error inputs must reject. Numerical error contract conditional on supplied low whole-domain h bound, independent from fit mismatch or physical uncertainty.

## Actual API and source contract

`JoinedWaterVapor(water_source_directory, thermochemistry_source_directory, *, low_enthalpy_error_j_mol, numerical_error_source_ids)` source-loads an immutable low_model IdealWaterVapor plus original NIST H2O Shomate gas. The high source pack and its registry must match fixed reviewed SHA256 values; modified or duck-typed source objects are not accepted. The registry is source linkage, not a claim that every original NIST web page is re-downloaded at runtime. Existing low water loader continues to check original assets and installed dependency. `source_asset_sha256` namespaces both water and thermochemistry assets; chemical identity checks must explicitly use `low_model` and its unchanged water assets.

Public identity includes method_id/model_id/version, both source definitions, low reference/R/numerical limits, all asset hashes, derived segment anchors/offsets/Cp jumps and declared numerical-bound sources. Explicit equality/hash use that immutable semantic identity, not runtime EOS instance identity; independent same-source loads compare equal. `classification=derived_from_evidence`; no mixture, liquid phase or entropy capability is added.

Public caloric fields are h/u/Cp/Cv methods, `temperature_range_k=(293,6000)`, `gas_constant_j_mol_k`, `molar_mass_kg_mol`, `reference`, `low_model`, `source_gas`, high `segments`, `segment_offsets`, `cp_jumps`, `anchor_enthalpy_j_mol`, `cv_lower_bound_j_mol_k`, `cp_lower_bound_j_mol_k`, and separate low/high Cv lower bounds. At500 the low branch is selected; above500 the original500–1700 Shomate Cp applies; at1700 the original1700–6000 Cp applies. Both high branches are integrated using exact Fractions of binary64 coefficients/endpoints, anchored to the single returned low h500. Every high segment stores an exact Fraction lower-anchor h, so no rounded segment-to-segment anchor accumulation occurs.

`SegmentOffset` keeps original h at each source lower endpoint, derived h, and their offset. `CpJump` records left/right Cp at500 and1700; no Cp smoothing occurs. The original +0.174811J/mol model mismatch is a source-model difference, not uncertainty or latent heat. Offset multiplication/addition is not used to compute h: the exact anchored integral is, avoiding repeated offset rounding.

## Cp greater than R certificate

For the verified IAPWS ideal contribution, phi0 consists of log(delta), a_tau log(tau), constant/linear tau terms, and positive n_i log(1−exp(−gamma_i tau)) terms. Here a_tau=3.00632, every n_i/gamma_i is positive, and tau>0. Therefore native ideal Cp is

`R_native,molar * [1 + a_tau + sum n_i (gamma_i*tau)^2 exp(gamma_i*tau)/(exp(gamma_i*tau)−1)^2]`.

The sum is positive, so dropping it provides a conservative low Cp lower bound. Subtracting the registered Rmix gives a positive low Cv bound. The constructor checks the relevant fixed log/power structure and positivity conditions against the already source-gated model; it does not rely on sampling a temperature grid.

For each high segment, exact rational interval arithmetic bounds `A−R+B*t+C*t²+D*t³+E/t²` by separate monotone term extrema over positive t intervals. Intervals are subdivided until every lower bound is positive; failure to certify at the declared finite subdivision limit rejects construction. The minimum is converted downward to binary64. This follows the existing solid caloric rational interval-polynomial method while applying it to Cp−R, and reuses existing ContinuousSegment/Fraction Cp-integral primitives. It proves mathematical branch monotonicity of u over the declared fits; it is not material accuracy or phase-stability evidence.

## Conditional numerical error contract

The caller must explicitly supply `low_enthalpy_error_j_mol` covering returned low h throughout293–500K, and nonempty numerical_error_source_ids. This is a declared model-numerical envelope, not independently admitted by this loader; naming a source does not prove a bound. In particular neither the500K mismatch nor a finite set of derivative checks supplies this bound.

`numerical_error(T)` returns separately the low/anchor declared contribution, exact high-integral arithmetic error (zero relative to binary64 inputs), and output rounding terms. Low h is already covered by the supplied declaration; low u adds a full ulp for R*T and u subtraction. High h/u use exact Fraction integration and, for u, exact subtraction of binary64 R*T before the final float conversion; each conversion is covered by a full output ulp. Total nonnegative budgets are converted upward. There is no claim of coefficient uncertainty, original fit error or NIST/IAPWS physical accuracy. `qualification` explicitly remains conditional and not independently admitted.

JoinedWaterVaporError inherits ThermochemistryError, with `temperature_out_of_domain` outside293–6000K; low water source/domain/numerical failures retain underlying errors. This model alone does not update any host admission or authorize high-temperature WaterChemicalPotential. Integration is a separate change with its own explicit proof obligations.

## Actual verification record

First collection failed ModuleNotFoundError before implementation. The implemented module passed22 tests, then29 after semantic equality/hash, altered-source rejection, invalid numerical declarations and retained offsets/original Cp checks were added. Actual command: `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_joined_water_vapor.py -q`; result29 passed in0.31s. Independent Decimal integral uses only original coefficients and the reported low anchor, not candidate ContinuousSegment helpers. No tests or API claim qualified liquid/high-pressure mixture behavior.

Independent review found an extreme numerical-budget overflow: upward nextafter at maximum finite float could return infinity, and direct Fraction-to-float overflow escaped the custom error. Two explicit RED regressions reproduced both; conversion now catches overflow and checks finiteness again after directed rounding. Final focused regression:31 joined +28 existing bridge tests =59 passed in0.35s. No physical domain, bound acceptance or comparison tolerance was relaxed.
