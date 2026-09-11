# Preregistered single RHS comparison

This is a new implementation diagnostic, not a source trajectory resume. Do not
re-run the old parent, initial-U work or failed ordinary segment. Original
native01/native02 failures and all their actual work remain preserved.

Run once, after frozen installed regression and independent code/manifest
review, with the installed interpreter:

`python -I -m sludge_sandbox.source_managed_worker managed-request.json`

The supervisor uses the existing run_attempt, timeout 120 s and cleanup grace
1 s. Its 120 s covers child startup/imports through output publication. The
worker's own deadline starts at _execute_request entry, after top-level imports;
it is checked after reconstruction and around/inside the RHS. Required profile
and result publication remain covered by the external supervisor deadline.
The workload includes source admission, four real provider constructions, one
RHS, integrity validation, and required output publication.
It performs no initial-U evaluation, wet-pair collector request, integration,
accepted step, automatic retry or checkpoint construction. Original source
configuration numerical limits and physical inputs are unchanged. Its new
profile and single manifest row explicitly select the new implementation.

`managed-request.json` takes all 3x4 N, 3 U, interface modes and the normalized
exact time directly from rhs01/segment/events/000014.json. All float values must
roundtrip with identical binary64 hex. The original event SHA identifies this
input, not an authorization to resume it under a new runtime. Rebuild states
through storage.state and adapter.pack, assigning the actual new energy model
identity. Retain both complete old and new identities.

Pre-execution inputs: IMPLEMENTATION_FREEZE.json, INSTALLED_IDENTITY.json, this
plan, launch_managed.py, request, source case and all 17 assets. The supervisor
also watches every installed/source Python module. Input mutation invalidates
the run. Do not edit them while it is live.

Acceptance of this diagnostic requires worker and supervisor exit 0, exactly
4 HEOS starts/kernel returns/full returns, 1 RHS start/return, 0 initial-U/wet
queries, 0 accepted steps, closed worker admission with exactly one verified
RHS, and all 4 kernels verified at entry and exit. Capture the actual point count
without treating this single observed count as a universal resource limit.

Compare the complete raw returned semantic graph to rhs01's actual return.
Every physical number, Fraction, array, response residual, branch, diagnostic,
model policy, inventory and qualifier must remain exactly equal. Enumerate each
changed metadata value explicitly: execution phase; wrapper/native descriptor
and their dependent implementation hashes; the new source config SHA bound by
the manufactured liquid relation; dependent storage/operator/energy identities.
Review that finite mapping, including nested canonical descriptors. Never drop
all hash or identity fields or declare full raw bytes equal across versions.
Unexpected differences fail the comparison and remain recorded.

Profile the same actual RHS region with cProfile, including its new scope and
journaling costs. Report raw total/admission/RHS and transaction/getter counts.
No promised speed factor or post-hoc numeric tolerance. Reduction is meaningful
only after the complete equality check; it does not prove full ordinary
continuation, a full brick cycle, material applicability or external validation.
