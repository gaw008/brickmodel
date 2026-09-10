# Actual native closed-column run plan

The source-native probe completed with 1.290798 s build and 2.347864 s single three-cell evaluation. Using that measured cost, run exactly one fixed midpoint step over 1/1024 s with the unchanged make_column configuration: three nonuniform cells, original source dry Cp, actual HEOS water and NIST O2/N2/ideal water vapor, declared manufactured geometry/transport and closed boundaries.

Keep inverse policies 1e-5 J / 1e-6 K / 100 iterations, existing native numerical envelope, phase/face parameters, and default aggregate projection budgets 1e-8 J and 1e-12 mol unchanged. Whole integrator wall limit is 45 s; outer supervisor hard timeout is 60 s. This is one full bounded step, not a long-time or spatial-convergence claim. A failure saves its actual status/reason and accepted prefix and does not authorize a second attempt with looser scientific or numeric gates.

Success requires actual run.status=completed, exactly one accepted ledger and endpoint, all expected cell/face indices, 20 exact Fraction local/global inventory-energy assertions, three successful operator evaluations, no material admission, and unchanged source/native files. Process exit0 alone does not establish completion. Native EOS/fit error and material volume/transport uncertainty remain conditional or unknown as declared.
