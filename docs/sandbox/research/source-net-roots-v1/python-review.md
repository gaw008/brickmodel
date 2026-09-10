# Independent Python review: rational source inventory roots

Scope: new `rational_polynomial.py`, `source_net_roots.py`, the two small helper extractions in `exact_affine_depletion.py` / `exact_root_order.py`, and three associated test files. No production files were edited by this reviewer. Source freeze and tool availability are in `freeze01.json`.

Final disposition: **APPROVE**. The provider resolved the sole public API typing item below with exactly six return annotations. Independently removing only those six annotations reconstructs the original reviewed SHA `c0389459f403d9d298e02808ec8432ad377c824283af68c02f071930af05b215`; no arithmetic changed. Final source SHA is `022912c0a26c4fba15fe1071880b5cc9b2e41c3cf3e0a50f190e87fb063ee6f2`. No outstanding CRITICAL/HIGH finding, root-order correctness, source provenance binding, security, swallowed-error, legacy-budget relaxation, or material/event-qualification defect was found in this review.

## Resolved finding

[HIGH] Public first-root API return contracts are not annotated

File: `src/sludge_sandbox/source_net_roots.py:131` and `:251`

Issue: `isolate_first_root` returns either root evidence or strictly positive no-root evidence, but its return type is absent. `order_source_panel_roots` also omits its public result type. Four public `check` methods omit `-> None`.

Fix: declare `QuadraticRoot | QuadraticNoRoot`, `SourcePanelRootOrder`, and `None` respectively. The root label tuples can also use `tuple[tuple[str, int, int], ...]` for clarity. Exact `type(...) is ...` checks are intentional in these numerical evidence contracts; replacing them with broader `isinstance` checks would admit bool/int/Fraction aliases and subclasses.

Resolution: all six required return annotations are present. The optional tuple label detail is not a blocking requirement. Actual final-source adverse rerun is recorded in `tests03-final.log`, `tests03-final.xml`, and `FINAL.json`: **29 passed**, zero failures/errors/skips.

## Actual verification

- Initial combined run: `tests01.log` / `tests01.xml`, 77 passed and 1 reviewer-fixture failure in 0.50 seconds. This was **not a production defect**: the probe assumed an existing NumPy rate array could be made writable, but the byte-backed array correctly rejected `setflags(write=True)`. Original probe preserved as `test_adverse01.py`.
- Revised adverse suite: `tests02.log` / `tests02.xml`, **29 passed in 0.16 seconds**. The revised probe checks the original read-only defense, then explicitly replaces the field through `object.__setattr__` with a writable modified array; the saved source-panel check rejects the changed array.
- Adverse checks cover frozen-record field mutations, nested coefficient and label exact types, forged qualification/status/complete/competitor records, later common roots, proportional first roots with different domains and refinement counts, retained source identities, and mutated rate arrays.
- `bound01.json`: two very close irrational roots using an exact `2^-2048` coefficient perturbation, maximum 256 refinements. Actual construction **2.1875924579799175 seconds**, revalidation **2.1570364170183893 seconds**. Returned `unresolved`, `complete=false`, `refinement_level=256`, with both root records retained at 256 refinements. This is a measured two-inventory arithmetic probe, not a general wall-time guarantee for arbitrary inventory counts or coefficient sizes.
- The three supplied new test modules ran in the initial combined run and passed; the legacy fixture compares all recorded successful evidence and failure diagnostics to the pre-extraction baseline.
- `git diff --check` passed. All seven changed/new Python modules and tests parsed with `ast.parse`.
- `ruff`, `mypy`, `pylint`, `black`, and `bandit` are absent from PATH and the configured Python environment. Static lint/type/security tool execution is therefore **not claimed**. The configured environment also lacks `pip`; no installation was attempted by this read-only review.

## Additional parent evidence script review

Reviewed `/private/tmp/brick-source-net-roots-v1/root/check_install.py`, SHA `7fa4f5b866184e7ced453d0af4b0c127255ae1d8a3d5abb264df9108b823291a`, line by line. No blocking finding. It locates the installed package, requires a distinct site-packages location, checks every source package file byte-for-byte against its installed counterpart, and records source hashes. It parses actual JUnit XML and requires exactly 123 tests with zero failures/errors/skips. Missing files, mismatched bytes, or failed counts raise directly. Its claim covers every source package file; it does not inventory unexpected extra files in the installed directory.

Independently read the parent's pre-annotation source and installed XML records (no repeat execution): both contain 123 tests, zero failures/errors/skips, at 17.993 and 18.111 seconds respectively. The exact XML hashes and script hash are saved in `parent-xml-read01.json`. Those are parent-run broader tests, not reviewer-run tests, and were observed before the parent's final post-annotation installation freeze. The parent owns final installation verification.

## Boundaries checked

The shared bisection helper preserves the legacy `value >= 0` lower-endpoint update. The GCD helper is arithmetic-only; the new root layer independently validates descending branches and excludes a common later root. Every positive declared liquid and gas inventory competes; zero-initial inventories explicitly leave the route incomplete. Source-panel checking rebuilds derived content and snapshot bindings. The result qualification denies physical event admission, correction/writeback, dry transport, rewetting, or material qualification. No EOS, source dynamics, network, or event writeback was needed by these probes.
