# Accepted-prefix cancellation/resume

Baseline `7110752`. New application/checkpoint code preserves the physical solver
and original case. Public `resume` accepts a cancelled ordinary integration with
an interior accepted step; it does not restart from initial inventories.

Evidence:

- 50 installed tests pass, zero failures/errors/skips; XML retained.
- 49 actual installed modules match source bytes before and after native work.
- First cancellation retains1 panel, process9.879597792s.
- Resume and second cancellation retains2 cumulative panels, process9.912309584s.
- CLI resume completes4 cumulative panels, process15.641943167s.
- Uninterrupted reference completes4 panels, process27.051292875s.
- All saved inventories/energies and ledgers exactly equal reference; final
 temperature/pressure differences are zero in this registered fixed-cap case.
- Original independent per-prefix ledger oracle passes for all four saved runs.
- Cumulative integration wall26.825257790s, original allowance120s; suffix budgets
 debit complete original history. Each native process also had150s external cap.

`PLAN.json` in the archive predates native results and specifies the refinement1
case, order, triggers and comparison thresholds. Original physical values were
unchanged. Parent result/manifest bytes and hashes survive in new outputs; original
input/source/live energy identity is checked before suffix evaluation. Raw suffix
is saved before original-initial cumulative N/E/component-roundoff auditing and
admission. Two exact arithmetic counterexamples show that locally small errors
cannot reset the total allowance on a restart. Initial test-trigger failures and
the precise fix are retained, not relabelled as successful solver runs.

`original-evidence.zip` contains the native run artifacts, provenance/source
packages, original and final tests, failure/success XML, scripts, PLAN, audit and
review. Every member was reopened and hash/length verified against `manifest.json`.
No native process remains live.

This verifies cooperative ordinary-integrator restart in the manufactured wet
model. It does not certify general adaptive bitwise equivalence, hard-kill
recovery, depletion-event checkpoints, raw-sludge material validity or full-cycle
Goal completion. See [CLI guide](../../CLI.md) for supported commands and limits.
