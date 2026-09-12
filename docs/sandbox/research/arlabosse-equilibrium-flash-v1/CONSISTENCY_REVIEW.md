# Independent review — nominal thermodynamic consistency diagnostic

**APPROVE as a local implementation diagnostic, with one provenance-record warning.** The single passive JSON/Fraction review passed **11 checks**, with no application import, EOS call or repeated physical sampling. The five stored samples and the actual script were reviewed against the present storage, low-water excess and chemical-potential definitions.

With x=Nc, the script keeps exact total water, fixed carrier inventories, dry mass and rigid available volume. It recomputes mechanical pressure at each T/x sample. Thus g=μl(T,P)+μex(T,x)−μv(T,pv) and its T difference follow the **fixed-volume, fixed-composition mechanical path**, not fixed pressure. For a common differentiable Helmholtz potential A, g=A_x and U=A−TA_T imply U_x=g−Tg_T. At fixed x the current excess h is T-independent, so its contribution does not alter U_T; comparison with the actual closed-composition Cv is appropriate. These structural identities do not create a bounded runtime derivative certificate.

Independent reproduction gives **U_x=-46331.4292833594 J/mol**, **g−Tg_T=-46331.429269910484 J/mol**, residual **-1.3448916e-5 J/mol**, within the unchanged nominal tolerance **4.63314293 J/mol**. The T difference is **20.839583678044473 J/K** versus stored Cv **20.83958367723455 J/K**, relative residual **3.88646e-11**. The saved pressure-drive form RT·ln(peq/pv) agrees with each saved g to at most **3.27418e-11 J/mol**, using the existing nominal phase identity tolerance.

Exact Nt is **283346711338661571981 / 4722366482869645213696 mol**. All five projected Nc+Nv residuals are exactly zero and both pools stay positive. The center matches the prior actual long-case point's U, Cv, pressure, stated errors and source IDs. Samples retain the original T/P/W domain and IAPWS/NIST/Arlabosse-derived properties, conditional low-W extension and manufactured rigid geometry. Saved source IDs and this center correspondence are not a new independent authentication of the executing environment.

Only the stored U uncertainties already contribute about **0.721540 J/mol** to the composition difference and **7.21541e-6 J/K** to the temperature difference. Chemical-potential/logarithmic and differencing-truncation bounds remain unknown. The center has **g≈8132.76 J/mol**, so this is not an equilibrium root. Five samples establish neither a global thermodynamic identity/error bound nor a flash equilibrium heat-capacity floor or temperature certificate. Material and global-certificate flags correctly remain false; recorded runtime is **1.46518 s**, below 60 s.

**[MEDIUM] Initial plan revision overwritten.** `check_consistency.py:29–30` writes the changed dx back to the same `CONSISTENCY_PLAN.json`, leaving only the final 1e-7 revision. Source ordering places this after the three T samples and before either x sample. Exact inventory arithmetic confirms the original +1e-5 choice would make Nv negative; no such failed physical point exists in the saved observations, and the diagnostic thresholds are unchanged. Nevertheless, the surviving record does not independently preserve original registration chronology. Describe it as an amended local diagnostic; retain separate original/amendment records in subsequent runs rather than reconstructing an original plan retrospectively. No repeat EOS evaluation is required to acknowledge this limitation.

Evidence: `audit_saved01.py`, `AUDIT01.log`, `SAVED_REVIEW01.json` and `REVIEW_SHA256.json`; original artifacts were not modified.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | info |
| LOW | 0 | pass |

Verdict: APPROVE — scoped nominal diagnostic, with the plan-history limitation retained; no global or flash-temperature certification.
