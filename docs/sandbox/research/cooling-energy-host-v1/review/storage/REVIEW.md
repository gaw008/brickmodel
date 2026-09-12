# Independent storage review

Status: **APPROVE for the pure constant-coefficient rectangular-domain storage increment**, bound to the SHA256 values below. No unresolved CRITICAL/HIGH issue was found within this review scope. This is not time-integration or physical-material acceptance.

Frozen artifacts verified locally after the author's freeze message:

| Artifact | SHA256 |
| --- | --- |
| Candidate `thermoelastic_energy_storage.py` | `68d3f6b222b01a05c28c583f2575cfe46ca4d923eeb6729fd79c1411f34714cd` |
| Author `test_thermoelastic_energy_storage.py` | `0785c23cb8e5f6cd047ef0f2883f32b8d50f1e02a30aa67fb287d9017142bad3` |
| Frozen `cooling_thermoelastic_plate.py` | `33851857946f16b560529ad8a9d3ab1bc4fec6c1a18ae63bb9897d77a03746d7` |

The installed plate actually imported by the review is byte-identical to the repository plate at the displayed SHA.

Scope: `thermoelastic_energy_storage.py`, the frozen `cooling_thermoelastic_plate.py`, and `COUPLING_NEXT.md`. No native-host adapter audit or time integration. The only review writes are under this directory.

## Findings and dispositions

The initial implementation checked strain admissibility at each scalar trial although its existence proof covered only the temperature box. A trial could therefore be misclassified as a physical-domain failure, and a temperature-box root alone did not certify the strain constraints. The author amended construction to require the entire temperature box to satisfy the common-strain, thermal-eigenstrain, and mismatch bounds, and changed an out-of-box inverse trial to a numerical-resolution failure. That closes the reviewed gap for the explicitly supported rectangular domain. The mismatch-extrema check is conservative; narrower correlated domains are refused as unsupported configurations.

The author's first tests also exposed a public-certificate composition issue: the original temperature radius used exact dmin, while the exported dmin rounded downward. Each field was individually valid, but their public product could understate the residual norm by rounding. The final implementation divides by the already downward-representable dmin, rejects its zero-underflow case as numerical resolution failure, and rounds the radius upward. Independent exact checks now verify `norm(residual + target_error)^2 <= (returned_radius * returned_dmin)^2`. No target energy, material coefficient, or numerical acceptance tolerance was changed. The author reports preserving its initial red log; this reviewer did not read or alter that log.

Public API parameter/return annotations and concise docstrings were added before the final freeze. No other substantive mathematical correctness issue was found.

## Independent evidence

- Final local run: **76 passed in 0.21 seconds**, comprising the author's 56 tests plus the reviewer's 20 independent tests. The command used `/private/tmp/brick-cooling-thermoelastic-v1/installed-venv/bin/python -m pytest -q -p no:cacheprovider` on exactly `candidate/test_thermoelastic_energy_storage.py` and `review/storage/test_independent_storage.py`, with `PYTHONDONTWRITEBYTECODE=1`. No host or integration tests were run in this review.
- The original B coefficients are M=1e9 Pa, alpha=1e-4/K, C=1e5 J/(m3 K), Tr=300 K, k=1 W/(m K), half-thickness=.02 m, area=.01 m2, two cells, T domain=[290,310] K, strain domain=[-.01,.01], and outer surface T=300 K. No trajectory, numerical gate, or material coefficient was changed. Alpha-zero and sign-flipped-alpha cases are explicitly algebraic controls only. Boundary tests narrow the declared temperature domain without changing constitutive coefficients.
- An independent Fraction recomputation uses original represented binary64 M/alpha/C/Tr and the same rounded binary64 cell volume as the frozen plate. It checks `U_i=V[C(T_i-Tr)+M(e+alpha Tr)^2-M alpha^2 T_i^2]` and the resulting free-strain map. It does not interpret the rounded product stored internally by the frozen plate as exact M alpha^2. The candidate explicitly bounds the resulting plate-evaluation energy/strain differences.
- Exact central directional differences of the quadratic energy map match `J_E d`, and differ from `A_rate d` on nonuniform T. An explicit Helmholtz-energy substitution fails the internal-energy comparison.
- The scalar formulation uses `h(T)=CT-bT^2`, `q=mean(T)^2`, and the exact intersection of the temperature-square interval with every `h(T_i)=E_i/V+CTr-bq` interval. Positive fixed-strain heat capacity makes h strictly increasing and the closure F strictly decreasing. The SPD energy Jacobian proves uniqueness; the scalar endpoint signs separately prove existence.
- The B-domain target E=(-100,0) J has a nonempty q interval but no root. Independent rational bisection directly in T proves F(q_hi)>0; the candidate rejects it as `monotone_scalar_has_no_domain_root`. A separate target proves the empty-feasible-interval path.
- Residuals are recomputed at the actual returned binary64 temperatures in the exact binary-input energy map. Independent recomputation checks the absolute residual bounds, addition of target uncertainty, and the Euclidean temperature bound against an original temperature known to lie in the target energy interval. The exported Jacobian lower bound rounds downward.
- A zero target-error vector remains zero and is distinct from the positive numerical energy tolerance. The implementation rejects unattainable tight numerical tolerances and excessive target-error budgets. The model's manufactured status does not certify physical source uncertainty as zero.
- The exact domain endpoint at Tr succeeds without clipping; adding energy uncertainty that reaches outside the declared box produces a resolution failure. Alpha zero follows the exact linear branch; negative alpha retains the free-energy map and passes the signed-strain checks.
- The integer-isqrt routine passed 1004 exact rational enclosure/width checks, including extreme magnitudes. Eight additional exact inequalities verified binary64 outward conversion for zero, positive/negative values, subnormal values, and very large finite values.

## Limits and tooling

No integration, material calibration, fluid/pressure/reaction closure, production acceptance, or native-host derivative audit is implied. `FreeEnergyState` was verified to carry the final real plate evaluation, and the tests check its declared numerical energy and strain discrepancies.

`git diff -- '*.py'` was empty in the source repository. The selected Python environment provides pytest but not ruff, mypy, pylint, or black; none of those commands is available on PATH. Candidate syntax compilation succeeded without writing bytecode. The formal independent tests use only the existing environment and the standard library.
