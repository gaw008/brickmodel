# Eight-cell audit

{
  "verdict": "PASS budgets, not converged",
  "artifacts": 89,
  "steps": 2,
  "evaluations": 15,
  "service_s": 58.90486937499372,
  "prefix_N_E_work_mechanical_roundoff": [
    2.47026571154876e-17,
    5.277028852838227e-12,
    7.247684568425059e-12,
    1.3852976359904806e-16,
    3.970466940254533e-23
  ],
  "center_face": [
    {
      "cells": 2,
      "water": -2.9548160898131963e-17,
      "energy": -1.5258650867835372e-05
    },
    {
      "cells": 4,
      "water": -5.909629780265577e-17,
      "energy": -3.0517162342905686e-05
    },
    {
      "cells": 8,
      "water": -1.1819240365898277e-16,
      "energy": -6.1033209567717255e-05
    }
  ]
}

All sealed artifact hashes and prefix budgets pass; nine mechanical values retained. Exact initial parent inventory/energy sums agree with2-cell baseline. Actual final volumes agree with current normals/common tangent. Center face integrals nearly double each refinement, not a converged value. Eight-cell fine-time control has not run. Prior runtime/case identities differ; no same-runtime convergence or material validation claim. q density scaling is a builder/source property verified separately by nonzeroB tests; this baseline starts B=0, so initial q=1 alone does not establish changing-composition scaling. No EOS/source edits.
