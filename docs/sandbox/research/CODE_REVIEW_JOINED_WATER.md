# Independent review: JoinedWaterVapor and host integration

Verdict: APPROVE for the bounded ideal-gas caloric continuation and explicit host adapters. This does not approve a complete wet-to-dry trajectory or a material-valid high-temperature brick model.

Reviewed the complete new provider, surrounding phase/storage/reaction/phase-transfer interfaces, four production diffs, source contracts, and final tests. The 293–500 K branch preserves the original source-gated IdealWaterVapor exactly, including 500 K. Above 500 K the represented NIST Cp coefficients are integrated with Fraction from the low-branch stored enthalpy anchor, across both original high-temperature intervals. Source h offsets and Cp jumps remain visible; neither a latent heat nor a chemical phase transition is introduced at a caloric fit seam. u=h−RT uses the same fixed R and common reference. The high branch does not claim entropy or liquid chemical potential.

The high-domain Cv proof bounds each polynomial/inverse-square term on positive temperature intervals with exact rational arithmetic and subdivides until the lower bound is positive. The fixed low-source ideal Helmholtz terms have positive exponential contributions and the checked constant contribution supplies a positive Cv lower bound after the fixed-R conversion. Thus this is a mathematical monotonicity certificate for the specified constitutive representation, not a bound on real-water model discrepancy. Endpoint ownership preserves reported one-sided Cp changes.

The conditional numerical contract distinguishes the caller-declared whole low-domain enthalpy error from high-branch output rounding. Exact integration of represented coefficients does not eliminate coefficient/model uncertainty. The runtime RigidStorage check rejects an active joined species whose gas-u envelope does not cover the provider's current conditional error. Zero inventory retains the original inactive-species semantics. Complete source/anchor/error-policy identity is preserved through reaction bindings; separately loaded equal providers compare equal. The phase-transfer adapter accesses only the original low model for source/reference compatibility and retains the actual chemical temperature and liquid-interface gates.

Resolved finding: an initial directed upper conversion could step from maximum finite float to infinity after its finite check. Independently reproduced a successful numerical_error result with infinite error using maximum-float low error. The author added two failing regressions, then guarded both Fraction conversion overflow and post-nextafter finiteness. The final version rejects this case; no outstanding HIGH finding remains.

Independent execution: final provider suite 31 passed in 0.31 s, XML `/private/tmp/joined-water-review.xml`. Final host 9 tests and write-back 15 tests ran together: 24 passed in 2.23 s, XML `/private/tmp/joined-host-roundoff-review.xml`. These are reviewer executions, not author-only reports; no full installed suite was repeated.

The four actual SolidFluidHeat integrations heat/cool through 500 K and 1700 K with conserved complete inventories and total-U inversion on actual trial states. Their independent high-branch reference directly integrates original coefficients with Decimal at 60 digits; its low branch deliberately shares the separately tested low water model. Final temperature is checked at 2e-5 K absolute, prefix U and summed work at 1e-7 J absolute. This tests integration/interface consistency, not an independent validation of the underlying EOS or the adopted low-anchor error. Additional tests cover insufficient low/high error budgets, source identity, low-temperature wet chemistry, and retained high-temperature liquid/dry-active-transfer rejection. No complete evaporation event, nucleation, real high-temperature solid physics, or high-pressure ideal-mixture qualification is inferred.

## Final SHA256 bindings

- `src/sludge_sandbox/joined_water_vapor.py`: `4fab351fd03ae8ba77afa4193c7392bd40bea54bf90107e90aa9b46566ebf0f6`
- `tests/sandbox/test_joined_water_vapor.py`: `2b5be04a1d98521aa00eba066603cc5630a9ee26b25a968932bd68bf1a5ae4e3`
- `docs/sandbox/JOINED_WATER_VAPOR.md`: `b53382330e698baf09b8284a80191f551821aa8345b95a525303ae482af98781`
- `src/sludge_sandbox/phase_storage.py`: `91152f709d705812a01f1795a70463be5e2731c4c13de250a59dbb7c64730bb6`
- `src/sludge_sandbox/rigid_storage.py`: `7dc2b56522a3b7d3a10ec401549418acc78f50cf2eba8a426eb0f0d316dfebbf`
- `src/sludge_sandbox/solid_reactions.py`: `b159bd9d10281f2bf6d8c8458eb5be7761566d67b728f09d6fa7fd4754e6af3a`
- `src/sludge_sandbox/water_phase_transfer.py`: `44f4a97276cbb9de0c8ac3b5508df70ac7be5d253cac24513cfdfb8584a0c212`
- `tests/sandbox/test_joined_water_host.py`: `b37d5c4037b2dc743dbcbbbe0ed869792d385318507c47902670115d8f46017e`
- `docs/sandbox/JOINED_WATER_HOST.md`: `3c7147110dc85a687f6120fe1d2ad02f96f5206522ee8b38e2fdfe0f00617787`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE within the explicitly stated component scope; the full Goal remains broader.
