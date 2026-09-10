# Independent Python review — source inverse pressure

## Current mapping follow-up approval

APPROVE current production `5695976e4f655bca189c7eadd87e62a321c048349d1ddcbf79a74b12f2d52e36` (16,681 bytes), author tests `0f5d3636f532ba0c8e2df1eb68cc47b16923e5246e3748ef538ac9811d85821b` (9,428 bytes). The three shared modules remain at the hashes below. The installed saved-data path exposed an equal dict/MappingProxyType asset-map rejection; an independent 1-failure/6-pass RED reproduced it without HEOS. The local Mapping/exact-string-key/strict-dict-content fix passes all original 22 plus seven new cases: **29 passed, JUnit 0.678 s**. See MAPPING_REVIEW.md and current FINAL.json. No numerical conditions or global _same/decoder behavior were relaxed.

## Original review before the mapping follow-up

APPROVE at the final hashes below. No unresolved critical/high finding in the bounded review scope. The earlier four identity failures and five source-metadata failures were actually reproduced, retained, fixed by the parent, and independently verified green.

## Frozen files

| File | Bytes | SHA-256 |
|---|---:|---|
| src/sludge_sandbox/source_inverse_pressure.py | 16,287 | f0c12306b011d4ebdf016f8935b33dab84614686b734de8ee59fa51abbf473c1 |
| src/sludge_sandbox/rigid_storage.py | 15,507 | bbfcb815d5918a93ec6a193f41c0779079019f02c9c89286fd65a24b8aee23e7 |
| src/sludge_sandbox/rigid_water_gas.py | 15,377 | 9247db9712ef881995c57a836b12adb7dbbf73c69bcdc036f02b99a15e1d5662 |
| src/sludge_sandbox/mass_wet_storage.py | 17,249 | dc9bead1cb0993953ad9c154dea6c8be5c4a8fbf1cefbdec3998d2d3d33e79fd |
| tests/sandbox/test_source_inverse_pressure.py | 8,481 | de205edc5ba04e70af0878941a1b6d40dedd4a2cd5c2b84ae789452f85da8f40 |

All hashes were rechecked after the final test process. The source/test files parse, and git diff --check passes. Ruff, mypy, pylint, black and bandit are unavailable in the existing interpreter; none was installed. FINAL.json retains exact file metadata and parsed JUnit results.

## Actual adverse verification

Final independent batch: **22 passed, zero errors/failures/skips, JUnit time 0.624 s**. Evidence: final.log and final.xml. This is the original 17 probes plus the five parent-requested metadata cases, without a broadened follow-up test campaign.

The fixture creates an actual SourceWetStorage point/inverse with the existing explicitly manufactured constant-liquid seam and nonzero available-volume uncertainty. Native water solving is forbidden. After fixture preparation, six source/storage/water evaluation entry points are patched to raise; all continuation construction, rechecking and adverse mutations run under those guards. No native HEOS case construction, native EOS, installation or full integrated suite was performed by this reviewer.

The checks cover planar liquid-pressure and exact gas-constant identity, individual original closure residual/resolution mutations, single-ULP underreporting of all three source pressure-error quantities, original temperature/capacity/source-sensible-energy relations, source-asset substitution, original source metadata and explicitly unknown fields, changed output qualifications/exact types, and the extracted closure_diagnostics binary64 sequence. The tests establish these input and record contracts, not a whole-domain EOS certificate.

Preserved actual progression:

- first.xml: 17 tests, 4 failures / 13 passes, 0.555 s, source 7cc846444bdb4314c0aafa324030cc112afb07d8f3fa964022f13f5c05bf1745. Contradictory wet liquid_pressure_pa values and a Fraction substitution for binary64 R were accepted. FIRST_FINDINGS.md and first-* source snapshots retain the evidence.
- identity-green.xml: those 17 tests pass, 0.540 s, source b58d0a617116d5200b69f2bb778576421c029d6455a87a1ed04406609ecfd495. The fixed model binding uses exact typed equality for planar liquid pressure and R.
- metadata-red.xml: five failures, 0.478 s, same b58d0a... source. Empty source IDs, stronger qualification and invented fit error/solid volume/total enthalpy were accepted inside the supplied actual-point graph. METADATA_FINDINGS.md and identity-fixed-* snapshots retain this evidence.
- final.xml: all 22 pass on f0c12306... . The point-source union now matches original evaluate semantics, including legal additional runtime fluid sources; fixed qualification and None-valued unsupported fields remain unchanged.

## Review conclusions and limits

The three shared arithmetic extractions preserve their original expression order, directed conversions and existing caller gates. The independent diagnostic check confirms the original represented closure arithmetic on the fixture. This reviewer did not independently rerun the parent's full legacy/native captures, and does not claim this one diagnostic probe as complete legacy validation.

The new source entry binds the actual storage/state/inverse graph, rechecks caloric lower-capacity and source-sensible-energy accounting, declared error floors and source additions, original closure residual/resolution, and nominal/global/local pressure-error requirements. It explicitly retains a saved-energy-roundoff contract; it does not independently reconstruct the native liquid EOS samples or all underlying energy terms. The record's immutable digest detects subsequent input changes.

Pressure continuation remains exact Fraction arithmetic under explicit whole-box smooth/stable-branch and declared-response hypotheses. The global enclosure establishes the smaller bootstrap domain first. It is a conditional bound, with source_certified=false and event_admitted=false. The trial wrapper adds its separate conditional gate and leaves the original reported-temperature endpoint gates and unresolved full-source certification intact. Unknown material properties are not invented.

A future saved-native bridge may construct HEOS providers and execute DmassT reference-anchor validation. Those construction/anchor costs must be recorded separately; this review does not label such reconstruction zero-EOS. The endpoint continuation itself can remain passive once its actual inputs and identities are supplied.

The parent owns the production fixes, actual component/integrated tests, native evidence work and final documentation. All reviewer artifacts are confined to the assigned temporary directory; no production edits or commits were made here.
