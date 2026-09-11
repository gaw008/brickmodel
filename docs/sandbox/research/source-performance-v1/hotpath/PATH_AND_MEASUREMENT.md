# Source RHS hot path: static evidence and a bounded measurement

Baseline requested by Root: `86d9733`. This is read-only code tracing, not a
performance result. No provider was constructed, no physical function evaluated,
and no EOS/test/install performed. Module hashes and actual asset file sizes are
in `STATIC_INPUTS.json`; `profile_results` is deliberately null. Root's separate
cProfile of reading saved records measures passive decoding/audit, not this live
RHS. Do not transfer a passive-reader ranking to the physical operator.

## Actual call path

```text
ExactSourceColumn.__call__ -> evaluate
  emit rhs_started / observer
  unpack -> repeated column/storage source and model checks
  SourceWetColumn.evaluate
    for each actual cell:
      SourceWetStorage.invert
        evaluate(T_domain_low), evaluate(T_domain_high)
        binary64 midpoint evaluate(T) for each inverse iteration
          evaluate_wet_fluid
            replace RigidWaterGas(available volume), replace RigidStorage
            RigidStorage.evaluate_at_temperature
              RigidWaterGas.evaluate_at_temperature
                wet: 2 pressure endpoints + pressure trial loop
                  _liquid_volume -> HEOSWaterProperties.state_tp
                    HEOSCandidate.state_tp
                      _transaction identity/lock checks
                      _saturation_pair_locked(same trial T)
                      native PT seed + checked density correction
                dry: represented Ng R T / V, no liquid closure query
              wet: water.state_tp_response(T, solved P)
                same HEOSCandidate.state_tp -> new coexistence + TP solve
              each gas: ideal caloric U/H/Cp/Cv and numerical-error checks
            wet_fluid_pressure_bounds: exact original global/local eV bound
          source mass caloric U/Cp/minCp + exact sum/projection/error arithmetic
      evaluate_wet_phase -> chemical.equilibrium_at_liquid_tp(T, P)
      ideal_gas_state
    optional decoded_liquid_state for each cell
      wet: water.state_tp at the selected inverse's same T/P
      dry: no liquid transport property query
    each shared internal face: gas diffusion/advection enthalpy + liquid donor h
    end source/state guards
  Rates construction + derived fields, end operator identity
  emit rhs_returned / observer; Rates.derivatives
```

Pointers: `exact_source_column.py:83–124`, `source_wet_column.py:184–249`,
`source_wet_storage.py:203–252`, `mass_wet_storage.py:73–94`,
`rigid_storage.py:179–243`, `rigid_water_gas.py:140–145,159–286`.

The source inverse always begins with two full temperature-domain evaluations;
it does not retain a temperature guess from the preceding RHS. On a successful
cell with `I` recorded inverse iterations there are exactly `2 + I` calls to
SourceWetStorage.evaluate. Its acceptance residual, error allowance, midpoint
order and returned bracket are part of saved evidence. Altering the inverse
algorithm or warm-starting it is not an output-preserving first optimization.

## Repeated work provable from code (not measured ranking)

### 1. Source Cp metadata/asset checks

`ArlabosseDryCaloric._source` (`arlabosse_caloric.py:72–86`) reads and hashes the
source JSON, parses it, resolves each asset path and reads/hashes every asset on
every cp/delta_h call. Four asset files currently exist. Read-only stat gives:

| Item | Bytes |
|---|---:|
| source.json | 4,033 |
| article.html | 115,329 |
| cp-equation.gif | 1,221 |
| nomenclature.gif | 9,743 |
| table1.gif | 6,086 |
| Total per complete _source check | 136,412 |

This is logical read/hash volume, not measured disk IO; the OS can cache file
pages. No asset content was hashed by this investigation, so the table is size
evidence rather than a fresh source verification.

A successful direct `SourceWetStorage.evaluate` statically triggers **12**
Arlabosse `_source` calls:

| Caller | _source calls |
|---|---:|
| initial self.check -> storage.binding | 2 |
| caloric.specific_internal_energy: its guard + delta_h | 2 |
| caloric.cp: its guard + provider.cp | 2 |
| caloric.minimum_specific_heat_capacity -> cp(lower) | 2 |
| self.source_ids -> storage.binding | 2 |
| final self.check -> storage.binding | 2 |

Each storage.binding calls caloric._check (one reference cp) and then a second
caloric.binding (one more reference cp); see `source_wet_storage.py:144,160`
and `source_mass_caloric.py:111–139`. Thus the direct evaluate contribution is
`12*(2+I)` checks per successful inverse cell, before adapter/column overhead.
At the current asset sizes this is 1,636,944 logical bytes per direct evaluate.

`SourceWetColumn.binding` adds another independently countable chain: for N
storages, each loop does storage._check (2), current/first caloric.binding
comparisons (1+1), then the final stored content asks each storage.binding (2):
**6*N source checks per successful column.binding**, including repeated first
storage comparisons. See `source_wet_column.py:127–142`. The adapter's operator
and energy properties, unpack, column state checks and final identity request
call these paths again. Profile actual call counts rather than infer a complete
RHS multiplier from just the visible inverse iteration count.

### 2. Same-temperature coexistence solve inside pressure trials

Each wet pressure trial calls liquid state_tp at fixed outer T. Kernel
`state_tp` calls `_saturation_pair_locked(t)` unconditionally
(`_heos_kernel.py:284–292`). That method initializes QT liquid/vapor seeds and
solves checked coexistence again; there is no existing kernel saturation-result
cache. `last_coexistence` and `last_tp` are copied diagnostic records, not memoized
returns. The Python WaterProperties saturation cache is a different backend and
does not remove these HEOS calls.

Every successful wet mechanical closure also re-queries the final T/P through
state_tp_response (`rigid_storage.py:190`, `water_heos.py:89–93`); the last pressure
trial already solved that liquid T/P. With liquid transport, decoded_liquid_state
queries the accepted inverse's final T/P once more (`liquid_transport_state.py:61`).
Thermal and chemical providers can be different live objects with matching source
metadata, so equal T/P across those objects is not permission to share a cache.

The transaction performs pre/post native config serialization and native Water
JSON hashing (`_heos_kernel.py:126–140`). These guards are repeated per request too;
their cost must be distinguished from actual native EOS and coexistence work.

Important dry qualification: although Nl=0 storage closure does not query liquid
EOS, `evaluate_wet_phase` calls `chemical.equilibrium_at_liquid_tp` for **both**
modes (`mass_wet_transport.py:88–95`). This supports the dry condensation refusal.
The complete mixed RHS is not EOS-free on its dry cell; do not remove that query
just because phase flow is zero.

### 3. Repeated ideal-vapor caloric tuple

Below 500 K with positive H2O gas inventory, one RigidStorage temperature point
calls JoinedWaterVapor.numerical_error (h and u), IdealGasPhase.evaluate (u and h),
then the curve cp and cv: six calls to IdealWaterVapor._caloric at the same T.
Each _caloric obtains the full (h,u,cp,cv) tuple again from the independent Python
ideal-Helmholtz path. See `rigid_storage.py:207–212`,
`joined_water_vapor.py:173–179`, `phase_storage.py:164–168`,
`ideal_water_vapor.py:78–113`. HEOSWaterProperties.ideal_vapor additionally invokes
its metadata guard; it does not invoke a native real-fluid flash.
Face and chemical evaluations add further ideal-h work at actual face/donor T.
Zero diffusive flux currently still evaluates h, while zero advective flux skips
it. Skipping zero-flux queries changes existing domain/source-failure detection,
so it is not a safe automatic optimization.

### 4. Static dataclass rebuilding and full identity serialization

evaluate_wet_fluid reconstructs RigidWaterGas and RigidStorage on every temperature
point (`mass_wet_storage.py:73`). The available volume is constant in this source
profile, yet constructors revalidate gas/reference/phase data. Many bindings also
recursively serialize the same dataclasses to JSON (`deforming_solid_storage.py:85`).
This is measurable Python work, but dropping the constructors/checks can alter
mutation detection and source ordering. Keep it as a candidate only if its
exclusive profile cost is material.

## Candidate optimizations, ordered by evidence needed rather than guessed speed

1. If source JSON parsing is material: memoize only the immutable parsed, pinned
   metadata/asset manifest, while retaining each existing read/hash and path guard.
   Do not hand out a mutable cached dict through _source/registry_payload. This can
   preserve existing per-operation asset checks and every exact Cp formula; it
   cannot eliminate the measured read/hash work if that dominates.
2. If repeated ideal tuple computation dominates: introduce a narrowly scoped
   combined caloric evaluation after the same original guards, and reuse its exact
   represented h/u/cp/cv within one temperature evaluation. Keep source guards at
   public entry points, exact arithmetic order and all numerical-error terms. No
   rounded-temperature cache key or inventory/state result reuse.
3. If HEOS coexistence dominates: a per-actual-kernel exact-T successful-result
   memo is a separate reviewable change. Keep every _transaction pre/post guard,
   lock and failure behavior; no cross-instance sharing; never cache a failure or
   partially initialized state. Preserve/supply complete coexistence diagnostics,
   and test native handle state after a hit. A repeated state_tp/full response cache
   similarly needs all diagnostic and mutation bindings; it is not a trivial dict.
4. If identity checks dominate: first measure and eliminate pure duplicated
   computation within a check, retaining all actual mutable-source checks. An
   explicit immutable asset scope would be a new lifecycle contract, not a silent
   mtime/size fast path. Existing tests intentionally detect changed files/content
   and transient provider mutation; frozen dataclasses alone do not prove safety.

Do not change tolerance, midpoint/proposal ordering, pressure stop criteria,
declared eV/eU/eT bounds, source IDs, mode behavior or qualification for speed.
Preserve returned float/array bits, Fraction values, errors, bracket/iteration
evidence and exception classification when claiming numerical equivalence.

Runtime/implementation identity caveat: water_heos.py records its own and related
source-code SHA in WaterImplementation (`:42–50`). Changing those files legitimately
changes implementation identity; it must not be forced to the old SHA. Keep old
outputs as evidence, declare the new implementation and require scientific-data
and arithmetic equivalence separately. Prefer a narrower optimization outside
these identity-bearing files if the measured profile supports it.

## Next bounded single-RHS measurement (proposal; not executed here)

1. Root selects one saved successful **ordinary mixed wet/dry/wet** capture from
   native02 and records exact input state/time, explicit modes, source/config/
   runtime identities and its complete returned evaluation hash. Use the first
   such successful ordinary capture by recorded order, not a later favorable one.
   Validate/read it in the passive stage; report that wall separately.
2. Reconstruct the original installed actual providers/column once under the
   existing observer. Restore the declared dry view against the same newly built
   per-cell storages. No initial-U/probe/seed/event rerun. Record real constructor
   and anchor costs before profiling the RHS; retain failures normally.
3. Execute exactly **one** adapter.evaluate(saved_state, saved_exact_time) under
   cProfile and the normal source observer/journal. Record started/returned/failed
   counts; this is one actual RHS even if failed. Root has now preregistered a
   concrete original-parent one-RHS script with **120 s** outer supervision;
   that selected input and preregistration govern the actual measurement, rather
   than the proposed ordinary-capture selection above. Retain that fixed
   cap, retaining the original inverse/pressure iteration and numerical policies.
   A timeout preserves the started/partial evidence; no automatic retry or cap
   increase. Obtain Root approval for this measurement separately.
4. Save the pstats, complete result or failure, elapsed wall, runtime before/after,
   and per-cell inverse iterations/final pressure trial ledgers. Report cumulative
   and self-time separately for _source, read_bytes/sha256/json, storage/column
   binding, source evaluate/invert, pressure closure, state_tp, coexistence,
   native update, ideal caloric, Fraction, and observer/raw projection/disk write.
   Cumulative callers overlap; do not sum their cumulative times as disjoint cost.
5. Compare the whole returned numerical/source record with the saved control;
   pressure iterations/ledgers and error fields are part of the comparison, not
   just N/U/T/P. Do not label one profiled wall sample a robust speed estimate.
   This first call decides which narrow component, if any, to optimize.
6. If exact duplicate keys are needed after profile counts identify a candidate,
   use a separately registered lightweight call-argument trace; cProfile alone
   supplies aggregate function counts, not exact T/P key histograms. Do not pretend
   the static same-T proof is an observed hit count. Avoid invasive instrumentation
   or a second physical measurement before deciding what uncertainty it resolves.

An eventual before/after numerical test should reuse identical inputs, full output
fields and failures; a one-RHS physical A/B can follow author/independent cheap
tests and a frozen implementation. No performance claim is made in this note.

Handoff note: Root reported its independent passive profile completed in 13.151 s
with zero live calls and repeated source-sample encode/decode work. That result
does not establish the live RHS's bottleneck. This agent did not inspect or rerun
that profile and will wait for the separate frozen one-RHS measurement before
any optimization implementation is assigned.
