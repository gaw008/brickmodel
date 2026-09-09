# Arlabosse2005 source-specific dry-mass caloric candidate

Re-read cached publisher HTML lines1078 (85% industrial/15% municipal feed) and1121 (C80 calorimeter,35–105°C); visually inspected original cp-equation.gif (Eq2:1434+3.29T) and nomenclature.gif (T°C, Cp J/kg/K, DM=dry matter). Source metadata and original asset SHA values are recorded in repository data/sandbox/research/arlabosse2005/source.json. No new search, EOS, original asset redistribution or repository change.

`ArlabosseDryCaloric(source_path, repository_root)` checks the reviewed metadata SHA and all recorded source asset SHA values at construction and each operation. This verifies current bytes, not a repeated scientific reading of the article. This conservative candidate requires cached source assets; missing/changed files refuse execution. A future metadata-only distribution mode would require a separately explicit binding contract.

`cp(temperature, unit='K'|'degC')` returns an exact Fraction evaluation in J/(kg*K). `delta_h(start,end,unit=...)` returns its analytic integral in J/kg. Each immutable result contains exact normalized Celsius inputs, source SHA/node ID, dry sample basis, unquantified fit error and material_qualified=false. Reverse/zero differences are supported; both endpoints must lie in the measured domain. No absolute enthalpy, formation energy, molecular mass, volume, Cv or mol-host interface is supplied.

Input policy `exact_values_float_shortest_decimal_readout_v1`: int/Fraction/finite Decimal preserve exact values. Finite float means its shortest round-trip decimal readout (repr), not its exact binary64 rational. Thus308.15 as a float means precisely308.15K, matching a printed temperature. Adjacent float below the endpoint is still outside and is rejected; no clipping occurs. Callers wanting binary-exact semantics can explicitly pass Fraction.from_float(value), including its resulting domain rejection. Bool/string/nonfinite/incorrect units reject.

`registry_payload()` is compatible with the existing EvidenceRegistry v1; trace(NODE_ID) resolves the source locator/assets. Applicability remains conditional on the exact original sample and temperature interval; uncertainty unquantified. The full_text_checked enum is accompanied by the actual narrower reading_scope (“relevant sections and original Eq2/nomenclature/Table1 images read”), not a claim that all manuscript statements were reviewed.

Actual tests01 and tests02:19 passed in0.05s each. Test02 adds ordinaryfloat/Decimal/exactbinary/nextafter semantics. Independent Decimal endpoint/trapezoid integration gives116501 J/kg from35 to105°C. Tests also cover sign/additivity, immutable output, registry trace, source metadata changes and actual copied-asset corruption. Prior strict-Fraction-only version is preserved as before-temperature-input.py and test-before-temperature-input.py. No material prediction or statistical uncertainty was validated.

Derived-node fix: delta_h now traces ARLABOSSE2005_DRY_SENSIBLE_ENTHALPY_DIFF → Cp Eq2 → source, with analytic integral/units/code locator. Preserved before-derived-node snapshots; actual derived-red 1fail19pass, derived-green20pass0.04s. No numerical formula or domain changes.

## Applied implementation and actual installed example

Applied production source42e828e640bdc10d69dd7195cba7440e5851096e23a9a933e080e98211ab6ca3 and portable testf606bd85a066e0313ca40be1520d40d410f96a8a8dda2c76fe9d758ef1d55bd9. Tests now import the installed package and resolve their repository input location, with no hardcoded user path. Temporary overlay conftest is archived for candidate reproduction only and was not applied.

Root combined source verification89 passed18.21s; frozen offline noneditable package, from/private/tmp without PYTHONPATH,39 dedicated record/caloric tests passed12.39s.78actual installed modules match source. Source/installed XML and full identities are retained in exact-record-v1, not a claim of a newly run full sandbox suite.

Root actually executed the installed caloric API and EvidenceRegistry trace and saved actual-installed-example.json. This exposes two equations/source locators through Python; it is not yet a new CLI command or a complete material case. Original source.json is an unchanged historical evidence snapshot; the newly implemented bounded relation does not grant the missing full material-package admission.
