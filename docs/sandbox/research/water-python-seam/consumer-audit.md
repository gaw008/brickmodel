# Water backend seam — consumer contract audit

Scope: read-only source/consumer search on 2026-09-07; no EOS, tests, code edits or deep re-review of water_properties internals. This maps constraints for an isolated **default-Python-only seam**. It does not admit HEOS.

## Direct private-provider dependencies

| Consumer | Exact dependency | Seam constraint |
|---|---|---|
| `src/sludge_sandbox/water_chemical_potential.py:117–130` | `_standard_entropy` calls `water._model._phi0(tau,delta)` with native fitted R/M and fixed critical constants | Keep the original ideal Helmholtz object/semantics; this calculation is part of the native entropy convention, not an arbitrary generic backend function. |
| `src/sludge_sandbox/joined_water_vapor.py:116–124` | `low._water._model.Fi0` coefficient shape/sign checks establish the low ideal positive-Cv bound | Preserve coefficient access and exact native coefficients, or introduce a separately reviewed explicit coefficient-proof interface. A numerical cp getter is not a substitute for this proof. |
| All other source consumers | No direct `_backend` access found outside water_properties.py; no other direct `_model` use found | The nonlinear raw solver boundary can be factored internally without touching these consumers, provided `_model` remains the same native validation/ideal object. |
| `tests/sandbox/test_water_cache.py`, `test_water_properties.py`, `test_water_response.py`, `test_water_chemical_potential.py` | Monkeypatch `_backend.IAPWS95`, `_model._Helmholtz`, `_phir`, `_phi0`; delete solver; mutate reference/assets | A seam must not capture stale bound callables that bypass existing injected failures or saturation invalidation. Preserve these fault contracts in the default implementation. This audit inspected tests but did not run them. |

## Scientific identity and default-equality dependencies

| Location | Current identity/admission contract |
|---|---|
| `ideal_water_vapor.py:54–83` | Loads WaterProperties itself; retains the same reference and asset mapping. `_caloric` requires exact WaterCaloricState type, **reference object identity**, and `derived_iapws95_ideal_helmholtz`. Bridge R remains the separately declared mixture constant. |
| `water_chemical_potential.py:109–150` | Exact WaterProperties/IdealWaterVapor types, equal references/assets, fixed bridge R/method; liquid state requires **same reference object**, liquid phase and `iapws95_real_fluid_helmholtz`. |
| `phase_storage.py:107–124`; `rigid_water_gas.py:99` | Exact WaterProperties type gates; liquid metadata takes molar mass and source IDs from WaterReference; native liquid properties flow into closure/storage. Substituting a subclass is not an accepted seam. |
| `rigid_storage.py:156`; `solid_fluid_storage.py:105` | Exact water molar-mass equality against other phase metadata. Do not silently round M or replace native R with mixture R. |
| `deforming_solid_storage.py:47–60` | `_canonical` specially serializes WaterProperties as `source_gated_water + reference + source_asset_sha256 + numerical_limits`; floats use hex. Private model/backend/cache object identity is intentionally excluded. |
| `deforming_solid_storage.py:154–164`; `deforming_solid_heat.py:86–112` | Canonical digest binds templates, total-energy targets/state tags and runtime mutation guards. Changing default canonical output changes conserved-state identity, even if thermodynamics match. |
| `rigid_fluid_heat.py:61–72,161–164` | Ideal-water cross-cell identity includes method, reference, sources and numerical limits; liquid cross-cell check compares reference/assets. |
| `solid_reactions.py:26–36` | Liquid reaction provider identity is provider type/metadata plus reference/assets/limits; ideal providers use caloric identities, joined providers use joined identity. |
| `joined_water_vapor.py:155–161` | Joined equality/hash includes low method, reference, limits, merged source assets, coefficients/anchors and error sources. |
| `water_phase_transfer.py:131–143` | Active chemistry binds liquid and ideal/Joined.low by reference, source assets, method and mixture R. K=0 existing-liquid path intentionally skips active chemistry matching. |
| `solid_fluid_heat.py:248–251` | Liquid transport output currently hardcodes provider `iapws95_real_fluid_helmholtz`, version `1.5.5`, and native asset hashes. A future HEOS solve cannot inherit this provenance silently. |
| `rigid_water_gas.py:159–160` | Mechanical results expose native liquid R and source assets/IDs. Those remain necessary but are not execution-backend identity. |

## Minimum first seam

Move only raw nonlinear TP/saturation solve dispatch behind an internal default adapter. Keep WaterProperties public class/loader, native reference construction, source verification, validation model, all original independent EOS/caloric/stability/Gibbs/response checks, result types/units/method IDs, failure classifications and immutable returned snapshots unchanged. Keep the default `_backend` and `_model` compatibility views as the actual native objects. Resolve the current solver dynamically so monkeypatched/deleted solver attributes still affect calls and cache validity.

Do not replace the native ideal model merely to route liquid solves. In particular, future HEOS liquid plus original native ideal/validation model is a **hybrid implementation** that must be described as such; neither `_phi0` entropy nor Fi0 lower-bound proof can be silently reassigned.

For this default-only phase, preserve the existing five source assets, WaterReference values/object relationships, numerical limits, state method IDs and canonical digest bytes. A new private field must not leak through generic dataclass serialization into existing identities. The WaterProperties-specific canonical branch is relevant here. Do not claim default equality merely from identical public numbers; old target/state tags, cross-cell/provider identities and injected failure behavior also matter.

## Required before any non-default backend can be selected

Existing identities **do not distinguish execution backends**. Same reference/source mapping and numerical limits would allow an invisible alternate solver to pass canonical, cross-cell, chemical and reaction bindings. Therefore do not expose an arbitrary adapter/backend injection path under the existing identity contract.

Introduce a separately validated immutable backend descriptor before alternate admission: implementation ID/version, formulation/mode, installed binary or native source identity, coefficient/fluid-definition binding, fixed reference/constant convention, and validation-policy version. Keep mutable AbstractState handles and cache contents outside that descriptor. Descriptor claims must be verified against actual loaded assets, not accepted solely from caller strings.

Propagate it into every binding above: canonical total-state/target digests; ideal/Joined/reaction identities; cross-cell liquid equality; active phase matching; saturation cache keys; and emitted liquid/transport provenance. Reference compatibility and implementation identity are distinct checks: preserve scientific reference fields rather than overloading WaterReference to mean backend provenance. If the method ID continues to identify IAPWS-95 equations, a separate explicit backend field is still required. The hardcoded transport `1.5.5` must be retained only for the default or derived from the verified selected provider.

Version any identity schema change deliberately. Either keep the first seam default-only with legacy identity bytes, or design an explicit compatible default branch plus a distinct non-default identity; never omit the descriptor for an alternate. Old tagged targets must not be reusable with a newly selected implementation by accident. Full alternate-provider proof and gate coverage remain separate work.
