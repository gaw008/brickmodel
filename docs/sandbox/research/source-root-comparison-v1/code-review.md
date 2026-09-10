# Independent source root/common-endpoint review

Verdict: APPROVE for the reviewed bytes; no confirmed production defect remains.

Scope: baseline b7466e3, new source_root_comparison.py and its author tests, plus the existing trial/approach/endpoint/pressure interfaces needed to assess integration. Production was read only. No native EOS, installation, whole suite, or Git mutation was performed.

The implementation compares exact absolute root intervals using the maximum cross-endpoint distance and each panel's remaining original refinement budget. It binds the shifted seed to the actual approach reference endpoint, then compares two freshly evaluated reference endpoints at a common positive time. Joined fine-path N/U residuals are accumulated from the original state for every accepted ledger prefix. Saved checks use retained source observations and passive reference replay; no separate integrator or event controller is introduced. Root-time, reported endpoint, conditional pressure and event/material qualification stay distinct.

The maximum-step question was resolved explicitly: maximum_step_s constrains each original integrate_exact reference step; a complete coarse SourcePrefixTrial can cover multiple such steps, and its complete affine prefix must still meet the original direct discrepancy. This is supported by a bounded actual manufactured regression, not a tolerance change. The only new run controls changed were initial/max step = original H/16. Its 2.3443898872767783 s coarse span was accepted in two reference steps, each <= 1.1721949436383892 s. Both common trials retained D <= 1. N/U/T gates were true, reported and conditional pressure gates false; no event/material qualification. The probe completed in 12.367788875 s with 47 source callbacks, below the explicit 48-call/30 s soft bounds. A subsequent common.check took 0.215812167 s and made zero additional source calls. Full trial evidence, policies and step durations are in maximum-step.json; script and console output are retained.

Independent additional tests: 3 passed in 7.83 s (additional02.xml/log). They verify passive final runner imports, helper hashes and complete policy construction, then inject DomainExit and RuntimeError at the second common path's first callback. Both preserve the completed 11-callback coarse reference, the actual one-capture shifted failure, original failure kind/reason, and the shifted_common_trial stage. Their saved checks invoke no further source callbacks. These use the existing manufactured source fixture, not native water EOS. The reviewer's first test collection attempt used the wrong DomainExit import; additional01.xml/log and test_current_review_attempt01.py preserve that reviewer-script error. Only the review script's import was corrected; production was unchanged.

The added strict ExactEventTime.seconds Fraction checks and documented per-reference-step semantics were present in the final reviewed bytes. No repeat of the earlier unchanged 143/135-test suites or native runs was used. This review does not certify material parameters, physical event times, full EOS uncertainty, or a wet/dry transition.

Reviewed SHA-256:

- source_root_comparison.py: b9328c5620d6bf27e6b7cbd75430aaf7a7bba136c7760ad9c6cb6843ba3c1c87
- test_source_root_comparison.py: 6cc7307539273c9ef2f9b374f552bbf66fae1f40827cc28c68d54569d0a84b07

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — no confirmed defects in the bounded review scope.
