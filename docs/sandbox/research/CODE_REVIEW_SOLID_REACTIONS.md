# Independent review: solid reactions and full-storage source coupling

Verdict: APPROVE within the explicitly declared continuous-net-source, fixed-bulk, manufactured-validation scope. No unresolved high-confidence findings remain after the compatibility/domain fixes below. This is not qualification of real carbon pyrolysis, sludge pseudocomponents, oxidation kinetics, product yields, or sintering.

## Corrected findings and actual verification

A confirmed positional compatibility regression initially inserted reaction_cells between existing LiquidFace evaluation defaults. Independently reproduced the old eight-positional-argument call: it silently put 'fixed_decoded_temperature' into reaction_cells and False into liquid_pressure_interval_scope. The implementation now appends reaction_cells after all previous fields. The author added a failing regression first; reviewer independently passed the final old-call regression. Kinetic temperature-domain failures were also explicitly mapped to DomainExit rather than being reported as a generic numerical/configuration IntegrationError. Final tests cover this distinction. Neither fix changes the reaction equations.

Reviewer executed final frozen tests serially:

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_solid_reactions.py -q --junitxml=/private/tmp/solid-reactions-review.xml
13 passed in 0.49s
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_reactive_solid_fluid_heat.py -q --junitxml=/private/tmp/reactive-solid-host-review.xml
8 passed in 2.42s
```

Both processes exited zero. XML bindings are listed below. No concurrent or repeated heavy integration was used for this review.

## Binding and source identity

SolidReactionConfig admits the explicit existing ReactionNetwork and exact supported providers. Every declared network species maps injectively to one complete-layout column, with all network species covered; extra inert host columns remain zero. Bindings may use documented aliases rather than silently equating phase names. Construction checks the actual phase, molar mass, molar basis, common formation-energy reference, and provider semantics in every storage. Gas identity includes the complete caloric branch/coefficients/anchor, selected segment and sources; solids include their full caloric/volume model; liquid water compares reference, assets and numerical settings rather than a private independently loaded EOS object's identity. Kinetic R must match the actual mechanical gas R.

Elements remain explicit SpeciesDefinition declarations. Their exact stoichiometric conservation and separate declared-mass balance are handled by the existing audited ReactionNetwork; they are not inferred or independently validated from a heat-capacity table. Aliases and nonempty source labels are not material admission. The configuration, network/provider and geometry manufacturing gates propagate through the host and both outer wrappers. Classification-only tests relabel synthetic controls to isolate a gate and remove only the reaction configuration as the negative control; they do not qualify the relabelled data.

The public cell evaluator verifies that its row and supplied decoded state's liquid/gas/solid inventories agree. This detects stale inventory pairing but cannot prove an external caller supplied the state belonging to its target U. The actual SolidFluidHeat path provides that guarantee by performing one current full-storage inverse, binding the same storage objects and layout, then passing those results directly. ReactionRates, actual nominal T, current bulk volume and binding/source identity remain available in reaction_cells. Rates do not carry a rigorous uncertainty interval propagated from the inverse temperature bound.

## Physical and numerical coupling

The normalized Arrhenius law uses actual mol divided by current cell bulk volume; it does not substitute gas pore volume, gas partial pressure, solid activity or surface area. Positive activation-energy tests compare rates at two actually decoded temperatures against an independent exponential ratio. Zero necessary reactant inventory makes the corresponding positive-order pathway rate zero. O2 recognition and element/mass accounting come from the explicit network, not an external atmosphere flag.

One stoichiometric source vector is mapped into Rates.reaction_species_mol_s. Current Ns changes the next trial's solid volume and available fluid pore volume, and the existing total-U inverse reconstructs T/P with all current gas/liquid/solid inventories. Formation energies are already present in species internal energies; there is no extra reaction heat or pQ in cell_power. Gas and liquid faces, conduction, dynamic outer heat and WaterPhaseTransfer preserve the same existing ledgers. Water transfer adds its equal/opposite water source onto the reaction matrix rather than replacing the solid reaction source. The combined diagnostic-chain test evaluates these mechanisms together; it is not claimed as a long fully combined firing trajectory.

The root explicitly selected continuous coupled net-source ODE semantics. The old maximum_forward_step_s and amounts_after_extents gross-consumption helpers are not automatically called. They must not be described as active integration guards or a universal ban on intermediate formation and consumption within one time interval. Actual stage positivity and error control remain in the integrator; no clipping or arbitrary product/oxygen creation is introduced. General cycles, stiff kinetics and intermediate networks need their own accuracy/convergence validation. The finite-oxygen test uses a network that never generates O2, so its initial oxygen-supply upper bound is applicable.

## Independent local oracle and actual host coverage

A reviewer-selected case changes the normalized second-order law to A=.125 mol/(m³ s), Ea=0, c_ref=2 mol/m³, Nsolid=.3 mol and bulk=1e-4 m³. Direct arithmetic gives extent=.125*1e-4*(.3/(1e-4*2))²=28.125 mol/s. With the full layout reordered and the binding tuple independently reversed, the actual returned source is (28.12499999999998,-28.12499999999998,0,0), agreeing within 1e-12 absolute and preserving inert columns. This independently checks both bulk normalization and alias/layout mapping.

The 13 binding cases cover sourced liquid/gas-water aliases, phase/mass/R/provider mismatch, incomplete/duplicate mappings, zero reactant, kinetic domain, cross-cell caloric differences, immutable configuration and invalid row/identity contracts. The eight final host cases include actual finite-O2 integration, O2=0 stopping only oxidation, an independently decaying feed trajectory, accepted-prefix C/O and mass conservation, nonnegative finite inventories and oxygen upper bound, fixed total U, changed Vs, and a final temperature lower error endpoint above the known initial 300 K. Positive Ea=12000 J/mol two-temperature rates match the independent exponential ratio. The program/water/liquid/reaction diagnostic chain and isolated manufacturing propagation are also exercised.

The oxygen trajectory is finite-supply, not a claim that positive-order depletion reaches mathematical zero in finite time. Exact-zero oxygen behavior is tested separately. The thermal result is assessed against the final conditional inverse bound rather than a bare floating-point inequality. All chemical/caloric/volume values in this host fixture are explicitly manufactured; use of source-gated inactive water does not make the reacting materials real.

## Independent whole-coupling analytic reference review

Read the root's SOLID_REACTION_ANALYTIC_PLAN and separate 60-digit Decimal reference. For constant Shomate Cp, h=Cp*T+1000F; the solid u adds -p0*vs, and gas u subtracts R*T. With Ns=N0*exp(-t), product gas=N0-Ns and fixed carrier, total U gives T=(U0-sum(N*offset))/sum(N*Cv). Gas volume=bulk-Ns*vs then gives P=Ng*R*T/Vg. These formulas use actual binary-float input F coefficients converted exactly to Decimal, not fictitiously exact arithmetic in the earlier float anchor construction. The A=1, c_ref=1, first-order, Ea=0 bulk law indeed reduces to dNs/dt=-Ns.

The reference imports neither reaction rate, storage inverse nor integrator. Its negative product formation enthalpy is explicitly manufactured and cannot be interpreted as real solid-carbon gasification. It supports an independent coupled inventory/U/solid-volume/pressure numerical experiment. It does not establish realistic activation-temperature stiffness or material kinetics. Final candidate inspection/results are recorded separately below.

## Final reviewed implementation bindings

| File | SHA256 |
|---|---|
| `src/sludge_sandbox/solid_reactions.py` | `83730a4c6cd2719e76fd6a3e1ac3ed226e880c3cf9dd6c0de77c343fa8e0c21b` |
| `src/sludge_sandbox/solid_fluid_heat.py` | `989ce9db821414f1af0b2e2fa39b046c2e7221c2c4726ccac329fe8409c56243` |
| `src/sludge_sandbox/programmed_solid_fluid_heat.py` | `5d48830c42f7bcb52c81bfe9c5a52ba23468bf0e652537df8819237b1e9dc924` |
| `src/sludge_sandbox/water_phase_transfer.py` | `0160e55f5caaef9a618ede5d359b59c87c6d725570cf47255084ae76f233f951` |
| `tests/sandbox/test_solid_reactions.py` | `854489b680fe664424380f0b67bf2d1f0cc6a6d3ba96c2ad0729bf5b00130993` |
| `tests/sandbox/test_reactive_solid_fluid_heat.py` | `e39f3c26b2bfafa00ce20d153916e093290a4d3c4973a6e06f2c65639793996e` |
| `docs/sandbox/SOLID_REACTIONS.md` | `3a50a2a7acd8141bfc3872b5027deffff2fee161ece4dc0db802ba3b62c6e53c` |
| `docs/sandbox/REACTIVE_SOLID_FLUID_HEAT.md` | `67a3d52bdf474c69874d80d0bb08042608ab2bd50b817f8a0133a3ec87ed9d2b` |

| Independent XML | SHA256 |
|---|---|
| `/private/tmp/solid-reactions-review.xml` | `b28ecf3395b302bc5487f26d4690dc7d2d94894f40fc135e74596b4abb350098` |
| `/private/tmp/reactive-solid-host-review.xml` | `1f8e919f75afcd3a6fd0fd2c3522032bab79d8657a3cff995262f3a025b979d8` |

## Final three-grid candidate inspection

The implementation worker executed attempt_001 and attempt_002; this reviewer did not repeat those integrations or the parent-reported 833-test installed suite. Both attempts are preserved and passed. Attempt_002 adds explicit rejected-trial/evaluation counts, actual step-energy checks and fixture/source bindings. Independently compared all fields of all 227 old/new CSV records: every field existing in attempt_001 is unchanged in attempt_002; the step-energy column is additional. This is an evidence-detail update, not a physics or acceptance-threshold change.

Read the entire final candidate script. It builds the explicitly manufactured Xsolid -> Xgas first-order network, actual bound providers and complete SolidFluidHeat host; it calls the real integrate function and decodes every accepted state. Reference values come from the separate pre-existing analytic function. Initial U is generated by the actual host; it is checked against the independent formula, not substituted from the oracle to force conservation. The full trajectory includes actual current Ns, product gas, unchanged carrier, T, P, U and conditional inverse T bounds. Formation energy and current solid volume therefore participate in the actual candidate inverse throughout. The permissive local integration policy intentionally isolates fixed-step truncation; the separately registered physical-unit acceptance limits remain unchanged.

Independently rederived the solution using fresh 80-digit Decimal arithmetic without importing either candidate or reference module. For all 227 CSV rows, recomputed Ns, constant U, T and P and reproduced every corresponding recorded absolute error exactly at the float comparison boundary. Separately recomputed the C/N inventories and total mass from the raw mol columns, every reported maximum, the actual time differences, accepted-step counts, endpoints and .25/.5/1/2 s checkpoints. Confirmed carrier inventory is exactly .01 mol and every saved U equals its initial U. Verified every listed current dependency hash and the CSV hash in attempt_002 JSON against the actual files.

| Actual dt (s) | Accepted steps | Max Ns error (mol) | Max T error (K) | Max P error (Pa) |
|---|---:|---:|---:|---:|
| 0.0625 | 32 | 6.130220242734664e-7 | 0.005742031439694983 | 25.408816957788076 |
| 0.03125 | 64 | 1.5145879413798122e-7 | 0.0014186797902766557 | 6.2777367607923225 |
| 0.015625 | 128 | 3.7642782987033774e-8 | 0.00035261696194766046 | 1.5602576524834149 |

All three finish at 2 s with exact uniform binary step differences and zero rejected trials. Actual model evaluations are 225/449/897. Inventory error ratios are 4.047450844716182 and 4.023581205198135, meeting the preregistered >=2.8 and monotonic-decrease requirements. The finest inventory/T/P errors meet 1e-6 mol/.02 K/100 Pa. Maximum recorded inverse T bound is 2.871455730655821e-9 K, well below the observed temperature discretization error.

Maximum total-U/reference, step-energy and prefix-energy errors are zero in the saved output. Carbon error is at most 6.938893903907228e-18 mol, nitrogen error zero, and mass error at most 5.421010862427522e-20 kg. Those are within the original thresholds. The step/prefix ledger calculations in the script use actual run.steps face-energy and cell-work fields; CSV retains their residuals, not a separate full raw face-work history. The independent saved-state check establishes constant U for this explicitly sealed, zero-power case. It should not be represented as an independent reconstruction of an exported nonzero boundary-work ledger.

Failure handling inside the candidate execution captures exceptions and writes a numbered JSON and any collected CSV rows. A zero error causing an undefined ratio would be caught as failure rather than silently passing. Numbering checks existing attempt JSON files, and the actual two artifacts were retained; this is not a claim of atomic concurrent-writer or orphan-CSV protection. No concurrent execution was used here. No acceptance criterion was relaxed between the two actual runs.

These results support second-order temporal convergence for this nonstiff, oxygen-free, manufactured reaction/formation-energy/solid-volume limit. The finite-O2 host test, positive-Ea local comparison and combined wet/program diagnostic evaluation remain separate evidence. Neither the 833-test installed result reported by the parent nor this analytic pass is material validation, a stiff-network convergence proof, or completion of the full brick-firing model.

| Final analytic evidence | SHA256 |
|---|---|
| `docs/sandbox/research/SOLID_REACTION_ANALYTIC_PLAN.md` | `e88deba9db0754488ed1245e2106cd0045ce434de70912968235f7fce97b7d75` |
| `docs/sandbox/research/solid_reaction_analytic_reference.py` | `76c0740d23c9fce0c92ec012586d017722cca314ce102f1163830c3539543240` |
| `docs/sandbox/research/solid_reaction_analytic_reference.json` | `3d75f5bc4b05e466ca9d94583d3744e88956c518034f6aa63a340327393e1c60` |
| `docs/sandbox/research/solid_reaction_analytic_candidate.py` | `f180345fbaff30bc8f8387933814caecd353048212e4fc79bc8009ca2d8f9706` |
| `docs/sandbox/research/solid_reaction_analytic_candidate_attempt_001.json` | `efa755e77ab13aa422cb945a81c8f147ce9aa264a67fb2f94d356b6701d80264` |
| `docs/sandbox/research/solid_reaction_analytic_candidate_attempt_001.csv` | `efe2a3e192e63088851ad5205156c0068890b3b86de4ae75f27da04294f44ce6` |
| `docs/sandbox/research/solid_reaction_analytic_candidate_attempt_002.json` | `aa39c5496b4d870fdc8c35406168350b05ceaf9d6d81cd4f543881c8329b3eb5` |
| `docs/sandbox/research/solid_reaction_analytic_candidate_attempt_002.csv` | `15e6012e5854a852e2ebad29b5489e8eb29263a4bc25329a990fa749c09fdf5d` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — the confirmed compatibility and kinetic-domain findings are fixed and independently retested; source/provider binding and real total-U/current-inventory coupling pass the stated bounded numerical checks. Material and broader reaction-network qualifications remain explicitly open.
