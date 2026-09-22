"""Prepare the existing low-W source join from recorded source facts, offline."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_water import RecordedWaterProperties
from sludge_sandbox.thermochemistry import load_thermochemistry
from sludge_sandbox.water_properties import NumericalLimits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    records = {key: json.loads((root/path).read_text()) for key, path in config['source_files'].items()}
    water = RecordedWaterProperties(root/config['water_facts_file'], NumericalLimits(**config['numerics']['water']))
    r = load_thermochemistry(root/config['thermochemistry_file']).gas_constant_j_mol_k
    mass = water.reference.molar_mass_kg_mol
    domain = records['low_moisture_definition']['domain']
    t0, wj, wr = (domain[k] for k in ('reference_temperature_k', 'join_moisture_kg_water_per_kg_dry', 'reference_moisture_kg_water_per_kg_dry'))
    pressure = records['wet_definition']['design_domain']['fixed_liquid_pressure_Pa']
    latent = (water.ideal_vapor(t0).enthalpy_j_mol-water.state_tp(t0, pressure, phase='liquid').enthalpy_j_mol)/mass
    construction = config['source_construction']
    curves = {}
    for figure, name in [(1, 'activity'), (2, 'heat')]:
        rows = []
        for w in construction[name+'_levels_kg_kg']:
            item = next(p for p in records['curves']['observations'] if p['figure'] == figure and
                        float(p['requested_moisture_kg_water_per_kg_dry_matter']) == w)
            value = item['value']
            exact = Fraction(int(value['numerator']), int(value['denominator']))
            rows.append({'moisture_kg_kg': w, 'value': float(exact), 'source_value': value,
                         'unit': item['unit'], 'source_status': item['status']})
        curves[name] = rows
    activity = curves['activity']
    heat = curves['heat']
    m = [(p['moisture_kg_kg'], r/mass*t0*math.log(p['value'])) for p in activity]
    q = [(p['moisture_kg_kg'], p['value']) for p in heat]
    integral = lambda nodes: math.fsum((b-a)*(x+y)/2 for (a,x),(b,y) in zip(nodes[:-1],nodes[1:],strict=True))
    # Nodes run from join to reference; desired integrals run reference to join.
    h = latent*(wj-wr)+integral(q)
    g = -integral(m)
    s = (h-g)/t0
    b = latent-q[0][1]
    c = (b-m[0][1])/t0
    result = {'schema': 'recorded_low_moisture_source_join_v1', 'source_files': config['source_files'],
        'source_url': records['dry_caloric']['url'], 'doi': records['curves']['doi'],
        'material_identity': records['curves']['material_identity'],
        'source_curves': curves, 'gas_constant_j_mol_k': r, 'water_molar_mass_kg_mol': mass,
        'celsius_zero_k': construction['celsius_zero_k'], 'dry_caloric_relation': records['dry_caloric']['caloric_relation'],
        'model_domain': {'temperature_k': domain['temperature_k'], 'moisture_kg_kg': [0, wj],
                         'classification': 'conditional extension, not measured validity domain'},
        'reference_temperature_k': t0, 'reference_moisture_kg_kg': wr,
        'reference_liquid_pressure_pa': pressure, 'reference_ideal_vapor_minus_liquid_enthalpy_j_kg': latent,
        'join': {'moisture_kg_kg': wj, 'h_j_kg_dry': h, 's_j_kg_dry_k': s,
                 'g_at_reference_j_kg_dry': g, 'partial_h_j_kg_water': b, 'partial_s_j_kg_water_k': c},
        'dry_endpoint': {'h_j_kg_dry': h-b*wj, 's_j_kg_dry_k': s-c*wj-r/mass*wj},
        'construction': records['low_moisture_definition']['construction'],
        'assumptions': records['low_moisture_definition']['assumptions'],
        'water_source_record': water.source_record,
        'source_policy': 'Explicit input/source values recorded; no content digests generated or compared.',
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'join': result['join'], 'dry_endpoint': result['dry_endpoint']}, indent=2))


if __name__ == '__main__':
    main()
