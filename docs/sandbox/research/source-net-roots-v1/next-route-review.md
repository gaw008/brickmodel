# Narrow review of next-route.md

The author's proposed shared affine integral/update extraction and N-cell incidence ledger are mathematically consistent. Preserve its original route; these are binding clarifications for the next bounded implementation, not a replacement architecture.

1. Every zero-initial fluid remains unsupported in the next prefix API, including an identically zero polynomial. Do not implement the optional zero-polynomial exception described in the author's route in this step. A zero polynomial alone does not establish a compatible interface mode or physical wet/dry constitutive domain, and cannot bypass the current root-order completeness contract. A later explicit state/mode design must establish that independently. Parent agreed to this stricter boundary.
2. Preserve all original numerical budgets. Checking only the final state projection is insufficient: integral projection errors and the full incidence-plus-state residual must remain visible and gated according to the original amount/energy contracts. Cumulative prefix checks must sum signed represented face terms exactly as Fractions, then compare actual state minus initial state against that ledger; do not replace cumulative budget gates with only per-cell or per-term checks.
3. Internal shared faces must be projected once and reused on both sides. The same applies to paired local phase amounts if separately represented: their liquid/vapor signs must cancel exactly. Author's total-U authority and diagnostic decomposition residual prevent double counting liquid/gas donor enthalpy or conduction.
4. A minimum of zero or an isolated root only permits an explicitly numerical boundary record; it does not authorize a wet host state, evaporation correction, drained-liquid-to-vapor transfer or physical event commit. The proposed tests and original evaporation gates should retain that separation.

No EOS, trajectory, code edits or tests were run for this route review.
