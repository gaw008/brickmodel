# Saved endpoint extraction, no event tolerance selection

extract_endpoints.py passively read the frozen completed native trial (SHA7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505). Prefix terminal and final successful reference capture share the exact end1/16384 s; reference is completed. ENDPOINTS.json stores all differences, original uncertainty inputs and conditional pressure calculations as exact numerator/denominator objects. EXTRACT01.log displays approximations only. No new event policy or tolerance was chosen and no EOS was called.

Per-cell |U difference|:0,1.9208528101444244e-9,1.1525407899171114e-6 J. All three reported temperature differences are0, while sums of inverse temperature errors are3.774998253690762e-9,5.6182564775326137e-8,4.130934431170084e-8 K. Equal reported temperatures do not erase inverse uncertainty.

Per-cell reported-T pressure difference-plus-error upper bounds:0.0025730662129493393,0.0027357101317249293,0.003380390424404161 Pa. The largest nominal reported pressure difference is0.0005942638963460922 Pa in cell2. Full4-slot amount differences are retained exactly; max is1.1954456868856767e-10 mol (cell2,N2).

The new analytic propagation route, explicitly conditional on the original manufactured numerical |uP| envelope and stable smooth branch, gives bootstrapped full pressure difference upper bounds0.0025853136999620355,0.002934899677443897,0.0035392830997053887 Pa. All exact T intervals and global conditional P enclosures stay inside the declared310..350 K/1e5..1e7 Pa domains. These numbers reduce the unknown thermal contribution under an existing contract; they are not independently source-certified full-pressure bounds and do not grant an event comparison pass.
