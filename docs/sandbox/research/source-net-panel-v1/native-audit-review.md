# Independent saved source net-panel audit

445 independent standard-library assertions passed. The audit read the committed original native and audit JSON plus the completed replay JSON; it did not invoke replay, panel classes, InventoryPolynomial, source code, EOS or any trajectory.

Input hashes:

- Replay: b1652b5b9c0e6887592bee70a0927637df78ea4213eb1411c4ffc87bd274a643
- Committed native: 033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2
- Committed native audit: c705d9410458690d0a8379da59e5a7c86a01fd4f59e2897699a5616e55c1914d

All seven selections match the actual capture ordinals [1,4], [7,10], [14,17], [20,23], [27,30], [33,36], [40,43]. Original trial objects, including their status and error evidence, match the committed audit exactly. The sequence remains rejected/accepted/rejected/accepted/rejected/accepted/accepted; no rejected trial was promoted by creating a numerical panel. Every replay panel has material_qualified=false and physical_trajectory_or_event_admitted=false.

For all 105 serialized polynomials (12 fluid inventories and three energies per panel), the audit independently derives exact initial value and coefficients from the actual first and interior capture states/rates. It assembles the signed divergence directly from the four-fluid shared face rates and local source rates. Both sampled derivatives match p'(0) and p'(h_mid) exactly. The quadratic coefficient is (r_mid-r_start)/(2*h_mid); no tested polynomial code is used.

All 84 inventory minima are independently recomputed by evaluating endpoints and the interior stationary point when the polynomial is convex and that point lies within the horizon. Both minimum values and locations match serialized results exactly.

At five exact offsets per panel (0, horizon/4, horizon/2, 3*horizon/4 and horizon), integrated global liquid-plus-vapor water change equals the shared external affine face-water integral exactly, with local phase contributions cancelling. Integrated global U change equals external affine face energy plus the declared cell power integral exactly. All 70 water/U comparisons and 35 phase-cancellation comparisons pass. These checks establish numerical incidence conservation for the affine panel; they do not require the interior captured Euler state or accepted trajectory to lie on that panel.

Actual audit computation after parsing took about .0094 s. Script audit.py, actual stdout AUDIT01.log and RESULT.json preserve the result and hashes. No auditor failure occurred in this task.

Scope remains saved numerical affine interpolation. Exact coefficient arithmetic, matching sampled derivatives and exact polynomial minima do not prove a physical depletion event, ODE event time, full constitutive interval validity, or material qualification. No polynomial-to-original-Euler or polynomial-to-accepted-trajectory equality was imposed or claimed.
