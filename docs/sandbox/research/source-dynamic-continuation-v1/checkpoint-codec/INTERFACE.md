# Ordinary checkpoint persistence v1

The two public functions are:

```python
from sludge_sandbox.exact_integration_checkpoint_codec import (
    encode_exact_checkpoint, decode_exact_checkpoint, ExactCheckpointCodecError,
)

raw: bytes = encode_exact_checkpoint(clean_paused.checkpoint)
checkpoint = decode_exact_checkpoint(raw)
```

Decode returns the existing `ExactIntegrationCheckpoint`, with all original
problem, initial state, policy, exact clocks, next h, knot index, component
schema, represented/exact/absolute-roundoff cumulative balances, accepted
states/ledgers, actual callback observations, handled `DomainExit`/`_Reject`
messages, rejection/evaluation/attempt counts, elapsed binary64 and binding.
Only a clean interior accepted-boundary pause is accepted. Arbitrary failed
tails and observer-commit snapshots are not relabelled as resumable checkpoints.

Both entry points run the existing passive `checkpoint.check()` arithmetic
replay. No solver copy, EOS/provider construction, new physical call or live
adapter restoration is introduced. A source service must independently verify
its original configuration/live operator and charge the actual decode and
reconstruction duration through `admission_elapsed_seconds`. Stored wall time is
retained exactly; this codec cannot authenticate historical wall-clock truth.

The outer JSON has exactly `schema`, `validation_scope`,
`source_resume_authorized` (always false), `checkpoint` and `payload_sha256`.
Its schema is `exact_integration_checkpoint_v1`. Class names are resolved only
against nine fixed numerical dataclasses, with explicit version-one field
lists. Original checkpoint binding is neither regenerated nor replaced during
decode. Payload SHA is integrity evidence, not source authentication.

Floats use canonical hex; arrays use fixed little-endian binary64 bytes (including
signed zero/subnormals), exact shape and explicit `<f8`; decoded arrays are
bytes-backed and read-only. Fractions must be reduced with positive denominator.
Mappings use ordered key/value pairs; duplicate keys and constructor-induced
reordering are rejected. Constructors run only for the registered numerical
classes, and every reconstructed field (including init=False diagnostics) must
re-encode identically. The existing checkpoint's runtime binding still applies;
the codec never rewrites a binding to make a different runtime pass admission.

Finite bounds: 32 MiB wire bytes, 300,000 parsed nodes, depth 96, integers up to
4096 bits, individual non-array strings up to 65,536 UTF-8 bytes, 250,000 total
array elements, 4096 callback observations and 256 accepted steps. Live encoding
also uses a conservative 32 MiB size estimate including 128 bytes structural
overhead per value, before JSON serialization or numerical replay. Unsupported
size/shape/type/data is rejected, never truncated. All caps are checked before
passive replay; array count/hex length is checked before ndarray allocation.

Evidence: `FINAL_FREEZE.json`, `final02.xml` and `final02.log`, 50 passed in 1.16 s
(XML 1.158 s), no EOS or installation. The actual initial missing-module RED and
first implementation's explicit NumPy NDArray alias mismatch (18 failures,
15 passes) are preserved in `initial-red.*`, `first01.*` and
`before-numpy-alias.py`. NumPy 2.5 exposes `NDArray` as a `TypeAliasType`; matching
its explicit identity fixed this without broad annotation acceptance. Subsequent
33-test and 46-test passing batches remain in `first02.*` and `final01.*`.

The final tests exercise nonstationary evolution with actual handled rejection,
pause/encode/decode/continue versus all uninterrupted callbacks and ledgers;
passive checks make no operator calls. Independent original N/U/stretch and
absolute-component roundoff traps still reject after persistence. Other tests
cover original step/wall budget, exact large origin, scalar types, mapping
order, signed zero/subnormal bits, malformed JSON, duplicate fields, unknown
classes, nonfinite/oversize arrays, changed derived fields, rehashed h tampering,
failed/nonboundary evidence and resource refusal before replay.

AST parse/compile and Git whitespace checks passed. Ruff, mypy, Black and Pylint
were not available in the existing environment and were not installed. Only the
two newly authorized production/test files were changed; parent source-session
and material-data work was left intact. Independent reviewer was notified with
the frozen source/test hashes.
