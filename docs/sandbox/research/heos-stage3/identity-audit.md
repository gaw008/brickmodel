# Fixed CoolProp 8.0.0 HEOS stage-3 identity audit

Read-only review of the retained installation, fluid/result/license artifacts and repository ADAPTER_DESIGN.md. No CoolProp import, EOS call, test or repository edit. Existing installed extension/METADATA/RECORD/license hashes still match. The earlier two-point numerical agreement is feasibility evidence, not sufficient adapter admission.

## Concrete design correction

The design says existing native mass R is `float(.46151805)*1000`. That evaluates to **461.51805**, whereas the actual existing model/reference is **461.5180499999778**, obtained from native `8.314371357587/18.015268` then multiplied by 1000. The respective binary64 hex values are `0x1.cd849eecbfb16p+8` and `0x1.cd849eecbf98fp+8`. Preserve the actual original WaterReference arithmetic/value; do not reconstruct it using the rounded design literal. This is separate from the already documented one-ULP molar-mass difference.

## Minimum fixed descriptor

Use a frozen, canonically serialized descriptor verified against actual loaded assets. Paths are audit provenance, not scientific equality. Include:

| Field group | Fixed binding / requirement |
|---|---|
| Schema and implementation | Explicit descriptor schema and adapter/checking-policy version; HEOS Water single pure-fluid mode; CoolProp 8.0.0, revision `ae81610e7d23efc57f9d051c8e70a4d66e87537f`; adapter implementation source digest. |
| Loaded code | Expected hashes of all three imported extension modules, the imported Python wrappers listed below and package metadata. Verify actual module `__file__` resolves to those checked assets; distribution version/RECORD presence alone is not sufficient. |
| Fluid/model data | Full retained fluid artifact hash plus a defined canonical parsed-data hash; require exactly one Water EOS, `pseudo_pure=false`, EOS citation Wagner-JPCRD-2002, complete ideal/residual terms, reducing/reference state data and saturation/critical machinery. Do not hash only the citation or the two displayed constants. |
| Constants and coordinates | Native HEOS R=8.314371357587 J/mol/K, native M=0.018015268 kg/mol, reducing T=647.096 K and rhomolar=17873.72799560906 mol/m3, with explicit native-mass conversion to rho scale 322 kg/m3. Keep separate exact public M=`float(18.015268)/1000`=0.018015267999999997 and original public mass R above; record conversion convention rather than accepting a loose equality tolerance. |
| Reference and ideal branch | Native IAPWS reference convention; original native ideal coefficient/reference binding; complete existing WaterReference and common energy-offset/anchor convention. If original Python computes any anchor/ideal proof/validation, identify the implementation as hybrid and bind its native source/dispatcher too. No independent h/s zeroing or CODATA substitution in the liquid EOS. |
| Runtime policy | Exact admitted domain and old numerical tolerances; automatic flash phase choice; separate density-based validation role; pinned effective CoolProp configuration and reference-mutation policy; immutable result/cache identity. |
| Original scientific sources | Existing five IAPWS/reference source hashes remain separate source evidence, not substitutes for the CoolProp implementation identity. |

The same verified descriptor must enter cache identity and future consumer/provider/target/transport identities before host admission; same source/reference with a different execution backend must not compare invisibly equal. No scientific identity should contain an object address, lock or absolute install directory.

## Actual imported asset closure

The retained installed-assets.json already binds CoolProp/CoolProp.abi3.so (`1769af71ee559ad3040f286d991617713e4442d272c56adc2e2a69fd4d33dd8f`), State.abi3.so (`35bc6bc53793d44ad704447698db59523c1d9c2ca0a2520a82090ce7cb3177ea`) and _constants.abi3.so (`c63e90766d225fd927df28142878f14495ea132e62589d7ef76da0d78ac01ccc`), plus METADATA/RECORD. Importing CoolProp also executes/imports these **previously unbound** wrappers:

- `CoolProp/__init__.py`, 3372 bytes: `04abc96cc96b83e2436d68faed709693c64cd507c24d469bc862ea3bf51ab927`
- `CoolProp/constants.py`, 9251 bytes: `ebdc956ff1b9437530abd5af3cf40f83426cbb3f414768dbda1b4f3b1e753e00`
- `CoolProp/HumidAirProp.py`, 845 bytes: `fe4583c8c953ab87d0369ccaf475478b9c6b367303ae41f92e234a2e857ff20a`

The initializer imports State and the constants shim even if the adapter only uses AbstractState. It contains a legacy branch that tries to remove an unexpectedly loaded constants shared library. Reject wrong-package/legacy-shadow assets before relying on import; do not treat that branch as a repair mechanism. Keep hashes of .pyi, bibliography, include headers or optional Plots/GUI only if used or distributed for the experiment; they are not mandatory scalar HEOS execution dependencies merely because they exist.

WHEEL identifies `cp312-abi3-macosx_11_0_arm64`; METADATA declares numpy>=1.20. Record actual Python/ABI/platform and NumPy implementation/version in the execution manifest, and pin/hash any Python/NumPy/SciPy/IAPWS files that the adapter actually uses. Do not claim SciPy is a HEOS-native dependency: it enters only if the hybrid/reference path uses it. Static `otool -L` on the core extension shows system libc++ and libSystem, no external CoolProp/REFPROP dynamic library. This is a platform-specific artifact, not a portable wheel proof. Original wheel bytes were not retained/hashed by the old installed-assets manifest.

## Fluid artifact and runtime mutation distinction

The saved `coolprop-water-fluid.json` SHA-256 is `ee7a5ab5852a61cc4cf251e94750790164bad95ed9d661f05cd6a7106213c2a3`. It is a pretty-printed **re-serialization** of the API JSON, not the untouched returned JSON string. A canonical digest of its first/only fluid object using Python json.dumps with sorted keys, separators `(',',':')`, allow_nan=False is `17d81c16ff1352523835dff3557fe5e5f2bb2f157f29b5cd7fdd34cd4931ccb2`. Define that object/list choice and numeric canonicalization explicitly; do not compare hashes from different serialization schemes. Full-data pinning is simplest for this exact installation and includes superancillary/critical machinery, rather than assuming alphar alone identifies all saturation behavior.

File/JSON hashes do **not** establish that in-memory reference state/configuration is unchanged. Local stubs expose reference setters and settings including NORMALIZE_GAS_CONSTANTS, DONT_CHECK_PROPERTY_LIMITS and OVERWRITE_FLUIDS. The old probe did not save a complete effective configuration baseline, so no such baseline may be invented from its result.json. New stage-3 construction must establish explicit expected configuration/reference observations in its controlled fresh process, and reject incompatible loaded state before publishing a scientific descriptor. Subsequently detect relevant mutation or invalidate/rebuild/reject; never silently reset global reference/configuration to make a check pass. Numeric reference/ideal checks are needed in addition to source hashes, particularly if mutable global state does not appear in the fluid JSON.

## Required rejection conditions

Reject missing/changed wrapper or extension assets, wrong loaded paths/modules, unexpected version/revision or fluid/EOS count/mode, mismatched coefficient/ancillary/constant/reference data, unsupported effective configuration, changed validated descriptor/checking implementation, or an unbound hybrid dependency. Reject malformed/nonfinite observations and partially initialized identities. Do not fall back to Python or overwrite sources to conceal failure.

Keep the original 293–500 K/positive P<=100 MPa and phase/ambiguity/response gates even though the fluid JSON advertises a wider range. Stage 3 may exercise its predeclared small points only; no broader state, chemical bridge, concurrency, host or performance approval follows from this identity review. The MIT license copy is 1103 bytes, SHA `9bf835333ef602af4cb19338b9f9d43671e174fa029b00280e9bdba6ea4719b2`, matches installed notice, and must be retained for distribution; it does not establish optional backend licensing or source reproducibility.
