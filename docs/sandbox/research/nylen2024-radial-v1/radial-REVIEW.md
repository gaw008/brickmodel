# Independent frozen spherical-host review

Reviewed all7 files in author FREEZE.json, actual full diffs, new geometry helper and tests, relevant existing transport/energy consumers, and prior HEAD rigid host. FREEZE_CHECK.json confirms all7 current bytes equal author freeze. This review does not change author files.

## Physics and integration

FixedSphericalShells derives each volume with factored difference of cubes, avoiding direct cube subtraction; positive finite radii, resolvable centers/volumes/areas and resistance lengths are validated. Integrated distances dl=rface*(rface-rleft)/rleft and dr=rface*(rright-rface)/rright give exactly the analytic spherical half-shell resistance after division by4*pi*rface² and k. Outer resistance splitting into two equal lengths preserves the same total resistance while satisfying existing conduction API. Center is zero initialized in face arrays and never passed to inverse-radius helper. Midpoint unknowns, binary64 arithmetic, fixed geometry and source labels remain explicit.

RigidFluidHeat checks geometry count, outer area, widths and available pore volume against actual shell volume. SolidFluidHeat checks each solid/fluid storage bulk volume against same transport helper. Both actual evaluators call the same conduction helper and same gas-face metric; no alternate standalone solver introduced. Diffusion/mobility harmonic resistance uses equivalent distances; interpolation/density/enthalpy conventions remain the existing local face model. Shared face energy enters neighboring cells with opposite signs and outward boundary sign unchanged. No claim of exact global nonlinear Darcy solution is warranted.

All residual slab area/width consumers found in selected hosts were inspected. Solid liquid transport is rejected for radial geometry before planar liquid-face code; programmed convection/radiation and both slab-motion wrappers reject before planar boundary/motion consumption. Verification-case snapshot depends on those sphere-rejecting motion hosts and is not a newly admitted radial capture. WaterPhaseTransfer operates per-cell source rates and existing host face assembly; no extra planar face geometry there. No native liquid EOS or fullcontroller execution performed during this review.

New field participates in existing dataclass canonicalization even whenNone: slab identity changes by explicit simulator revision while original numerical arithmetic remains. Unsupported exact/mixed record packers reject operator and geometry; generic geometry presentation is not whole-operator replay. `material_qualified` remainsFalse. Geometry does not supply Nylen thermal/drying parameters, time-varying shrinkage, or center thermocouple reconstruction.

## Actual independent verification

- Submitted spherical file:21 tests passed8.06s, session56799 terminalexit0, submitted-tests.log. Includes actual same-host/integrator spatial and temporal convergence, source identity, invalid meshes, gas Darcy resistance, storage volume, boundary and unsupported codec paths. Author separately reported26 with5slab tests; this reviewer does not conflate these counts.
- Reviewer-created4 tests passed0.32s, independent-tests.log: previousHEAD class versus current slab full species/energy face arrays and pressure bitpatterns for3 distinct thermal states; zero-k internal/outer insulation; nonuniform mesh C+B/r harmonic profile gives constant analytic4*pi*k*B flux; both moving wrappers reject a valid radial base before accessing deliberately unreadable mechanical points.
- Initial reviewer parity fixture used gas inventory outside unchanged pressure bracket and failed normally. Original failure log retained; only reviewer inventory corrected to existing admissible fixture values. No source implementation or domain widened.
- All7 frozen implementation/test hashes independently rechecked after tests. No ruff/mypy/pylint/black tools available in isolated runtime; no static-tool pass claimed. Root's separate installed107module/55test result is outside this review's own execution scope.

## Conclusion and limits

No outstanding physical correctness, security, source-binding or numerical regression defect identified in the frozen change. Scope is fixed spherical geometry in existing hosts, not full Nylen drying validation or final brick model. Public type annotations for new geometry property getters and cell_bulk_volume_m3 remain a maintainability improvement consistent with earlier review feedback; no numerical revision or repeated installation is needed solely to record that follow-up. Source geometry identity and material non-admission are preserved.

## Final annotation-only freeze

Author added requested helper/getter/volume annotations and removed unused conduction_rate_w import in solid_fluid_heat. Reviewed complete3file difference, and check_annotations.py independently proves AST equality after stripping function annotations and that one unused import. Existing rigid_fluid_heat still imports the same exchanges dependency. All3 final files compile; final7 source/test hashes match updated author FREEZE.json in RESULT.json. Earlier FREEZE_CHECK.json intentionally retains tested preannotation hashes. Numerical tests21+4 were run on preannotation byte revision; no repeat numerical run claimed after this executable-equivalent cleanup. All review feedback resolved.
