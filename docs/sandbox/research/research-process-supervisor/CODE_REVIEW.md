# Independent Python supervisor review

Reviewed 2026-09-07. **WARNING / cancellation repair pending** for the audited source below. No CRITICAL/HIGH issue found for trusted local research commands; one reproducible MEDIUM cancellation issue should be resolved before relying on supervisor cancellation to stop an EOS experiment.

Audited supervisor SHA-256: c9c27179d16053ede75bf94b26b861901c0946624d81ba07be648ceb49a9a639.
Audited tests SHA-256: 931f99c435cc8e07f6cbc148f142fade40bec05e1d00b7f9f73d3d86ae65316f.
All seven original manifest bindings passed. This file and independent review XML are additive; original evidence was not rewritten.

## Actual validation

`git diff -- '*.py'` was empty. Ran the actual isolated test suite with the project's Python, PYTHONDONTWRITEBYTECODE=1 and an isolated cache: **12 passed in 0.47 s**, exit 0; result is review-tests.xml. No EOS import/evaluation, benchmark, production edit or dependency installation occurred. Static tools were unavailable in prior same-session executable checks.

Also ran two bounded standard-library-only process observations, under `/private/tmp/independent-supervisor-4033don2/`:

1. A leader spawned a sleeping descendant and exited zero. run_attempt returned complete; the descendant was no longer present after cleanup. This independently exercises the leader-already-exited case missing from the initial suite.
2. A separate supervisor process launched a sleeping child in its own session; after the child printed its PID, the reviewer sent SIGTERM to the supervisor. Supervisor exited -15, child remained alive and status.json remained running. The review's finally block explicitly SIGKILLed the child's process group; no test workload was intentionally left running.

Both extra observations together completed in about .061 s. The tests/observations are well below the authorized ten-second execution budget.

## Finding

[MEDIUM] SIGTERM to the supervisor bypasses cleanup and leaves the independent child running
File: supervisor.py:94-104
Issue: The default SIGTERM action terminates the supervising Python process without executing its finally blocks. Because Popen uses start_new_session=True, its research child does not receive the same group cancellation and continues after the supervisor's timeout machinery has disappeared. The saved running status correctly avoids false success, but does not stop work. README acknowledges abrupt supervisor death without making this ordinary cancellation outcome explicit.
Fix: Install a temporary, restored SIGTERM handler for supported main-thread invocation that unwinds through cleanup and persists a failed/cancelled terminal status. Define behavior outside the main thread and preserve existing handlers. Add a real subprocess cancellation test and retain the leader-exits-with-descendant regression. SIGKILL/host crash and escaped sessions necessarily remain outside this guarantee. Coordinate with the author; this review did not modify source.

The finding was sent to Root for forwarding after direct author messaging returned an agent thread limit error. This report does not imply the repair has occurred.

## Remaining code assessment and boundaries

- Timeout uses an external parent wait and TERM/KILL of the original group, then bounded direct-leader reap. The actual TERM-ignoring child/leader test passes. Group cleanup runs even on ordinary leader completion; direct log files avoid communicate/pipe-drain waits. Reaping grandchildren depends on the OS; success records leader_reaped rather than proving all descendants exited. Deliberate setsid escapes, uninterruptible tasks and hostile process containment remain expressly excluded.
- Ordinary Python exceptions in wait unwind through cleanup; KeyboardInterrupt/SystemExit are recorded as failure and re-raised after finally. SIGTERM is the demonstrated missing path. A second abrupt signal or OS shutdown can still interrupt cleanup/publication.
- Exclusive directory creation rejects collisions before writing previous artifacts. Atomic JSON uses a newly created temporary file, fsync and replacement. The storage-failure test correctly leaves canonical status running while a pending temporary file says complete; consumers must ignore temporary files. Directory power-loss durability is not claimed. The attempt name is caller-selected, not a generated UUID; callers must choose a unique directory.
- No shell is used; argv validation excludes scalar strings, empty values and NUL. cwd and declared inputs resolve before launch. This is a trusted-command API, not an untrusted path sandbox. Declared hashes are before/after observations with potential concurrent mutation/restore windows; undeclared executable/import dependencies are not attested. README correctly requires callers to declare needed dependencies.
- metadata.json stores argv, cwd and full resolved input paths verbatim; stdout/stderr and exception strings are also retained verbatim. No secrets were present in these tests. README should explicitly tell callers not to supply credentials in argv and that child logs are not redacted. This runner is not suitable for secret-bearing arbitrary commands without an explicit logging policy.
- Time budget applies to process waiting, followed by cleanup. Input hashing, launch, file I/O, final hashing and OS scheduling are outside a strict wall deadline. File output lacks a disk quota. These are acceptable documented limitations for a small trusted bounded research experiment, not general resource isolation.
- The initial descendant-reaping observation can be platform-sensitive: kill(pid,0) also sees zombies, despite the test comment. Its .5-second disappearance assertion passed on this macOS run; it is not a portable guarantee about orphan reaping speed.

Approval is limited to the demonstrated trusted no-EOS execution cases. It does not approve an EOS experiment, scientific outcome, full process-tree isolation or a production deployment.

## Final independent repair review

The initial WARNING above and intermediate failing revision are retained as history. **Final verdict: APPROVE the narrowly scoped trusted main-thread research supervisor; no unresolved CRITICAL/HIGH/MEDIUM issue from this audit.** This is not experiment or production approval.

Final supervisor SHA-256: `939a86f4a8a45a127e49c18009c8fc9f7bd296d79243741bf3f3d2e6fb2f36d1`. Independent added regression source SHA-256: `8615b7e391eddc6d0fe95ddd33a21048574a8ecaeaf2d7c57983ebf695982066`.

Root repaired TERM ownership by deferring signals during spawn and cleanup, restoring the original handler, rejecting non-main-thread invocation, and propagating SupervisorTerminated after saving failure. Signals received before actual Popen creation no longer install SIG_IGN for the upcoming child. No pthread signal mask is used. Cleanup now reaps the leader promptly and still escalates the original group after the leader exits; signaling errors remain in cleanup diagnostics and preclude complete status. This avoids the observed sandbox EPERM from probing a zombie group with killpg(pid,0).

Actual independent combined suite: **17 passed in 1.38 s**, exit 0, saved as review-fixed-final-tests.log/XML. It includes the original 12 tests plus before/after-Popen TERM injection, first TERM during cleanup, caller-handler restoration on invalid input and worker-thread rejection. The intermediate 3 failed/14 passed run remains in review-term-fix-red/.

Reran the retained real-process observation body: leader-exits-with-descendant still cleans successfully; SIGTERM to the supervising process now yields parent exit **1**, child no longer alive, canonical status **failed**. stdout/stderr retained in review-fixed-final-process.log/.stderr; attempt artifacts are `/private/tmp/independent-supervisor-guvhw463/`. The traceback is expected cancellation propagation, not a missing cleanup. This observation completed in about .300 s. All review tests remain below the authorized 10 s aggregate execution budget and used no EOS.

Remaining limits are unchanged: SIGKILL/host failure, escaped sessions, uninterruptible tasks, durable power-loss recovery, secret-bearing logs and undeclared/mutable dependencies are not covered. A canonical running status is never success. README may be updated by Root to reflect this final evidence; no candidate source was changed by this reviewer.
