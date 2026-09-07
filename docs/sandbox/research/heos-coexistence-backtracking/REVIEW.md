# Independent frozen candidate review

Scope: diff of candidate/sludge_sandbox/_heos_kernel.py against production at ae38c70, full surrounding kernel and call sites, test_backtracking.py, IMPLEMENTATION.md, PLAN.json, and before/after XML. Production Git index and working tree were clean when review began. No native EOS run or production edit was performed by this reviewer.

Reviewed candidate SHA-256: `88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93`.

No blocking defect found in this numerical-control change. At constant temperature, dg = dp/rho, so derivatives of the Gibbs residual with respect to log liquid and vapor density are dp_l/drho_l and -dp_v/drho_v; the pressure row includes the corresponding densities. The existing inverse 2x2 Newton direction remains correct. The max residual merit uses each original absolute convergence gate (1e-4 Pa and 1e-6 J/kg), and acceptance either meets BOTH gates or strictly reduces their maximum normalized residual. Improving only one component cannot justify an increased maximum merit.

Accepted trial tuples and densities are assigned together, so carried values describe the next outer state. Rejected candidates do not overwrite them. The eight outer evaluated states include the seed; no transition after unsuccessful iteration 7 is evaluated. This does increase EOS trial work, bounded by six pairs per transition (maximum 1 + 7*6 = 43 coexistence pairs, before successful final snapshots). It is not an eight-EOS-evaluation claim. Nondecrease at all six fractions fails explicitly; numerical stagnation can still occur and is not claimed solved globally.

The original Newton log-step limit, liquid/vapor density branches, positive stable slopes, finite native values, final snapshot Table 3 checks, native h/u/s and physical constants are unchanged. Invalid trial EOS/native failures propagate immediately through the established exception mapping, with phase reset in finally. Public callers still hold the original transaction lock and source/configuration guards across all helper work. No global reference reset, artificial h/u/s adjustment or mass/energy correction was introduced. Diagnostics retain outer tuples and add all successfully evaluated trial residuals and acceptance decisions; native failure details remain exception evidence rather than a completed trial entry.

Independent validation (no native EOS):

- Reran all 11 worker tests against the frozen candidate: 11 passed in 0.04 s.
- Additional in-memory scripted check forced rejection of fractions 1 through 1/16 and acceptance at 1/32; verified the full exact fraction schedule, acceptance flags, carried density equality and final phase reset.
- Additional scripted check improved pressure but worsened Gibbs enough to increase maximum merit, and confirmed rejection followed by half-step acceptance.
- The scripted tests deliberately do not represent a consistent thermodynamic EOS. They establish bounded control/guard behavior, not thermodynamic accuracy or real-material validation.

Approval is confined to this frozen code and no-EOS behavior. Root-owned original native failure/neighbor runs, 30-state and seven-derivative validation, source-manifest rebinding, installed regression and original coupled depletion run remain required before an integrated verification claim.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — frozen candidate numerical-control change; native and integrated verification pending.
