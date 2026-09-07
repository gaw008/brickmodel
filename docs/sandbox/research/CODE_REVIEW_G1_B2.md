# G1 evidence registry and B2 repair: independent code review

Reviewed: 2026-09-07 UTC. Reviewer: separate Codex Python review agent. This is a code/numerical review, **not physical external validation, external expert certification, or completion of the sandbox Goal**.

Baseline HEAD: `4b4f2d37913b96d30842f86d38f302d578887e72`. The review examines uncommitted files on that baseline. The findings below describe the initial reviewed implementation; a later repair requires a separate recorded recheck.

**Current review decision after the final recheck below: Approve for a local implementation milestone commit.** All defects raised in this review have been repaired and independently rechecked. The initial Block and second-pass findings are retained below as history. This approval does not establish scientific source validity, full B2 commit-bound certification, or completion of the physics sandbox.

## Decision

| Scope | Initial decision | Reason |
|---|---|---|
| A: B2 solver/audit/resources/harness and associated tests | Approve within existing synthetic B2 scope | No new CRITICAL/HIGH defect found. The quadrature derivation, fixed audit tolerance, current actual invocation count and macOS/Linux RSS conversion were checked. Full bound-suite/demo certification is outside this review's executed checks. |
| B: `sludge_sandbox.evidence` and `units` | **Block** | Two reproducible HIGH false-admission paths exist in the evidence registry, plus malformed-input and JSON provenance ambiguity issues. |
| C: Wang Figure 3 digitization | Warning; graph-derived data only | Figure/sample mapping and saved CSV reproduced. Research dependency is absent from the project environment; readout uncertainty is incomplete as a measurement uncertainty. |

## Findings

### [HIGH] Empty and nonnumeric structured parameters receive full evidence admission

File: `src/sludge_sandbox/evidence.py:163`

Issue: `_validate_node` checks only the outer `int/float/list/dict` type. An empty list, empty object, nested `null`, string array or boolean/string/null mixture is accepted as a known physical parameter. `assess` then returns `allowed=True`, `result_lane='evidence_constrained'`, and `traceability_coverage=1.0` when declared citations otherwise pass. This bypasses the explicit-unknown requirement and admits values that cannot be evaluated as a physical quantity.

Reproduction (repository root):

```python
import runpy
from sludge_sandbox.evidence import EvidenceRegistry
ns = runpy.run_path('tests/sandbox/test_evidence.py')
for value in ([], {}, {'value': None}, ['not-a-number'],
              {'samples': [True, None, 'unknown']}):
    p = ns['registry_payload']()
    p['nodes'][0]['value'] = value
    a = EvidenceRegistry.from_dict(p).assess(['surface_heat_flux'], ns['CONTEXT'])
    print(value, a.allowed, a.traceability_coverage)
# All five cases print True, 1.0 in the initially reviewed version.
```

Fix: specify allowed structured numeric schemas; validate their required fields, nonempty dimensions, finite numeric leaves and explicit missing-value policy recursively. Keep descriptive metadata separate from numerical values. Reject unsupported structured values before admission and add behavioral tests for each case above.

### [HIGH] A design value can be promoted into an evidence-backed material constant

File: `src/sludge_sandbox/evidence.py:260`; propagation at `:305`; derivation validation at `:173`.

Issue: design choices and numerical policies inherit `own_coverage=True`. A `derived_from_evidence` physical parameter requires only a nonempty dependency list and a derivation string, so it can depend exclusively on an arbitrary design value. Its physical evidence coverage becomes 100% without any upstream measurement/law/constitutive relation supporting the parameter. The existing role check stops direct relabeling but not this indirect path.

Reproduction (extend the fixture used above):

```python
from copy import deepcopy
p = ns['registry_payload']()
choice = deepcopy(p['nodes'][0])
choice.update(id='chosen_k', role='design_input',
              evidence_kind='virtual_design_choice', citations=[],
              rationale='Arbitrary exploratory choice')
p['nodes'].append(choice)
p['nodes'][0].update(evidence_kind='derived_from_evidence',
                     dependencies=['chosen_k'], citations=[],
                     derivation='k = chosen_k')
a = EvidenceRegistry.from_dict(p).assess(['surface_heat_flux'], ns['CONTEXT'])
print(a.as_dict())
# initially: allowed=True, evidence_constrained, coverage=1.0, issues=().
```

Fix: track physical evidence roots separately from permitted design/numerical inputs. Require an evidence-supported derivation relation and appropriate upstream physical evidence for a derived material parameter; a design-only or numerical-only lineage cannot establish material knowledge. Valid designs may still participate in a sourced physical calculation without being counted as measured/material evidence. Add transitive bypass tests, including numerical-policy-only and multihop design chains.

### [MEDIUM] Duplicate JSON keys silently discard conflicting provenance values

File: `src/sludge_sandbox/evidence.py:97`

Issue: plain `json.loads` keeps the last duplicate key. Replacing the fixture's `"value": 0.6` with `"value": null, "value": 0.6` in its source JSON is silently accepted, and assessment reports full admission/coverage. The canonical registry digest represents only the overwritten result, so it does not preserve the ambiguity in the source registry. B2 already has a strict duplicate-key parser; this new entry point has no equivalent protection.

Fix: reject duplicate object keys using `object_pairs_hook`, reject nonfinite constants at parse time and apply explicit size/depth policies suitable for local registry files. Preserve the raw source artifact identity separately when required by the provenance contract.

### [MEDIUM] Malformed schema fields escape the public error contract

File: `src/sludge_sandbox/evidence.py:141`, `:150`, `:181`, `:189`; `src/sludge_sandbox/units.py:55`.

Issue: list-valued `read_status`, `evidence_kind`, citation `source_id`, or applicability `status` raises raw `TypeError: unhashable type: 'list'` during set/dict membership. `convert(10**1000, 'K', 'K')` raises raw `OverflowError` from `math.isfinite`. These inputs fail closed, but callers expecting `EvidenceError`/`UnitError` cannot reliably render a controlled input rejection.

Fix: validate scalar field types before membership checks, then raise the declared exception with a field path. Guard representability of integer scalars and ranges so overflow is translated into the documented domain exception. Test through the public constructors/conversion API.

### [MEDIUM] Digitization runtime is not reproducible from the project environment

File: `data/sandbox/research/digitize_wang.py:16`; project `pyproject.toml`.

Issue: the script imports Pillow, which is absent from `.venv` and absent from the declared project dependencies. The independent readout run succeeded with the existing system Python 3.14/Pillow, not the project's Python 3.12 environment. A clean project environment therefore cannot reproduce this required data transformation from current dependency declarations.

Fix: add a controlled optional research dependency or a documented locked research environment, record the actual Python/Pillow versions, and execute the command in that environment. Keep this optional tooling separate from core solver dependencies where appropriate.

## A: B2 derivation and operational checks

The new limiter controls trapezoidal integration of `H(tau) = integral K(tau) dtau`. It uses `K''`, equivalently `H'''`; it is not an error estimate for the full reaction-transport solution.

For a linear temperature segment, let `A = theta*T_ref`, `v = dT/dtau`, and `K = K_ref*exp(theta - A/T)`. Direct differentiation gives:

```text
K''(tau) = K * v^2 * A/T^3 * (A/T - 2).
```

Writing `x=A/T`, the temperature-dependent factor is `exp(-x)*x^3*(x-2)`. Its stationary points satisfy `x^2-6*x+6=0`, so `x=3 +/- sqrt(3)` together with segment endpoints suffice for the maximum absolute curvature. `x=2` is a zero, not a missing positive maximum. Holds, `theta=0` and `K_ref=0` need no truncation cap.

With total nonconstant-ramp duration `D`, a segment curvature bound `M`, and `h <= sqrt(12*epsilon/(D*M))`, its accumulated trapezoidal truncation error is bounded by `epsilon*(segment_duration/D)`. Summing completed/partial segments gives at most `epsilon=1e-7`. Integration stops at every temperature knot and output time; the schema restricts `dt_scale` to `1`, `0.5`, `0.25`, so its multiplier cannot enlarge the bound. The current schema fixes `T_ref=600 K`, consistent with the coefficient evaluator. This argument covers quadrature truncation, not floating-point roundoff or external material uncertainty.

- `audit.TOL` remains `1e-6`; no threshold increase found.
- The RK state/transfer/reaction ledger weights are unchanged.
- An independent dense scan checked 18 nonconstant frozen-program segments, 1001 temperatures each. Maximum sampled curvature / limiter curvature was `1.0000000000000002`, consistent with rounding.
- Historical W07/L01 ramp tests passed at the original audit threshold and retain the inventory assertion. Those are synthetic scenarios, not observed materials.
- Independent `sys.setprofile` observation of the actual `solver.integrate` code object during all 14 unit tests counted **2** invocations; the harness mock also counted **2**. Current unit tests contain no additional successful subprocess solves. The named numerical suite has its separate existing counter. This observation does not guarantee future alias/subprocess tests will automatically be counted.
- Linux `ru_maxrss/1024` and Darwin `ru_maxrss/(1024*1024)` both produce MiB. The two platforms' 76 MiB and 513 MiB mocked cases exercise acceptance and the 512 MiB rejection threshold.
- Failure telemetry now preserves the fixed tolerance plus scenario/sample/check/error for finite mismatch comparisons. The historical audit's explicitly limited inventory/derived-consistency scope remains intact.

## C: Wang digitization evidence and limits

Read locally: source PDF text `data/sandbox/research/raw/energies-14-07722.txt`, methods Section 2.2/2.3 and Table 3; visually inspected both unchanged Figure 3 bitmaps containing panels a-d.

- Methods specify 10-minute sampling, temperatures 40/50/60 degrees C, RH 30/40/50/60%, and three repeats. The source material is a 2 mm sludge layer on a steel plate at 1.5 m/s air speed. This is neither a sludge/clay brick nor full-brick drying validation.
- Figure colors match the code: 60 degrees C red squares, 50 green circles, 40 blue triangles. Panels map to ascending RH. The x-axis calibration is 0-280 minutes and the y-axis is MR 0-1.
- The 12 per-condition sample counts match Table 3. Calling `digitize()` without invoking `main()` returned 186 rows, 12 conditions, no duplicate `(temperature,RH,time)` tuples, monotonically increasing time within each series, and exact agreement with the saved CSV.
- Figure 3 presents the source experimental trajectories; the script selects their colored bands at known sampled x coordinates. It does not call a Midilli formula or use the later fitted coefficients to manufacture the CSV. The initial MR=1 row is explicitly labeled as source-equation normalization rather than a pixel measurement.
- Independent raw image hashes: `ab=3c7131a49177eba8a3af6351bf4fff4b2e0fc19cc0380213fd5d039349d3cba0`, `cd=d09e903400a062595b551ae2c6ad2c7fdea0e4ae3bc1876878d3f440faa363be`.
- Noninitial readout bounds range from `0.012308` to `0.030864` MR. They describe a vertical pixel band selected in a 5-pixel-wide strip. The color parser does not geometrically separate the marker from its connecting line; the stored method is source-specific and should not be generalized to other plots without review.
- These are graph-derived observations. The readout bounds explicitly exclude source measurement scatter and axis calibration uncertainty. Underlying triplicates are unavailable, and this review does not independently redigitize every marker. Do not turn these bounds into an experimental confidence interval or use them alone to set tight validation tolerances. Raw uncertainty is still unknown.

## Executed checks and review limitations

```text
git diff -- '*.py'
git status --short
git diff --check
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox -q
  27 passed
cd experiments/material_dynamics_v2b2
B2_TEST_OUT=validation/review_g1_b2 PYTHONPATH=. ../../.venv/bin/python -B -m unittest discover -s tests -v
  14 tests passed
```

The first sandbox test invocation without `PYTHONPATH=src` failed collection because the new package was not installed; the explicit source-path rerun above passed. The high-severity reproductions are additional independent probes and are not covered by those initial 27 tests.

Ruff, mypy, pylint and black were not installed in `.venv` or available on PATH, so their analysis was not claimed. Manual source inspection, test execution and `git diff --check` were performed. No production source file was changed by this reviewer; only this report and ignored review test fixtures were written. No stage/commit/push was performed by this reviewer.

Reviewed implementation SHA-256 values:

```text
b2dee009af7a60719fc5ca3d45658e5f027e5ce67a9983f7a84af3bbd5618272  src/sludge_sandbox/evidence.py
772f489e151e585ff0f33354908e25f834c390c4ce051c6c33b99a2d51d6632c  src/sludge_sandbox/units.py
0887487193993c3d1a86d962e8f1eddf3ba24036509ce0009b3122e9d8d7958f  experiments/material_dynamics_v2b2/solver.py
ca7a2cfd66f35c530b89b563e3455c377ea4f22e5ec779feac48eb4d87847a2b  experiments/material_dynamics_v2b2/audit.py
6b39bf1c2a0a2060a6da4d1dd619d6f73ee3442fc6cf9fd45de0d4c6847f214b  experiments/material_dynamics_v2b2/resources.py
e9bc4db990690e06bab043d24f1a4326da618bc76b561f515064e721656e7430  experiments/material_dynamics_v2b2/run_tests.py
75c1cca36c07444519b6b9d238939f0e94ae503598c3cefeb0bd600e26faafd6  data/sandbox/research/digitize_wang.py
```

Metadata-only admission, even after these code defects are fixed, cannot verify scientific correctness or authentic reading of a source. The registry explicitly returns `scientific_validation='not_established_by_registry'` and `source_assets='not_checked'`. Downstream execution must not interpret `allowed`/traceability coverage alone as completed source review, verified source assets, applicable constitutive science, or external experimental validation.

## Second pass: implementation repairs and newly added geometry

The main implementation agent repaired the initial findings while this review continued. The initial findings above are retained as historical evidence, not claims that the same defects remain unchanged.

Executed `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox -q`: **51 passed**. Independently repeated 12 original probes: five malformed structured values, four unhashable schema fields, one design-only material lineage, one huge integer conversion and one duplicate-key file. All now rejected through the intended API or returned disallowed assessment. `git diff --check` passed.

At this recheck the hashes were:

```text
1dc18e192783db288e7400ac83905b6c7a3571c3440d70568f66092df1b47a8b  src/sludge_sandbox/evidence.py
bf2f0bd87bc87f9264d0dd46c53f8cdd68342a3dbf411817a7857cb348c2d07c  src/sludge_sandbox/units.py
966ad4c884ab446895749cb8b75e81117a23abb1238cecfa272851eada421d6f  src/sludge_sandbox/geometry.py
```

`pyproject.toml` now declares `research = ["Pillow==12.1.1"]`. The dependency declaration gap is repaired; actual installation/reproduction in that environment remains an execution check for the main agent.

The added `geometry.py` consistently uses a shared tangential stretch `lambda_t`, shared current face area `A0*lambda_t^2`, per-cell normal stretch `lambda_n`, and volume ratio `J=lambda_n*lambda_t^2`. Phase volumes use reference bulk volume as their common basis: total pore volume `J-V_s`, open volume `J-V_s-V_closed`, gas volume after subtracting liquid water, and porosity obtained by dividing reference-basis open volume by `J`. Exhausted open gas volume raises instead of being clipped. This checks kinematic algebra, not the validity of any shrinkage constitutive model.

Additional second-pass issues sent to the implementation agent:

- **[HIGH] Derived equations lack required derivation provenance.** In the fixture, change the `fourier` equation to `evidence_kind='derived_from_evidence'`, `citations=[]`, `value='q = k * 42'`, leaving only the measured conductivity parameter as its upstream dependency. Assessment still returns `allowed=True`, `evidence_constrained`, coverage `1.0`, no issues. At reviewed `evidence.py:211`, a derivation is required only for physical parameters; the physical-root test at `:321` can be satisfied by an unrelated measured number, with no declared derivation for the equation. A reproducible derivation/transform artifact and appropriate upstream relation provenance must be required for derived equations. No schema alone can certify the scientific correctness of an asserted derivation; that remains a separate source/model review.
- **[MEDIUM] Mixed booleans are silently coerced in geometry arrays.** At `geometry.py:28`, `np.asarray([True, 1])` produces an integer array, bypassing the dtype boolean rejection. `ReferenceSlab(1, 1, 2).deform([True, 1], tangential_stretch=1)` returns widths `[0.5, 0.5]`. Validate supplied element types before lossy NumPy coercion.
- **[MEDIUM] `pore_geometry` does not validate the public current geometry input.** `CurrentSlab` is a public dataclass, and its owning arrays can also have writeability re-enabled. Set one `current.volume_ratios` element to NaN and call `pore_geometry` with finite nonnegative phase volumes: it returns NaN gas volume/porosity rather than `GeometryError`. Validate `J` as a finite positive per-cell array at the public function boundary, independent of how `CurrentSlab` was obtained.

These second-pass issues must be resolved or explicitly kept open; the initial Block decision is not changed by the 51 passing tests alone.

## Final recheck: defects resolved; local milestone commit approved

The final pass was restricted to the four requested fixes: missing derived-equation derivation, a numeric-only root for a derived equation, mixed boolean geometry arrays, and modified/nonfinite current volume ratios. Production code was not edited by the reviewer.

Executed:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_evidence.py tests/sandbox/test_geometry.py tests/sandbox/test_units.py -q
56 passed in 0.07s
git diff --check
passed
```

The reviewer also executed **14 independent probes**, all with the expected outcome:

1. A derived equation without a derivation string now raises `EvidenceError`.
2. An arbitrary relation with a derivation string but only a measured-number root is disallowed in evidence mode.
3. The same numeric-only relation is disallowed in exploratory mode.
4. The explicit manufactured mode permits that numerical test relation only in `manufactured_test_fixture` lane with incomplete evidence coverage.
5. A declared derivation with an upstream sourced equation passes the metadata/lineage gate.
6. Changing its source reading status to metadata-only removes the usable equation root and disallows admission.
7. Mixed `[True, 1]` normal stretches raise `GeometryError`.
8. The equivalent object-typed NumPy array also raises `GeometryError`.
9–14. Public `CurrentSlab` inputs with NaN, infinity, zero, negative, two-dimensional or empty `volume_ratios` all raise `GeometryError` before pore arithmetic.

Derived physical parameters and equations now require declared derivation text. Derived equations separately require a transitive root whose role is `equation` and whose citation directly supports an equation with a checked reading status. This repairs the specific numeric-only provenance bypass. The registry still checks declared lineage rather than the mathematical/scientific truth of that lineage; source review, derivation verification and actual dependency binding remain required downstream.

Pillow execution was also rechecked in the **project's locked environment**: Python `3.12.13`, Pillow `12.1.1`. Invoking `digitize()` without writing the source artifacts reproduced all **186** CSV rows exactly. Both dependency declaration and environment execution gaps from the first pass are therefore closed. The limitations concerning pixel readout, absent original triplicates and scientific validation remain applicable.

Final rechecked implementation hashes:

```text
616249bd154490ffcb663bfff67bcf1788c78be94e81c7a28c89c6d235cd1a50  src/sludge_sandbox/evidence.py
384d35d67ed7aa043991d69e795169bafddb8e1466c1d1f0b072521c10a72312  src/sludge_sandbox/geometry.py
bf2f0bd87bc87f9264d0dd46c53f8cdd68342a3dbf411817a7857cb348c2d07c  src/sludge_sandbox/units.py
```

The SHA-256 values of the four B2 implementation files still match the initially reviewed values in this report. Their previous derivation review, 14-unit-test result and independent invocation-count check therefore remain relevant; no redundant full B2 run was claimed in this final pass.

**No unresolved CRITICAL, HIGH or MEDIUM code defect identified by this scoped review remains. The reviewed B2 repair is suitable for the user's authorized local stage commit, alongside the reviewed G1 registry/geometry and controlled digitization changes.** This is code-review approval of a milestone, not approval to label the bound B2 suite passed. After the actual local commit, the implementation agent must run the existing commit-bound `run_tests.py` workflow and required current demo/audit, inspect their actual artifacts and binding readback, and record any failures without relaxing thresholds. The reviewer did not stage, commit, push, or execute that post-commit workflow.
