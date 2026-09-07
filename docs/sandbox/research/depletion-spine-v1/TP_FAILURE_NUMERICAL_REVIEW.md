# Actual v3 T/P snapshot: numerical review and next diagnostic hypothesis

Reviewed the saved tp-failure-snapshot.json and matching current caller/solver source. No EOS, tests, provider imports, candidate changes or production edits performed. Numerical figures below come only from exact stored binary values and standard-library arithmetic.

## Confirmed failing input and caller meaning

- Temperature: 295 K, hex `0x1.2700000000000p+8`.
- Target pressure: 53692.54782795906 Pa, hex `0x1.a379187ce8000p+15`.
- Phase: liquid.
- Host RK stage time: 0.5002785505335737 s.

295 K is explicitly the LOWER ENDPOINT of the temperature inverse's (295,310) K bracket. The captured SolidFluidStorage.temperature_from_energy frame is at low=self.evaluate_at_temperature(lo,...), with lo=295; that calls the rigid mechanical liquid-pressure bisection. The failing pressure is a trial inside the captured mechanical bracket [53692.53307580948,53692.56258010864] Pa. Neither 295 K nor this pressure has been accepted as the actual brick/cell thermodynamic state. The stage contains positive liquid 2.3817884127730237e-8 mol, so requesting real liquid properties is appropriate. No evidence supports calling this a physical cooling-to-295 K or an out-of-domain material failure.

## Actual stopping rule and observed cycle

The original gate is min(1e-4, rho*1e-7) Pa, not a constant 1e-4 Pa. At these liquid densities it is approximately 9.977857491595e-5 Pa. A repair or probe must retain this exact dynamic gate.

All eight recorded evaluations alternate exactly between:

| rho kg/m3 | rho hex suffix | residual Pa |
|---|---|---|
| 997.7857491595237 | `0x1.f2e4936daf81cp+9` | -0.00010403933993075043 |
| 997.7857491595711 | `0x1.f2e4936daf9bdp+9` | +0.00010410800314275548 |

The residual magnitudes are approximately 1.04270 and 1.04339 times their original gates. The loop never meets its criterion. It has a reproducible *recorded two-cycle*, not monotonically improving slow convergence. Increasing the eight-iteration cap would repeat this observed pattern absent another algorithmic change.

The densities are separated by 4.7407411329913884e-11 kg/m3, or exactly 417 binary64 ULPs at this magnitude. They are not adjacent representable densities. Therefore this snapshot does not establish a fundamental density-representation impossibility. The final frame rho is the post-iteration Newton update back to the first density; the eighth _tp_iterations entry is the second density, the last actually evaluated native state.

The measured secant dp/drho between these two native evaluations is 4390607.654676259 Pa/(kg/m3), while the first recorded analytic derivative slope/rho is 2196068.5972881895 in the same units, a ratio 1.9993035099622987. This explains why a full Newton displacement traverses approximately the whole alternating interval. It suggests local native evaluation/rounding behavior or ineffective full-step globalization; it does not by itself prove an EOS derivative defect or identify its ultimate cause. Saturation solve has already succeeded (ps about 2621.24 Pa), and the explicit positive-slope/branch guards did not fail.

## Preregistered next experiment sequence

1. Root/worker's already prepared bounded 30 s *unchanged public-provider exact-point baseline* should run first using float.fromhex above. Save the original gate and complete last_tp/native identity. If it does not reproduce, retain that outcome and investigate call-history dependence before generalizing the snapshot.
2. Only after that baseline, prepare a separately reviewed bounded diagnostic of a residual-decreasing density step. No production change yet. Starting from the captured first density and its existing Newton direction, consider the fixed fractions 1,1/2,1/4,1/8,1/16,1/32. Evaluate at most six candidates, with original native source/configuration transaction, same temperature/phase/stability limits and native SI state evaluation. Do not reuse diagnostic pressure estimates as an accepted physical state.
3. Candidate acceptance must require the ORIGINAL residual gate at the candidate density or a strict decrease of abs(residual)/min(1e-4,rho*1e-7), with all original branch, finite positive-slope and full-step-size limits intact. Invalid native/source/phase results remain fatal; they are not ordinary line-search rejections. The final returned state, if any, must still pass the original full snapshot/Table-3 checks.
4. A bracket alternative can use the two actual opposite-sign evaluated densities. An arithmetic interior density or safeguarded secant may avoid the full-step cycle, but an interval width or interpolated zero is NOT an acceptance criterion. Only an actually evaluated native residual satisfying the unchanged gate can establish success. Opposite signs of a numerically noisy evaluated function are not a new certified physical root enclosure.

Hypothesis to test: a shorter interior step may produce an actual native residual below the original gate where the full Newton step cycles. The snapshot alone does not show the midpoint or any shorter-step native residual, so no successful fix is claimed. If all bounded candidates fail, preserve this failure and reassess; do not widen the gate, average h/u/s, replace the target pressure, narrow the host inverse bracket to skip 295 K, or switch to Python IAPWS for acceptance.

Any later production algorithm needs an explicit bounded iteration/trial policy, diagnostic identity/source rebinding, no-EOS control tests for cycling/stagnation/invalid trials, exact-point and nearby native checks, then the unchanged coupled v3 replay and installed regression. Fixing one exact point would still not demonstrate complete wet-model accuracy or source-qualified sludge behavior.

## Exact-point baseline script review and actual saved outcome

Static review approves the narrowly scoped baseline scripts. `exact_point.py` SHA256 is `2b4153979e7b62dd1d5f2b5a0074827f656c8760e316686a6ac06c231703fcaa`; `run.py` is `11ad7e7b3be2be8aadc8788a74b09e49f556c7a2cc6ede39d50b63a4e75ed511`. Both actual hashes match PLAN and both parse. The captured JSON is byte-identical to the original diagnostic snapshot. Public provider construction retains approved manifest/source/runtime checks, the kernel identity is explicitly checked, and the one requested state call reconstructs captured inputs with float.fromhex. Diagnostic properties only read existing iteration records; no extra EOS evaluation, backend substitution, tolerance change or warmup was added. Native work in the unchanged constructor is explicitly acknowledged. The supervisor retains its 30 s cap, snapshots its declared input files, and requires both complete supervisor status and child exit zero for success. This review did not run either script.

The already executed result, read from `exact-point-result.json`, is **failed**, reason `heos_tp_not_converged`, one requested public state call, inner elapsed **0.9478506250015926 s**, and eight existing TP iterations. I independently compared all eight decoded diagnostic rows with the full-trajectory snapshot: they are exactly equal, including every stored float value/hex/repr, h, u, derivative and residual. Parent reports supervisor child exit 1 and 1.18991 s; the other reviewer separately audited 105 unchanged input files. Those two supervisor/input-audit facts are attributed to their reviews, not newly executed here.

The fresh-provider baseline therefore reproduces the same two-cycle without requiring the long preceding wet trajectory. This strengthens the case for the bounded interior-step experiment above, but does not establish that any candidate will pass. Step 1 is now complete with a preserved failure; next work is preparation and independent review of the fixed six-fraction diagnostic, followed by one explicitly supervised trial. Keep the original dynamic gate and native state validity checks, retain all unsuccessful trial evidence, and accept no state merely because residual decreased. No production change or successful repair is approved by this report.
