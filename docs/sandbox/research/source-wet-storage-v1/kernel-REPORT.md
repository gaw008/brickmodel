# Shared wet fluid closure extraction

Only mass_wet_storage.py and new test_mass_wet_fluid_kernel.py changed. Frozen old HEAD and working copy precede edits. old-golden.json captures full canonical points, hashes, identities and liquid-call counts using the actual existing legal fixture, with its explicitly artificial constant-volume liquid seam and source-bound dry/ideal gases. This is not a native liquid EOS experiment.

RED: 13 missing-API failures and 3 unchanged golden passes in 0.48 s (command wall 0.575 s). Final: 30 passed in 0.62 s (command wall 0.713 s), the new kernel file plus existing mass wet storage file only. No installs, commits, long trajectories or full suite.

WetFluidEvaluation retains actual replaced RigidStorage, actual ClosedStorageState, Fraction global/extra pressure bounds, and float total pressure bound. Caller retains solid volume positivity interval certification. Error Fraction is never replaced by its float validation result. The original closure/pressure-bound arithmetic is moved in its original order; old aggregate U/H, solid terms, inversion and identity fields remain unchanged. check_wet_water moves all original checks verbatim with explicit arguments.

Tests preserve full numerical output and model identity against independently captured old implementation, validate one backend call, immutable template replacement, exact rational bound construction, malformed inputs and global-domain rejection, backend failure propagation, and existing water-source regressions. No new scientific model or material qualification is claimed.
