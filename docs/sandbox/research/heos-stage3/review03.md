# Independent review: coexistence and frozen stage 3 candidate

Disposition: approve **isolated research evidence only**. No critical/high issue found within that bounded use. This is not WaterProperties/provider, mixture-host, trajectory, performance, or whole-domain admission. Reviewer performed source/diff/AST, JSON, hash and saved-number checks; no EOS execution, tests, installations or production edits. Repository Python diff was empty. Ruff/mypy/pylint/black were unavailable on PATH; AST parsing passed.

## Numerical construction

QT supplies densities only. Imposed-phase DmassT evaluations supply native p/h/u/s; no native energy or entropy is reset. At fixed T, dp/d(log rho)=rho RTD and dg/d(log rho)=RTD. The implemented two-row Jacobian and signed inverse updates for pL-pV and gL-gV are correct. Positive slopes, separated density branches, finite determinant, step <0.1 and eight-evaluation cap reject failures; this is not a demonstrated globally convergent solver.

The original snapshot gates remain: pressure max(0.01 Pa,2e-8|p|); h-u-p/rho 1e-6 J/kg; Helmholtz h and T*s 0.002 J/kg; cp/cv 1e-5 J/kg/K; molar response identity 1e-7 J/mol/K. Final common pressure is vapor EOS pressure. Returned pair pressure equality is by construction; the independently checked native liquid pressure and coexistence dp supply the actual pressure evidence. Native h/u/s remain untouched. Public molar conversions retain the exact Python reference mass/R while recording distinct native mass.

Attempt03/04 forced one Newton update even though initial EOS-evaluated densities already passed dp<=1e-4 Pa and dg<=1e-6 J/kg. In saved03, dp worsened from -6.994695e-6 to -3.113312e-5 Pa and dg from -5.311449e-9 to -3.034074e-8 J/kg, still passing. Recomputed the recorded native Gibbs/pressure differences and Newton update from saved operands. This does not demonstrate a Newton improvement. Final05 correctly accepts the qualified seed: one coexistence evaluation, zero updates. Relative to04, the only numerical change is removal of `iteration>0`; the other change adds the recommended post-transaction fluid digest check.

## Identity and failure boundaries

Construction binds adapter SHA, exact package .py/.so file set and hashes, loaded core-extension path, version/revision, raw and canonical full-fluid JSON, EOS constants, effective config, original water assets and reference. Ideal h and entropy anchor checks use original ideal values/phi0 and native alpha0 with original 0.002 J/kg tolerance; no global reference reset. Snapshots bind the descriptor digest. Ordinary attribute reassignment is sealed and diagnostic traces returned as copies. Per-instance lock, pre/post config and fluid checks, and warning rejection improve fail-closed behavior.

This is ordinary Python immutability, not a hostile-mutation boundary (the fault script intentionally bypasses it). The instance lock and before/after checks do not prove safety against concurrent process-global changes, changes reverted between checks, or imported-object monkeypatching. Constructor/file identity checks plus single-process controlled inputs are the supported research setting. Python/NumPy/SciPy/OS/build closure and registered consumer canonical identity still need explicit treatment before general provider admission. Runtime fluid-mutation and constructor-anchor rejection were not injected in this five-fault set.

## Actual evidence and independent checks

Attempts03,04, fault-attempt01 and05 have distinct supervisor records, complete status/exit0, 30 s external cap, input-before/after hashes equal; elapsed respectively 1.088321792, 1.125824125, 1.096810416 and 1.169894750 s. Archived `passed03-source` and `passed04-source` source/manifest hashes match their recorded attempts. All 59 final05 input hashes match current files. Original failed01/02 remain failures; neither is erased by later success.

Final `result05.json`: four comparisons (300 K saturation liquid/vapor, liquid TP at 304469.31354 and 567435.65536 Pa), six domain rejections and three ordinary immutability checks. Recomputed every saved candidate/old difference, native h-u-p/rho, and compared all seven saved residuals with original limits. Descriptor runtime equals frozen manifest, and each snapshot implementation equals its recomputed descriptor digest. Raw derivative operands are not all saved, so some Helmholtz residuals remain runtime evidence rather than independently reconstructed EOS calculations. The single saved coexistence trace is from the last repeated saturation call; it is not a trace for every earlier call. This does not validate 293..500 K broadly or any vapor TP case.

Final `fault-results05.json` records five expected typed rejections: native u+0.01, nonfinite derivative, warning, effective config change, wrong adapter SHA. Reviewed fault injection/restoration and final child sequencing: physics JSON is written before faults, so both JSON results and supervisor exit0 are jointly required. All three are present and passing. No performance conclusion follows from these short smoke-run elapsed times.

Final evidence SHA-256:

- `heos_candidate.py`: `7712d64b5b479196b06817dc83cfc17c94627b2ddecab7227fd744c3d0a46771`
- `expected.json`: `343150a9ecabb72addc81ab62eee34e07f424f0f677dc303f4bb8c3e08a89a33`
- `result05.json`: `5d2d8b74ac6751e9a7eb2e4649606fa3abaf785c14fb32bd442ad381cd0bba1c`
- `fault-results05.json`: `18598ede930006286c5724135223824adf1baabd08ca165b9b94b6010adb3f85`
- Recomputed descriptor: `285d0b6dfe3b775bfc4a3ffa16f632d58e09e5e19a98be77c672c235d666a9bc`

All paths above are relative to `/private/tmp/brick-heos-stage3`. No production application is authorized by this report.
