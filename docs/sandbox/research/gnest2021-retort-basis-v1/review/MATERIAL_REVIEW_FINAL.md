# APPROVE — source-specific retort basis evidence

Final checker SHA256:
`2cffe8cfcd25c39e2f583414985190486554533da5c532cad9983c56f1d229fd`.
All six actual delivered file hashes are in `MATERIAL_REVIEW_FINAL.json`.
Facts, source locations, README, report and ARITHMETIC01 remained unchanged.

The independent source and mathematical checks are described in
`REVIEW_INITIAL.md` and `INDEPENDENT_ARITHMETIC.json`: the actual PDF hash was
verified, PDF70/80/81 text read and PDF81 visually inspected; 24 original printed
values and all 12 conditional four-corner basis projections agree. The 66
independent assertions passed. Actual 2.8% moisture is kept distinct from the
9.90% ad table denominator. Neither a signed 5.17% correction nor raw product
recovery is invented; ±0.005 is explicitly a hypothetical print-rounding box,
not experimental uncertainty or correlated joint closure.

The initial 6 isolated checker cases are retained with their original files and
stdout/stderr. Two real findings were reported: 120% actual moisture yielded a
negative dry mass with successful exit, and an upgraded input material flag was
ignored. The author added only the corresponding input-domain and qualification
guards. The exact arithmetic and original records were not changed.

Independent focused retest of the original two adverse inputs plus the normal
control passed in **0.079138208 s**. Both malformed inputs now exit 1; the normal
output is byte-identical to the initial normal control. See `GREEN_RESULTS.json`
and `fixed/`. Old RED artifacts were not overwritten. No findings remain.

The checker AST parses. This is a standard-library research arithmetic script,
not an installable general untrusted-input codec; review does not promote it to
one. It uses ordinary Python assertions and was run with normal, non-optimized
Python. No EOS/provider/performance run, installation or repository edit was
performed by the reviewer.
