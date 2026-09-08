# Local Chinese research UI

Baseline `1c98e4c`. Added installed static Chinese UI and `local_app` loopback HTTP
boundary over the SAME case validator, job supervisor, replay/resume and trace
services. CLI `ui` takes explicit operator paths; the browser cannot choose
arbitrary files or commands. Source access requires a valid run manifest and
post-read hash. Host/Origin/token and bounded JSON requests are enforced.

## Actual validation

- 22 HTTP tests pass2.65s. Installed101 related tests pass5.65s, no skips.
  Initial restricted-sandbox attempt failed22 fixtures at127.0.0.1 bind; original
  errors retained. Approved loopback-only execution then passed.
- 52 actual installed Python modules match source before/after. Three installed
  UI assets checked; successive visual/export revisions are retained separately.
- Actual in-app browser: grid edit/validation, rejection of falsely admitted
  material, real run, replay, source-file opening, temperature endpoints, two-run
  comparison, separate spatial legend, keyboard focus after polling, immediate
  cancel, timeout display, accepted-prefix cancel/resume, report generation and
  switching away from an old report were exercised.
- Native UI jobs (supervisor elapsed wall):
  - `57b07404…`: completed2steps16.061144875s.
  - `db4bf733…`: replay completed2steps15.939939125s.
  - `dc8d9d35…`: additional run completed2steps15.941877791s.
  - `96de4274…`: immediate cancel2.726554875s, zero accepted steps.
  - `456c35e3…`: timed_out0.239611333s, zero accepted steps; work0.05/grace5.
  - `87cf4ccf…`: refinement1 cancelled12.662678958s, one accepted step.
  - `e3d0296e…`: resume completed4cumulative steps21.646842334s.
- All seven child processes are reaped/terminal. Original independent exact
  ledger oracle passes all five accepted trajectories. Run/replay N/E, ledgers,
  times, initial/final snapshots exactly match. Resume preserves parent prefix
  and original policy, debits step allowance, and passes service cumulative audit.
- Final raw report read from the displayed textarea equals the ENTIRE saved
  result and manifest under Python's exact integer JSON parsing.

## Failures discovered and retained

Initial static review found stale provenance on new selection, delayed artifact
responses, mismatched spatial legend and lost keyboard focus during refresh.
All were fixed and reviewed. Browser observation then found indistinguishable
four-significant-digit energy labels; eight digits now distinguish the plotted
values. Original assets/reviews remain in evidence.

The browser did not confirm a Blob download event within10s. The UI now says
report generated/download requested and also exposes the report as selectable
text. Successful download is NOT claimed on this platform. Actual selectable
report content is verified; it is a report, not a full standalone replay bundle.

Independent export comparison discovered JSON.parse/stringify rounding exact
ledger integers beyond2**53. Original run files were unaffected. Export now takes
response.text directly to the textarea/Blob. Two Node VM handler tests pass on
final source and installed asset; the old script gives one expected failure/one
pass. The initial minimal DOM fixture lacked replaceChildren (one fixture error)
and was repaired; all raw failures are preserved. A browser tool read truncated
an earlier206317-character report; that partial read is explicitly named
browser-export-tool-truncated.txt, not treated as the full report. Final raw
150850-character report was read in three bounded DOM text chunks and compared.

Two intended delayed actions arrived after short runs had already completed;
one created the additional completed run above. They do not prove busy refusal
or cancellation. Immediate cancellation and the separately preregistered12s
refinement1 cancellation subsequently exercised the actual paths. The HTTP test
suite independently verifies busy refusal.

Full-page stitched/early-scroll screenshots showed capture artifacts; retained
viewport and settled plot screenshots establish the actual layout. Browser DOM
and saved numerical evidence, not screenshot pixels, establish result values.

## Limits and next work

Only the current manufactured wet case is selectable/editable. Full furnace
program editing, admitted real-sludge material selection and full-cycle plots
remain incomplete. T/P show only saved initial/final points; no intermediate
thermal history is manufactured. N/E plot accepted states; spatial coordinates
are cell indices. Different cell extensive quantities are not normalized into
an invented comparison. There is no product-quality or optimizer ranking.

The server is local-only, one owned job at a time, default20 history cap. It does
not provide a watchdog after supervisor death. Direct Ctrl-C performs close
cleanup but currently propagates KeyboardInterrupt with a nonzero CLI exit;
this cosmetic exit behavior is not claimed fixed. All four browser test server
handles40104/23725/57004/76677 were stopped. No public deployment occurred.

Full Goal stays active: raw-sludge material closure, free sintering/cooling,
three public mechanisms/held-out validation and multigeneration experiments are
mandatory unfinished work. Next add bounded experiment definitions/comparison
using the same services and explicit evidence admission, while retaining the
material-domain gaps rather than ranking fixtures as real bricks.

See [CLI guide](../../CLI.md). Archive includes source/tests, raw logs/XML,
original/final assets, browser observations, all scientific run bundles, reviews
and independent verifier. Every archive member is reopened/hash/length checked.
