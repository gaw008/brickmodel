# Canonical exact times and program queries

Baseline `5462deb`. See [the numerical contract](../../EXACT_EVENT_CLOCK.md).
Two new explicit modules provide canonical rational time/interval values and
exact query/knots for an existing validated scalar or boundary program. Physical
column outputs remain binary64; schedule translation is explicit and must join
any future run identity. No implicit absolute-time projection is provided.

The 23 new primitive tests and 41 legacy boundary-program tests passed both from
source and after offline noneditable installation: **64 passed in 0.11 s** in
each environment. The primitive installation contained 69 actual source-matching
modules. Later exact-integrator installation evidence is recorded separately in
`../exact-integration-v1/`; these counts describe successive frozen checks.

`CLOCK_CODE_REVIEW.md` covers identity, strict record decoding and display
separation. `PROGRAM_NUMERICAL_REVIEW.md` covers knot/weight selection, full
schedule translation, convex physical values and composition checks. The
archive contains the candidate, actual logs and test-only loader; only the two
modules and normal-import test were applied to the package.

This removes a time-representation obstacle, but does not establish native
depletion, spatial convergence, materials evidence or full firing completion.
