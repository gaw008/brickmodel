# Deforming solid heat host: isolated candidate

Repository source/tests unchanged. Candidate baseline was copied from actual `src/sludge_sandbox` during root's final review checkpoint, including actual module name `sludge_sandbox.deforming_solid_storage`. Modifications are restricted to new deforming_solid_heat.py, the private decoded assembler extraction in solid_fluid_heat.py, and current_storage context appended to DeformingSolidState in deforming_solid_storage.py. No water/depletion wrapper type admission is changed.

## Initial recorded results and fixes

red.log records actual missing-module RED. attempt01.log caught a manufactured fixture's liquid-column mismatch. attempt02.log caught area/width swapped despite equal volume, confirming full reference geometry guard. attempt03.log caught an implementation API typo (CurrentSlab has face_areas_m2, not face_area_m2). These were corrected without relaxing geometry/identity checks. attempt04.log: original normal-only dry compression, constant offset/single inverse and scope/inventory tests **3 passed in 2.03 s**.

attempt05.xml/log retain the expanded isotropic three-cap run: **1 failed, 5 passed in 5.00 s**. Caps 1/32, 1/64, 1/128 are adaptive maxima, NOT guaranteed uniform grids: accepted counts were 35,64,128. Finest maxima: T error 1.8114890167453268e-5 K (passes 2e-5 K), elastic prefix error 1.1253733233924229e-7 J, interface 4.348754882783391e-9 J (pass 1e-6 J), pore 1.849691513893248e-4 J (**fails 1e-6 J**). Middle/fine pore error decreases approximately fourfold. A passed T tolerance does not replace component work acceptance.

Independent reviewer found current_storage was inserted before the old qualification positional field. It was moved to the end. positional-fix.log records the new compatibility test: **1 passed, 6 deselected in 0.33 s**. The saved tests-attempt05-plus-positional.py is the actual test snapshot after that additional regression, not a claim that all seven ran in attempt05.

## Required implementation contracts

- Explicit total-energy canonical model digest; initial extensive total joules include thermal, elastic and absolute interface energy. Legacy host still rejects tagged total energy. The new host checks fixed per-cell solid inventory and exact point/template/index/motion binding.
- Same current-volume storage returned from point _prepare is retained in the point state, and the private assembler reuses the original thermal_inverse object; there is no second thermal solve or new target with lost error. The assembler checks inverse type, full liquid/gas/solid inventory, geometry and source labels; it is private, not an authentication service for arbitrary caller-created inverses. Provider provenance comes from the host's canonical point/template binding.
- Initial represented total E is a deterministic input. Current source/caloric/mechanical numerical bounds enter each total inverse; dynamic target error 0 is not a certificate of zero initial material uncertainty or propagated trajectory uncertainty. Integration discretization, source uncertainty and mechanical model validity remain separate.
- Five component powers use the same skeleton evaluation and fluid pressure: elastic, interface, dissipation, pore=-p*Vbulk_dot, body=old base zero. Fixed incompressible solid inventory implies Vp_dot=Vbulk_dot. Fluid face enthalpy already contains flow work.
- Manufacturing-only prescribed relative moving faces and cellwise quasistatic actuator interpretation. No free sintering, capillary law, solid reactions or new wet-wrapper support.

## Attempt06 preregistration (not executed until root releases full-suite freeze)

One scan only: adaptive maximum steps 1/512,1/1024,1/2048. Keep all physical inputs, relative/absolute integration precision, inverse precision and acceptance thresholds from attempt05. The only additional change is resource allowance: root approved per-integrate wall limit **20→90 seconds**, with outer whole-scan hard timeout **150 seconds**, including postprocessing. This is a resource policy change, not relaxed numerical accuracy.

The source-gated dry fixture explicitly prohibits water.state_tp. Independently evaluate isochoric-free isotropic compression from lambda=1 to .9 using prescribed smooth stretch, fixed solid volume 4e-5 m3, reference bulk1.4e-4 m3, fixed Ns=2 and Ng=.01. Ctotal=10+.01*(30-R); T=300*(1e-4/Vp)^(.01*R/Ctotal). Compare elastic energy .5*K*V0*(3lnlambda)^2, absolute-interface difference .0015*(lambda²-1), and pore work Ctotal*(T-300), at every accepted prefix. Endpoint potential differences are only independent references, never the solver's work quadrature.

Actual metrics must report caps, accepted/rejected counts, min/max accepted dt and elapsed time. Retain exact per-prefix component/total reconstruction, zero body/dissipation and the previous failed convergence evidence. Acceptance remains finest T<=2e-5 K and EACH elastic/interface/pore prefix error<=1e-6 J, with reported error decrease. No result or performance claim exists for attempt06 until executed.

## Attempt06 observed completion

The one approved scan completed in 72.617779 s (outer runner), pytest **1 passed, 6 deselected in 72.39 s**. Original gates were retained. `attempt06.xml` retains actual captured metrics; `attempt06-metrics.json` was extracted from that XML without rerunning. All three actual grids had zero rejected trials, and min=max accepted dt matched the respective cap (512,1024,2048 accepted panels). This uniformity is an observed property of this run, not an assumption about adaptive integration.

At the finest grid, maximum T error=7.078398311932688e-8 K, elastic-prefix error=4.3959832995987824e-10 J, interface-prefix error=1.6987323765531304e-11 J, pore-prefix error=7.225205731486994e-7 J. The original T and each-component gates pass. Pore errors at the preceding two grids were 1.1560369269858484e-5 and 2.8900834365686023e-6 J. Initial attempt05's coarser failure remains part of the record.

No performance optimization, equation change, source-bound reduction or gate relaxation was made between these runs. Actual per-integrate resource allowance increased from 20 to90 s as preregistered; the runner enforced the whole-scan150 s limit. Code/test/runner/evidence digests are in manifest.json. Remaining six bounded cases are delegated for independent verification; this paragraph does not claim a fresh seven-case aggregate run.

## Post-run source capture and initializer-only review fix

No pre-attempt06 source-hash manifest was captured. The hashes first recorded in `attempt06-frozen/postrun-manifest.json` were collected AFTER the completed scan; they must not be described as a measured before/after match. The worker made no source/test edits while the scan ran. Before the following initializer fix, those actual files were copied into `attempt06-frozen/` to preserve the completed scan's source and test snapshot.

Independent review found that the initializer's direct float conversion accepted a string temperature. `initializer-red.log` records actual `DID NOT RAISE` for `['300.']`. The only subsequent host source change imports and uses existing `_column` strict input validation, replacing len/float-only acceptance. No storage equation, mechanics, inverse, integration setting or convergence gate changed. Additional tests reject string/bool/scalar/NaN/dict/empty inputs. A direct AST extraction of the initializer from the archived actual attempt06 source verifies valid input initial amounts, total-energy bits and model identity are exactly unchanged under the new initializer.

`initializer-and-light.xml/log`: **13 passed, 1 deselected in 0.40 s**. This includes all six previous bounded non-scan cases, six invalid-input cases and the valid-input comparison. The 72-second scan was NOT rerun on the initializer-fixed source; its numerical evidence remains bound to the archived source snapshot, with valid-initial-state equivalence separately demonstrated. `final-manifest.json` binds the later source/test version.

## Formal test entry configuration

After physical review, the formal convergence test now selects `(1/512,1/1024,1/2048)` and per-integrate wall90 s directly, without an environment opt-in. It no longer defaults to the known failing coarse experiment. Old coarse evidence and the actual attempt06 test snapshot remain archived. `acceptance-config-check.json` records an actual AST check that the formal caps equal the three persisted attempt06 cap values and wall allowance is90 s. This is configuration equivalence evidence, not a repeated72 s simulation. Numeric gates and physical parameters did not change.

When relocating to the repository, preserve the read-only `attempt06-frozen/sludge_sandbox/deforming_solid_heat.py` initializer source fixture or explicitly rebase its path; the valid-input equivalence test deliberately reads that actual historical source and must not silently lose it.
