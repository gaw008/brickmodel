# Whole-service process supervision

Baseline `7401e13`. Added synchronous `job_supervisor` and fixed `job_child` plus
CLI `supervise`, `job-status`, `cancel-job`. Physical kernels/case unchanged.

The owning Popen is the only signal target. Whole-child work time includes
imports, build, integration and diagnostics; SIGINT starts a grace interval,
then SIGKILL+wait if necessary. Actual completed output requires exit0 and a
manifest-verified completed run. Status, logs and resource observations are
separate from the run's frozen scientific artifacts.

## Executed evidence

- 79 selected source tests pass2.95s; same79 installed tests pass2.97s, no skips.
- 51 actual installed modules match source bytes before/after native work.
- Actual installed CLI run: completed2panels, outer15.728251667s.
- Frozen replay: completed2panels, outer15.744784333s; all saved N/E, ledgers,
  times and initial/final T/P diagnostics exactly equal first run.
- Actual CLI cancel request at10s: cancelled outer10.844923917s, one accepted
  panel retained, sealed result; child exit1/reaped, no hardkill.
- Startup timeout work0.05s+grace0.1s: timed_out, child-9/reaped; observed whole
  experiment0.269836250s and supervisor0.169675333s. Missing metrics=unknown.
- Unchanged independent exact ledger oracle passes completed/replayed/cancelled.
- Actual short process tests also cover lock contention, inherited lock after
  owner death, eventual lock release, corrupt results, abnormal child exits,
  callback/startup failures and cleanup. These fixtures perform no EOS work.
- Completed child CPU user15.350372s/system0.150377s; native ru_maxrss178307072 on
  darwin. Native RSS units remain explicitly unnormalized, not asserted as bytes.

## Review and protocol limitation

Independent agent code review approved product supervisor/child/CLI. Experiment
review identified an outer-runner discrepancy: original native.py used150s for
the timeout trial's emergency wait although PLAN specified10s. Measured completion
was under10s, and inner product deadline was enforced; the10s outer emergency
bound was not implemented in that trial. The executed script, original plan,
PROTOCOL_DEVIATION.md and review are all retained. No repeat or retroactive plan
change is used to hide the discrepancy.

The initial aggregate verifier omitted asserting noncompletion outcomes (the
per-trial runner did assert them). Final verifier now requires all four reports,
expected statuses, exits, reaping and measured bounds; original verifier retained.
Outer experiment emergency cleanup only owns its supervisor; that branch was not
entered. Missing report after a runner exception means incomplete evidence.

## Scope and continuation

POSIX flock scope is one active child per resolved job-parent directory, not
machine-wide. Inherited lock survives parent death; no independent watchdog
survives that death. Work+grace is subject to OS polling/reaping scheduling.
CPU/RSS cover child RUSAGE_SELF, no descendant sum, no memory hard limit.
Saved status is observation only; a cancel command acknowledges a UUID-bound
request, not confirmed termination. Hardkill does not ensure a sealed checkpoint.

All four native processes are terminal. Next implement a light local Chinese UI
using the same validation/run/trace/job services, expose cancellation and known
source/material gaps without claiming live status from old PIDs. Raw-sludge
material closure, free sintering/cooling, public three-mechanism and held-out
validation, multigeneration search and full-cycle delivery remain mandatory
unfinished Goal work. This process phase does not establish those outcomes.

`original-evidence.zip` contains original logs/results/source snapshots/tests,
PLAN, original/final verifier, unchanged ledger oracle, review and installation
checks. Archive members are reopened and SHA/length checked in manifest.json.
