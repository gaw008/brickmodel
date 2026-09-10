# Next fixed-sphere surface-boundary connection

Read-only audit of frozen candidate. No repository edits. All references below are current source function/line anchors; no new PDE/integrator/material package is proposed.

## Existing consumers and smallest actual change

`programmed_solid_fluid_heat.py:140-181`, `ProgrammedSolidFluidHeat._surface`, solves a massless surface heat balance and is the only additional heat consumer needed for fixed spherical `SolidFluidHeat`:

- line147 sends `base.face_area_m2` to `boundary_heat`;
- lines151-155 independently reconstruct planar conduction from two quartercell widths and last conductivity;
- lines156-161 compute the existing watts residual and its original absolute+relative limit;
- lines163-181 preserve the existing adiabatic/degenerate branch and bracketed bisection.

The opt-in metric is already connected to `RigidFluidHeat._face_metric` and `_conduction`. Therefore the smallest implementation is:

1. At `_surface` entry select `last=len(base.storages)-1`, `area=base._face_metric(last,None)[0]`. For existing slab this is exactly the previous physicalfacearea. For sphere it is4*pi*R², not an averaged/internalarea or a volume/width surrogate.
2. Replace the independent quarterwidth `conduction_rate_w(...)` call with `base._conduction(surface,cell_temperature,last,None)`. This uses the existing source-frozen spherical outerhalfshell resistance and preserves original slab conduction-call arithmetic. Its direction is surface→cell, intentionally opposite to the base outwardledger.
3. Pass `area` to the existing `boundary_heat`. Do not change the residual, tolerances, surface root solver, actual source IDs, limits, or returned record fields.
4. Remove the candidate constructor rejection `spherical_programmed_boundary_not_supported` at lines71-73 only AFTER the above sphere tests pass. Keep rejection of sphere+DeformingSolidHeat/FreeSolidSlab in those constructors and sphere+liquidtransport in SolidFluidHeat. Allowing static surface heat does not authorize radial mechanics or liquidflux.
5. Remove the now-unused `conduction_rate_w` import in this file only if no remaining caller exists.

`ProgrammedSolidFluidHeat.evaluate:186-227` already calls actual basehost once, then uses `transport._face(last,reservoir,...)` for gasexchange and existing enthalpy convention, and sets `fe[-1]=existing+enthalpy-into`. No geometry reassembly or new conserved state is needed there. `_current_content_digest:97-101` already includes the entire basehost with sphericalgeometry; source IDs collect basehost geometry provenance. Exact branch changes are a simulator revision; frozen previous operator identities/implementations remain their own evidence.

`programmed_gas_heat.py:125-170` also reconstructs planar area/quarterwidths, but wraps the DIFFERENT `GasHeatModel` and currently cannot accept `RigidFluidHeat`. It does not lie on the proposed source solid/fluid chain, so changing it is unnecessary scope. `exchanges.py:39-59` and `:66-89` already implement Fourier heat and grayboundary correctly for explicit area/resistance; leave them unchanged.

## Derived fixed-sphere surface equation

Let outerradius R, last temperature-node radius rc>0, last cell conductivity k>=0, actual exteriorarea As=4*pi*R². For constant k in the last halfshell:

Rcond = integral_rc^R [dr/(4*pi*k*r²)] = (1/rc-1/R)/(4*pi*k) [K/W]
G = 1/Rcond = 4*pi*k/(1/rc-1/R) [W/K]

For k=0 set conductiveflow=0 by the existing explicit insulatingbranch; do not divide by zero. `FixedSphericalShells.face_metric(N)` returns equivalentlength ell=R*(R-rc)/rc. The shared helper uses ell/As/k = Rcond; splitting ell into two identicalhalf-distances is solely compatibility with the existing two-positive-distance API, not two physicalmaterials.

Unknown surface temperature Ts balances:

F(Ts) = G*(Ts-Tc) - As*h*(Tg-Ts) - As*epsilon*sigma*(Trad^4-Ts^4) = 0 [W].

Thus F'(Ts)=G+As*h+4*As*epsilon*sigma*Ts³ >=0 for positive temperatures. Unless all heatconnections vanish, the same bracket[min(Tc,Tg,Trad),max(...)] encloses the unique physicalroot. No new Newton method or loosened residual gate is necessary. Existing h=epsilon=0 branch returns Tc; when also k=0 surface is explicitly undetermined. For k=0 but finitefilm/radiation, solve equilibrium between those exteriorpaths, yielding zero conductiveinput; gasenthalpy can stillcross as previously defined.

Boundary radiation remains the explicitly existing gray surface/effective blackbodyenvironment/viewfactor1 assumption from `exchanges.boundary_heat`; Nylen walltemperature or furnace gastemperature cannot automatically be substituted as Trad. h,epsilon and environmentaltemperature must carry actual source/design provenance. Thermal surface balance does not add an extra latentheat sink: the phase-transfer wrapper already exchanges liquid/vapor inventories at shared storedenergy.

## Meaningful validation before removing rejection

1. **Exact linear sphere film surface and net heat:** one sphere cellR=.02m, rc=.01m, k=.5W/(mK), h=20W/(m²K), Tc300K,Tg310K,epsilon0.
   - G=4*pi*k*R; H=As*h;
   - Ts=(G*Tc+H*Tg)/(G+H)=304.444444444444...K;
   - Qin=(Tg-Tc)/(Rcond+1/H).
   - A mistaken planarouterarea/halfradialwidth gives Ts302.857142857...K, so this test distinguishes the geometry paths materially.
   Use actual existing solid/fluid host+program and require exactlyone baseinverse/evaluation pertrial as the current planar test does.
2. **Nonlinear radiation:** choose strictlypositive epsilon and Trad different fromTg. Independently solve polynomial `As*epsilon*sigma*Ts^4+(G+As*h)*Ts-[G*Tc+As*h*Tg+As*epsilon*sigma*Trad^4]=0` at higherprecision or an independent bracketingroot. Compare actual surfacevalue within original SurfacePolicy/residual budget; assert actual area and sphereG, not the same helper twice.
3. **Sameintegrator energy ledger:** disablegasflux andphasechange in a manufactured constantcapacity singlecell. For epsilon0 constantTg, exactTc(t)=Tg+(Tc0-Tg)*exp(-Geff*t/C), Geff=1/(Rcond+1/H). Existing integrate mustmatch within predeclared temporaltolerance, and eachstep storedenergychange equals -outerfaceenergyintegral. State remains source-unqualified. This tests actual wrapperintegration, not another solver.
4. **Limits:** h=epsilon=0; k=0 withh>0; h0/radiationonly; Tg<Tc cooling; boundaryTc=Tg=Trad; finitepositiveparameter validation and failedsurfaceiteration propagation. Keepgasenthalpy distinct in zero-conduction case.
5. **Preserve slab:** run existing `test_half_cell_film_and_full_inverse_once`, `test_nonlinear_radiation_independent_root`, and ramp/hold/cooling ledger. Explicitly compare Nonegeometry surface balancedvalue and heat bitvalues where original code yields identicalarithmetic.
6. **Record/identity:** differentR changes underlyinggeometry+operator identity; sourcegeometry retained in source IDs; old exact/mixed capture continuesrejecting unsupported sphereoperator path. Generic serialized surfaceevaluation can be recorded only with existing source/runtime binding; no resume claim is introduced.

## Nylen scope remains unqualified

This plugs real spherical external heattransfer into the existing coupled solver, and is a necessary next computation. It does not supply MSJ/CB conductivity/Cp/moisturetransport, h,emissivity, hotsupplyhumidity, or dynamicradiushistory. It also does not turn firstcellmidpoint into experimentalcenterthermocoupletemperature. Those observations need an explicit sampling/refinement policy and source-specificcalibration/holdout separation. No Rosheim/Arlabosse property transfer follows from this wiring.
