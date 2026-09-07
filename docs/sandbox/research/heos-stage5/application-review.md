# Applied source and provenance review

Approve the reviewed application/provenance delta. Read-only source/file/JSON/hash inspection; no EOS, tests, installation or production edits performed by reviewer. The full installed suite is still running; this report contains no full-suite outcome.

All 13 applied source files compare byte-for-byte equal with the frozen isolated candidate: water_properties, water_heos, water_implementation, _heos_kernel, ideal_water_vapor, joined_water_vapor, water_chemical_potential, phase_storage, rigid_water_gas, rigid_fluid_heat, solid_fluid_storage, solid_fluid_heat and deforming_solid_storage. Thus previous source review and source-bound isolated smoke/inverse evidence apply to these source bytes. Installation of 41 modules and the live full-suite result are Root's separate evidence; neither was rerun here.

The new source entry resolves `coolprop-8.0.0-heos-water` to software implementation evidence, the IAPWS formulation, version/revision, explicit MIT license path, approved manifest and raw fluid-definition path. Both referenced local license and fluid files actually exist. License text is MIT with CoolProp copyright; its SHA matches the source JSON. Canonicalized full fluid JSON matches the approved manifest's fluid digest, and its EOS BibTeX value equals Wagner-JPCRD-2002. The approved manifest is byte-identical to the reviewed candidate manifest and has the exact SHA pinned by the applied wrapper. This is a repository-local source lookup entry, not a claim that an unrelated central registry auto-discovers it.

HEOS_BACKEND.md matches actual behavior: Python default; explicit backend+manifest selection; no automatic CoolProp installation or fallback; only the reviewed installed build admitted; other platforms/builds unqualified. The example loader and chemical constructor signatures exist. HYBRID real-fluid versus Python ideal roles, pure scientific reference versus implementation identity, derived descriptor asset, optional state-schema change and preserved default provider canonical are accurately distinguished. Existing IAPWS source/license requirements remain present; CoolProp's MIT notice does not relicense the hybrid's Python dependency.

The document accurately limits current evidence to bounded grid/formula/derivative/fault/shared-instance checks and one manufactured closed-storage inverse. It makes no full wet-trajectory, deformation/depletion, transport/material or performance claim. No source-ID/path/hash mismatch or documentation blocker was found.

Reviewed artifacts SHA-256:

- `data/sandbox/water/heos-8.0.0-source.json`: `2d3d322f0148da5d2074a938b79c31c69b9b3397592f5b4f7189dd79717b557f`
- `data/sandbox/water/heos-8.0.0-approved-manifest.json`: `a2d309e79615b283477d8368fe03477704ed5ba468cc3bf11350773ac716783d`
- `docs/sandbox/HEOS_BACKEND.md`: `7bb5293d015fb868717faf2e5172478b78c5fbadb30abb0c91a824ae65251314`
- `docs/sandbox/research/heos-stage3/LICENSE-CoolProp`: `9bf835333ef602af4cb19338b9f9d43671e174fa029b00280e9bdba6ea4719b2`

Source/document paths above are relative to `/Users/wanggaoying/Desktop/brickmodel-github`. Final repository test completion and commit/archive verification remain outside this application audit.
