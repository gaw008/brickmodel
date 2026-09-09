# Independent audit-script code review

Reviewed audit_saved.py SHA256 a266618478230e96f48779f527bba7b2c234bf3a91b89ad7ea07915b87945424 and audit-result.json. Read-only review; I did not rerun the script, call EOS, or modify the saved native data.

Disposition: APPROVE for its explicitly stated scope, "saved speculative terminal arithmetic only; no packet acceptance". No incorrect numerical formula found in the covered checks. Do not expand this to complete physical admissibility or packet validation.

The script imports only standard-library modules, not the tested production implementation. It binds the original saved failure input/state/totals/policy, source identity and runtime-before/after; reconstructs predictor and terminal face/source/work/stretch affine integrals with Fraction; checks represented raw N/E and mechanical/component rounding; reconstructs the exact paired phase correction, signed/absolute storage accumulation, original local/absolute/evaporation-fraction/element/mass/cumulative gates; and binds the selected root samples and excluded wet-cell polynomial minima to the actual stored observations. Its hash reconstruction and exact dyadic bracket checks agree with the serializer/kernel contracts reviewed. The retained report records actual fraction 3.1123660944895586e-9 and energy representation residual 6.898554109237729e-12 J.

Coverage limits (not covered by its PASS):
- check_panel checks raw endpoints and quadrature, but not every species/stretch polynomial minimum over the entire interval. Wet-cell no-root exclusions do include their interior minima. Full panel positivity is a separate production/test gate.
- Selected clock sign enclosure is checked, but strict derivative negativity over the full declared domain and exact equality of clock.time_absolute_s to the input time gate are not explicitly asserted. The bracket width is tested directly against the ORIGINAL input time gate, so the reported width check itself is not weakened.
- Some redundant diagnostic fields are not independently checked: panel_liquid_roundoff_mol and half_neighbor_spacing_mol. The actual vapor update is independently rounded from Fraction and its residual/cumulative budgets are checked, so this does not invalidate the numerical storage result.
- The script is intentionally specialized to this one actual selected cell and single root candidate. It is not a general hostile-record decoder; Python numeric type coercion and zip truncation are not exhaustively rejected. It must not be reused as a general admission/restore validator.
- Evaluation attempts/completions are checked; all new pure-stage attempt counters and wall/resource semantics are not independently re-audited here.

These limits were sent to the audit author. The reviewed report appropriately avoids packet acceptance. The native result belongs to the original e324... executor runtime. The later DomainExit classification-only implementation change has a different source identity and is not retrospectively claimed to have run this native experiment.
