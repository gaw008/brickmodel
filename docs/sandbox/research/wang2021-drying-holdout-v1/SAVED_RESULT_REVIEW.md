# Independent saved Wang train/holdout audit

**PASS for saved execution/accounting consistency. The model does not pass readout-bound agreement.** No fit, optimizer, EOS, Midilli evaluation or new curve prediction was run in this review. Source/curvature interpretation remains the other reviewer’s separate scope.

All28 EXECUTION_FREEZE files were independently rehashed unchanged, including source CSV/PDF, numerical code, preregistration and reviews. Every saved prediction was joined one-to-one to its original CSV row, with every original column checked, not just moisture ratio. All12 defined t0 rows are excluded. Exactly117 positive-time40/60°C training points and57 positive-time50°C held-out points are present, no omissions or duplicates. Minutes-to-seconds conversion is exact for all174 rows.

Nine preregistered starts are retained and converged. Each nfev is within200; saved actual residual calls include finite-difference Jacobian work:391 attempted/completed =103 nfev +3×96 njev. These are inspected execution counters, not reconstructed optimizer trajectories. The selected start is index2, the literal minimum of (objective,index) among converged training starts; no post-holdout selection is present. Independent Fraction sum of SSE/(8×curve_n) gives0.007850445317069278. This is the equal-curve training objective, not pooled RMSE². All nine starts satisfy the preregistered near-best rule; that does not establish parameter uniqueness.

Parameter file SHA288564642ecee9f99c561b806493c2276a638569f2fbcbc0d3f3a0a44efb03fd matches TRAINING_LOCK, the externally pinned holdout command argument, single parent-directory HOLDOUT_UNLOCKED token and final report. Its saved hashes bind training report/metrics; held-out report parameters exactly equal the frozen values. TRAINING_LOCK records holdout-not-yet-unlocked, and code creates the token exclusively before value parsing; the final report records completed access and evaluation. Together with root’s reported prior tool pin this is consistent with the intended train-then-one-holdout chronology. Unsigned files alone are not a cryptographic proof that no other process ever read data; no such stronger claim is made.

Both saved supervisors reportexit0, no external timeout and child reaped. Actual external times are0.642735417s training and0.381623625s holdout, both below135s; internal saved times0.298558333s and0.032324s are below120s. Successful process completion does not mean model validation.

All residuals and outside-bound fields match original binary64 subtraction. Metrics were independently recomputed from exact Fractions of saved predictions/observations and80-digit Decimal square roots; maximum discrepancy from saved summaries is9.565e-18MR. This is ordinary reporting roundoff, not a change to any scientific gate.

| Split | N | RMSE | MAE | Max abs | Bias | Outside readout / +1e-6 numeric |
|---|---:|---:|---:|---:|---:|---:|
|training|117|0.0993179550|0.0821953176|0.2134900643|-0.0175647410|101 / 101|
|holdout|57|0.0821124348|0.0619352618|0.1792068042|-0.0525674154|41 / 41|

| T °C | RH % | N | RMSE | MAE | Max abs | Bias | Outside |
|---:|---:|---:|---:|---:|---:|---:|---:|
|40|30|14|0.10585848|0.09296404|0.16107314|0.07373383|13|
|40|40|16|0.09006767|0.08303938|0.13333411|0.02586468|15|
|40|50|21|0.09968093|0.08685722|0.15887781|-0.05463066|20|
|40|60|28|0.13472557|0.10951261|0.21349006|-0.10717842|21|
|60|30|8|0.06090905|0.05517108|0.09685348|-0.02226371|7|
|60|40|9|0.05021776|0.04555946|0.07745877|-0.00919408|8|
|60|50|10|0.05176637|0.04741284|0.07149886|0.01919748|9|
|60|60|11|0.08053942|0.07007624|0.12056317|0.06508526|8|
|50|30|10|0.04901372|0.04326676|0.08377993|-0.01124119|9|
|50|40|12|0.06881386|0.05498140|0.11684974|-0.04460883|10|
|50|50|16|0.08058732|0.06110434|0.14013137|-0.05867303|10|
|50|60|19|0.10248571|0.07685243|0.17920680|-0.07420296|12|

Saved MP comparison maxima are all below1e-6MR (largest5.969e-13MR). The original record saves only maxima, not independent reference vectors, so this review verifies those reported diagnostics and their allowance but does not independently reconstruct the maxima or run a fresh oracle. Numerical agreement between implementations does not explain the much larger data residuals.

Ea=149999.99999999997J/mol lies at the150000J/mol numerical search upper boundary. The fit is an effective, constrained model fit to digitized curve centers; it is not an intrinsic measured transport/activation parameter. Empty experimental-uncertainty fields remain empty. Readout bounds are digitization bounds, not experimental statistical confidence intervals; no covariance confidence statement or material prediction qualification follows. Training101/117 and holdout41/57 readout-plus-numeric violations remain fully retained.

Evidence: review_saved.py, RESULT.json and review01.log. RESULT retains per-condition/overall exact-derived statistics, source CSV line numbers, budgets and counters. No original candidate, CSV, prediction, freeze, token or parameter file was modified.
