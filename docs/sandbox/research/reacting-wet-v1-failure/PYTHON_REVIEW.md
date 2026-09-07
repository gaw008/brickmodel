# Reacting wet fixture / execution Python review

Initial verdict: one supervisor propagation fix required before execution. All inspection was static source/AST/hash inspection; no module imports, EOS, fixture callback, test, integration or probe were run by this reviewer. No production or fixture files were edited; this report is the sole reviewer write.

Reviewed frozen fixture.py, callback.py, depletion.py, run.py, compare.py and PLAN.json after the preparing worker's ready signal. All five initial file hashes matched PLAN.prepared_script_sha256 exactly and all ASTs parsed. Read the relevant actual source for the water wrapper, solid phase and caloric fixture, reaction config, depletion event/roundoff types, default policies and process supervisor.

[HIGH] Runner discards a supervisor failure when child exits zero
File: /private/tmp/brick-reacting-wet-v1/run.py (final return expression)
Issue: return 0 if result['returncode']==0 ignores result['status']. The reused supervisor explicitly changes a nominally complete zero-exit run to failed if declared input hashes change or cleanup cannot be verified. The wrapper can then emit exit 0 despite that failure.
Fix: require both status == 'complete' and returncode == 0. Preserve supervisor metadata and update the preregistered run.py hash. Worker notified before any execution.

## Fixture and scientific boundaries

The fixture uses the actual installed approved HEOS provider with matching ideal water vapor and chemical potential providers, retaining the source/hash guards. Manufactured A and B are each declared C with equal 0.012 kg/mol mass, positive complete phases, different volumes and explicitly manufactured caloric references. The fixture's delta-u=-4 J/mol follows delta-h=-5 J/mol minus reference pressure times delta-v=-1 J/mol. The first-order A->B law yields A(t)=2 exp[-0.1(t-START)] independently of the current bulk volume; current storage rebinding is separately asserted. The deliberately widened *new manufactured kinetic domain* is preregistered rather than attributed to a real sludge source. Neither q nor interface kinetic coefficient is presented as sourced material data.

The geometry is one isotropically prescribed cell with reference volume 1e-4 m3; current bulk volume comes from the existing smoothstep program at START=0.5. Solid volume remains sum(N_i*v_i) and fluid available volume is current bulk minus current solid volume. Initial energy is newly constructed under the reacting energy identity; no old fixed-skeleton total energy is reused. The reference interface energy is explicitly changed to 0.3 J and q=1+10*N_B. The callback checks original/current storage object reuse, retained thermal inverse, simultaneous stoichiometric A/B and water transfers, unchanged inert carrier, closed faces and exact preservation of host cell power through the phase-transfer wrapper. It does not add composition, reaction or latent heat as an extra source.

## Evidence and gates

The scripts require site-packages paths and byte identity to the actual source tree, before construction and after successful work. The supervisor records source/test/water/script/plan hashes before and after, including failure paths, and enforces bounded cleanup. Its status must also control the runner's exit code (finding above).

Depletion saves the complete returned states, steps, events, refinements, corrections and roundoff totals before trajectory acceptance assertions. A returned failure/domain exit therefore remains inspectable. An exception before return is retained with traceback; an externally killed child cannot promise final Python serialization, and supervisor failure evidence must be inspected in that case.

Every audited accepted prefix checks exact represented component sum plus recorded residual against cell work, accumulates work and boundary energy in Fraction, checks total-energy residual and water amount residual at preregistered gates, retains explicit elemental/mass residuals, and verifies solid analytic A, A+B, unchanged carrier and zero face flux. The correction audit independently reconstructs actual/ideal vapor increments and their signed, absolute and phase totals. Existing production roundoff limits remain in the unchanged inherited policy; the looser prefix diagnostic is not a replacement for those limits.

A successful path requires exactly one actual interior depletion event, retained nonzero interface coefficient, zero liquid after the event and continuing positive A->B reaction on a later dry state. The final geometry is checked from current A/B inventory. The two-cap comparison uses preregistered amount/energy/temperature/pressure/event-time differences and explicitly calls this a convergence indicator without an independent wet temperature oracle. No complete-model or source-qualified sludge validation follows from these checks.

Full runtime outcome is pending: the current scope is approval to execute bounded reviewed scripts after the runner fix, not a prediction that event gates or resource budgets will pass.

## Final corrections and execution approval

Verdict: APPROVE bounded execution of the final frozen scripts. This is not a runtime success claim.

Root subsequently assigned this reviewer ownership of the single run.py success-condition fix and its PLAN hash, superseding the original read-only assignment for those two edits only. Applied exactly the required status=='complete' AND returncode==0 gate; AST parsed and final bytes reread. Final run.py SHA: `dcc9ba014c8f642824f25662dc0ac39961f5580e0db85d367f7032bb7369e612`. The independent tg_code_review agent cross-reviewed this change against the actual supervisor status contract and found no new issue. The HIGH finding is closed.

Cross-reviewed tg_code_review's separate compare.py failure-record correction, final SHA `b2f9385f489f3362f88bea79e21b8e9c40a3557a359a45945f8e20b687ede3c3`. Missing/malformed input or precondition failure now writes explicit failed status, available input path/hash/byte evidence and traceback, rather than leaving no result. Finite computed differences are required before inserting them into the allow_nan=False result. Original comparison metrics and limits are unchanged. Final compare.py AST parses and its SHA matches PLAN. PLAN mutations were sequential: this reviewer changed only run hash, then tg reread and changed only compare hash.

The unchanged initial hashes for fixture.py, callback.py and depletion.py remain those in PLAN. No source qualification, physical parameters, finite-run gates or resource caps were changed during review. No runtime/import/EOS/test/probe execution was performed. Root must execute callback, inspect its actual terminal evidence, then serialize the two bounded depletion runs and comparison; a failure must remain a failure.
