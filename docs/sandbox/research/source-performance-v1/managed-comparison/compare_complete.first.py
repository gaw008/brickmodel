"""Independent standard-library comparison; never import/evaluate any provider."""
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from time import perf_counter

BASE = Path('/private/tmp/brick-source-performance-v1')
REPO = Path('/Users/wanggaoying/Desktop/brickmodel-github')
OUT = Path(__file__).parent


def raw(path):
    return json.loads(Path(path).read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


class Canonical:
    def __init__(self, data):
        self.data = data


def canon(x):
    if type(x) is Canonical:
        return x.data
    if x is None or type(x) in (str, bool, int):
        return x
    if type(x) is float:
        return ['float', x.hex()]
    if type(x) is F:
        return ['fraction', x.numerator, x.denominator]
    if type(x) is dict:
        return ['mapping', [[k, canon(x[k])] for k in sorted(x)]]
    if type(x) in (tuple, list):
        return [canon(v) for v in x]
    raise TypeError(type(x))


def digest(x):
    return sha(json_bytes(canon(x)))


def record(name, **values):
    module, cls = name.rsplit('.', 1)
    return Canonical([module, cls, [[k, canon(v)] for k, v in values.items()]])


def data_node(nodes, x):
    if type(x) is not dict:
        return x
    if set(x) == {'binary64'}:
        return float.fromhex(x['binary64'])
    if set(x) == {'fraction'}:
        return F(*x['fraction'])
    assert set(x) == {'ref'}
    n = nodes[x['ref']]
    if n['type'] == 'builtins.tuple':
        return tuple(data_node(nodes, v) for v in n['values'])
    values = {k: data_node(nodes, v) for k, v in n['fields'].items()}
    if n['type'] in ('builtins.dict', 'builtins.mappingproxy'):
        return values
    return record(n['type'], **values)


def derive(case, nodes):
    """Reconstruct only canonical digest operands from config/source data, no live shells."""
    config_sha = sha(json_bytes(case))
    fields = nodes['53']['fields']
    desc = json.loads(fields['canonical_descriptor'])
    implementation = data_node(nodes, {'ref': '53'})
    impl_sha = sha(json_bytes(dict(schema=fields['schema'], provider_id=fields['provider_id'],
        provider_version=fields['provider_version'], source_ids=data_node(nodes, fields['source_ids']),
        definition=desc)))
    reference = data_node(nodes, {'ref': '51'})
    assets = dict(desc['real_fluid']['python_water_assets'], **{'water_implementation_v1.json': impl_sha})
    # Numeric-limit field order is its original dataclass declaration.
    limit_order = ('pressure_relative', 'pressure_absolute_pa', 'energy_identity_absolute_j_kg',
        'eos_caloric_absolute_j_kg', 'heat_capacity_absolute_j_kg_k', 'gibbs_absolute_j_kg',
        'temperature_absolute_k')
    limits = record('sludge_sandbox.water_properties.NumericalLimits',
                    **{k: desc['numerical_limits'][k] for k in limit_order})
    water = Canonical(['source_gated_water', canon(reference), canon(assets), canon(limits)])
    R = 8.31446261815324
    vapor = record('sludge_sandbox.ideal_water_vapor.IdealWaterVapor', gas_constant_j_mol_k=R,
                   reference=reference, source_asset_sha256=assets, _water=water)
    thermo = raw(REPO/'data/sandbox/thermochemistry/nist_gases_v1.json')
    mass_facts = {v['species_id']: v for v in raw(
        REPO/'data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json')}
    phases = {}
    for name in ('O2', 'N2'):
        gas = next(v for v in thermo['species'] if v['species_id'] == name)
        segments = tuple(record('sludge_sandbox.thermochemistry.ShomateSegment',
            temperature_range_k=tuple(map(float, v['temperature_range_k'])),
            coefficients=tuple(map(float, v['coefficients'])),
            formation_enthalpy_298_j_mol=gas['formation_enthalpy_298_j_mol'],
            gas_constant_j_mol_k=thermo['gas_constant']['value_j_mol_k'], source_ids=tuple(v['source_ids']))
            for v in gas['segments'])
        caloric = record('sludge_sandbox.thermochemistry.ShomateGas', species_id=name,
            segments=segments, classification=gas['classification'], source_ids=tuple(gas['source_ids']))
        facts = mass_facts[name]
        phases[name] = record('sludge_sandbox.phase_storage.IdealGasPhase', caloric=caloric,
            molar_mass_kg_mol=facts['nominal_molar_mass_kg_mol'], segment_index=0,
            additional_source_ids=(facts['source_id'], facts['cache_sha256']))
    phases['H2O'] = record('sludge_sandbox.phase_storage.IdealGasPhase', caloric=vapor,
        molar_mass_kg_mol=desc['reference']['molar_mass_kg_mol'], segment_index=None, additional_source_ids=())
    storage = case['storage']
    pressure_policy = data_node(nodes, {'ref': '33'})
    mechanical = record('sludge_sandbox.rigid_water_gas.RigidWaterGas', water=water,
        gas_species_ids=('O2', 'N2', 'H2O'), available_pore_volume_m3=storage['fluid_volume_m3'],
        pressure_bracket_pa=tuple(storage['pressure_domain_pa']), assumption=storage['pressure_closure'],
        policy=pressure_policy)
    fluid = record('sludge_sandbox.rigid_storage.RigidStorage', mechanical=mechanical,
        gas_phases=phases, envelope=data_node(nodes, {'ref': '39'}), allow_manufactured=False)
    component = 'arlabosse2005-original-mixed-feed-dry-matter'
    ref = storage['caloric_reference_temperature_k']
    caloric_sha = digest(('source_mass_caloric_v1',
        '2f9caf23689092e548b2b3d7abf7c54d58d177569a7850b47c69df15e74295d6', component,
        (F(6163, 20), F(7563, 20)), F(ref['numerator'], ref['denominator']), F(),
        'fixed_composition_incompressible_temperature_independent_volume',
        'exact_rational_float_binary64_input_no_physical_fit_error_bound'))
    chemistry = record('sludge_sandbox.source_mass_caloric.ReactionDisabled', solid_ids=(component,),
        gas_ids=('O2', 'N2', 'H2O'), rationale=storage['chemistry_rationale'])
    volume = record('sludge_sandbox.source_wet_storage.ManufacturedFixedFluidVolume',
        value_m3=storage['fluid_volume_m3'], error_m3=storage['fluid_volume_error_m3'],
        rationale=storage['geometry_rationale'], classification='manufactured_test_fixture')
    providers = (('sludge_sandbox.water_heos', 'HEOSWaterProperties', implementation),) * 2
    convention = (REPO/'data/sandbox/research/water-element-convention-v1/facts.json').read_bytes()
    storage_sha = digest(('source_wet_fixed_mass_v1', caloric_sha, storage['dry_mass_kg'], fluid,
        providers, volume, tuple(storage['temperature_domain_k']), chemistry,
        (sha(convention), convention.decode())))
    chemical = record('sludge_sandbox.water_chemical_potential.WaterChemicalPotential', water=water, vapor=vapor)
    grid = case['grid']
    faces = tuple(record('sludge_sandbox.mass_wet_transport.WetFace', area_m2=grid['face_area_m2'],
        half_widths_m=(grid['cell_widths_m'][i]/2, grid['cell_widths_m'][i+1]/2),
        conductivities_w_m_k=tuple(grid['conductivities_w_m_k'][i]),
        diffusivities_m2_s=tuple(grid['diffusivities_m2_s'][i]), permeability_m2=grid['gas_permeability_m2'][i],
        viscosity_pa_s=grid['gas_viscosity_pa_s'][i], source_ids=tuple(grid['source_ids'])) for i in range(2))
    inverse = record('sludge_sandbox.phase_storage.InversePolicy', **{k: case['inverse_policy'][k]
        for k in ('energy_tolerance_j', 'temperature_tolerance_k', 'maximum_iterations')})
    modes = data_node(nodes, nodes['1']['modes'])
    content = ('source_wet_closed_column_v1', (storage_sha,)*3, (inverse,)*3, chemical, providers,
        (1e5, 'pure_real_liquid_ideal_vapor_fixed_r_chemical_potential_v1',
         'derived_iapws95_ideal_water_fixed_r_bridge_v1', R, (293., 500.)),
        tuple(case['transfer_coefficients_mol_s_pa']), faces, tuple(grid['cell_widths_m']), grid['face_area_m2'],
        modes, tuple(grid['source_ids']), ('closed_no_flux', 'closed_no_flux'), 'manufactured_test_fixture')
    liquid = case['liquid_transport']
    order = ('saturation_knots', 'permeability_m2', 'relative_permeability', 'viscosity_pa_s',
             'temperature_range_k', 'pressure_range_pa', 'model_id', 'version', 'classification',
             'source_ids', 'source_asset_sha256', 'relation_kind')
    table_values = dict(liquid, classification='manufactured_test_fixture',
        source_asset_sha256=(('source_run_config_v1', config_sha),), relation_kind='tabulated_saturation_relation')
    table = record('sludge_sandbox.liquid_transport.SaturationMobilityTable',
                    **{k: table_values[k] for k in order})
    connections = tuple(record('sludge_sandbox.liquid_transport.LiquidConnection', status=status,
        connection_id=identity, version=liquid['version'], classification='manufactured_test_fixture',
        source_ids=tuple(liquid['connection_source_ids']))
        for status, identity in zip(liquid['connection_statuses'], liquid['connection_ids']))
    transport = record('sludge_sandbox.solid_fluid_heat.LiquidTransportConfig',
        relations=(table,)*3, connections=connections, allow_manufactured=True)
    return {'config_sha256': config_sha, 'water_implementation_sha256': impl_sha,
            'storage_sha256': storage_sha,
            'column_sha256': digest((content, 'explicit_internal_liquid_transport_v1', transport))}


def differences(a, b, path=''):
    if type(a) is not type(b):
        return [(path, a, b)]
    if type(a) is dict:
        assert a.keys() == b.keys(), ('keys', path, a.keys(), b.keys())
        return [d for k in a for d in differences(a[k], b[k], path+'/'+k)]
    if type(a) is list:
        assert len(a) == len(b), ('length', path)
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, path+'/'+str(i))]
    return [] if a == b else [(path, a, b)]


def main():
    start = perf_counter()
    paths = (BASE/'rhs01/segment/events/000015.json', BASE/'rhs02/events/000015.json')
    events = [raw(p) for p in paths]
    nodes = [e['payload']['nodes'] for e in events]
    cases = [raw('/private/tmp/brick-source-dynamic-continuation-v1/native02/parent/case.json'),
             raw(BASE/'rhs02/case.json')]
    ids = [derive(c, n) for c, n in zip(cases, nodes)]
    result = {'derived': ids, 'recorded': [{
        'config_sha256': n['165']['values'][1],
        'water_implementation_sha256': n['35']['fields']['water_implementation_v1.json'],
        'storage_sha256': n['27']['fields']['model_identity'],
        'column_sha256': n['23']['fields']['model_identity']} for n in nodes]}
    (OUT/'IDENTITY_DERIVATION.json').write_text(json.dumps(result, indent=2)+'\n')
    assert result['derived'] == result['recorded'], result
    print(json.dumps({'identity_derivation': 'passed', 'elapsed_seconds': perf_counter()-start}, indent=2))


if __name__ == '__main__':
    main()
