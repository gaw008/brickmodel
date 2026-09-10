# Independent shared wet kernel and source dry-mass/wet storage review

Read full mass_wet_storage diff, helper regression tests, source_wet_storage implementation and its tests. Review artifacts only in this tempdirectory; no repository edits or native EOS experiment performed by reviewer.

## Existing shared kernel

Extraction moves original actual RigidStorage evaluation and two-stage volume→pressure uncertainty calculation in original order. Global/local Fractions and outward rounding remain; check_wet_water retains source/commonreference/type/backend/molarR conventions. Existing WetMixedStorage solid account, U/H arithmetic and identity remain. Independent execution of16newkerneltests passes as part of23test run, including old fullpoint/identity/callcount goldens, single closure invocation, errors and source guards.

Found correctness defect in newly public helper inputvalidation: inventory/inventories conversions were discarded, so a nonbinary Fraction gasinput was converted by fluid closure but used unconverted in ng for compliance. Independent actualprobe confirms mismatched raw/decoded inventories and a returned extra_pressure_error below the exact formula using actualdecoded gasinventory by1.9928451705542003e−21Pa. Reproducer/log retained in probe_fraction.py/fraction-probe.log, precise testerrorFraction recorded. Magnitude does not excuse breaking directed-bound semantics. Existing hosts pass binary64 and do not trigger this. Worker asked to reject nonrepresentable nominalinventory/volume inputs while preserving exactFraction error; fix pending at this report revision.

## Source wet storage

New storage binds actual supported caloric, fluidtemplate, sourcewater convention, fixedmass, explicit3gasorder, source/fluid temperature-domain intersection and manufacturedconstantavailablefluidvolume. All collaborators revalidated before callbacks. SourceArlabosse dryspecificenergy combines with actual existing fluidinternalenergy; no AB/reference-network solve, fabricatedsolidvolume, totalenthalpy or bulkgeometry needed. ReactionDisabled is separate from water phaseinventory changes. Testfluidvolume/error is explicitly not measuredmaterial evidence, and unknownfiterror remainsNone.

Energy aggregation uses exactFraction sourceintegration and represented fluidenergy, then includes totalU floatrounding, existingfluiderror and liquidinventory*declared|du/dp|*extra volumepressureerror. Minimumcapacity combines lower-directed fluidbound and sourceCp minimum over whole configureddomain; pointheatcapacity uses actualtemperature. Inverse preserves bracket/residual/error gates, fixedstateidentity and source-domain limits. Unsupported binaryrepresentation, changedmass, forgedprovider or sourcegeometry/domain do not silently clip or alter inventory.

Seven independent checks plus16kernel tests actually23passed0.55s: five collaborator substitutions reject before closure, wrongstateidentity/mass/domain/nonbinaryT reject withoutliquidquery, independent sourcepolynomial totalenergy and energyerror/Cp bound reconstruction. All use explicitly artificialexistingliquid fixture; these are code/arithmetic tests, not nativewater/source-material validation. Sourcevolumeerror cannot replace missing material volume data.

Root later forwarded actual out.source_ids into SourceWetPoint as union with staticstorage sources. Read new metadata-only probe: original sourcebound RigidStorage evaluation executes, and only an explicitlymanufactured marker is added by dataclassreplace. This tests runtimeprovenance without altering physical fields or asserting marker as literature truth. Numerical/source formula unchanged.

Current conclusion: new sourcewet storage has no identified functional defect in reviewed checks; sharedhelper nonbinaryinventory mismatch must be repaired before final freeze approval. Finalhashes and postrepair regression will be appended. No lint/fullsuite/longEOS/nativewater pass claimed.

## Final correction and approval

Reviewed final helper correction: validate that every liquid/gas inventory, temperature and nominal volume equals its converted binary64 value, then consistently pass those converted values to closure and compliance. Nonrepresentable inputs reject before backend invocation. Available-volume uncertainty remains exact Fraction. This removes the reproduced mismatch without altering old represented-state arithmetic. Worker froze dc2fad864f41b5cf77fafbc870569a54fcc19f07c0da28dcf7b81bb1481a7a80 / e2e0676a0e5504459efd3141c2558374f053409b93263a919c3df8a5e33bbc7b; independently checked both against current bytes. The old underbound reproduction remains as historical failure evidence.

Actual final independent invocation: 45 passed in 1.45s (seven independent checks, 22 helper tests including original full-point/identity/call-count goldens and representation rejection, and all 16 source-wet tests). See final-tests.log. No full suite or native EOS execution by reviewer. All five reviewed Python files parse successfully. Ruff/mypy executables were not available on PATH; no lint-clean claim.

Read run_native.py: direct actual source water/NIST gas/provider construction, no ReactionReference or fixture setup, exact representable 1/1024 liquid-to-vapor transfer, unchanged total U and exact total-water check, actual temperature inverse. Declared numerical envelope is explicitly conditional and fixed fluid volume manufactured. This execution is not an independent EOS certificate or physical material validation. Parent owns execution and installed results.

Approve final scoped implementation: no unresolved critical/high functional issue identified in reviewed scope. Missing material volume and fit uncertainty remain explicit limitations. FINAL_FREEZE.json binds all two production modules, two tests and example script actually reviewed.
