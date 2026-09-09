# Strict exact-run record candidate

Source SHA256 `9634890467bf716d868520923dbcf010de51d74c45b246a0f2d5cb3ea5d87ae5`.
Portable test SHA256 `5f462d969c9dc62b2265bc0a39ee4a80426f4da442f25ea11df6e43b6faccb67`.
Actual tests07: 12 passed in 7.00 seconds. No EOS/repository edits/install.

Apply only exact_record.py and test_exact_record.py to their corresponding source/test locations after review. conftest.py is a temporary relative-path overlay and must not be applied. The test imports production module names and existing test_exact_depletion_integration.setup. That fixture uses partial typed host shells; its constructor-only patch permits mode dataclass reconstruction while leaving actual source digest checks in place. It is not native validation.

The schema records every ExactDepletionResult field and all nested numerical packet, terminal and refinement evidence. ExactFreeWaterTransfer becomes a frozen identity/modes reference. WaterTransferEvaluation becomes the exact comparison vectors, Rates and phase diagnostics used by the core; live provider/inverse object graphs are explicitly omitted. Thus schema_complete_numerical_evidence does not mean complete physical or Python object graph capture.

read_exact_run returns immutable canonical bytes, EvidenceNode mappings, exact times and actual validated ConservedState/ExactStepLedger projections. Arrays in both typed and generic evidence cannot regain writeability: generic arrays use immutable bytes storage. No arbitrary class import, provider constructor, saved code, integration or resume is executed. The static allowlist only recognizes reviewed record types; their field sets and strict primitive annotations are checked. Policy objects are reconstructed for their existing local validation. Accepted ledger shape/time/state and committed packet membership, event sequence, mode changes and correction counts are linked. Counter structure and ordering are checked; this is not a full recomputation of discarded work or numerical acceptance.

validate_binding reparses the immutable bytes rather than trusting manual ExactRunRecord construction, compares case/runtime/original operator to external inputs, invokes live source checking, then reconstructs each saved interface-mode configuration from the externally supplied actual original operator and compares identities. The original default interfaces=None representation is retained for its original mode reference because an explicit wet tuple has a different source identity. Further source failure capture intentionally uses constructor-frozen identity without invoking a failing live getter. This allows failure preservation; it does not approve a mutated operator for continuation.

A future resume adapter still must rebuild from externally frozen case/water/implementation, audit every original-initial ledger/correction and six-gate/refinement/root-order acceptance under original policies, validate cumulative budgets and checkpoint status, and join exact prefixes once. This codec grants none of that authority. Existing compact research JSON is rejected instead of silently promoted.

Preserved failures:
- tests02: partial instrumented fixture cannot use the real WPT constructor; explicit test-only constructor patch documents that seam.
- tests03: source identity differed when None default interfaces were normalized to wet tuple. Fixed preserving the original operator reference.
- array-red: actual recovered-writeability attack failed the original implementation; immutable bytes backing closes it. Pre-fix source retained.

Known bounded validation scope: evidence-node structural typing and committed associations, not EOS re-evaluation, global conservation re-audit, all root proof arithmetic, speculative full-state comparison recomputation, or material validity. The separate existing actual-run audits remain necessary. Roundtrip is not resume.

## Reviewed corrections (supersedes initial freeze above)

Final pending-review source: `f03abafa6251f3ad57a73b3622a2fd852c7246c376bd4cc43fbaebec06db4408`; test: `450a41c18a48d009e934a8d7c4be5138ddb9dee4afbb8602cd691d99b95c6139`. tests09: 18 passed in 12.20s.

`validate_binding` now RETURNS the freshly parsed checked record. Callers must consume this returned object; manually replacing fields of the input wrapper does not grant them validation. All nested state, ledger and Rates records run original constructors; each TerminalObservation binds Rates shapes/mechanical presence to its actual saved stage state. No derivative evaluation at a substituted initial state is used.

WaterState, WaterReference and WaterImplementation are explicit data-only allowlist members. The actual saved four-cell phase-equilibrium projection is preserved in exact-record-native-equilibrium.json with source file SHA/pointer in NATIVE_INPUT.json. Apply that fixture beside the portable test. Its roundtrip includes the actual liquid WaterState and backend descriptor and requires no EOS.

Whole-prefix mechanical presence, exact six-gate value types and committed correction indices/raw-writeback values are associated. The prior review-red contains four genuine negative tests that failed before these fixes, plus a test setup failure because the constant exact-zero fixture has no correction. The replacement correction test explicitly injects a wrong-cell saved correction and updates the count, then asserts the specific association refusal; it is not a physical correction example.

## Original numeric-policy compatibility fix

Latest source `18fc962896b26a786620880e6190b882358af001f215fa602a50eea96b85118f`; portable test `e5c0993d2625b0e87c72650e6f79e568ef60243b697a72cfb01d14ea5efb8bbe`. tests10: 19 passed in 12.03 seconds.

The formal two-cell case stores energy_scale_j as integer 1, accepted without conversion by IntegrationPolicy. integer-red preserves its original codec refusal. Float annotations now accept exact Python int or float, never bool, matching the existing numeric-input contract while preserving source representation. Explicit time/counter/index/six-gate rules are unchanged. Apply exact-record-integer-policy-case.json beside the test; INTEGER_POLICY_INPUT.json records the actual source path and SHA. No original case or physical/numerical gate changed.
