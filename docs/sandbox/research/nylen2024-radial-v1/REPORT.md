# Nylen temperature targets and shared spherical heat host

This increment adds 43 readable Figure 8 internal-temperature observations and fixed spherical geometry to the existing RigidFluidHeat/SolidFluidHeat solver. It does not establish a source-specific MSJ/CB drying prediction.

## Experimental targets

Source metadata and exact conditions: `data/sandbox/research/nylen2024-drying/source.json`. Transcription: `data/sandbox/research/nylen2024-drying/figure8/`. Counts: MSJ 2 cm 8, MSJ 4 cm 12, CB 2 cm 15, CB 4 cm 8. Only clearly readable filled temperature symbols were retained. Unresolved merged plateaus remain unmeasured; this subset has readability selection bias and is not a complete trajectory or independent holdout.

Independent SciPy component extraction and exact Fraction axis conversion verified all 43 rows. Review and result are saved here. The review script is an unchanged execution record using local paths and a private native.npy raster. To reproduce, obtain the legally accessible PDF according to METHODS.md, verify its hash, extract the original I16 image and supply its RGB array at the recorded path. No publisher PDF/image is redistributed in this evidence directory. Graphic reading bounds are not experimental standard deviations or acceptance tolerances.

## Numerical capability

See IMPLEMENTATION.md and ../../RADIAL_HEAT_GEOMETRY.md. Actual existing host and integrator recover the manufactured spherical heat eigenmode with volume-weighted midpoint RMS errors 0.0493322904912455, 0.01223021257327988, 0.0030299424309214 K on 4/8/16 cells. Finest time-step halving changes temperatures at most 3.4453470334483427e-6 K. Author run: 26 passed in 8.02 s. These caloric/transport values are manufactured tests, not sludge properties.

Noneditable installation was tested from /private/tmp with no PYTHONPATH: all four spherical/rigid/solid/programmed heat test files passed, 55 tests in 34.20 s, zero failures/errors/skips (installed-tests.xml). Actual site-packages matched all 107 source modules (installed-identity.json). Independent implementation review also ran 21 spherical tests and 4 separate old-HEAD slab parity/zero-conductivity/nonuniform-shell/motion-guard checks; final written review is recorded separately. This is a scoped test set, not a new full-repository validation.

## Remaining work

The current optional sphere supports fixed geometry and fixed outer surface temperature. Programmed convective/radiative sphere boundaries, radial liquid transport and slab deformation wrappers explicitly reject it. MSJ/CB-specific heat capacity, conductivity, moisture/transport relationships and measured shrinkage remain unresolved. An internal thermocouple at r=0 cannot be compared by relabelling the first midpoint cell. No material parameter may be borrowed from Rosheim or Arlabosse without a material applicability argument. Full raw-sludge wet-to-fired-to-cooled brick simulation and Goal section 11 remain incomplete.

## Final review and installation revision

Independent radial review found no outstanding correctness issue. Requested type annotations and removal of one unused import were applied after the numerical runs. The reviewer confirmed AST equivalence after removing only annotations and that unused import; final source was reinstalled, all 107 modules byte-matched and compiled. Numerical tests remain attributed to tested-pre-annotations-identity.json, not described as rerun. Before/after source and freeze records are preserved. The next concrete boundary implementation is specified in SPHERE_SURFACE_NEXT.md; it is not implemented in this increment.
