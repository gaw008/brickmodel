# Independent review: rigid fluid heat coupling

Scope: `rigid_fluid_heat.py`, its focused tests and `RIGID_FLUID_HEAT.md`, with surrounding storage, transport and integration contracts inspected. This review does not re-admit the underlying conditional numerical envelope or qualify a brick material.

## Independently reproduced finding

Two separately constructed `IdealWaterVapor('data/sandbox/water')` providers have identical verified references, asset hashes and physical methods, but their dataclass equality includes private water backend object identity. Constructing otherwise matching H2O cell storages therefore raised `cross_cell_caloric_identity_mismatch`. The initial implementation compared complete provider objects. The requested correction is semantic identity comparison for this verified provider, retaining method, constant, source asset and reference identity; genuinely different source curves or energy offsets must remain rejected. This is an availability defect for valid independently loaded cells, not a demonstrated energy conservation failure.

The final source corrects this with `_caloric_identity`: exact provider type, species, method, classification, temperature domain, R, constant sources/derivation, full reference, asset hashes and numerical limits remain compared; private backend object identity is excluded. Shomate and continuous providers retain full immutable value comparison. The added regression constructs independently loaded water bridges; the existing tests still reject changed Shomate energy offsets and molar masses. The reproduced finding is resolved.

## Physical and interface checks

- Every operator evaluation resolves each current cell's inventory and internal energy through the actual coupled storage inverse. The gas EOS uses its resulting gas volume; liquid volume and transported gas inventories therefore affect pressure. `decode_inverse` and `storage_inverses` retain the original temperature bracket, residual and conditional error diagnostics without a second solve.
- Internal faces have one molar flux per declared gas column and one energy flux used with opposite signs. The liquid column has zero transport. Heat uses two half-cell resistances. Diffusion enthalpy is evaluated at the common face temperature; advection uses the donor temperature. No additional pressure-work or latent-heat term is inserted.
- The new binary test deliberately orders B before A and uses unequal molar masses. Its independent caloric formula is `h_B=35*T+1000`, `h_A=30*T`; mass-weighted corrected diffusion sums to zero. This exercises species column mapping and distinct formation-energy contributions.
- The existing pure-gas outflow test checks `dU=h*dn` and `dU-u*dn=R*T*dn<0`, the correct adiabatic blowdown cooling identity for fixed geometry.
- An additional reviewer calculation reversed the pressure gradient: a 300 K cell with 0.01 mol in 1e-4 m3 against a 500 kPa, 307 K reservoir; area 0.01 m2, half-distance 0.005 m, permeability 1e-15 m2, viscosity 1e-5 Pa s. Direct Darcy and boundary EOS arithmetic predicted -0.009816344469499359 mol/s and -90.4085325640891 W. Actual assembly returned -0.009816344469499394 mol/s and -90.4085325640894 W, within the preselected 1e-14 mol/s and 1e-8 W thresholds. The negative face flux correctly carries reservoir donor enthalpy inward.
- Explicit complete gas identities, molar masses, R, source IDs, geometry and manufactured-model opt-in are checked. Domain exits remain distinguishable from unresolved numerical budgets/configuration errors. No general exception handler silently converts unexpected bugs to successful states.
- The final additions exercise actual prescribed-surface half-cell conduction and an out-of-domain 3000 K continuous-caloric reservoir donor. The latter correctly raises `DomainExit` through the existing `ThermochemistryError` hierarchy; this test adds coverage rather than fixing an exception inheritance defect.

## Executed verification and limitations

The reviewer independently ran the initial focused suite: **12 passed in 37.54 s**. Subsequent binary-test and diagnostic changes require final snapshot verification below; this historical run is not represented as verification of later edits.

The actual two-cell integration covers 0.001 s of manufactured transport with real IAPWS liquid response, preserving liquid inventories and global gas/energy balances while gas moves and pressures change. This demonstrates assembly and bookkeeping, not space/time convergence or real-brick transport coefficient validity. Static reservoir and prescribed material-surface temperature are supported; dynamic furnace programs, surface convection/radiation coupling, liquid migration, phase change, solids, reactions and shrinkage are not implemented by this module. The retained source-domain error envelopes remain conditional declarations.

## Final snapshot

SHA-256 binding:

| File | SHA-256 |
|---|---|
| `src/sludge_sandbox/rigid_fluid_heat.py` | `c934f742df6a025a2d7a247b9042cf68692924ade4cc207d72325ab14236b7aa` |
| `tests/sandbox/test_rigid_fluid_heat.py` | `cd728c6e664a8a68e7c40ee286d1bfe4a26ba821643aca1065c2141a147e27a1` |
| `docs/sandbox/RIGID_FLUID_HEAT.md` | `0a7363288d3fcf8d64edaf736ef9a4acacdf2d831fb0771533bcdcb4f4362d9c` |

Final independent focused run: `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_rigid_fluid_heat.py -q` — **16 passed in 40.10 s**. This includes the actual two-cell integration, newly retained inverse diagnostics, binary transport, semantic identity regression, surface conduction and caloric-domain exit. Source and test hashes above were checked against the frozen implementation snapshot.

Documentation-only follow-up: the two pending verification statements in `RIGID_FLUID_HEAT.md` now record the actual 16-test result and bounded APPROVE verdict. The reviewer inspected these final statements and rechecked unchanged source/test hashes. Final document SHA-256 is `0e5e1f8073ddce2fc14bd5c0c0dad4efb8b3e30b6ba33c1c6bf0e279af479e95`, superseding the historical document hash in the table. No physical or numerical claim was expanded; no test rerun was necessary for this status update.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass; one finding resolved |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — no unresolved CRITICAL or HIGH findings in this bounded conditional fluid-transport scope.
