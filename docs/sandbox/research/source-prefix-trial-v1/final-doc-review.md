# Source prefix trial final documentation/evidence review

Disposition: **APPROVE**. Read-only narrow factual review completed. Numerical results, version scope, hashes, archive contents, and new local links match the preserved evidence. The parent applied the minor replay-scope wording correction, and both edited paragraphs were reread and confirmed. No unresolved factual/scope blocker, production-code issue, or new test work remains.

Verified directly from retained files:

- All six source/test/fixture byte sizes and SHA values match `source-freeze.json`, including final trial source `d092a37fe69be5e5cae968f7c7967233ea8cdd4837428bf6236ddbed3c204b99` and helper `d65b6844141ff73f4ad23cee5950e4548062646072195b862e8bfb5125af4409`.
- All XML entries in `archive.json` match their actual count/status/time fields. Source tests are 143/0/0/0 at 55.587 seconds; installed tests are 143/0/0/0 at 47.693 seconds. Installation identity records 119 Python modules and 126 matching source-package files.
- Native result is 3538988 bytes, SHA `7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505`. Actual nested trial status is `validated_positive_numerical_trial`, reason None, 11 captures, 81.12517700000899 trial seconds, and direct discrepancy 0.001086768806259706. Top-level wall time is 82.73211950005498 seconds, with original 210-second/32-callback limits and material_qualified false.
- Native summary/audit agree on 8 reference evaluations, 1 accepted reference step, 0 rejections, and 235 independent saved-data checks. Reported U/water changes, reference residuals and reference estimator match the retained audit. The pressure-bound and coefficient-reconstruction limitations are stated explicitly.
- Independent evidence matches the report: 46 code tests, 5 final runner tests, 25 independent Python cases, and 56 manufactured-water checks. Their roles remain distinct from the one native run and from real-material validation.
- Archive has 103 members, 501670 bytes, SHA `551232c83d4358834d2d65693e33e2d8581406696cb55c84000c3def04de0697`. Every member was independently reopened and compared to the preserved raw file: zero mismatches.
- Checked the newly added links in all six central documents and all Markdown links in the new evidence directory: 12 checked, zero unresolved local targets.

Minor wording note sent to parent: WORLD_SPEC's “失败调用和原参考恢复序列均可被动重放” and ACCEPTANCE_MATRIX's “保存/被动重放失败及恢复序列” should explicitly limit passive replay to recoverable DomainExit/retry sequences inside a completed reference. All actual failures are retained and structurally checked, but terminal/unrecoverable failures are not generically replayed. REPORT.md already gives this correct scope. Suggested replacement: “保存全部失败，并被动重放成功参考中的 DomainExit 拒步/恢复序列”.

Resolved: both current central-document paragraphs now explicitly say they save all failures and replay only DomainExit rejection/recovery sequences within a successful reference. Their existing links remain unchanged.

No unsupported full-material, event-time, dry/rewetting, production, or full-Goal completion claim was found. Remaining event/pressure-propagation/material/full-cycle/public-validation/application work stays explicitly unfinished. No tests, EOS, native run, source edits, central documentation edits, or frozen raw-archive writes were performed in this review.
