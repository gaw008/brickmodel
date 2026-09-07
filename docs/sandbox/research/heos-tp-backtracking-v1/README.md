# HEOS TP bounded backtracking — numerical regression evidence

Production baseline: `9ab4b65`. Only TP Newton globalization and its implementation bindings change; the EOS data, original dynamic pressure gate, domain/source/config guards and final state checks remain in force. Eight accepted density states, six fixed fractions and at most 43 actual density evaluations bound each TP solve. Rejected and failed actual evaluations are retained.

The original joint v3 failure, exception capture and unchanged public-provider reproduction are archived in `../depletion-spine-v1/`. The failing 295 K state is an inverse bracket endpoint, not a converged brick temperature. The current six-fraction probe uses that identical seed: original fullstep fails, five shorter steps pass the same gate and full snapshot. This justifies a numerical step-selection correction, not an EOS data change.

Control chronology is preserved: initial artificial test pressure falls in the original ambiguity guard (14 failed/1 passed); corrected artificial fixture gives baseline5 expected failures/10passes; reviewed final19 controls plus11 original coexistence controls give30passes. These are manufactured controls, not water measurements. The actual frozen3x3 native grid gives original8passes/1center failure and corrected9passes. Raw XML is retained, including failures.

Fresh v4 callback passed in2.087812s. Depletion0 terminated failed in121.780958s; internal120.127148s,365evaluations,44trialpanels,6acceptedsteps,0events. Terminal comparison levels4/5 both passed all original gates; the independent half-cap/half-safe-fraction approach exhausted the budget after13panels/122evaluations, before reaching its terminal. No second whole-trajectory run or successful event is claimed. Its five scripts are byte-identical to v3; all original physical, source-uncertainty, acceptance and resource settings remain.

The A/B chemistry and prescribed deformation are manufactured fixtures. This is not raw-sludge material qualification, free sintering, public experimental validation or full Goal completion. Required material/full-cycle/CLI/UI/search work remains open. See the unchanged full Goal contract and current status.

Readable XML strips trailing whitespace per line and ends with a newline; original raw XML remains in the ZIP with per-entry size and SHA256 verification.

Final installed regression: session9190 exit0; 1220passed, zero failures/errors/skips, XML 539.545s. All42actualinstalledmodules exactlymatchsource before/after. NoEOS/testhandles remain active. Independent v4audit confirms177depletion/176callbackinputs unchanged; allsixacceptedprefix ledgers pass, eventcompletion stillfailsbudget.
