# Complete-graph comparator code review

APPROVE. Read-only static review of frozen `compare_complete.py` SHA `db79a202aa69bb3c74264727d36b778f15d7c6e7e4700c04968349464d282586`, its COMPARISON/REVIEW/final04 outputs and FINAL hash manifest found no blocking defect for these two fixed saved RHS graphs. The comparator was not rerun; no provider, EOS or full graph calculation was repeated.

`differences` traverses both complete event envelopes with exact type, key-set, list-length and list-order checks. Binary64 and Fraction carriers remain raw and are compared without numeric tolerance. `verify_pair` requires the actual differing path set to equal the finite 18-path allowance exactly, and checks both old and new values against the independently derived identities. It neither deletes arbitrary hash/identity fields nor accepts unknown differences. Reachability checks cover every graph node and the raw reference labels/aliasing remain compared.

The sole allowed descriptor-string replacement is independently constrained by reconstructing the old descriptor with the approved wrapper hash and exact new manifest. The manifest reconstruction permits only kernel hash, the three fixed execution-source entries and the named execution contract. All source constants, reference data and numerical limits remain compared. Both case documents are compared with exactly four authorized paths, each manifest asset size/hash/path checked against the retained files. Four independent canonical identity derivations on each side must equal the recorded values before any of their 16 identity occurrences are admitted.

The saved three comparator controls reject a one-ULP physical pressure change, a qualification upgrade and an unapproved energy identity. The numerical equality statement is appropriately limited to one matched RHS. This fixed-file evidence script is not a generic untrusted-input schema validator or a source/material authentication system. No full trajectory or arbitrary transient-setter equivalence is claimed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — frozen comparator and saved comparison scope.
