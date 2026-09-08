# Candidate UI review

Disposition: APPROVE for the bounded UI diff; no critical/high findings or code blockers found.

Scope: direct comparison of candidate app.js and index.html with src/sludge_sandbox/assets equivalents; candidate mechanical_test.cjs and existing tests/sandbox/ui_export_test.cjs. Repository staged/unstaged changes were inspected first and contain Python changes outside this review. This is a local candidate review, not a PR; merge readiness/CI was not available and was not verified. Source assets were not edited. No native process, service, browser, or installation was used.

Validation:
- JavaScript-only scope: TypeScript checking not applicable. No package.json, ESLint configuration, installed local node_modules, or executable eslint was found; lint could not run.
- node --check candidate app.js passed.
- Candidate mechanical tests: 4/4 passed against actual candidate script through Node VM.
- Existing export tests with SANDBOX_UI_SCRIPT pointed at candidate: 2/2 passed. Exact raw JSON integers and late-export job binding remain preserved.
- Additional inline Node VM checks passed for both display quantities: invoking actual trace click handler requests quantity=mechanical_stretches, displays returned full vector and original pointer without projection, and ignores a response after display quantity changes. These are mocked API checks, not backend/browser integration evidence.

Inspection:
- Mechanical series require matching accepted-state/time counts, finite strictly increasing times, stable inventory/energy cell dimensions, and cells+1 finite positive stretch coordinates for every state.
- Normal series use indices 0..cells-1; tangential series use only index cells and mark it global. renderPlots excludes global tangent from spatial data.
- Text output continues using textContent; no new dynamic execution, HTML injection, or user-controlled URL path surface was introduced.
- Existing refresh, trace generation, artifact generation, and export job-binding code remains intact. Trace stale guard correctly retains the display quantity, so switching between two mechanical display modes invalidates a pending request despite their common backend quantity.

Test coverage limitation (nonblocking): committed candidate tests cover actual series construction and renderPlots data routing, but stub draw and test traceQuantity rather than the actual trace handler. Additional reviewer checks above exercise the handler; persisting those tests would better guard future request-wiring regressions. No real SVG/browser rendering was verified. Mixed valid/invalid compared runs silently omit invalid mechanical series while showing the aggregate success note; this is a minor clarity concern, not data fabrication.

SHA-256 reviewed inputs:
- candidate app.js: 24951fe1f9c45ea20a025e2185faa7c05547273eb9b0cfdb5703c7fe7fe63040
- candidate index.html: ca878c874bbb7a838be9549da8487fd176ba20021e67cbab9d0dde2cf3797840
- candidate mechanical_test.cjs: 848b0ebefc2982e89e06e26c66cd112116356fb040230b18e77080981a5f552e
- source app.js: 97d3cb7a3c17825450ecccfcb56dfb03ebad9763402cedbe3f17bcf357206d25
- source index.html: ae372af41da7c3c2f3cade68d78ff74023c660d4aa74867606215f52d6f3f7e1
