"""Review literal pore-distribution normalization against the primary 1992 limit.

This records a source discrepancy. It does not admit a corrected material
model, infer unavailable size moments, or fit the sintering observations.
"""
import argparse
import json
from pathlib import Path
import mpmath as mp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); p = json.loads(args.parameters.read_text())
    mp.mp.dps = p['decimal_digits']; r = mp.mpf(p['mean_radius_m']); r2 = mp.mpf(p['mean_square_radius_m2'])
    s = mp.mpf(p['polydispersivity']); records = []
    for value in p['porosities']:
        phi = mp.mpf(value); eta = 1-phi
        z0 = (4*phi*r*r*(phi+3*s*eta)+8*r2*(s*eta)**2)/(phi**3*r2)
        z1 = (6*phi*r*r+9*s*r2*eta)/(phi**2*r2); z2 = 3/phi
        literal_ev = lambda z:phi*mp.exp(-2*s*eta*(z0*(1+z)**3/8+z1*(1+z)**2/4+z2*(1+z)/2))
        literal_rf = lambda z:s*eta*(3*z0*(1+z)**2/4+z1*(1+z)+z2)*literal_ev(z)/phi
        integrated = mp.quad(literal_rf,[0,1,mp.inf]); boundary = literal_ev(0)/phi
        # Lu/Torquato1992 Eq4.34, x = distance/(2*particle radius), A=2.
        original_survival = lambda z:mp.exp(-eta*(3*z/phi+(3+mp.mpf('1.5')*eta)*z*z/phi**2+(eta+1)*z**3/phi**3))
        unshifted = lambda z:mp.exp(-2*s*eta*(z0*z**3/8+z1*z**2/4+z2*z/2))
        density = lambda z:-mp.diff(original_survival,z)
        primary_integral = mp.quad(density,[0,1,mp.inf])
        correspondence = max(abs(original_survival(mp.mpf(x))-unshifted(mp.mpf(x))) for x in p['comparison_radii_normalized'])
        records.append({'porosity':value,'printed_z_coefficients':list(map(str,[z0,z1,z2])),
            'literal_distribution_integral':str(integrated),'literal_boundary_probability_ratio':str(boundary),
            'literal_quadrature_vs_boundary_error':str(abs(integrated-boundary)),
            'literal_normalization_error':str(abs(integrated-1)),
            'literal_distribution_normalized':bool(abs(integrated-1)<=mp.mpf(p['normalization_budget'])),
            'primary1992_normalization_error':str(abs(primary_integral-1)),
            'unshifted_vs_primary1992_survival_error':str(correspondence),
            'primary_mean_distance_over_radius':str(mp.quad(original_survival,[0,1,mp.inf])),
            'arithmetic_agreement':bool(abs(integrated-boundary)<=mp.mpf(p['arithmetic_agreement_budget']) and correspondence<=mp.mpf(p['arithmetic_agreement_budget']))})
    result = {'settings':p,'records':records,
        'all_arithmetic_comparisons_met':all(x['arithmetic_agreement'] for x in records),
        'literal_source_normalization_passed':all(x['literal_distribution_normalized'] for x in records),
        'interpretation':'As printed, Eq7/6/9 do not yield initial normalized porosity1. The1992 monodisperse limit uses unshifted surface distance and agrees with removal of the spurious1+zeta shift. This is a sourced limiting correspondence, not a formal erratum, complete polydisperse proof or a material-fit correction.',
        'production_model_admitted':False,'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
