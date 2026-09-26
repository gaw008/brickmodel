"""Trace the published pore-radius input back to literal source geometry.

The two particle distributions are source-described mathematical examples,
not inferred specimen distributions. No physical parameter is calibrated.
"""
import argparse
import json
from pathlib import Path

import mpmath as mp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    mp.mp.dps = p['decimal_digits']
    radius = mp.mpf(p['radius_m'])
    records = []
    for item in p['porosities']:
        phi = mp.mpf(item)
        eta = 1-phi
        # Eqs2.24/2.25: y3 fixes the initial survival probability exactly.
        y0 = (2-phi+eta**2-eta**3)/phi**3
        y1 = eta*(3*eta**2+4*phi-7)/(2*phi**3)
        y2 = eta**2*(1+phi)/(2*phi**3)
        y3 = -(y0+3*y1+12*y2)

        def mono_survival(z):
            return mp.exp(-eta*(y0*(1+z)**3+3*y1*(1+z)**2+12*y2*(1+z)+y3))

        mono_integral = mp.quad(lambda z: -mp.diff(mono_survival,z), [0,1,mp.inf])
        mono_mean = mp.quad(mono_survival,[0,1,mp.inf])
        examples = []
        for example in p['distribution_examples']:
            r2 = mp.mpf(example['relative_second_moment'])
            r3 = mp.mpf(example['relative_third_moment'])
            s = r2/r3
            z0 = (4*phi*(phi+3*s*eta)+8*r2*(s*eta)**2)/(phi**3*r2)
            z1 = (6*phi+9*s*r2*eta)/(phi**2*r2)
            z2 = 3/phi

            def literal(z):
                return mp.exp(-2*s*eta*(z0*(1+z)**3/8+z1*(1+z)**2/4+z2*(1+z)/2))

            integral = mp.quad(lambda z: -mp.diff(literal,z),[0,1,mp.inf])
            formal_mean = mp.quad(literal,[0,1,mp.inf])
            examples.append({'example':example,'polydispersivity':str(s),
                'initial_survival':str(literal(0)),
                'density_integral':str(integral),
                'density_integral_vs_boundary_error':str(abs(integral-literal(0))),
                'probability_normalized':bool(abs(integral-1)<=mp.mpf(p['normalization_budget'])),
                'formal_survival_integral':str(formal_mean),
                'formal_length_m_not_a_valid_distribution_mean':str(radius*formal_mean)})
        records.append({'porosity':item,'monodisperse_initial_survival':str(mono_survival(0)),
            'monodisperse_density_integral':str(mono_integral),
            'monodisperse_probability_normalized':bool(abs(mono_integral-1)<=mp.mpf(p['normalization_budget'])),
            'monodisperse_mean_distance_m':str(radius*mono_mean),
            'monodisperse_survival_samples':[{ 'zeta':z,'survival':str(mono_survival(mp.mpf(z)))} for z in p['distance_samples']],
            'polydisperse_examples':examples})
    result = {'settings':p,'records':records,
        'dimension_review':{'definition':'zeta = a / mean(R), dimensionless',
            'printed_after_Eq2_26':'a = mean(zeta) / mean(R)',
            'printed_right_hand_dimension':'inverse_length',
            'required_dimension':'length',
            'dimensionally_consistent_identity':'mean(a) = mean(R) * mean(zeta)',
            'printed_identity_dimensionally_consistent':False},
        'all_monodisperse_probabilities_normalized':all(r['monodisperse_probability_normalized'] for r in records),
        'all_literal_polydisperse_probabilities_normalized':all(e['probability_normalized'] for r in records for e in r['polydisperse_examples']),
        'all_integral_boundary_arithmetic_agrees':all(mp.mpf(e['density_integral_vs_boundary_error'])<=mp.mpf(p['arithmetic_budget']) for r in records for e in r['polydisperse_examples']),
        'published_radius_independently_reproduced':False,
        'interpretation':'Published5.9um remains a reported derived parameter. The source does not provide the required measured moments in the acquired data; literal Eq2.27 fails normalization. No inferred correction or replacement radius is introduced.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','settings')},indent=2))


if __name__ == '__main__':
    main()
