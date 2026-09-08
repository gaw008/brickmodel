# Independent saved-result audit

Pure standard-library Fraction recomputation; no EOS, tests, installation or repository edits.

```json
{
  "disposition": "PASS no blockers",
  "hashes_matched": 162,
  "trajectory_sha256": "8c1c656e4e2fe5cc41ec0f42a15bb66ec720a1fc8898d54580f00fc836253075",
  "prefix_maxima": {
    "water": 5.4062724891452973e-17,
    "external_work": 1.3595373028759336e-11,
    "stretch_represented": 1.1947230314432455e-16,
    "stretch_exact": 1.1947054984602628e-16,
    "stretch_abs_roundoff": 1.7532982982783005e-21,
    "local_energy": 1.4290024106513796e-11,
    "constraint_represented_abs": 2.710505431213761e-20,
    "constraint_exact_abs": 4.996003610813205e-20
  },
  "endpoint_differences": {
    "amounts_mol": 6.130079083233042e-16,
    "internal_energy_j": 0.0,
    "mechanical_stretches": 9.103828801926284e-15
  },
  "logged_temperature_difference_k": 3.410605131648481e-12
}
```

Both original step caps and original accuracy gates retained. One/two accepted panels, 8/15 evaluations; every cell water, fixed inert/solid, zero mass faces, opposite local phase directions, shared nonzero heat, local total-energy ledger, global pressure work, full three-component mechanical state and exact/represented constraint cancellation pass. Source hash comparison uses actual current files. Temperature comparison is independently subtracted from recorded final decode values, not newly recomputed with EOS. Full fine/coarse inverse states are not saved in trajectory.json. This demonstrates a short real-water/manufactured-skeleton phase-transfer numerical coupling, not an independent physical trajectory oracle, spatial convergence, liquid face transport, depletion event or real-sludge validation.
