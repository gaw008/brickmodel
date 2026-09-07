# Six-fraction TP diagnostic: independent numerical/Python review

Decision: APPROVE the single bounded diagnostic described in PLAN.md, conditional on root execution scheduling. No numerical repair or production admission is approved. This review ran no EOS, provider import, test, probe, install, or source mutation. Repository Python diff was empty. Standard-library AST and file/hash comparisons passed; ruff/mypy/pylint/black were unavailable on PATH and were not installed.

Frozen scripts reviewed:

- probe.py: 179323379e85d4ee9f2ac1eabd486b2b448ff32ff6a152ac1c81542891879d9a
- run.py: d660d46622a98200786d2e9eaeb6c35c8754cb0738eaf76a3ea5b7a8ad5d4df5

All six file hashes in PLAN match actual files. All three evidence copies match original bytes and input-manifest hashes. PLAN retains the prior failure context: 295 K is an inverse bracket endpoint; 417 ULP separation does not demonstrate unavoidable density quantization.

## Numerical and source checks

Compared directly with current _heos_kernel.py state_tp and _snapshot and water_heos.py wrapper. The diagnostic constructs the approved public provider, checks captured kernel identity against both source snapshots, uses original wrapper guards before/after, and enters the original locked configuration/fluid transaction. Temperature, pressure, phase, saturation ambiguity and stability guards match the source; original domain exception classes are retained. No alternate EOS or source/manifest replacement is introduced.

The native PT seed must equal captured first density. Re-evaluated base density, native pressure, target pressure, h, u, residual and derivative must each equal the captured first row. The slope expression preserves the original arithmetic order. Positive finite density/slope, phase branch, finite residual, and abs(full log-density step)<0.1 remain enforced. Additional explicit phase/finite native record checks reject invalid diagnostics.

The six fractions are exactly 1, 1/2, 1/4, 1/8, 1/16, 1/32. Each density is seed*exp(fraction*step), based on the same first point. No chained steps, adaptive candidate extension, target adjustment, interpolation or averaging occurs. Full-step density must reproduce the original second density.

Each candidate gate is exactly min(1e-4, trial_density*1e-7), and normalized residual decrease alone cannot produce success. Every gate pass must additionally pass the actual existing _snapshot Table-3/state-response checks and final density branch. _snapshot updates the separate check object; it does not substitute a different flash state for the next candidate. Successful diagnostic records are never returned to a host as property solutions.

Any invalid source/native/phase/snapshot result aborts the whole diagnostic with nonzero status, even after an earlier passing fraction. Exceptions are retained with traceback; they are never interpreted as ordinary merit rejections. Phase is reset in finally. This matches the required scientific boundary: an observed interior point may motivate solver design, but is not proof of global convergence or a complete coupled simulation.

## Evidence and bounded execution

The final version records active_trial before native evaluation, preserving requested fraction/density even when evaluation throws. Completed trials, field equality checks, captured arguments and installed identities are saved atomically. A prior output is refused. External termination can prevent child JSON; PLAN correctly relies on supervisor evidence in that case.

run.py uses argument-vector subprocess invocation through the existing supervisor, strips PYTHONPATH, disables bytecode writes, snapshots declared code/data/plan/evidence inputs, retains the 30-second cap, and requires both supervisor complete and exit zero. Fixed native work is constructor qualification, one saturation solve, one PT seed, one base evaluation, six candidate evaluations, and at most six original snapshot checks. Constructor work is acknowledged rather than falsely counted as zero native calls.

No critical/high defect found in this bounded diagnostic. Execution outcome remains unknown at review time. Preserve failure if all six candidates miss the original gate; do not extend fractions or loosen limits within this attempt.

## Actual saved outcome and proposed next control contract

Read step-probe-result.json after root's execution; SHA256 `deb603ff03a8f6c9a8585c569eae3cbc841de02535438544b3bb09669b1ff5f9`. Child status is diagnostic_gate_pass_observed, inner elapsed 0.9446232919872273 s. Root reports terminal supervisor complete at 1.162603 s. This reviewer performed only stored-data arithmetic/hash inspection, not a new native run.

All seven captured base-field equality flags and full-step density identity are true. The completed source/config transaction flag is true; kernel identity equals captured identity. Recorded installed module hashes match current file bytes, and modules common to before/after have identical identity records. The six actual fractions and residuals (Pa) are:

| Fraction | Native residual | Original gate and snapshot pass |
|---|---:|---|
| 1 | +0.00010410800314275548 | no |
| 1/2 | +0.00005536824755836278 | yes |
| 1/4 | -0.00007320060831261799 | yes |
| 1/8 | +0.000013573320757132024 | yes |
| 1/16 | -0.00008316020102938637 | yes |
| 1/32 | -0.00004665277083404362 | yes |

Independently recomputed each stored trial density as seed*exp(fraction*full_step), each gate as min(1e-4,rho*1e-7), and both gate-pass and strict normalized-merit flags. All agree exactly. The half-step gate is 0.00009977857491595473 Pa. Each of the five passing rows includes the actual verified native snapshot. The highly nonmonotone short-step residuals reinforce that the evidence supports measured residual-based safeguarding, not a smooth local-error or mathematical convergence theorem. No fraction should be selected by interpolating these records.

ROOT_NEXT_TEST_SCOPE.md is an appropriate independent control-test contract for a later isolated candidate: eight accepted density states including seed, at most six fractions per transition, hence at most 1+7*6=43 density evaluations; no duplicated native evaluation of an already measured accepted candidate; original first full-step bound before damping; unchanged density-dependent gate and final snapshot; all invalid source/native/phase/branch/slope outcomes fatal; phase cleanup; prior saturation behavior retained. Scripted responses must stay explicitly numerical fixtures, not alternate property evidence.

Additional useful boundary cases for those independent tests: equal merit or unchanged representable density must not count as improvement; after the eighth accepted state fails its gate there must be no ninth accepted state or forty-fourth evaluation; record failed candidate inputs before evaluating them; reject an error in post-transaction source/config validation without returning a snapshot; verify a final snapshot exception cannot be hidden by a prior gate pass. Test the full-step worsening/half-step passing sequence using independent expected density arithmetic, not candidate helper calls. Verify the complete nonimproving six-trial sequence is based on one unchanged base and fails explicitly.

Approve preparation of the bounded candidate and its independent tests under that contract. This successful diagnostic is not approval of an unseen candidate, source-identity changes, production integration, or the full coupled wet replay. No further source/native action was performed in this review.
