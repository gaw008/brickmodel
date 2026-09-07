# Independent Python review: certified pressure-bound bootstrap

Verdict: APPROVE this scoped numerical-bound change. No CRITICAL/HIGH defect found. Read-only source/diff/AST/XML review; no EOS, fixture import, tests or probes executed by this reviewer, and no production/test file edited. Ruff/mypy/pylint/black unavailable on PATH.

Reviewed bytes:

- src/sludge_sandbox/solid_fluid_storage.py: `67e407cdce28a159902f292d53d4076b507a2bb43c6fb2989b8699423f8580e6`
- tests/sandbox/test_solid_pressure_bound.py: `a7fcb5a3919d2102a581c0fc4ab2d93e0d90659735b873311db649067751b6ae`

## Production assessment

The actual ten-line insertion retains the original global d0 calculation and pressure-error addition. It checks that whole original p +/- error interval is within the original mechanical pressure bracket *before* tightening. Thus no previously rejected uncertainty/domain case is rescued by a narrower local estimate. The existing final interval-domain check remains after tightening.

The local upper endpoint is min(global envelope upper, p + original outward total error), with all operands converted to exact represented Fractions before addition, min, squaring and division. Since the original accepted interval is above the positive pressure lower bound, certified_upper is positive. Positive ngRT was already checked through bmin; exact arithmetic cannot introduce a zero local derivative. No rounded-down float upper endpoint is used. _directed then converts the additional radius outward and _sum_upper retains the original fluid-only radius. Original bounds are finite checked values, and bound overflow/nonrepresentability continues through existing explicit numerical exceptions.

Both the baseline-volume root and volume-perturbed root lie in the original global interval. Their connecting segment has P <= certified_upper. For stable liquid, -dV/dP >= ngRT/P^2 >= ngRT/certified_upper^2, so the same available-volume uncertainty produces an additional pressure displacement no greater than the new bound. This is the preregistered bootstrap proof, not evaluation of a derivative only at nominal pressure. It relies on the same stable-liquid and declared-uniform-error conditions as the existing global propagation; it does not newly qualify arbitrary source laws.

The added uncertainty is still the complete error_v, including declared solid-volume errors, bulk error and representation error. No source parameter, domain, pressure bracket, acceptance tolerance or material status changes. Fluid error is untouched. The reassigned extra_p is used consistently by the existing liquid energy-error term later in the method; pressure and energy no longer use different geometry-pressure estimates. No public API or return schema changes, no added EOS evaluation, no cache, and no altered nominal mechanical state.

## Test independence and actual evidence

The seven tests use independent rational roots P=ngRT/(V +/- deltaV) with exactly representable reference geometry. They check both asymmetric uncertainty signs, retain a nonzero original fluid error, include solid-only and bulk-only uncertainty, verify zero-extra-error identity, test a near-upper-bracket case, retain original global-domain rejection even when a tighter ideal-gas answer would fit, and reject uncertainty reaching zero pore volume. The >100-fold improvement assertion distinguishes the specific motivating conservatism; it is accompanied by containment checks and is not used as a substitute for them.

Their exact_binary_ceiling oracle duplicates the mathematical definition of an outward binary ceiling but does not call production conversion or pressure-bound helpers. Comparing the old global radius respects its actual two outward conversions. The manufactured declared u error is kept consistent with p_ref*delta_v; this only fixes fixture consistency, not production source values.

Inspected actual baseline02-tests.xml: seven tests, three failures, zero errors/skips, 0.462 s. Each failure is the intended >100-fold tightness assertion for one of the three positive-volume-error parameterizations. Inspected candidate-tests.xml: seven tests, zero failures/errors/skips, 0.441 s. Historical initial baseline fixture evidence is preserved separately; no original failure is rewritten.

These seven are dry, no-native-EOS tests. They prove the independent ideal-gas root enclosure cases, not a new empirical wet-EOS uncertainty certificate. Wet/stable compressibility support is justified by the existing mathematical/source contract and still requires the root-owned related wet regression and original source-bound coupled-run verification. No passing coupled depletion, full regression or overall Goal completion is asserted by this approval.
