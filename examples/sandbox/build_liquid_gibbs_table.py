"""Generate an offline liquid Gibbs polynomial from the declared IAPWS backend."""
import argparse
import json
from pathlib import Path

from iapws import IAPWS95
import iapws
import numpy as np
from numpy.polynomial.chebyshev import chebvander2d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    c = json.loads(args.parameters.read_text())
    degrees = c['polynomial_degrees']
    nodes = [np.cos(np.pi*np.arange(d+1)/d) for d in degrees]
    x, y = np.meshgrid(*nodes, indexing='ij')
    bounds = np.array([c['temperature_domain_k'], c['pressure_domain_pa']])
    center, scale = bounds.mean(axis=1), (bounds[:, 1]-bounds[:, 0])/2
    reference = c['native_gibbs_reference_state']
    mass = IAPWS95.M/1000
    base = IAPWS95(T=reference['temperature_k'], P=reference['pressure_pa']/1e6)
    offset = (base.h-base.T*base.s)*1000*mass
    values, source_points = [], []
    for a, b in zip(x.ravel(), y.ravel(), strict=True):
        t, p = float(center[0]+scale[0]*a), float(center[1]+scale[1]*b)
        point = IAPWS95(T=t, P=p/1e6)
        if point.x != 0:
            raise ValueError('fit point is not a stable liquid state')
        g = (point.h-t*point.s)*1000*mass
        values.append(g-offset)
        source_points.append({'temperature_k': t, 'pressure_pa': p, 'native_gibbs_j_mol': g})
    matrix = chebvander2d(x.ravel(), y.ravel(), degrees)
    coefficients, _, rank, _ = np.linalg.lstsq(matrix, values, rcond=None)
    result = {**c, 'schema': 'liquid_gibbs_chebyshev_v1',
              'gibbs_coefficients_j_mol': coefficients.reshape(degrees[0]+1, degrees[1]+1).tolist(),
              'native_gibbs_offset_j_mol': offset, 'molar_mass_kg_mol': mass,
              'source_backend_version': iapws.__version__, 'fit_matrix_rank': int(rank),
              'source_points': source_points, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'source_points': len(source_points), 'matrix_rank': int(rank)}))


if __name__ == '__main__':
    main()
