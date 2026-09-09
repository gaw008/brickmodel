# Atomic joint depletion accounting contract

Baseline f9d57c0. Reuse original per-member DepletionRoundoffPolicy and exact
cumulative DepletionRoundoffTotals. A group must not pool gross evaporation to
rescue a failed member, reset totals, duplicate its common trajectory ledger,
or change energy and mechanical state during water phase writeback.

The initial implementation covers explicitly certified affine common roots and
already reconstructed shared terminal states. Revalidate full root membership
and earliest ordering; do not trust a RootGroup instance as proof. Every member
requires its own panel terms and evaporation diagnostic. Any member failure
returns no accepted updated group; caller state and prefix remain intact.
Exact-zero corrections remain None, never artificial positive adjustments.
Nonrepresentable times need an explicit existing clock certificate and original
time budget or must be refused. Finite localization shifts are not roundoff.

Independent tests: exact arithmetic water/element/mass deltas for every member;
unchanged energy, mechanical coordinates and nonmembers; failed last member
leaves original state/prefix unchanged; local evaporation cannot borrow;
cumulative budget counts each correction once; missing/duplicate/late-root and
unresolved-cluster rejection. No material parameters or tolerance changes.

This accounting helper is not full group integration, physical mode admission,
shared panel quadrature construction, or spatial-convergence evidence. The next
integration design should retain the existing numerical RK/refinement contract
without mislabelling it as a rigorous true-RHS event enclosure.
