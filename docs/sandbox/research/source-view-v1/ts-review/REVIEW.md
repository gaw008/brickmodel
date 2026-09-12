# Source view v1 independent JavaScript review

Verdict: **WARNING — 2 MEDIUM issues; no CRITICAL or HIGH findings.** This is a local unstaged-change review, not PR approval, physical validation, or browser acceptance. Production files were not edited.

## Scope and tooling

Scope was established using `git status --short`, `git diff --staged --stat`, `git diff --stat`, and the actual unstaged JavaScript/HTML/CSS patch. HEAD was `48568d3ba88f33368ce85d8f5809e3ede3335565`. There was no staged patch. The source-view assets are additions to the existing plain JavaScript local application; surrounding legacy handlers, `source_run_view.py`, `source_study_service.py`, and `local_app.py` were read for the actual response contract.

PR merge readiness and CI were not verified: no PR was supplied and this scope is local WIP. No repository `package.json`, TypeScript configuration, or ESLint configuration was found, and `eslint` is not available on PATH. Type checking is intentionally skipped for this JavaScript-only change; no dependency installation or lint-success claim was made. `node --check src/sludge_sandbox/assets/app.js` passed with Node v24.14.1. `git diff --check` for the three reviewed assets passed.

Reviewed bytes matched `docs/sandbox/research/source-view-v1/AUTHOR_READY.json` at review time:

| File | SHA-256 |
| --- | --- |
| `src/sludge_sandbox/assets/app.js` | `e5e6aa599078f28d1be6521fe691f88d26adb11e4b7ec1871df2c7859dec7b56` |
| `src/sludge_sandbox/assets/index.html` | `7099fda70114096c025c6d5c142486811314e27993ee4f3b0beef36ec9be8140` |
| `src/sludge_sandbox/assets/app.css` | `7b89fe0cac31ec2afcc25ff4796352b7fe17059826ef7ceb630771b2b04ec12e` |
| `src/sludge_sandbox/source_run_view.py` | `5896dc849aa2388d5cedbfdd3cab60c1ae524367b5ea89083608f10f31fe8dce` |
| `src/sludge_sandbox/local_app.py` | `94b77a18b8de84ded23dfcadc3c210a5b2da6899f2ebc4b42799365745c1b7a4` |
| `docs/sandbox/research/source-view-v1/AUTHOR_READY.json` | `e6bbab8bdcebe605b8ceb774206693cefc4440e8ecffb6ec185d45c6dbb354ca` |

## Findings

### MEDIUM — Failed revalidation leaves the prior verified summary unmarked

Location: `app.js:283–288`, with retained fields established at `app.js:229–236` and only partially cleared at `app.js:222–226`.

Reproduction: render a successful source response, click “重新校验记录”, and let that request reject with `artifact_hash_mismatch:assets/fixture-source.txt`. The generic message displays the mismatch and the observation rows are cleared, but `sourceData`, `source-status`, and `source-summary` remain the earlier values. The summary still reports `artifact_hashes_verified: true` and the earlier record SHA without identifying them as an old snapshot. The old asset selector and controls also remain available.

The response is not physically requalified and the error is visible, so this is a presentation/freshness issue rather than silent acceptance. Nevertheless, this interface is explicitly used to assess provenance: after the latest verification fails, the prior successful statement needs an explicit “last successful snapshot; current verification failed” label, or the verified presentation/state should be cleared. The existing numerical failure identity must not be rewritten while doing so.

`VM_RESULTS.json` records `summaryStillVerified: true`, `oldDataRetained: true`, and zero remaining observation rows after the mismatch.

### MEDIUM — Obsolete request errors bypass the generation guard

Location: `app.js:286–290`; the same pattern exists for source-asset requests at `app.js:301–304`.

Successful responses are guarded by `sourceSequence` / `sourceAssetSequence`, but a rejection exits before that comparison and reaches the shared `handle` catch (`app.js:16`). Reproduction: start source refresh A, then select capture 2 with request B; allow B to return successfully, then return an error for A. The selected capture correctly remains 2, but A replaces the current message with `OLD_REQUEST_ERROR`. With a historical hash mismatch, this falsely associates an obsolete verification failure with the current successful display.

Handle both success and failure inside the request-generation boundary. Only a failure belonging to the current generation should alter current UI state or notifications. If `loadSource` returns a completion flag or other status, callers should also gate their completion messages so a discarded request cannot claim to have refreshed the currently displayed selection. Apply the same error guard to asset requests when the asset or selected capture changes.

## Independent execution evidence

`review_vm.cjs` runs the actual reviewed `app.js` in a Node VM with a deliberately minimal manufactured DOM, deferred fetch promises, and manufactured source responses. It does not start a browser, server, Python provider, EOS, native integration, or restoration. The fixture is presentation data, not a source material or physical run. It is an async/DOM logic check, not an E2E or accessibility substitute.

All six positive checks passed:

1. Exact numerator `1208925819614629174706195` and denominator `3` remain strings in the rendered clock; unknown error bounds stay unknown; trial identity is explicit and no source chart points are drawn.
2. Failed/no-saved-return selection removes previous physical rows and retains failure identity.
3. An older successful study response cannot replace the later selected capture.
4. A late successful asset response cannot replace a newer capture's cleared asset panel.
5. Raw export text and the resulting Blob preserve unsafe numeric JSON literals and UTF-8 text without JSON parsing/stringifying in the browser.
6. View-only startup makes only the config and source GET requests, schedules no polling timer, and hides legacy case/trajectory controls.

The first check also supplies `<img src=x onerror=...>` as source metadata. It remains `textContent`; the fake DOM deliberately throws on `innerHTML`. Static inspection found no added `innerHTML`, dynamic JavaScript execution, user-controlled URL navigation, or browser-supplied filesystem path. Source assets use opaque IDs and plain text. Backend authentication/traversal/concurrency/limit validation and real browser behavior remain separate reviews.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `review_vm.cjs` | `9b26621795131d969491f8f1bed0cf21c8b2c84de01efc8bc508c57a2462d5da` |
| `VM_RESULTS.json` | `d5cf27e1828b3a3dda602beb32d01753cb61597efc0f4f639fb24ad425f2781c` |

Both negative observations are reproduced and asserted in the same harness; their reproduction is not counted as a product pass. No current scientific, material, training, or full-cycle qualification is upgraded by this review.
