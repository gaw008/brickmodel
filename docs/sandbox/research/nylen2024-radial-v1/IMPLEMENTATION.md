# Fixed spherical-shell integration candidate

## Actual implementation

- `FixedSphericalShells` in `spherical_geometry.py` records immutable source-labelled faces from center0 to outerR; cell midpoint radii, spherical volumes and physical faceareas; integrated halfcell radial resistance via area-equivalent distance. No reference/deformation reinterpretation.
- `RigidFluidHeat.spherical_geometry` defaultsNone. None executes original slab call arithmetic. Sphere checks physical outerarea, widths and percell availablevolume, adds geometry sources, uses actual shell volumes and one shared `_conduction`/`_face_metric` path.
- `SolidFluidHeat` consumes same volume and conduction helpers; gas faces already delegate to transport. Source caloric/phase storage and existing integration remain the same actual implementations.
- Constant prescribed outer surface temperature works with exact analytic spherical outer halfshell resistance. Center face remains zero gas/heat without computing singular1/r.
- Radial gas-face transmissibility uses integrated geometric resistance and existing face interpolation/density/mass correction. This does not certify a globally exact nonlinear compressible Darcy solution.
- Unsupported radial liquidtransport, programmed convective/radiative boundary, prescribed/free slab motion reject explicitly at construction.

## Verification

Actual command uses `PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest` with spherical suite plus5existing slab regression cases. Final captured author run: **26passed8.02s**, session93309 terminalexit0; `/private/tmp/brick-nylen-integration-audit/author-tests.log`. No live author handle and no native-liquid EOS run. Source selection explicit; no installation/commit.

Existing host+integrator manufactured constantCv gas spherical Laplacian single-eigenmode, Tsurface300, Tinitial300+4*sinc(pi*r/R), midpoint unknowns, t*alpha/R²=.05:

| Cells | max timestep | volume-weighted midpoint RMS error K |
|---|---|---|
|4|.001|.0493322904912455|
|8|.001|.01223021257327988|
|16|.001|.0030299424309214|
|16|.0005|.0030286055934235154|

Finest temporal-halving maximum temperature difference3.4453470334483427e-6K. Three spatial levels reduce error>3perdoubling. Positivegas inventories unchanged; actual existing totalenergy ledger equals outerboundaryintegral. Midpoint temperature is explicitly neither cellvolume-average nor experimentalr=0thermocouple value.

Other tests independently evaluate radial volume/resistance with rational arithmetic using the declared binary64pi, piecewiseconductivity/outerboundary,1/3/7cell sharedface conservation, actual3cell solid/fluid storage assembly, radial gasfacemetric, sourceidentity, invalidgeometry and unsupportedconfiguration, explicit unchanged slab conduction bitvalues, and original planar puregas/solid/programmed-boundary regression.

Earlier author failures were test harness contract mismatches: NumPyarrays where existing temperatureAPI requires tuple/list; SurfacePolicy constructed without required parameters; generic presentation encoder was mistakenly expected to serialize a nativewateroperator containing an internalmodule. Source implementation was not altered to bypass these contracts. Final tests preserve them. Logs from those attempts are tool evidence; final savedlog is fresh terminalrun.

## Identity and replay

Per root decision, new optionalfield is an intentional simulator revision: generic `_canonical` includes spherical_geometry even whenNone; prior slab contentdigests therefore change while slab numerical call arithmetic remains unchanged. No generic canonical changes or hash omissions. Old archived implementations remain frozen; no cross-version resume/score equivalence claimed.

Old exact/mixed recordpack APIs explicitly reject RigidFluidHeat and FixedSphericalShells as unsupportedcapturetypes; tests verify. Generic presentationencoder handles the geometry dataclass; it does not serialize whole nativewateroperators (existing limitation). No new service/replay schema or package admission was added. `FREEZE.json` binds all7assignedchangedfiles for independent review.

## Scientific limits

This is reused solver spatial capability, not a standalonedrying model, Nylenfit or source material admission. ConstantCv/transport data in tests are labelledmanufactured. Actual MSJ/CB caloric/moisture/transport/boundary/radiushistory package remains absent. No Rosheim/Arlabosse transfer. Static sphere does not model Nylen observed shrinkage. Slab brick architecture remains intact; Goal completion unchanged. `AUDIT.md` records later kgsolid/genericN integration requirements and source gaps.
