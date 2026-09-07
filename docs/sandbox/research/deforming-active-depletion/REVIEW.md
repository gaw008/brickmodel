# Deforming depletion stage 1 review

Initial disposition: callback setup is consistent with its declared fixture, but evidence gates need the corrections below before calling the saved result a fully bound energy/inverse verification. Read-only code, AST and contract review; no EOS or tests executed. Repository Python diff was empty. Only this report was written.

Compared with `/private/tmp/brick-clock-final/active.py`: motion, reference geometry, skeleton energies, constitutive constants, deforming point and host construction are unchanged. Liquid inventory changes from 1e-4 to 1e-6 mol; coefficient becomes 1e-6 mol/(s Pa); inverse policy becomes 1e-6 J / 1e-6 K / 120 iterations. These three settings and the inventory vector occur in `tests/sandbox/test_depletion_host.py::wet_dry_host`. This transfers selected wet/dry constraints, not that test's entire host: its programmed oven boundary is absent here. The present experiment retains the clock-final prescribed mechanical motion and closed faces. Stage 1 is one callback at t=0.5 s and cannot establish an event or dry continuation.

Corrections requested of the author:

1. Record and assert `abs(DeformingSolidInverse.total_energy_residual_j) <= 1e-6` as well as the recorded temperature bound. A configured energy tolerance and matching identity are not a saved actual energy residual. Also retain recovered temperature versus the manufactured 300 K initial state.
2. Bind actual installed Python files, not just repository files. Current runner inputs bind src, tests, water data, scripts, plan and supervisor; current callback checks only a site-packages path, after provider construction. Record module SHA-256 and compare actual installed bytes with source before EOS construction, and add installed module files to the supervisor's before/after input set. The tests-only PYTHONPATH and `/private/tmp` cwd avoid a direct src import, but a stale installed package could otherwise satisfy this path assertion.
3. Restore exact inventory-layout assertion before interpreting positional column 2 as liquid. Save actual energy identities and complete five power components, with total/component equality to the underlying base evaluation, plus reaction source +rate/-rate symmetry. The existing positive-rate and five-key checks are appropriate stage-1 gates but alone cannot show no extra latent-power term was introduced.

The runner uses a subprocess argument list, reviewed process supervisor, 30 s bound and explicit source inputs. This is suitable for stage 1. The future 120 s integration / 150 s external stage in PLAN needs a separately bound stage-2 runner and event policy before execution; it is not authorized evidence of completion in this script. Unique attempt directories should remain separate, and any later rerun must preserve the first callback result instead of overwriting it.

Imports preceding the try block can fail without a callback JSON; supervision stderr/exit status remains authoritative in that case. A successful process plus a matching fresh result is required. No broad formatting or unused-import cleanup is needed for this temporary research script.

Initial inspected hashes: callback `05f6d269173888383bee6231c58c5c591c389c0d307d3409663485bca9ba44d3`; plan `f1060569cf6a1eb0dfede5bedc6d6b361d7bb0bc6591610fde9935e58581d74c`; runner `efc662fbf2296667e02ca1b44fb0ad8f7e8fcedb0810e383e16b53e2b556e794`.

## Revised stage-1 gates

Verified the author's added total-inverse residual, actual 300 K recovery, exact layout, power equality and reaction symmetry checks. `total_inverses` is the correct deforming result attribute; `storage_inverses` supplies the thermal bound. The runner now binds all installed sludge_sandbox Python files alongside repository source. These changes close the numerical and source-binding omissions. One remaining ordering correction was requested: move provider construction after the initial loaded-module byte check. In the revision inspected, it still precedes that check, so describing that check as pre-EOS would be inaccurate. Stage-1 execution is acceptable after that small ordering correction; runtime/result success remains untested by this review.

## Stage-1 actual result and stage-2 execution review

The provider-construction ordering is now corrected. Callback attempt `callback-attempt01` is complete, exit 0, 1.988353041 s externally. All 163 recorded inputs match before, after and current SHA-256; all 31 recorded loaded-module files match their saved hashes. Callback result reports positive rate 0.0035312221883480213 mol/s, total-energy residual -1.437729224562645e-8 J, recovered temperature 299.999999999856 K and inverse bound 4.1441961933191635e-9 K. These meet their original gates. Signed vapor/liquid sources are opposite, other reaction columns zero, and five powers are saved. Callback SHA `f55817d6ed8c0bd59203d40913afd430ec062d6cfd2b1dc3dce0a23659ab44d2`; result SHA `83b1570e6d7623d365bf0b4eccd57868f24e86519a6c7c178fa3b78cae8cc8e5`.

Stage 2 is acceptable for one bounded execution. `depletion.py` retains the stage-1 setup and checks exact initial inventories and energy against the supervisor-bound callback result. Integration and event-policy overrides match the existing wet_dry_host fixture, including physical molar mass in its roundoff policy. Start/end are 0.5 and 0.5+1/128; integration maximum is 120 s and the separate runner bounds the process at 150 s. This is the pre-registered combined case, not the original oven-boundary trajectory.

Returned run data are serialized before success assertions, excluding the executable operator. The script requires completion, one interior depletion event, zero final liquid, continued zero-liquid states, unchanged coefficient, matching energy identity, closed faces and five-component work identities. Its exact Fraction component identity uses the correct residual sign. The callback output is a bound runner input; installed Python files, source, test helpers, water files, plan and scripts are also bound. No EOS or tests were run by this reviewer.

Remaining result-audit obligations: the current script only sums signed correction roundoff; independently check each correction's ideal/actual vapor increments, liquid removal, signed and absolute cumulative roundoff and cumulative numerical phase correction against saved operands, as the original test does. Also verify each step's energy residual (not only cumulative prefixes), alignment/length of times/states/steps, and all water/element/mass accounting. These can be checked from retained run data after execution and do not require extra EOS calls. An execution approval does not constitute a passed depletion result. Import failures or a hard timeout may leave only supervisor evidence, so the general statement that every failure produces result JSON remains conditional on Python reaching the finally block.

Reviewed stage-2 script SHA `449859683c493953726deca5e40912115f4ed7137a53974dad793636dbe45725`; runner SHA `ec2b7b1ea65e98d1575c5c0d2d77f5de4dd31fdc1ebebede28c96658e5a917af`.

## Actual stage-2 failure and bounded replay review

Actual depletion-attempt01 exited 1 after 27.881735166 s, with unchanged and independently rehashed inputs. The returned run is numerical_failure / heos_coexistence_not_converged, 72 evaluations, 8 attempted steps, 6 accepted ledgers, 7 states and no events. The accepted endpoint is 0.5002335408845405 s. Its first terminal refinement reports 17 evaluations and 4.061437416 s, also failing coexistence. This is not depletion completion or dry continuation. Saved result SHA `ad4794b933b6e5e6437e7633eddea509aa60922646001681b24a0e2d5e61d5ef`.

Independently recomputed accepted-prefix energy and water sums with Fraction: maximum cumulative energy residual 3.3052693255850507e-11 J and water residual 1.224227306578481e-22 mol. Every accepted step also meets the 1e-7 J energy residual gate. A sound accepted prefix does not validate the failed terminal trial.

The proposed replay reconstructs the same operator and policies and restarts from the exact saved endpoint inventories/energy/time, with separate output and a 30 s external bound. This is acceptable as one bounded diagnostic after two small evidence corrections: assert the saved energy identity and saved policy/event/implementation equal the current values before attaching the current identity; and serialize the returned run before reading private diagnostic properties, preserving it if a diagnostic read fails. Root was notified. No numerical threshold changes are needed or approved.

The actual kernel clears last_coexistence at each coexistence solve and appends every iteration before testing convergence. Consequently, the kernel raising not_converged retains its eight failed dp/dg evaluations, useful for diagnosis. Other providers can still hold earlier-call histories; label each provider and do not assume all three histories identify the failing call. This corrects the reviewer's initial message that the property contained only successful snapshots. Replay also restarts controller state and budget rather than reproducing an exact suspended integrator instruction stream. Exit 0 should mean diagnostic capture only, not numerical completion.

## Replay evidence and damping feasibility probe

Replay-attempt01 completed as a diagnostic, exit 0 after 6.008556500 s, with all recorded input hashes matching before/after/current files. The actual returned run still has numerical_failure / heos_coexistence_not_converged (18 evaluations). Independently compared its reconstructed restart state and time with the saved accepted endpoint, and its policy, event policy and implementation with the failed original run: exact equality.

Chemical-provider diagnostics at 299.9996124454831 K show eight evaluated coexistence pairs, alternating pressure residual around -1.0544e-4 and +1.0560e-4 Pa; all eight fail the original 1e-4 Pa pressure gate while meeting the 1e-6 J/kg Gibbs gate. Recomputed dp and dg from the saved native p and Gibbs operands agree. The fluid provider has a separate earlier one-evaluation history at another temperature. The unused vapor-provider flash reports -Infinity with an empty history; this is retained nonphysical debug metadata, not a valid thermodynamic result or strict-JSON numerical dataset.

Static approval for one 30 s damping feasibility probe. The script constructs the verified public provider, then an independent native AbstractState, and evaluates the two saved density endpoints and logarithmic interpolation at fractions 1/2 and 1/4. It does not modify the kernel, reference, configuration or original dp/dg gates. Native p/h/u/s/rho/T are saved; allow_nan=False rejects nonfinite output serialization. Runner binds the replay result and source/runtime input files. Failure before output serialization remains visible through supervision logs.

The experiment tests availability of a better nearby density pair, not an implemented line-search algorithm, convergence proof or full depletion path. Its endpoint reproduction and original-gate results must be inspected before using it to motivate any isolated solver change. No EOS was executed by this reviewer.

Hashes: replay result `2ac0cde6f63d654b8a755319f743ee26d5976b6330df0ce4a238eb39ae2b11db`; probe `15f1122413b4f0939174cc7aa0fab1650b7cb568cfde48dcca083b2b293cfdea`; runner `0cc82ae2cc911d0bb99a0c50a7ee3f55b0766870c5a90ec50b7bf16d283c6a89`.

## Actual damping probe: local feasibility only

Damping-attempt01 completed, exit 0, external time 1.149743000001763 s. Independently checked all 170 recorded inputs against before/after/current SHA-256 and verified the linked replay hash. Both native endpoint states reproduce the recorded replay densities, p/h/u/s and dp/dg exactly. All four saved native-state dictionaries contain finite numbers. Recomputed pressure and Gibbs differences directly from saved native operands agree with the reported values and original gate booleans.

Logarithmic half step: dp = 2.528966524550924e-5 Pa, dg = 2.4650944396853447e-8 J/kg. Quarter step: dp = 4.2952112380589824e-5 Pa, dg = 3.9639417082071304e-8 J/kg. Both meet the unchanged 1e-4 Pa / 1e-6 J/kg coexistence gates, whereas the two reproduced endpoints fail the pressure gate. This supports investigating a bounded backtracking update on this particular oscillating density pair.

No kernel has been repaired by this probe, no general solver convergence has been established, and the retained combined depletion run is still a numerical failure with zero events. Native-state feasibility at one temperature is distinct from full public snapshot checks or a completed depletion trajectory. Any solver implementation and broader validation remain separate future work. No EOS or tests were run during this result audit.

Damping result SHA-256: `c6ddf1f218a2ca312544c1b6a6f27399b87485ccf44cc5a88f3faea976323741`.
