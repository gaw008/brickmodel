# Installed passive study acceptance

Baseline is be506b6; original frozen N3 input is SHA256
6c55383e8d2063ed6c81f2126b40542ba44ee173fc1671b227573b908bfbfc53.
No new EOS evaluation or physical run is planned. Before execution freeze and
review source study core, its shared ledger helper, service and tests; install
that source non-editably and compare source/installed bytes.

The check invokes the installed CLI import, reads the resulting complete DAG,
compares every original top-level value recursively with roots/metadata/captures,
and checks all 32 original observation positions. Floats use exact hexadecimal
equality; arrays use shape and binary64 bytes; Fractions and event times retain
the original exact numerators/denominators. Only the six explicitly enumerated
old omitted live fields may acquire an unavailable reference record.

It then compares one original capture/cell and one full 2xN pressure-gate query
between installed CLI and Python. Constructors and live evaluation entry points
are replaced with raising guards for the entire import/decode/query operation.
The check is limited to 180 wall seconds; output directories are exclusive and
any failure remains. The already measured complete importer takes about 12 s;
the allowance covers repeated required decoding and complete value comparison.

This verifies serialization preservation and the codec's declared saved
arithmetic checks. It does not independently validate EOS hypotheses, reproduce
a process, authenticate original runtime identities, or authorize material
prediction/resume. Original independent pressure failures and material=false
must remain, even though the selected conditional event gate is true.
