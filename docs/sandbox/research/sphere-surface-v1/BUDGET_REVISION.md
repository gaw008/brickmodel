# Robin verification resource adjustment

The unique first new-suite attempt (session81963, terminalexit1) completed8tests but the multicell Robin test stopped with `resource_limit/wall_time_limit` at its original30s perintegration resource ceiling. Fullsuite elapsed70.45s. Original code, test and failurelog remain preserved; no result from that partialcase is represented as a completed comparison.

Root authorized one change:90s wallmaximum for EACH Robin grid integration. This changes validation resource allocation only. Same4/8/16/16 grids; dt.001/.001/.001/.0005; Fo=.05; Bi1; mu=pi/2; manufacturedsource/caloric/geometry/initial/outerconditions; error reduction>3perdoubling; finestRMS<.005K; temporalmaxdelta<finestRMS/20; all integration accuracy/step/rejection limits remain unchanged. The onecell and other originaltests retain30s and their existing policies.

Eachgrid now writes a terminal resource row immediately(status,accepted,rejected,evaluations,elapsed,budget,lasttime) and then a metricrow after successfulcomparison. Rows are flushed to capturedstdout and pytest temporaryjsonl so subsequent failure does not discard earlier evidence. No concurrentnumericalscan or sourceinstallation is started by this author.
