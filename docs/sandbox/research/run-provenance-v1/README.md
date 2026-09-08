# Run-bound equation/source graph

Baseline `525142d`; physical solver unchanged. This phase replaces file-only
navigation for new runs with a machine-checkable declared derivation graph for
the supported manufactured wet reacting/prescribed-motion model.

- 19 equation nodes, 38 parameter declarations, 4 output roots.
- Exact case values/JSON pointers, unit/basis/classification metadata, equation
  expressions, code AST line anchors, source positions and missing-source leaves.
- Catalog, implementation and source hashes bind queries to the original run;
  missing files do not become default physical values.
- Installed tests: 40 pass, zero failures/errors/skips. XML records actual time.
- Actual installed Python modules: 48, bytes match source before and after;
  installed JSON catalog separately matches repository bytes.
- Run/replay: both completed, 2 accepted steps each, external process times
  15.557919458 / 15.538707166 seconds. Each had a150-second external bound;
  case integration budget stayed120seconds. Processes ran serially and are terminal.
- All numerical fields except elapsed timing, initial/final snapshots, accepted
  ledgers, and entire provenance graphs agree. Original saved-ledger arithmetic
  checks pass without threshold changes. CLI/Python pressure trace is identical.
- Temperature/pressure traces contain94 ancestor nodes each; amount/energy
  traces91 each. All declared source assets are present in this local run.

The last bullet is **asset availability**, not100% material-parameter provenance,
source applicability, or experimental validation. Textual paper positions remain
explicit read declarations; JSON locations are actually resolved. The model's
manufactured A/B, carrier, transport and skeleton parameters remain manufactured.
Current supported source graph does not close missing raw-sludge chemistry,
free-sintering/cooling, full-cycle validation, checkpoint resume or UI/search.

`original-evidence.zip` retains run/replay inputs, implementation, legal source
assets/notices, graphs, manifests, process records, scripts, tests, XML, traces and
review. The archive was reopened and every member hash/length verified against
`manifest.json`. No saved Python file is executed by application replay.

See [CLI guide](../../CLI.md) for actual commands. Earlier source/runtime records
remain evidence for their own versions; no historical result was relabelled with
the new graph.
