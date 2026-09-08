# Four-cell time audit

{
  "steps": [
    2,
    4
  ],
  "runtime_equal": false,
  "initial_numeric_equal": true,
  "initial_energy_identity_equal": false,
  "changed_case_sections": [
    "case_id",
    "refinement",
    "numerics"
  ],
  "endpoint_differences": {
    "amounts_mol": 1.1102230246251565e-16,
    "internal_energy_j": 2.9103830456733704e-11,
    "mechanical_stretches": 4.440892098500626e-16,
    "temperature_k": 5.7980287238024175e-12
  },
  "paired_T_bound": 8.242679428856668e-08,
  "prefix_N_E_work": [
    9.318913548881963e-17,
    1.945716586661259e-11,
    3.92292357346328e-11
  ],
  "service_seconds": 53.14154100001906
}

PASS: saved fine artifact hashes and all-species/energy/externalwork prefix budgets. Initial numeric states equal, but case-derived energy identity differs and runtime versions differ; first audit explicitly detected identity inequality rather than assuming it. Actual meshes2/4 panels. This is cross-version time-control comparison, not exact same-runtime replay. Temperature difference is below the paired inverse uncertainty and cannot be claimed resolved accuracy. No EOS/source edits. Eight-cell data not read pending terminal notice.
