# Independent accepted-ledger audit: initial four dry reacting trajectories

**Result: all four individual-case gates pass, but the preregistered finest-pair endpoint energy gate fails.** For compressed caps 1/128 and 1/256 s, |ΔE| = 4.7827488742768764e-6 J, exceeding the unchanged 1e-6 J gate. This is a convergence/verification result, not evidence of an implementation energy leak: individual accepted-prefix first-law residuals remain below 5.46e-11 J. Further refinement is required; neither the threshold nor this failed comparison should be removed.

Read the actual `trajectory-results.json`, `probe.py`, preregistration, corrected smoothstep scalar oracle and fixture/provider definitions. Ran only independent arithmetic over saved data via `audit_ledgers.py`; no EOS, production inverse, ODE trajectory, installation or test suite was rerun. Machine-readable exact audit results are in `independent-ledger-audit.json`. Reviewed trajectory SHA256: `316be853b046226035991810866fc3dc7183384100e8b464fe24cc3aeafc1a99`.

## Actual run evidence

| Motion | Step cap s | Accepted steps | Rejections | Maximum T error K | Maximum prefix E residual J |
|---|---:|---:|---:|---:|---:|
| Fixed bulk | 1/128 | 16 | 0 | 7.332801033044234e-11 | 0 |
| Smoothstep compression | 1/64 | 13 | 1 | 9.619682259653928e-7 | 3.1947279999396117e-11 |
| Smoothstep compression | 1/128 | 16 | 0 | 6.242370886866411e-7 | 3.518965652725414e-11 |
| Smoothstep compression | 1/256 | 32 | 0 | 1.5606525494149537e-7 | 5.45033919255658e-11 |

All end at 1/8 s. The coarse compressed case has actual step durations 0.0070483893328100455..0.00997871672890202 s; it is not a fixed eight-step run. The two finer compressed runs have uniform durations equal to their respective caps. The observed fine T error reduction is useful evidence of convergence for this fixture, not a universal/asymptotic accuracy certificate.

The 1/128 versus 1/256 endpoint differences are:

- Maximum inventory difference: 4.710747764091749e-10 mol, passing 1e-9 mol.
- Total energy difference: 4.7827488742768764e-6 J, **failing 1e-6 J**.
- Temperature difference: 4.681718337451457e-7 K, passing 2e-5 K.
- Pressure difference: 0.0003788048343267292 Pa, passing 1 Pa.

## Complete accepted-ledger arithmetic

For every accepted step and stored prefix in all four runs, independently verified contiguous increasing time endpoints, states/observations/ledger counts, fixed energy identity, closed species/energy faces, exact represented reaction cancellation between A and B, and unchanged inert gas and zero liquid. Exact Fraction total-carbon deviation is at most 8.777700788442644e-16 mol (corresponding declared carbon-solid mass deviation 1.0533240946131173e-17 kg). Maximum species update-versus-ledger rounding residual is 2.0664893407573715e-16 mol. The first-order A inventory matches 2 exp(-0.1 t) within the original 1e-9 mol gate; the largest observed error is 9.673322143299856e-10 mol in the adaptive coarse compressed run.

Every accepted component schema is exactly the five reacting labels. Exact represented total work minus the sum of represented component work equals the stored Fraction residual for every step. Sum of absolute component residuals equals the stored cumulative Fraction value; maxima are 1.56e-17 J. Independently reconstructed total E change from cumulative represented work and checked each local increment. Body, dissipation and interface deformation components are zero throughout this fixture. In the fixed-bulk case all external work components and total work are exactly zero despite nonzero composition-energy increase.

The report does not store both RK stage RHS snapshots. Therefore individual `component_quadrature_roundoff_j` values were structurally read as rational numbers, but their quadrature derivation cannot be independently reconstructed from accepted endpoints alone. The exact component-to-total residual and conserved updates are independently checked; no stronger stage replay is claimed.

## Independent physics/formula checks

Confirmed the actual oracle uses the existing rest-to-rest motion λ = 1 - 0.1 t²(3-2t), λdot = -0.6 t(1-t), not the discarded linear-motion oracle. The fixture has NA+NB = 2 mol, CpA=CpB=5 J/(mol K), inert gas Ng=0.01 mol with Cpg=30 and R=8.31446261815324. Thus C = 10 + 0.01(30-R). The declared formation intercept difference is -5 J/mol; u=h_standard-p_reference*v with p_reference=1e5 Pa and vB-vA=-1e-5 m³/mol adds +1 J/mol, giving ΔuBA=-4 J/mol. These are manufactured definitions, not real carbon allotrope data.

Using a = 1.4e-4(1000/2 + 2*400/3), Eel0=a log²λ and Einterface0=0.3 J, the current mechanical energy is (1+10 NB)(Eel0+0.3). The independently derived thermal equation is:

    C Tdot = -p Vbulk_dot - [-4 + 10(Eel0+0.3)] NBdot
    NBdot = 0.2 exp(-0.1 t)
    p = 0.01 R T / [1.4e-4 λ - NA*2e-5 - NB*1e-5]

It agrees with the corrected scalar oracle source. Composition derivatives remain in thermal/chemical storage exchange. Fixed-composition elastic deformation power is q*2a logλ*λdot/λ and the separate bulk power is -p Vbulk_dot. Recomputed these from every stored state; maximum discrepancy versus recorded endpoint power is 8.89e-16 W. Recomputed pore and solid volumes and reference pressure from analytic NA and recorded scalar-reference T. Independently reconstructed nominal total-storage changes C(T-300)-4NB+q(Eel0+0.3)-0.3; discrepancies from stored E changes are below 1.21e-10 J, including floating inventory/reference rounding.

The stored DOP853 reference T values and comparison errors were audited, but no second scalar ODE integration was run. Algebra and formula independence from the production inverse are established by source inspection; this is not a separate numerical solver verification.

## Provenance and scope

Recorded input hashes before and after the actual four runs are identical. At audit time all recorded production, probe and PLAN files still match; only the current reacting-host test file has since changed as root extends verification. Root subsequently supplied `frozen-probe-host-test.py`; independently computed its SHA256 and matched the exact recorded original input hash `fd02fc0f504fee094e7b3b762dc092cc8fd46f1a32642a16f5b30cdc317a2d43`. This restores byte-level access to the original execution input; the current extended test file remains a distinct later snapshot.

These runs verify limited dry manufactured reacting storage under prescribed motion. They do not establish real sludge chemistry, free-sintering mechanics, spatial convergence, wet depletion or reacting multicell transport. The initial finest-pair energy comparison remains failed pending a newly preregistered finer execution.

## Follow-up: separately preregistered finer runs

**The new 1/512 versus 1/1024 pair passes all original endpoint gates. The earlier 1/128 versus 1/256 energy failure above remains unchanged.** Independently audited the complete two new saved trajectories with the same arithmetic checks, using `audit_refined_ledgers.py`; results are in `independent-refined-ledger-audit.json`. Reviewed refined result SHA256: `6e49549f7520fc4d6464e546588a197263eea9d7f2a2b20e4ed8cf0b87ae1af8`.

Read `REFINEMENT_PLAN.md` and compared actual serialized policies. Apart from the two smaller initial/maximum step sizes, the only change is maximum_steps 100 → 160, explicitly declared to permit 128 accepted steps. Wall limit remains 40 s, rejection cap 20 and all solver and physical comparison tolerances are unchanged. Actual accepted steps are 64 and 128, each uniformly equal to its cap, with zero rejections. Recorded elapsed times are 2.0191300000005867 and 3.932328916998813 s.

| Quantity | 1/512 maximum | 1/1024 maximum |
|---|---:|---:|
| Carbon residual mol | 1.2732870313669764e-15 | 5.689893001203927e-16 |
| Analytic A error mol | 3.924438551905496e-11 | 9.811040868612508e-12 |
| Temperature oracle error K | 3.9030169318721164e-8 | 9.757854968484025e-9 |
| Pressure oracle error Pa | 3.158068284392357e-5 | 7.895490853115916e-6 |
| Prefix first-law residual J | 1.224151827675839e-10 | 1.4078274772524717e-10 |

The two new endpoint differences are maximum inventory 2.943464569304943e-11 mol, total E 2.9892544262111187e-7 J, T 2.927231435023714e-8 K and P 2.3685191990807652e-5 Pa. Each satisfies the unchanged N 1e-9 mol / E 1e-6 J / T 2e-5 K / P 1 Pa gate.

Every new accepted ledger, component sum residual and cumulative absolute residual was independently checked as above. Maximum component sum absolute cumulative residual is 1.295e-17 J; maximum independently reconstructed fixed-N deformation/bulk power discrepancy is 8.89e-16 W. Independent nominal total-storage change agrees within 1.408e-10 J. No composition derivative has become an external power term. Recorded before/after hashes agree, and all their current referenced files match. The same limitation remains: no native EOS, second scalar ODE integration or stage-RHS replay was run by this reviewer.

## Additional test delta and actual related-test XML

Read the exact delta from the frozen probe-time host test to the current host test. The added fixed-host rejection explicitly exercises `solid_reactions_not_admitted`; the two new tests verify exact rational-versus-binary identity separation, reaction-stoichiometry identity changes, exhausted-pore rejection, acceptance of each individual component vocabulary and rejection of mixed old/new labels. No substantive defect found in these additions. Approved current host-test SHA256: `dba08b845798e4c197d17568609edefcc399cadc3a2eae977c7af629b431b3d4`.

Independently parsed `related-tests.xml`: 93 actual testcase nodes, zero failures, errors or skips; suite time 78.322 s. Confirmed the new rational/pore, schema and fixed-binding test names are included. This is actual related-test evidence, not a full installed-suite result. No test was rerun by this reviewer.
