# Independent fixed-inventory wet deformation entropy oracle

Pre-implementation plan, 2026-09-07. Only this /private/tmp directory is writable for this task. No wet EOS evaluation until root explicitly releases the running full suite. No storage, mechanical closure or inverse under test is imported or called as a truth reference.

## Scope and derivation

Closed one-cell adiabatic quasistatic specimen, eta=0, fixed Nliquid/Ngas/Nsolid, common T and liquid/ideal-gas total pressure, fixed incompressible solid intrinsic volume, temperature-independent skeleton/interface energy. These are constrained fixed-phase-inventory thermodynamics, not liquid-vapor chemical equilibrium. In the first oracle case the gas is the existing manufactured Cp30 ideal species `fixture`, not a silently added water-vapor amount. Phase transfer, diffusion, liquid migration, solid reactions, external heat and dissipation are disabled explicitly as this validation limit. A live evaporating specimen need not conserve this expression with fixed N assumptions.

Total power is Eelastic_dot+Einterface_dot-p*Vp_dot. Subtracting those temperature-independent reversible stores yields Uthermal_dot=-p*Vp_dot. For fixed constituent inventories the Gibbs relation of the liquid and ideal gas and incompressible constant-Cp solid gives dUthermal=T*dS-p*dVp. Thus dS=0. Mechanical energy offsets and all fixed-N reference formation/entropy constants disappear from the difference. Surface free energy can be identified with its internal energy only under the declared temperature-independent surface law; no temperature-dependent entropy term is suppressed.

Solve independently at each supplied current Vbulk:

`Vp=Vbulk-Ns*vs; Vg=Vp-Nl*Mwater/rho_water(T,p)`

`p*Vg=Ng*Rmix*T`

`DeltaS=Nl*Mwater*(s_water(T,p)-s_water(T0,p0)) + (Ng*Cv_g+Ns*Cp_s)*ln(T/T0) + Ng*Rmix*ln(Vg/Vg0) = 0`.

Water s is the **native mass-specific** `WaterState.native_entropy_j_kg_k` in J/kg/K; multiply by its own WaterReference.molar_mass_kg_mol and Nl mol exactly once. Density kg/m3 gives molar volume M/rho. The gas R=8.31446261815324 J/mol/K is the registered mixture constant, Cv=30-R; never replace liquid native IAPWS R with it. Solid Cp=5 J/mol/K, no R subtraction. Fixed native entropy offsets cancel; no NIST entropy alignment is required. `WaterState.enthalpy/internal_energy` offsets are not used by this oracle.

Nested scipy brentq: at each trial T solve pressure using volume residual `Nl*M/rho+Ng*R*T/p-Vp`, then solve DeltaS(T). Positive compressibility makes the pressure residual decreasing; stable closed material with positive heat capacity makes entropy increase with T at fixed total V. An actual bracket sign change and admitted stable EOS states are still mandatory. No clipping into a bracket, saturation substitution, or borrowed target inverse is allowed.

## Frozen fixture and initial numerical gates

Existing exact-volume wet fixture: Nl=1 mol, Ng=.01 mol, Ns=2 mol, T0=300 K, vs=2e-5 m3/mol represented from independent exact1/50000 definition; Vbulk0=1.4e-4 m3. K/G/interface energies are deliberately absent from this thermodynamic truth solve because their reversible derivatives cancel. Later compare the same lambda1→.9 isotropic motion, Vbulk=Vbulk0*lambda^3; do not reduce this10% deformation to obtain a pass. Supply actual source-gated WaterProperties only; record its reference/assets/limits in future evidence. Dry limit Nl=0 may use None or a forbidden water sentinel and must not access water at all.

Root point-storage inverse policy remains1e-6 J/1e-6 K. The independent oracle uses temperature bracket295..310 K and pressure bracket1e4..1e6 Pa, brentq xtol1e-9 K /1e-6 Pa, rtol8*binary64 epsilon and maxiter100. Forward residual acceptance: abs(volume residual)<=1e-14 m3, abs(DeltaS)<=1e-8 J/K. These are numerical root/residual gates, not certified total water-EOS error or guaranteed root-error enclosures. Stable-liquid checks and native pressure identity gates remain those of water.state_tp.

Before a trajectory experiment: root authorizes **one initial point plus one lambda=.9 point**, hard subprocess timeout30 s, record water call count and wall time per pressure/temperature/root. If these cannot pass the fixed residual gates, retain failure and investigate; do not run a full grid. Only after measured cost choose a finite grid and total wall budget. Planned host-vs-oracle gates, frozen now: max temperature difference2e-5 K and pressure difference0.2 Pa at selected matching times, unchanged per-component energy gates1e-6 J for the separate work ledger. Point inverse tolerance alone is not an integrated trajectory guarantee; the host must show time refinement to the fixed comparison gates. Before trusting these comparisons run the oracle at half its xtol values on one endpoint and require DeltaT<=2e-7 K, DeltaP<=0.002 Pa (1% of comparison thresholds). If not, the proposed oracle accuracy is unresolved rather than a pass.

Independent dry tests run first and require analytic T=T0*(Vp0/Vp)^(NgR/(NgCv+NsCp)), pressure law and absence of any water calls. Add dry constant-volume, invalid finite/domain/inventory and bracket failure tests. They exercise the reference solver without wet EOS. Wet execution, convergence and host agreement remain unclaimed until separately recorded.

Algorithm documentation checked: [SciPy brentq official documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html), read2026-09-07: continuous function and sign-changing bracket, xtol+rtol root stopping condition, failure on iteration exhaustion. This algorithm contract does not convert an imperfect EOS residual into a rigorous physical root enclosure.
