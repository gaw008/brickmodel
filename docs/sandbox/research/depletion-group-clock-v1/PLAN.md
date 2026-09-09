# Affine group clock implementation contract

Baseline: 38b01fd. This implements the pure multi-root step of the preserved
thermal-timescale-v1/NEXT_GROUP_PLAN.md. It does not admit native wet clusters.

Inputs describe explicit quadratic inventories (affine rates), with exact
represented coefficients and a declared interval. No sampled callback is
silently promoted into an affine law. Certificates describe this numerical
polynomial only. All input cells are considered; indexing is serialization,
not a physical ordering assumption.

Validation oracle: exact rational polynomial evaluation and independently
known analytic roots. Exact cases require equality; irrational root intervals
must contain an independently computed high-precision root. Positive-panel
claims must include any internal quadratic extremum. Overlapping root intervals
use their union, with exact common roots distinguished from uncertain ordering.
Time tolerance belongs to the input numerical policy; no material tolerance or
experimental uncertainty is introduced.

Adversarial cases: equal instantaneous depletion ratios with different roots;
different ratios with a common root; earlier cells regardless of index;
overlap chains wider than the original time gate; positive endpoints with a
negative interior; large time origins; invalid/bool/nonfinite inputs. Resource
bounds in root isolation must fail explicitly if precision is exhausted.

Run the new tests and existing affine clock/guard/integration/multicell tests.
Independent code review is required before local commit. Store actual command
results and report native integration, group state correction, event records,
resume, and full spatial study as not yet implemented by this increment.
