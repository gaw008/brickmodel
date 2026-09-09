# Atomic exact-affine group accounting and actual four-cell advance

`depletion_group_roundoff.writeback_exact_group` revalidates the complete earliest
exact-common-root group and the shared represented panel clock. Per-cell affine
left/right/source coefficients sum to the inventory model and integrate to the
actual individual panel terms; shared-face coefficients must be opposite. Every
raw N/E/stretch value is reconstructed from the single supplied panel before
writeback. This layer checks supplied quadrature, not its physical derivation.

Each member uses the original depletion_writeback budgets and its own gross
evaporation. Exact-zero members retain None; correction totals are carried once
per actual nonzero correction, and an error exposes no partially updated result.
Energy, mechanics and nonmembers stay as in the raw terminal state. It neither
constructs a trajectory nor admits a physical phase switch. Nonrepresentable
common event clocks and unresolved clusters remain unsupported here.

Initial review found missing model-to-component binding, including the zero
bypass. The original code/tests and actual RED1fail/16pass are retained in the
archive; corrected dedicated tests passed20. Independent rereview closed both
findings. Source regression command:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests/sandbox /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest tests/sandbox/test_depletion_group_roundoff.py tests/sandbox/test_depletion_group_clock.py tests/sandbox/test_depletion_roundoff.py tests/sandbox/test_affine_depletion_clock.py tests/sandbox/test_affine_depletion_guards.py tests/sandbox/test_affine_depletion_integration.py tests/sandbox/test_depletion_multicell.py -q
```
116 passed/30.34s. After frozen offline non-editable installation, the first
three test files passed52/0.11s from /private/tmp without PYTHONPATH. Installed
identity audit matched67 modules. No native run used this new67-module install.

## Actual unchanged four-cell wet-state probe

Before the new installation, the66-module runtime advanced the original4cell
state by2^-14 seconds using the ordinary integrator and unchanged tolerances.
Supervisor session32911 exited0 after4.384s; one accepted step,8 stage callbacks
plus initial/final observations. The original candidate gap0 became
3.371786427888473e-10s, still below1e-8s. It does not solve the selector rejection.
Independent every-prefix N/E/stretch and global external-pressure-work checks
passed original gates (global residual1.20454e-11J). All raw observations, states,
policy, case, runtime hashes, script and review are in the25-member archive.
This probe is numerical positive-stage evidence, not true event-free proof.

## Next full integration work

See INTEGRATION_NEXT.md, including its later ordering note: maximum localization
error and minimum required event separation are distinct. A versioned numerical
path can test strict surrogate root ordering with finer enclosures and actual
post-switch reevaluation while keeping all original full-state refinement gates.
This is a design to implement, not a proven four-cell solution. Joint event
records, mode transition, cancellation/resume and full spatial validation remain
open; original material and full-process Goal scope is unchanged.
