# Independent review: energy state identity

Verdict: **APPROVE**, no actionable findings in the scoped diff against `41e5911`. Reviewed five production files: integration, depletion_roundoff and the three historical thermal hosts, plus the new identity tests. This review does not approve full depletion-event identity propagation; that is a separately assigned subsequent change.

## Scope and reasoning

`energy_model_identity=None` preserves historical construction and numeric behavior. A supplied identity is restricted to nonempty immutable tuples/trimmed strings, with nested validation; booleans, numeric values, empty nodes and mutable lists reject. This is an opaque host binding, not evidence certification. A future host should digest its full typed scientific/numerical identity into such a tuple; directly inserting the skeleton identity containing floats is intentionally unsupported. Full sources remain in the host/provider metadata.

Both Euler validation stages and accepted RK combinations preserve the exact original identity. Rejected trials cannot introduce a different label. Inventory roundoff writeback preserves the identity without changing energy. Each historical gas/rigid-fluid/solid-fluid host checks for a non-None label before caloric/physical decode; these hosts therefore cannot silently interpret a future tagged total energy as their historical thermal energy. The source changes do not alter their numeric equations, error policies or transport sources. Explicit host initializers continue producing historical untagged thermal states.

No claim is made that an opaque string proves the energy scope, that generic user operators validate it automatically, or that all external serializers/event constructors now preserve it. `depletion_integration` terminal paths are specifically outside this approval. No in-process security guarantee is inferred from frozen dataclasses.

## Independent execution

Command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_energy_state_identity.py tests/sandbox/test_integration.py tests/sandbox/test_component_work_ledger.py tests/sandbox/test_depletion_roundoff.py -q --junitxml=docs/sandbox/research/energy-state-identity-independent.xml
```

Actual result: **73 passed in 0.81 s**, exit 0. Includes 13 identity tests plus integration/component-work/roundoff regression. Tagged actual rigid/solid host rejection is tested with liquid EOS forbidden. No EOS-heavy or full repository suite was run by this reviewer.

An additional independent old-code comparison loaded `git show 41e5911:src/sludge_sandbox/integration.py` into a separately named in-memory module, using its own state/rates/policy classes. Both versions ran identical untagged two-cell cases with a .375 s program node: inert; reaction plus shared mass/energy faces plus component body power; and a domain exit at t>.3. All result fields recursively compared exactly, including arrays, accepted times, ledger components/roundoff, evaluations and rejected counts; only elapsed wall time and the newly added None label were excluded.

| Case | Result | Accepted steps | Evaluations | Rejections | Exact matched serialized result SHA256 |
|---|---|---:|---:|---:|---|
| Inert | completed | 2 | 15 | 0 | `e5e82881a32d094dad378b4033dabe3c66c1f84966dee3846de427bca127a7a1` |
| Reaction/heat/shared faces | completed | 101 | 726 | 3 | `8d9f49e984ad292b07418de7188e03c8d9ebfb3595b51b760fe49eb101222398` |
| Domain failure | domain_exit | 41 | 386 | 45 | `e2d647aea77c3859c76402580177fa5dea454f006d9c63abebad98c58864a362` |

The first comparison harness attempt failed because the reviewer guessed an incorrect IntegrationResult component-field name; no production assertion ran in that attempt. The corrected harness enumerated actual dataclass fields recursively and then completed the comparisons above. This was a harness mistake, not a product failure.

## Reviewed artifact binding

| Artifact | SHA256 |
|---|---|
| `src/sludge_sandbox/integration.py` | `cedefb0c3af415be8d9a7fb165c1d2288249b354666567191bbf57c33d405b50` |
| `src/sludge_sandbox/depletion_roundoff.py` | `65b53e7a9f94b651e5dbc833054b637129ff659b63a290e0512154f3f9333148` |
| `src/sludge_sandbox/gas_heat_model.py` | `e000fc2aa7fd039e8f43d9741e3a73b04760303a3f2753bd7ad2c1387fd097af` |
| `src/sludge_sandbox/rigid_fluid_heat.py` | `c554ad1e53614c56fe2b3fbab0b9629c0a51ec6be4d6944eae0ea6fcdc6d4dcc` |
| `src/sludge_sandbox/solid_fluid_heat.py` | `9b9b69f51d9963da799096260b5a3f5483b22d27b47abbb4435c6e334d606be2` |
| `tests/sandbox/test_energy_state_identity.py` | `5b0512697b4f292d343fdbcb0de4ffddf5de9902233ced705591d1e81fc478b0` |
| `docs/sandbox/research/energy-state-identity-independent.xml` | `37f65e5eb2e415bdcf1a8f1dce415b031c7b83ce8ce679002140c21afa089ba7` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — scoped state-identity propagation and legacy-host rejection pass independent review; future depletion/total-energy-host work remains separate.
