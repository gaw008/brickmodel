# Fixed spherical programmed surface connection

## What changed

`ProgrammedSolidFluidHeat._surface` now obtains actual exteriorarea from the existing `transport._face_metric(last,None)` and conductive input from `transport._conduction(Tsurface,Tcell,last,None)`. The old spherical constructor rejection is removed, and its obsolete test is replaced by actual spherical-boundary tests. No new solver, sourcecaloricprovider, statebasis or phaseheat is introduced.

The original bracketed surface solver, stopping tolerance, iterationlimit, convective/radiative heatlaw, actual sharedface energyledger and basehostevaluation remain unchanged. Fixed sphere uses G=4*pi*k/(1/rc-1/R), area4*pi*R²; slab executes its previous planar call arithmetic. Radial deformation/liquidtransport restrictions are unchanged. Original radiationmodel remains graybody/effectiveblackbodyenvironment/viewfactor1, not an automatically applicable Nylenradiationboundary.

## Before-change failure and restricted changes

`RED.log` records the original fulloperator failing construction with spherical_programmed_boundary_not_supported. `programmed_solid_fluid_heat.before.py` retains the exact prior implementation. The initial new9-test suite then passed8tests but hit30s/resourcewall during Robin integration; its log and originaltest are retained. `BUDGET_REVISION.md` records rootauthorization to raise ONLY Robin pergrid resourceceiling90s, leaving allphysical/numericalcomparison requirements unchanged.

`FREEZE.json` was written before the unique resource-adjusted rerun, binds3changedfiles, and is ready for independentreview. No sourceinstallation or Gitcommit was performed by this author.

## Independent planar comparison

`slab_parity.py` executes the preserved old `_surface` and current `_surface` on the same actual slabhost.12combinations(film/radiation/zero-conductivity/adiabatic × Tc295/300/305) produced identical floathex and allreturnedfields, including surfaceiterations/status. `slab-parity.json` and `.log` preserve results. This is numericalbehaviorparity, not crossversionoperator-identity equivalence.

## Actual physics tests

Newtests use existing actual rigid/solid storage, gascaloricinverse, SolidFluidHeat, boundaryprogram and genericintegrator with labelledmanufacturedconstantcapacity/transport. No native liquidEOS scan.

- Onecell film analyticTs304.444444444444K distinguishes correct sphericalG from planarTs302.857142857K; confirms onebaseinverse and sharedenthalpy/heatledger.
- Nonlinear spherical radiation independently solved with scalarBrent polynomial, not the productionbisection/helper.
- Onecell programmedheating then cooling compared with exact piecewiselinear ambient ODE, with stepwiseenergyledger.
- Zero k film/radiation/adiabatic branches; gasenthalpy remains present withzero solidconduction; failedsurfaceiterations propagate numerical_failure withnoacceptedsteps.
- MulticellRobin Bi1 mode: μ=pi/2, θ=4*sinc(μr/R)*exp(-αμ²t/R²), actual4/8/16grids andfinegridtemporalhalving. Temperatureunknowns are explicitradialmidpoints, not experimentalcenterreadouts or volumeaverage. Samecode integrates all sharedinternalfaces plus actualsphericalfilmouterboundary. Errorgatesfixedbeforeexecution: >3errorreduction pergrid doubling, finestRMS<.005K, timehalvingmaxdelta<finestRMS/20.

Pergridterminalresource/metricrows are flushed in `author-tests02.log` and `pytest01/.../robin-grids.jsonl`. Finalrun status is reported separately after the live handle closes; no interimcompleted claim.

## Scientific admission remains absent

This extends coupledsolver geometry/boundary capability, not Nylenmaterialvalidation. It does not provide MSJ/CB conductivity, heatcapacity, h,epsilon,hotgasmoisture, shrinkingradius, constituentthermochemistry or measurementoperator. NoRosheim/Arlabossepropertytransfer. FullGoal completion requirements unchanged.
