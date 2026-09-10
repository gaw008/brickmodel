# Independent fixed-sphere programmed surface review

Inspected complete3file candidate diff and source/test contents. All3 hashes match author FREEZE.json; reviewer binding in RESULT.json. Source programmed_solid_fluid_heat SHA2569965aff35621112e763d1cbdf2f185b0fc10a483047e160773059f51df97adf8. No author files changed. Static tools remain unavailable in isolated runtime; no native liquid EOS, new fitting or duplicate multigrid run executed.

## Implementation and physics

Only actual _surface geometry consumers change: outer area from selectedbase._face_metric(last,None) and surface→cell heat from selectedbase._conduction. Selectedbase is supplied current transport for both DeformingSolidHeat and FreeSolidSlab; static default uses self.transport. Spherical helper gives exact analytic half-shell resistance with existing binary64 numerical policy, outer physical4*pi*R²area. Residual, tolerance, bracket, bisection, failedroot propagation and zero-conduction branches remain unchanged.

Actual evaluate still calls basehost once; its inverse objects are reused. Gas faceexchange and donor enthalpy stay on same outward ledger, while intoheat is subtracted. Zero-k therefore does not remove gas enthalpy. Program interpolation/breakpoints unchanged. Constructor removes only sphericalprogrammed rejection. Earlier sphere+liquidtransport and sphere+bothmovingwrapper guards remain in their constructors. Sourcegeometry still participates in base identity and source IDs. No Nylen material admission or new codec/replay schema follows.

Independent math in CONTRACT_REVIEW.md verifies linear seriesfilm, nonlinear monotone residual and Robin μcotμ=1−Bi boundary. Bi1 principal μ=π/2 mode and total gasCv+solidCp capacity in submitted convergence fixture are correct. Firstcell midpoint remains distinct from center observation. Submitted source tests meaningfully cover8 local cases and actual samehost/integrator Robin grids; removing old sphericalboundary rejection test is justified by new positive and limit tests.

## Actual reviewer evidence

1. PriorHEAD source captured before candidate changes with28 binary64 golden evaluations:4slab modes×7exact/interior program times. Current candidate matches every saved hexfield: temperatures, convective/radiative/conductive powers, residual/limit, iteration/status and entire face species/energy arrays. No old outputs recomputed for the comparison. Scripts and logs retained.
2. Three independent tests passed0.37s:90digit bisection of independent spherical radiation polynomial within original wattresidual-implied temperature allowance; explicit changed current slab area/thickness feeds both filmarea and seriesresistance rather than referencegeometry; zero-k gasinflow energy equals actual donorenthalpy times inflow.
3. Requested moving regressions actually1passed/1failed0.42s. FreeSolidSlab current surface/mechanics forwarding passed. DeformingWet fixture fails at wrapper construction before _surface: existing _canonical rejects an ndarray in its motion configuration. Frozen priorHEAD wrapper with the same fixture produces exactlythe same unsupported_identity_type:ndarray. Both complete logs retained. This is a verified preexisting test/setup limitation, not a newly caused surface regression, but that particular full DeformingWet execution remains unverified; it must not be reported as passed. Static currenttransport branch and independent validcurrenttransport helper test remain positive evidence with narrower scope.
4. Author's first Robin run recorded resource_limit with8passed/1failed under30s pergrid cap. Root authorized only90s resourcebudget change plus pergrid diagnostics; physical case, meshes/timesteps, Fo and numerical error gates unchanged in inspected finaltest. Author owns unique rerun and its handle; reviewer does not duplicate or prematurely claim its results.

## Conclusion

No new physical, numerical, source or boundary-flow defect identified in the frozen surface change. Final scientific convergence claim depends on author's terminal saved multigrid result, not this static approval. Keep preexisting DeformingWet construction failure explicit. All coefficients used here are manufactured verification inputs; complete sludge/brick model and material validation remain unfinished.

## Terminal author Robin result readback

Read terminal author-tests02.log (19passed79.04s), RESULT.json and all8 original robin-grids.jsonl rows. Four completed evaluated rows match log and summary exactly, endpoint0.10674214952738706s agrees with fixture Fo/alpha calculation. Accepted107/107/107/214, rejected0; elapsed4.9146/9.6506/19.0736/38.0421s all below90s budget. Saved RMS0.0133739916035/0.00330482479575/0.000815452738466K gives spatial ratios4.046808 and4.052748, both>3. Finest halfdt RMS0.000815441276494K; saved maxdifference1.645332758926088e−8K is below original4.07726369233057e−5K timegate. All3 final source/test hashes still match freeze.

check_saved_robin.py and ROBIN_SAVED_REVIEW.json independently check record consistency, exact Fraction gate comparisons and dimensional endtime. Raw final temperature vectors were not retained in these saved artifacts, so this review does not claim independent recomputation of RMS or temporal max from statevectors. No repeat gridrun performed. Previous report pending wording is superseded by this terminal savedresult audit; preexisting DeformingWet construction failure remains separately disclosed.
