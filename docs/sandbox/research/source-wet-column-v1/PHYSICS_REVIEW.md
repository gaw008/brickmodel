# Independent review of SourceWetColumn

## Finding

No blocking physics or ledger discrepancy found in the reviewed implementation. This is a fixed-source-mass N-cell closed slab with explicitly manufactured geometry and transport. It is not the full furnace boundary, moving host, event solver, or a matched-material predictive model.

Reviewed column SHA256: `33ed852d8a9ad73355369c954f6121dbb452b1647be76f0c9132110c8231abd0`. Helper and test hashes, script hash and runtime results are saved in RESULT.json. All three reviewed files were unchanged from start through end of this independent execution. The repository was not modified by this reviewer.

## Contract review

- N >= 1, N+1 ordered face observations, exact closed endpoints, and N-1 single shared internal evaluations implement the intended oriented chain. Internal f connects f-1 to f; the middle cell receives face[i]-face[i+1]. Nonuniform half-widths and face area are checked against slab geometry. The upper uncertain available-fluid volume is bounded by declared geometric bulk volume without inventing solid specific volume.
- Storage binding preserves source dry caloric identity and reference, actual gas caloric identity and liquid/vapor thermal-chemical conventions. Dry masses are fixed by each storage; chemistry is explicitly disabled. Phase transfer uses opposite liquid/vapor molar increments with no added latent-energy source.
- `_integrals` stores exact rational duration times the single binary64 face/phase rate. `_advance` sums old plus both adjacent face increments plus phase exactly before one projection per state component. Its signed projection residual is correctly defined as projected minus exact candidate. Repeated float admission does not change the already projected values.
- Full midpoint advancement starts from the prior accepted state. Predictor roundoff is separately stored and excluded from accepted global balances. Resource roundoff accounting includes predictor and full-step projections and energy decomposition discrepancies; the docstring correctly excludes temporal truncation, inverse propagation and physical fit error.
- Exact candidate negativity and undeclared dry states fail; no clipping or automatic depletion switch exists. Endpoint evaluation precedes all accepted-state/time/observation/ledger append operations. Failure during any trial therefore preserves the prior accepted prefix. No exact-event/adaptive/resume or programmed boundary admission is implied.
- Signed cumulative conservation correction is recoverable exactly by summing accepted ledger.roundoff fields. Run-level used amounts are absolute resource budgets and must not be substituted for that signed conservation correction.

## Actual independent numerical experiment

`check_column.py` used the declared test setup with artificial constant-v liquid `v=1.8e-5 m3/mol`, `u=75 T-300000 J/mol`, source dry Cp polynomial, and existing source gas caloric functions. The reference never calls Column.evaluate, SourceWetStorage.evaluate/invert, or extracted wet face/phase helpers. It computes storage U with the printed source polynomial and artificial liquid expression, independently finds temperature via scipy brentq, computes pressure directly from the artificial-volume closure, obtains chemical equilibrium from its existing primitive, and combines conduction plus gas face primitive transport/enthalpy independently. Thus the aggregate balance, nonlinear inverse and ODE integration are independent; gas face constitutive physics and source caloric/chemical primitives are reused.

A single independent RHS probe took 0.000821 s. DOP853 used 38 RHS calls over a preselected 0.25 s interval. Production midpoint used 2, 4 and 8 steps; total bounded check took 24.37 s and exited 0, below its 55 s hard cap. This was not a real-water run.

| Midpoint steps | Max energy difference from DOP853 (J) | Max inventory difference (mol) | Production run (s) |
|---|---:|---:|---:|
| 2 | 0.0014523929057759233 | 1.7565393473084612e-7 | 3.463 |
| 4 | 0.00035770328395301476 | 4.325259350679289e-8 | 7.035 |
| 8 | 0.00008876078936737031 | 1.0731719624068603e-8 | 13.763 |

Energy refinement ratios are 4.06033 and 4.02997; inventory ratios are 4.06112 and 4.03035. These support second-order convergence for this smooth bounded test, not a general error bound. DOP853 is a numerical reference, not mathematical truth. Reference tolerance and nominal source assumptions are recorded in the script.

Every accepted step was also checked with exact Fractions: global U, O2, N2 and total water changes equal the corresponding signed accepted projection corrections exactly. The middle cell's energy change equals left-face energy minus right-face energy plus its own projection correction; its dry mass remains unchanged. The initial middle-cell energy rate is -16.229998152284026 W, and both adjacent faces participate.

The resource arithmetic budget is much smaller than the finite-step integration error in this example. This is expected and confirms why it must not be described as a time-integration or physical prediction bound.

## Remaining scope

Closed endpoints do not replace the required ultimate furnace environment. No claim is made about real transport coefficients, actual raw-material available volume, matched source identity for Nylen observations, native EOS trajectory performance, moving cells, event-localized drying or complete kiln simulation. Those remain separate implementation and evidence requirements. Root's planned native three-cell evaluation cost probe must be reported separately from this artificial-liquid experiment.
