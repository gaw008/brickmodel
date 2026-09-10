# Source dry-mass storage pre-review

Read actual ArlabosseDryCaloric implementation and InversePolicy. Source supports Cp(T)=1434+3.29T Celsius, dry original mixed-feed sample, measured35–105°C, analytic sensible enthalpy difference only. Source assets and metadata are checked per operation. It does not provide intrinsic molar energy, density, reaction enthalpy or Nylen/Wang transfer.

Storage proposal must preserve exact source calculation by converting binary64 state values to Fraction.from_float before calling raw provider (which otherwise interprets float as shortest decimal). Exact lowerK endpoint308.15 differs from binary64 float308.15; policy must reject genuinely out-of-domain input rather than clip. An in-domain exact reference and fixed dry mass must enter identity, with source hash/equation node and explicit user-chosen energy zero. Energy offset is a reference convention, not source formation enthalpy.

Using measured Cp enthalpy to represent internal-energy changes requires an explicit incompressible/no-temperature-dependent-volume/no-pressure-energy model assumption; fixedvolume alone is not evidence that the paper measured Cv. Fit/model error is unknown and cannot be hidden in exact numerical residuals or inverse temperature certificates.

For positive fixedmass and affine positiveCp, a minimum derivative on the original complete bracket is mass*min(Cp(lo),Cp(hi)). Exact energy residual divided by this lower bound bounds numerical temperature distance to the nominal fitted model root, provided actual target lies in bracket image. Returned temperature rounding and target/energy rounding policy must be included explicitly; endpoint/midpoint/underflow/overflow cases need honest failure, no clipping or tolerance relaxation. Reuse InversePolicy rather than introduce a new integrator/PDE.

ReactionDisabled should bind complete unique actualspecies IDs and output exactzero reaction source for those IDs, without inventing A/B, oxygen reference, formationenergy or zeroing independent liquid-vapor transfer. Full thermal/material storage admission remains separate.

Implementation review awaits root freeze.
