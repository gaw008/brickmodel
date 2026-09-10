# Independent exact first-root mathematics review

1152 assertions passed against 117 independently constructed rational-factor polynomial/domain cases. The truth cases were written before comparing implementation. Actual check computation took .0693 s after imports. No EOS, native run, physical trajectory, event writeback or material acceptance was exercised.

Reviewed hashes at execution:

- source_net_roots.py: 12dbd5e56dbb40a244d87f4b427d5e7f8082daa68c5152b458590f8d2fd42061
- rational_polynomial.py: 20783e681388e9fa529bc583de35f20a39c54b5d84c7c2f2e44982c23c5c2a48

Both files were unchanged during the check. Artifacts are EXACT_CASES.json, build_cases.py/BUILD_CASES.log, check_implementation.py, actual stdout IMPLEMENTATION01.log and RESULT.json.

## Findings

No blocking mathematical discrepancy found. All positive-initial root/no-root classifications match independently known factors and exact minima. For each root case, eight refinement steps preserve the independently known earliest positive root inside the actual enclosure. Convex dip/recovery and second-root-at-H cases select the first descending crossing. Tangency at the final endpoint keeps exact_tangent classification. Concave initial-gain cases correctly restrict to the descending branch after the maximum. Linear root and exact endpoint behavior agree with the independently known rational roots.

The pair (t-1/4)(t-3/4) and (t-1/2)(t-3/4) has GCD root3/4 but distinct first roots; actual same_first_root returns false and ordering selects1/4. A later tied liquid group does not outrank an earlier gas root. Proportional first roots produce a tied group without event permission. Zero-initial gas states with zero, negative and initially positive derivatives yield unsupported_zero_initial and complete=false. A close irrational-root pair with one allowed refinement remains unresolved/incomplete rather than inventing order.

Forged branch endpoints, enclosures, bool refinement counts, no-root minima, status/earliest labels/complete/qualification fields are rejected on construction or check. Float coefficients, zero horizon and energy-as-inventory inputs are rejected. The distinction between constructor and explicit check is retained: InventoryRootOrder is revalidated by check, not automatically on dataclass creation.

The shared refinement helper keeps the legacy p(mid)>=0 lower update, including exact midpoint and upper-root zeros. Reading the legacy diff confirms the old exact evidence construction, exception paths and loop positions remain in place; its arithmetic transformation is from a sum of exact Fraction quadratic terms to the same exact polynomial/Horner sign, not an inexact float reassociation. GCD extraction preserves the original rational Euclidean steps and old wrapper interpretation. Separate legacy test evidence is still required for full return-record parity; this reviewer did not rerun the entire old event suite.

One non-mathematical hardening note was sent to the implementation author: SourcePanelRootOrder.check currently accesses self.order.maximum_refinements before an explicit InventoryRootOrder type check. A forged non-order object can therefore raise AttributeError instead of a controlled ValueError. The new arithmetic's valid-record behavior is unaffected; this is a record-validation surface concern for the code reviewer/author.

The source panel wrapper enforces all four fluid inventory labels per cell and excludes energy polynomials from depletion competition. Root evidence remains numerical first-zero evidence; it does not resolve zero-state constitutive laws, prove true ODE event times, or authorize evaporation/transport correction and post-depletion continuation.
