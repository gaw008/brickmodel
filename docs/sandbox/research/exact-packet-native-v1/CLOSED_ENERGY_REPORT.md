# Closed energy and constraint audit

All 32 accepted prefixes passed the original represented binary64 2e-8 J gate, exactly equal to four original per-cell absolute energy budgets. Maximum abs(sum E - initial sum E + pe*(V-V0)) = 6.1668334987649011e-11 J at state 12. Cumulative absolute cross-cell constraint sum = 2.3107070843279913e-20 J; individual cell constraint work is nonzero.

Volume is independently computed as A0*H/N * sum(n_i) * t^2 from represented reference dimensions and full state stretches using Fraction. Case outer gas reservoir and outer heat surface are absent; every accepted outer face species/energy integral and body-work component is exactly zero. Therefore no omitted boundary/material energy or body term is silently treated as zero.

Script audit_closed_energy.py SHA256 d90ab4d91f08f9f0fe55c21ff07932a3a0f3317167d4700d259aba3796251248. Actual standard-library execution completed exit 0, output attempt01/closed-energy-audit.json. No EOS/import of production solver. First pure run used decimal-exact 2e-8 (slightly tighter); it passed and is preserved as before-gate-representation files. Final run explicitly uses Fraction(2e-8), identical to original policy arithmetic; no widened scientific threshold or failure repair.

This checks the complete saved accepted prefix, not spatial convergence, material validity or a theorem that local ledger errors bound nonlinear pressure-volume quadrature.
