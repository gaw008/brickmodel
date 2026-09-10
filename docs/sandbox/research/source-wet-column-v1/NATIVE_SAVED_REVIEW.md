# Offline audit of saved native three-cell one-step ledger

**Passed: 47 independently evaluated exact/structural assertions.** Only the standard library JSON reader, Fraction arithmetic and SHA256 were used. No EOS, model evaluator or trajectory was run. No repository files were changed. The existing root `ledger_checks: 20` count was not used as evidence for these assertions.

Audited file: `/private/tmp/brick-source-wet-column-v1/native-one-step.json`

SHA256: `620a9603fc12345c702b5b78934d50da0fb6fc29ae048a2828a16f7bcb0c45ab`

The saved result reports `completed`, reason null, 3 attempted and 3 completed evaluations, and 23.03118550000363 s. Its prefix contains two three-cell state snapshots, exact times 0 and 1/1024 s, one accepted ledger, one three-cell endpoint observation, and a three-cell midpoint snapshot. Endpoint inverse targets match the accepted cell energies. Run and observation both have material_qualified=false. Endpoint chemical rates are zero.

For each cell, the script independently recomputes energy old+left-face−right-face+signed projection correction; liquid old−phase+correction; and each gas old+left-face−right-face+water phase (H2O only)+correction. Every exact Fraction equality passes. Dry masses and energy-model identities are unchanged. Both external faces have exactly zero gas and energy exchange. Each shared face's total energy equals conduction+diffusive enthalpy+advective enthalpy+its explicitly signed decomposition correction.

| Global quantity | Exact accepted change | Sum of signed accepted projection corrections | Balance residual |
|---|---|---|---|
| U | 0 J | 0 J | 0 |
| O2 | 0 mol | 0 mol | 0 |
| N2 | 0 mol | 0 mol | 0 |
| liquid+vapor water | -5/576460752303423488 mol | -5/576460752303423488 mol | 0 |

Thus the saved global water total changes by approximately -8.67e-18 mol solely due to its recorded projection correction. It would be inaccurate to call the stored binary64 water total exactly unchanged. Its audited conservation balance, including signed correction, is exactly zero. Predictor roundoff is correctly excluded from these accepted-state balances.

Artifacts: `check_native_saved.py`, actual stdout `NATIVE_SAVED.log`, and `NATIVE_SAVED_RESULT.json` contain all 47 checks and hashes.

This audits the arithmetic and structure of an already saved native result. It does not independently reproduce the EOS, phase kinetics, constitutive face rates, or timing, and it does not establish reality-matched material validation. Manufactured geometry/transport, closed boundaries and all remaining full-model requirements remain in force.
