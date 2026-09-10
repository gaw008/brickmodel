# Independent audit of actual failed native exact-source run

**The native experiment did not complete.** The inner result is resource_limit / wall_time_limit, with two attempted trials, one rejected trial, twelve actual callback captures, zero accepted steps and only the unchanged initial state in the accepted prefix. The outer runner then reports failed / complete_original_segment_required. This is not an accepted-step ledger audit and not a successful integration result.

Input SHA256: `c9485fc029de2593183f2db5ecaeca1faba3d7c4561691ede9398521c5b85a48`.

The original planned eight-capture success audit is preserved as PREPARED_EIGHT_CAPTURE_AUDIT.py. The actual failure-specific reproducer is audit_failure.py, stdout FAILURE_AUDIT.log and numerical evidence FAILURE_RESULT.json. 272 independent assertions pass. Only standard-library JSON/Fraction/math operations were used, with no EOS/model import or new trajectory.

## Failed first trial reconstructed independently

The audit follows the actual saved callback ordinals, without merging equal times:

- ordinal0: initial validation at t=0;
- ordinals1/2: full-step Heun pair at 0 and 1/1024;
- ordinals3/4: first half-step Heun pair at 0 and 1/2048;
- ordinals5/6: second half-step pair at 1/2048 and 1/1024.

It reconstructs the full trial and both fine half trials using exact rational duration times the represented rates, product rounding, each half's two-rate sum rounding, face-divergence rounding and state update rounding. It independently checks all observed Euler predictor inputs and the saved second-half initial state against those reconstructions. The fine result is reconstructed for error comparison; it was rejected and was never an accepted endpoint callback/state.

The controlling component is cell index2 (third cell), U. Fine minus full energy is +0.04345047037350014 J. The original combined scale is energy_abs_tol + relative_tol*energy_scale = .001 + 1e-8*1e5 = .002 J. The two equal half-step leading-error factor is 1/3, yielding normalized error **7.241745062250023**, above the unchanged acceptance threshold1. The first trial was correctly rejected under the declared policy. An exact internal face balance would not imply zero temporal error.

The original controller proposes h * max(.2,.9*error^(-1/3)), then rounds the nominal duration downward to binary64 and adopts that exact value. Independent reconstruction gives:

`523754638258309/1152921504606846976 s = 0.0004542847333192145 s`.

This exactly matches the second attempted trial's saved times. Ordinals7/8 are its full-step pair, ordinals9/10 its first half pair, and ordinal11 the start of the second half. The clock is exhausted before the second-half endpoint evaluation and possible accepted endpoint validation. The second trial has no complete fine state/error/accepted ledger, so its numerical acceptance cannot be inferred.

## What all twelve saved callbacks establish

All twelve mappings preserve exact semantic time and ordinal, three-cell/four-fluid layout, energy-model binding, fixed dry kg in source states, and total U. Liquid plus three gas face rates and total face energy map exactly to generic Rates. Local source rows are (-phase,0,0,+phase), with zero added cell power. Original source-evaluation gas, conduction and liquid enthalpy components remain present and sum correctly. Liquid boundary flow is zero. Final unpacked states equal the initial accepted states.

These are valid mapping/assembly checks, not successful time integration. With zero accepted steps there are no accepted quadrature fields to audit and no nontrivial accepted global water/U change to interpret. Trial states must not be called completed prefix states.

## Resource recommendation without changing scientific gates

The actual inner elapsed time is 82.158861 s against a 75 s cooperative budget. The overshoot is consistent with checking the wall guard after a costly callback completes; it does not show a tighter hard callback timeout. Twelve completed callbacks cost about 6.85 s each on average including overhead. The existing outer90 s cap allowed the failed result to persist.

Keep the scenario, endpoint1/1024 s, initial/max/min steps, absolute/relative tolerances, inventory/energy scales and original step/rejection limits unchanged. A bounded rerun may raise only resource limits, for example inner450 s and outer510 s. This conservative allowance follows approximately57 callback opportunities from the existing accepted/rejection caps times the observed average cost, with overhead margin. Actual callback cost varies and future rejection/domain behavior is unknown; this is an evidence-based budget, not a completion guarantee. An expected two or three accepted segments would cost less, but that has not been established by this failed run. Do not loosen the .002 J combined error scale, shorten the scenario or treat resource exhaustion as a scientific pass.

No code files or native original artifacts were changed. The failure remains preserved. Source material qualification and transportation-depletion writeback remain outside this audit.
