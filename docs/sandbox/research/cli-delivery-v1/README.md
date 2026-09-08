# Unified case/CLI delivery evidence

Baseline: `5163060`. New code adds an independent installed manufactured case
builder and shared Python/CLI service; the physical solver is unchanged.

- 25 installed application tests: no failures/errors/skips, XML 0.212 seconds.
- 47 actual installed Python modules match repository bytes before and after.
- Installed CLI run: completed, 2 steps, process 15.520782833 seconds.
- Installed CLI replay: completed, 2 steps, process 15.459735084 seconds.
- Every numerical integration field (except timing), initial/final diagnostic,
  initialization and policy equals the original run exactly.
- Saved ledger audit uses the retained independent two-cell arithmetic oracle
  unchanged. Local inventory residual at most 9.8811e-17 mol; energy at most
  1.7086e-11 J. Original thresholds were not changed.
- All four supported result queries inspected; console `validate` actually ran.
- Four-cell builder freshly constructs its two-cell parent, conservatively
  prolongs inventories/energy and checks the decoded initial temperatures.
  Initial callback completed in 4.083172666 seconds. No four-cell trajectory was
  run through this new service in this phase.

Native processes were serial and externally bounded at 150 seconds; case
integration wall policy is 120 seconds. None remains live. Native source/install
files were held fixed during runs. The final three application tests extend
SIGINT/malformed-manifest coverage without production edits.

`original-evidence.zip` includes exact saved runs, their frozen source/water
inputs and local manifests, process reports, scripts, XML, source identity,
independent ledger inputs/results, trace JSON, four-cell initialization, and
review notes. `manifest.json` records each ZIP member hash and size; the archive
was reopened and all members verified after writing. The archive is local
integrity evidence, not a signature or independent material validation.

Reproduction: see [CLI guide](../../CLI.md). The saved implementation is never
executed by replay; the actual installed implementation must match. The approved
native water manifest remains platform-specific. No claim of cross-platform
clean-environment delivery, complete equation provenance graph, real raw-sludge
material admission, free sintering/cooling, full-cycle operation, or completed
Goal is made. Earlier 1293 solver tests remain evidence for their own baseline;
they were not rerun as an application-only ritual.
