# Water-transfer behavior regression replacing stale AST lock

## Change and scope

Only tests changed. `test_deforming_wet_admission.py` replaces the obsolete whole-function AST comparison with an actual legal-host check → single base evaluation → single assembly regression. New `test_water_transfer_behavior.py` exercises current routing and contextual invariants. No src file, physical equation, admission guard or error tolerance was changed.

`RED.log` and `STALE_TEST.py` retain the actual old failure and exact old test. The historical assertion claimed entire evaluate AST remained unchanged; current code legitimately separates interface checks and transfer assembly and forwards mechanical rates plus runtime sources. Updating the old AST expectation would not have tested those behaviors.

## Actual evidence

Final targeted source-checkout run: **15 passed in 8.55s**, session11415 terminal exit0. `author-tests02.log` is the saved final output. This is a targeted suite, not a claim that every test in the repository or entire old test file ran.

Five new tests plus the replacement old-file test cover:

- Source-matched WaterPhaseTransfer and actual rigid/free-slab hosts are constructed through normal constructors. Spies observe original methods; no constructor bypass or fake chemical result is introduced.
- Invalid wet/dry inventory modes reject before base evaluation and transfer assembly. An explicit zero-inventory mode switch preserves coefficients and source IDs.
- The same actual two-cell free-slab state takes regular and autonomous entries. Both call check → one corresponding base entry → assembly, and return equal phase diagnostics, rate arrays and mechanical rates.
- Existing positive/negative phase fixture conditions yield equal-opposite liquid/vapor molar source terms, actual current-volume vapor pressure and nonnegative finite-vapor entropy production.
- Base face heat/species rates, mechanical rates and every mechanical power component are forwarded unchanged. No second latent-energy term appears.
- A fully constructed source-matched disabled interface preserves its actual free-mechanical context and does not call chemistry.
- Unsupported autonomous host rejects before evaluation.
- An actual joined high-temperature source model gives unknown dry condensation drive: strict policy exits; explicitly metastable mode preserves zero phase rate and reports unknown drive without inventing equilibrium.

Nine selected existing fast tests were reused for actual equimolar phase source/no duplicate latent heat, zero-vapor infinite-potential limit, near-equilibrium tiny-rate representability failure, wrong caloric bridge rejection, dry supersaturation/metastability, liquid reappearance, invalid switching, numerical failure distinction and zero-k strict dry screening. No trajectory refinement or large native EOS scan was repeated.

## Dynamic-source probe and preserved first attempt

The original real free-slab fixture's runtime sources were already contained in its static set. The first new run therefore failed the deliberate nonempty-runtime-difference assertion: **14 passed / 1 failed in8.61s**, preserved in `author-tests01.log` and the pre-probe test copy. Removing the assertion would have left runtime-source forwarding untested.

The final test adds only the explicitly named `manufactured:dynamic-source-forwarding-probe` to the legally constructed original base result using dataclass replace. All actual thermodynamic, rate, mechanical and inverse fields remain unchanged. Both entry spies add the same marker, and the test requires its propagation despite absence from static operator sources. This marker tests metadata routing only; it is not asserted to be a real material source or independent physics evidence.

`FREEZE.json` binds both changed tests and the unchanged water implementation SHA. No installation or commit was performed; independent review remains the next gate.


Final independent review accepted the two frozen test files. Root's installed33 selection, including all5newtests and full9deforming-wet-admission cases, passed in4.70s with zero failures. Evidence is in ../source-mass-caloric-v1/installed-tests.xml and installed-identity.json. The previously failed whole-AST test is replaced by actual behavior without changing water source SHA650dc159355b299f53d0c6a98a08a5d68cfc60a81f3d2379225335066c63b48e. No full wet trajectory or final material qualification is claimed.
