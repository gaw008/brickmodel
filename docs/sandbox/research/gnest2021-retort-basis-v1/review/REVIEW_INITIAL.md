# Retort basis independent review — two local checker gaps

Reviewed original checker SHA
`ec22d05e04becfb1f80ff911f356773fd4f899bfdc6d702fbd2bcde6dba516b7`
and facts SHA
`d54690e71850a09c640cc0644245028420a160fa64b007a87dde75bbdb4714a3`.
No repository edits, EOS, performance tests or installations.

The actual local PDF SHA matches the recorded
`77579a1a03652402527970c8b2a1896081224842f0646ec0cbbc3bf61ae63249`.
Read PDF 70/80/81 text and visually inspected PDF 81. All 24 transcribed printed
entries match; actual 34.32 g and 2.8% moisture are distinct from the table's ad
9.90% basis. Separate char and ash rows were not incorrectly combined for daf
conversion. The upstream record SHA matches its actual bytes.

Independent standard-library arithmetic performed 66 explicit checks, including
all 12 four-corner interval boxes, nominal projections and marginal overlaps.
Results are in `INDEPENDENT_ARITHMETIC.json`. Saved ARITHMETIC01 output agrees
with the unmodified actual checker run.

The report correctly treats ±0.005 percentage points as a conditional printed
rounding assumption, not an experimental confidence interval or proof of joint
correlated feasibility. The 5.17% daf discrepancy is preserved as a magnitude;
subtracting it from 50.35 is explicitly conditional on a positive tar correction,
not identification of original recovery. No unsupported material/source upgrade
is present in the unmodified facts or prose.

The isolated 6-case probe completed in 0.16204191698 s, zero EOS. It copies checker
and facts solely beneath this review directory. Charge and actual-moisture
changes correctly alter computed mass; changed printed gas fails the conversion
gate. This proves those computations use record fields rather than unrelated
hardcoded outputs. Original scripts, records, stdout and stderr are retained.

[MEDIUM] Missing actual charge/moisture domain guard
File: data/sandbox/research/gnest2021/retort-basis-v1/check_basis.py:56
Issue: Setting actual_run.initial_moisture_percent='120' exits successfully and
prints negative dry mass -858/125 g. The arithmetic checker does not reject an
invalid fraction of the recorded physical charge.
Fix: Require a positive finite exact charge and actual moisture within its valid
percentage domain, while keeping the original 34.32/2.8 data and formulas.

[MEDIUM] Input qualification field ignored by the output
File: data/sandbox/research/gnest2021/retort-basis-v1/check_basis.py:64
Issue: Setting facts.material_qualified=True still exits successfully, while the
output always prints false. The checker can therefore appear green with a
contradictory qualification declaration in its actual input record.
Fix: Explicitly require the original input qualification to be False; do not
reinterpret or quietly replace an upgraded input flag.

Both concrete probes and their preserved RED evidence were sent to the author
and Root. These are narrow checker guards; no broad decoder or source-authentication
framework is requested. Final approval will follow just the original two adverse
cases and normal control against the corrected checker.
