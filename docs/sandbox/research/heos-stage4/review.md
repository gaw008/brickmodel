# Independent stage 4 grid review

Disposition for original attempt01: **grid qualification blocked by two actual numerical failures**. Failure handling for these cases worked. The appended attempt02 review records the subsequently revised kernel and successful bounded grid. No EOS/tests rerun or production edits by reviewer; source/AST, retained JSON and stdlib arithmetic/hash checks only.

`heos_candidate.py` and `expected.json` exactly match frozen stage3 (SHA-256 `7712d64b5b479196b06817dc83cfc17c94627b2ddecab7227fd744c3d0a46771` and `343150a9ecabb72addc81ab62eee34e07f424f0f677dc303f4bb8c3e08a89a33`). PLAN and code specify six temperatures 293/300/350/400/450/500 K, each with saturation liquid/vapor, vapor at 0.1 original Psat, liquid at 2 original Psat and 100 MPa. Thirty states actually persisted. Cross-backend density, h/u/T*s and cp/cv tolerances match stage3; candidate Table3 gates are unchanged.

`grid-attempt01` finished failed/exit1 in 1.495137875 s under its 30 s external limit, with leader reaped and no cleanup signal errors. All 57 before/after input hashes agree and independently match current files. Result reports 28 passing and two failed states, both liquid TP at 100 MPa:

| T (K) | Saved h-u-p/rho residual (J/kg) | Limit (J/kg) |
|---|---:|---:|
|293|2.31401645578444e-6|1e-6|
|300|2.0962179405614734e-6|1e-6|

Both failures were captured as WaterNumericalError; later independent cases continued, and final process status correctly fails the grid. The corresponding pressure-reconstruction residuals (0.0024058074 and 0.0021741539 Pa) pass their existing pressure tolerance. These values do not by themselves establish the numerical cause: failed native snapshots are not persisted, only exception residual tuples and coexistence trace. Do not repair acceptance by algebraically replacing u/h or loosening the 1e-6 gate.

For all 28 successes, independently recomputed saved candidate/original differences and h-u-p/rho and checked original comparison/energy limits. Remaining Table3 derivative residuals are runtime evidence; full raw derivative inputs are not retained for independent reconstruction. Saturation comparisons use each backend's own saturation state rather than forcing identical pressure; TP cases share the original-derived input pressure. Coexistence traces can be stale if failure occurs before a new trace is established, so are diagnostic and not automatically failed-flash operands.

[MEDIUM] Grid failure isolation has a narrow gap. `grid.py` calls `old.saturation_pair(t)` outside the per-case try. An original-backend saturation exception would terminate remaining temperatures and omit an explicit failure row. Initialization failures likewise rely on supervisor logs. Neither occurred in this attempt, as all 30 rows exist. Before reusing the runner, capture these failures explicitly and continue independent temperatures where meaningful; always require supervisor completion and expected row count alongside JSON status.

This grid is not full continuous-domain proof, official verification, finite-difference response verification, a performance benchmark or any host/manufacturing/material admission. Existing stage3 smoke success remains bounded; the extended grid has not passed.

The preceding conclusion concerns the preserved original attempt01, before the TP refinement below. Its kernel/manifest are now retained in `baseline/`; references to matching current inputs above describe the actual attempt01 review time.

Evidence SHA-256 (paths relative to `/private/tmp/brick-heos-stage4`):

- `grid.py`: `4bb0368b47335a2e665e71cb8953c9b22f99d227e78bfaf8ab40829c073f788d`
- `run.py`: `ea61fe048a6dcc63161412c4e9488f9a8780f87ae14d6bd53853c0abee6caffc`
- `PLAN.md`: `9e86e2058e1c7caa4fd552282768db5738e9f8df73b2dd73bf81a4244c9ef1fe`
- `grid-result.json`: `cdaf2dc23e8b9b0cc3a6cc7c4d8c8275f064835a34c77d984b26c245d5c9df31`
- `grid-attempt01/status.json`: `7a7e35c92e0eea43596ac422753e2d30e1980bfa11862132d2f2c2e0745d8b69`

## Follow-up: genuine TP density solve, attempt02

Approve this revised kernel's **bounded 30-state grid evidence only**. The reviewed diff adds a TP diagnostic-copy property and log-density Newton solve, with no changes to the original numerical acceptance gates. Native PT must first report the requested phase; DmassT then solves native p(rho,T)=the original requested pressure. The derivative rho*RTD, update -pressure_residual/slope, sign and dimension are correct. Positive slope, finite operands, saturation-relative density branches, step<0.1 and eight-evaluation limit fail closed. Returned pressure remains the requested pressure and raw h/u are untouched. The min(1e-4 Pa, rho*1e-7 J/kg) solver target is a numerical accuracy policy with margin against the original energy gate, not measured material uncertainty. This is a physical density solve, not an energy-residual subtraction.

Actual `grid-attempt02` completed exit0 in 1.522169541 s; 30 rows pass. Independently checked all input-before/after SHA values against current files, native h-u-p/rho for all 30, every saved TP pressure residual, each logged Newton update, final solve thresholds, and final native rho/h/u equality to snapshots. The two formerly failing 100 MPa states now each require one update: 293 K p residual 0.0024058223 -> 0.0000555068 Pa, energy residual 5.340553e-8 J/kg; 300 K 0.0021741688 -> -0.00000444055 Pa, energy residual 4.307367e-9 J/kg. Thus this evidence actually demonstrates residual reduction for these TP solves, unlike the prior forced saturation step. Other states may require no update. This does not demonstrate global convergence.

The original grid remains failed and retained; only the new source-bound grid passes. The outer-original-saturation exception limitation remains and did not occur. Finite-difference derivative evidence is a separate task and is not covered by this report. No host, material, continuous-domain or speed admission follows.

Attempt02 SHA-256:

- `heos_candidate.py`: `20777eb928fff0090b50213ad264f2d9b9cfca1e483719c698ea3fe9c6fa815d`
- `expected.json`: `a2d309e79615b283477d8368fe03477704ed5ba468cc3bf11350773ac716783d`
- `grid02.py`: `2961cbc596a24439b1b7e8bba652e1b6f68c7d4a67bb4fe8c37c1260b78c3763`
- `grid-result02.json`: `4a46d6afaf800fd71ad5b1a241e27ad7aa2c18e99d9e187e8e3fcfa04b946954`
- `TP_PLAN.md`: `bfefd9c888e9997909dd6088e8072be9446d283cdf1f852cdfdf28e6a68d74fd`

## Independent finite-difference and printed-source checks

Reviewed `derivatives.py` against actual `tests/sandbox/test_water_response.py`. Seven (T,P,phase) cases, dt=0.01 K, dp=max(1 Pa,1e-4 P), and all three relative/absolute tolerances agree. M/rho is molar volume; M*u+the fixed energy offset is molar energy. Central differences therefore have the claimed m3/mol/K, m3/mol/Pa and J/mol/Pa units. All five snapshots, mass and offset are persisted for each case. Recomputed all 21 finite differences exactly from those operands and checked analytic mappings to central dv_dt/dv_dp/du_dp. A small implementation distinction: math.isclose uses a symmetric relative scale while pytest.approx uses the expected finite-difference scale. Independently verified all actual results also pass the stricter original asymmetric pytest comparison, so this difference does not affect these seven results. Before claiming an identical future gate, use the original comparator definition. This reproduces the seven numeric tests only, not all identity/immutability/fault tests in that production file.

Actual derivative-attempt01 completed exit0 in 1.502505709 s; seven passed rows, all 63 input hashes agree before/after and with current files. Local finite differences are not interval bounds or proof for every state.

Reviewed `official.py` against the bound `official_verification.json`: 21 Table8 saturation outputs at 275/450/625 K and 12 dimensionless ideal/residual Helmholtz values/derivatives at 500 K, rho=838.025 kg/m3. API mappings alpha0/alphar, delta/tau first/second/mixed derivatives are consistent; p/1e6 yields MPa and h,s/1000 yield kJ/kg and kJ/kg/K. Recomputed all 33 saved absolute errors and relative1e-8/absolute1e-11 acceptance checks against original printed values; also all pass using only expected-value relative scale. This tolerance checks rounded program verification values, not material uncertainty.

Actual official-attempt01 completed exit0 in 1.036537000 s; 33 passed rows, all 65 input hashes agree before/after and with current files. `HEOSCandidate` construction checks source identity, but these outputs are from a separate raw HEOS AbstractState, outside candidate transaction/phase/refinement gates. In particular 275/625 K do not extend the candidate's 293..500 K domain. This checks backend equations against saved source-print values, not new independent physical measurements or full candidate behavior. The official result omits Table6 density per row; its bound source JSON supplies that input unambiguously. No browser or EOS was invoked by this reviewer.

Additional evidence SHA-256:

- `derivatives.py`: `72b9d7181a5799dc9fcf9ced42fbf4657cb3d188ebd6eb04f315dde1104064bb`
- `derivative-result.json`: `2b0ce65f48a9bb08d0e9bbf0bbe3591aad708ee713841cd1f0c5be38719422e1`
- `official.py`: `96da1aab77af430fd4e44c31d3073e4988045d059daaa8d2a119c910d707588e`
- `official-result.json`: `28c8bc4ad8673a915a425a5f396ab44f6892b861e8dee117a19ca3b4e86c8e1a`

## Reference mutation and shared-instance execution

Reviewed original `identity_threads.py`, corrected `identity02.py`, PLAN02 and both terminal records. Original identity-attempt01 failed/exit1 in 1.020425083 s: it required an existing instance to reject a global reference setter, and exited before writing its non-finally result file. This original failure and stderr remain evidence, not a pass. The test expectation correction is justified: existing AbstractState objects retain their instantiated reference while new instances see a later setter, per the [official reference-state documentation](https://coolprop.org/coolprop/LowLevelAPI.html#reference-states), independently read for this review. No kernel or numerical tolerance changed.

Corrected identity-attempt02 completed exit0 in 1.404248791 s. Independently rehashed all before/after/current inputs and compared saved full snapshots: the existing 300 K/100 kPa liquid result is exactly unchanged after NBP; a newly created raw instance's enthalpy differs by -419057.7330939785 J/kg; a new candidate rejects with the original `heos_ideal_reference_anchor_mismatch`. Thus the test distinguishes unchanged existing physics from changed newly instantiated reference, instead of demanding rejection of the former. `finally` restores DEF and the subsequent ordinary constructor validates the anchor again. Corrected result persistence is in outer finally, including failure context.

After restoration, four workers call one shared candidate for 12 entries (four distinct liquid temperatures 300/350/400/450 K at 10 MPa, repeated three times). All saved sequential and threaded snapshots compare exactly equal. This supports the tested instance-lock behavior under this schedule; it is not evidence for concurrent global reference/config mutation, multiple instances, race freedom across all interleavings or parallel native EOS throughput. Global mutation occurred before threaded work, not during it. Official guidance discourages changing reference states after initialization; this deliberately isolated fault experiment is not a proposed production pattern.

- `identity02.py` SHA-256: `656cbd1dabdc0e998c4dd2fcc36527b0fc0ad958d46b1ee177fc5a22aecaa08a`
- `IDENTITY_PLAN02.md`: `05dd5df2796ed89ca6ad6592e0dc4d1dfacf152c4ea8f3864f20489b662f5462`
- `identity-result02.json`: `8eecc08ea8f9add1738a7a4deb041486adaffc86c2334652ddae00fee0f49b38`
