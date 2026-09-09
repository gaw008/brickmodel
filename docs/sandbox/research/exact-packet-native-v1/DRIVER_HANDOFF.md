# Exact ordered packet driver candidate

Frozen driver SHA256: `be323c820fe9f0c0981bb3bc7b4db817c8931c2501e704e394ae85a4c815a16b`.
Frozen test SHA256: `3e96e5a57c69076183daf74da2c4d80bd713c860d1ed698fc43f42312bb790f2`.
Actual final command and results: tests18.log / tests18.xml, 16 passed in 5.92 seconds. No EOS, installation, or repository source modifications were performed by this candidate task.

## Implemented behavior

`integrate_exact_depletion(initial, operator, *, start, end, integration_policy, event_policy, cancel=None)` joins exact ordinary integration, full-state affine terminal executor, real mixed-mode continuation, two consecutive refinement comparisons, and a separate approach with both cap and safe fraction halved. Every event and common endpoint checks the existing time, amount, energy, temperature, pressure, and full mechanical-vector gates. Paired pressure dispatch receives the actual underlying WPT operators, states and inverses; original independent bounds and endpoint costs remain recorded.

All callback times, accepted endpoints, terminal clocks and comparison times remain ExactEventTime/Fraction. Only future ordinary nominal step durations are rounded downward to a representable float for the existing policy; no absolute callback time is projected. Exactly rooted affine polynomials have zero localization remainder, as in the old clock; nonexact roots retain the certified dyadic interval width.

The independently evaluated approach grid contains only actual ordinary endpoints before the first terminal. Later mixed/dry continuation cannot supply apparent independent approach resolution. The candidate explicitly does not reuse an ordinary spine: both paths are computed and charged. It does not claim the legacy cache optimization was exercised.

Original panel budget semantics are retained: accepted ordinary panels + interrupted stage-replan panels + terminal panel attempts. Ordinary rejected trials consume the separate original rejection budget. Ordinary trial counts and predictor attempts are additionally retained as diagnostics; predictors are not newly charged against a gate that did not count them before. Every speculative path and independent approach charges the same global counters and original wall deadline. Accepted prefix auditing recomputes amounts, energy, component sums, stretch increments, exact stretch quadrature residuals and correction totals against the original initial state before atomic publication. Cancellation/domain/resource failure preserves the preceding committed prefix; no speculative mode changes are published.

Recoverable mechanisms are ordinary RK rejection, stage preview replan from the actual returned accepted local prefix, and further refinement after comparison failure. A refused terminal remains fatal as in the original ordered path. The legacy nonordered `_ReduceCommonTime` behavior is not newly claimed or implemented.

## Result boundary

`ExactDepletionResult` is an explicitly new research result. It carries exact times, full histories, packets, refinements, terminal attempts and actual costs. It is not admitted to the old event_record / service resume codec. Some diagnostic observations retain typed provider-containing objects: an external capture must select/encode safe diagnostic fields, not blindly recursively encode arbitrary host graphs. Source checking is performed live; a failure report must not rely on a failing live identity getter to serialize already captured data.

The tests use a strict typed autonomous host with the native-only evaluation seam instrumented. They exercise the actual exact integration, root ordering, full panel, writeback and packet math. The paired pressure dispatch test uses an explicitly labeled helper stand-in and is not a wet pressure proof. The narrow mixed-rate pulse is a control-flow adversary, not an accuracy oracle. No native four-cell packet success has been established by these tests.

## Preserved failures and corrections

- tests08 / acceleration09: actual mixed fixture initially failed comparison because an exactly zero polynomial root was incorrectly assigned nonzero localization-bin width. Corrected by testing the exact polynomial value, without changing physical settings or original gates. tests10 then passed the original fixture.
- tests05: test-only wrong box constructor keyword, preserved.
- tests16: new rejection fixture with rate coefficient 100 did not actually trigger rejection and completed. Preserved. The separate deliberate stress fixture uses 1000 and demonstrates rejection with one accepted panel. No original model/gate was changed.
- tests13/14/15 cover preserved cancellation and wall classifications, initial domain exit and pre-callback water molar-mass admission.
- tests18 additionally checks that post-event continuation exists but its endpoints are excluded from the approach-grid certificate.

Parent controls production admission and all actual native runs. Scientific material qualification, legacy checkpoint compatibility and spatial convergence remain outside this candidate result.
