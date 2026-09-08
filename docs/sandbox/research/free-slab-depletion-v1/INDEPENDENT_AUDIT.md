# Independent saved-result audit

Standard-library Fraction recomputation only; no EOS or repository edits. All 163 recorded source hashes matched before root was notified it could unfreeze.

```json
{
  "verdict": "PASS no blockers",
  "hashes_matched_before_changes": 163,
  "result_sha256": "acb0554880a54f9972e4095463a7fcfcb59c26fd0bec39e60267805e739e699e",
  "prefix_maxima": {
    "water": 3.8402440949436567e-16,
    "cellE": 1.652687733803235e-10,
    "globalwork": 1.06007702942873e-10,
    "mechrep": 4.678617189103466e-16,
    "mechexact": 4.678618568200983e-16,
    "mechroundoff": 7.336841286766986e-22,
    "constraintrep": 1.5811557408951124e-20,
    "constraintexact": 1.620850361686958e-20
  },
  "local_abs_constraint": [
    4.251593752834242e-06,
    4.251593752834234e-06
  ],
  "independent_differences": [
    9.825582188149884e-20,
    6.661338147750939e-16,
    1.1641532182693481e-10,
    1.0670047450737493e-07,
    1.4315056156706802e-05,
    6.661338147750939e-16
  ],
  "steps": 19,
  "evaluations": 305,
  "elapsed_s": 436.1729927919805
}
```

Exactly event cell0 and mixed depleted/existing-liquid final modes retained. Spectator condensation remains active in saved final callback. All original six refinement gates pass, two terminal passes followed by a distinct-grid independent halved-controls branch. Local constraint work is nonzero and globally cancels within arithmetic budget; no omitted local work assumption. Every prefix water, energy/face contribution, mechanical represented/exact/roundoff, external work and component cancellation checked. The speculative independent trajectory is represented by comparison records rather than a full separately saved trajectory. This supports a bounded numerical mixed-interface coupling result, not an independent complete physical trajectory oracle, spatial convergence or material admission.
