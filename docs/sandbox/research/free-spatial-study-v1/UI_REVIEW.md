# Eight-cell UI candidate independent review

Disposition: APPROVE for the bounded candidate diff. No critical/high findings or application blockers identified.

Scope established from local Git diff (clean at inspection) and explicit diff of candidate app.js against current source assets/app.js. Candidate grid_test.cjs inspected. No index.html candidate exists or is needed for this approach: its initial 2/4 options are replaced after validated configuration loads. This is a local candidate review, not a PR; merge readiness/CI metadata was unavailable and not verified.

Behavior reviewed:
- Exact free model ID enables 2/4/8, exact prescribed model ID enables only 2/4, and unknown model IDs throw.
- fillControls validates numeric grid cells and creates supported options before assigning the selected value, avoiding the real-select empty-value bug for 8.
- controlsToCase validates model/cells before modifying active case. Empty select values become 0 temporarily but are rejected before mutation or submission.
- JSON apply retains its authoritative /validate request before accepting caseData and filling controls. Backend refusal of unknown model/unsupported cells therefore preserves the prior active case. The client assumes a successful backend validation is truthful; local fillControls alone is not a transactional substitute for backend validation.
- No model ID, parent cells, or other hidden physics settings are changed. Existing profile/transport/refinement behavior is retained.
- DOM option values/text are generated from fixed numeric allowlists. No injection or async regression introduced by this diff. Export, trace, and rendering code are unchanged.

Checks run against candidate app.js:
- node --check passed.
- grid_test.cjs: 3/3 passed, including realistic select value semantics, free eight-cell roundtrip, legacy option restoration, and unsupported-value rejection before mutation.
- Existing mechanical tests: 4/4 passed.
- Existing lossless export tests: 2/2 passed.
- Previously persisted actual trace-handler tests: 2/2 passed.
- JavaScript-only scope: TypeScript check not applicable. No project package/ESLint setup or eslint executable was available from prior same-workspace inspection; lint not run. No installation performed.

Nonblocking coverage limit: grid tests call fillControls/controlsToCase directly rather than driving /config startup or asynchronous Apply JSON. They prove the new select mechanics; validation failure preservation remains supported by inspection of unchanged authoritative apply ordering. Tests use small representative cases rather than the full physical case payload. No browser or native solver was used. Backend eight-cell support must be applied/validated together with this UI change.

SHA-256:
- candidate app.js: 6a7eb1db2cdad751d1b87d645a95f81ea5ae9bfd02730c48edd16b666bec68a3
- candidate grid_test.cjs: cac96122c3f0cd0277f1b623130642c5fe67a6b8e136ae0d57a700f0cf837e9f
- source app.js at review: 24951fe1f9c45ea20a025e2185faa7c05547273eb9b0cfdb5703c7fe7fe63040

Reviewer modified only this temporary report; repository assets/native service were untouched.
