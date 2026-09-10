# SourceWetStorage independent physics review

Scope: reviewed source_wet_storage, extracted wet fluid closure, existing rigid water/gas energy closure, source dry mass caloric adapter, and already pinned source metadata. No repository changes. This reviews fixed-composition storage at a point; it does not close moving wet-cell transport, reaction, N-cell integration, or same-material experimental validation.

## Assessment

No blocking physical/numerical discrepancy found within the declared contract. Fixed dry mass uses the exact value of binary64 0.2, not the mathematical rational 1/5. The explicit binary64 input restriction is a defensible numerical API choice, not a scientific assertion about measured decimal data. The state factory fixes this mass and the checker rejects subsequent solid-mass changes. ReactionDisabled covers O2, N2 and H2O with exactly zero chemical rates; it does not claim that phase transfer is chemically prohibited.

The solid law is source Eq2, Cp = 1434 + 3.29 theta J/(kg K), theta in degrees C. Its sensible internal-energy coordinate is m[1434(theta-theta0)+1.645(theta²-theta0²)]. Under the chosen incompressible constant-volume fixed-composition approximation the temperature-dependent change in u equals the source constant-pressure sensible h change. No absolute formation energy is supplied or required. A change of anchor shifts U by a constant only while dry mass and composition remain fixed. This must not be reused for reactive or variable-mass solids without a physically consistent reference and transfer accounting.

The positive slope allows the source minimum Cp over the entire explicit 310..350 K host domain to be evaluated at 310 K. Adding this exact dry contribution to the existing fluid global lower bound and rounding down is appropriate. This is distinct from the actual point closed heat capacity. The lower bound is conditional on the fluid envelope and thermodynamic stability assumptions; it is not a bound on the unknown experimental Cp-fit error. fit_error remains None.

Fluid pressure error includes the existing water/closure error and the additional prescribed available-volume uncertainty. The latter first uses the global gas compliance bound, certifies pressure remains inside the EOS domain, then uses the certified local upper pressure. The aggregate energy error preserves existing fluid energy error, adds liquid n|du/dp| times the additional pressure error, and adds final binary64 total-energy rounding. The sensible solid term is exact nominal rational arithmetic. No independently added latent-heat term appears; shared liquid/vapor energy references already provide the phase-change energy difference.

Only a manufactured constant available liquid-plus-gas volume is admitted. There is no bulk volume or solid-volume source. Returning total_enthalpy_j=None and solid_volume_m3=None is therefore correct; fluid enthalpy may exist separately but cannot establish total H=U+pVbulk. Material qualification stays false. Arlabosse's original mixed-feed dry caloric identity is not transferable to Nylen materials without evidence.

## Actual independent calculation

Script check_native_independent.py imports make_case solely to reproduce configuration and obtain primitive water/gas providers. It never calls SourceWetStorage.evaluate/invert, RigidStorage.evaluate_at_temperature, or evaluate_wet_fluid. It uses scipy brentq for liquid-volume plus ideal-gas volume closure, direct water state and source gas caloric calls, and the printed polynomial above for the solid contribution. This provides independence of closure algorithm and aggregate arithmetic, not independence from the EOS library or source gas primitives.

At 331.25 K it obtains pressure 1048366.2303881466 Pa and U = -66683.25064047943 J. Differences from the production result are about 3.54e-6 Pa and 5.82e-11 J, within the reported 0.0013773563250684992 Pa and 7.4873681826009e-8 J numerical envelopes.

Centered energy differences at h=0.01 and 0.005 K give 351.8252909016155 and 351.82529090961907 J/K, versus reported point C = 351.8252909040792 J/K. These are local numerical consistency observations, not a whole-domain certificate.

Transferring exactly 1/1024 mol liquid to water vapor at unchanged temperature raises U by 38.947704198159045 J. At the conserved initial U, the independent temperature root is 331.1392713118579 K; the reported root 331.13927133381367 K differs by about 2.20e-8 K, within its 2.4454682928812732e-8 K bound. Water inventory is exactly conserved, dry mass does not change, and chemical rates are exactly zero. This is an imposed phase-inventory state comparison, not an evaporation kinetics or equilibrium validation.

All 13 bounded assertions pass. INDEPENDENT_RESULT.json includes exact Cmin rational, measured values, source/code hashes and script hash; INDEPENDENT.log is actual stdout. Historical CONTRACT.md and SOLID_ORACLE.json describe a pre-implementation proposed case and are not substituted for this actual case. The current inputs follow the parent's declared example before checking its residuals.

Remaining limitations: conditional test EOS envelope, unknown source fit error, manufactured available volume, no same-material admission, no solid transport volume, no complete wet-grid host or kiln process model. This calculation does not remove any of those missing requirements.
