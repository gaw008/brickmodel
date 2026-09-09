# Whole-state exact affine panel

Baseline a89bf04. Frozen module exact_terminal_panel.py SHA 2fdfb079e77c37c83745fe97cfd61ee4492c26814a80a762e0adc3ddf5490078. The permanent test replaces the temporary importlib loader with the installed package import; all test logic is unchanged.

Integrates every shared face/source/energy/component/stretch field over the same exact interval, rounds each term once, reconstructs the raw state and ExactStepLedger, and checks whole-polynomial inventory/stretch minima including interior extrema. Competing wet cells remain strictly positive. Local N/E checks compare represented state to represented ledger; they are not a bound on total affine-quadrature truncation error. Midpoint validity and actual source authentication remain caller responsibilities. See HANDOFF and CODE_REVIEW.

Combined source 68 tests passed in 5.18 s; installed 36 passed in .40 s. The complete original failed panel and actual mixed-mode endpoint were tested using this module; shared evidence is in ../exact-full-panel-replay-v1. This is a numerical terminal component, not event acceptance, spatial convergence or material validation.
