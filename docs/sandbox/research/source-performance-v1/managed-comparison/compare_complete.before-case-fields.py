"""Independent standard-library comparison; never import/evaluate any provider."""
from collections import Counter
from copy import deepcopy
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
        (1e5, 'derived_native_entropy_fixed_pressure_water_equilibrium_v1',
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


def allowed_changes(ids, expected_descriptor):
    out = {'/payload/nodes/0/fields/phase': ('ordinary_source_segment', 'single_source_rhs_comparison',
            'Explicit diagnostic invocation label; physical phase fields unchanged')}
    prefix = '/payload/nodes/'
    groups = {
        'water_implementation_sha256': ('35/fields/water_implementation_v1.json',
            '149/values/1', '177/values/1', '194/values/1'),
        'config_sha256': ('165/values/1',),
        'storage_sha256': ('9/values/0', '9/values/1', '9/values/2',
            '14/fields/energy_model_identity', '17/fields/energy_model_identity',
            '20/fields/energy_model_identity', '27/fields/model_identity',
            '64/fields/model_identity', '88/fields/model_identity'),
        'column_sha256': ('2/values/1', '23/fields/model_identity'),
    }
    for kind, paths in groups.items():
        for path in paths:
            out[prefix+path] = (ids[0][kind], ids[1][kind], 'Independently recomputed '+kind)
    out[prefix+'53/fields/canonical_descriptor'] = (*expected_descriptor,
        'Exact descriptor reconstruction; only wrapper, kernel and explicit manifest execution fields changed')
    return out


def verify_pair(a, b, allowed):
    diffs = differences(a, b)
    assert {p for p, _, _ in diffs} == set(allowed), 'unexpected/missing graph difference'
    for path, before, after in diffs:
        x, y, _ = allowed[path]
        assert type(before) is type(x) and type(after) is type(y)
        assert before == x and after == y, ('unapproved identity value', path)
    return [{'path': p, 'before': a, 'after': b, 'reason': allowed[p][2]} for p, a, b in diffs]


def graph_counts(graph):
    seen = set()
    references = 0
    def visit(x):
        nonlocal references
        if type(x) is dict:
            if set(x) == {'ref'}:
                references += 1
                assert x['ref'] in graph['nodes']
                if x['ref'] not in seen:
                    seen.add(x['ref'])
                    visit(graph['nodes'][x['ref']])
            else:
                for v in x.values(): visit(v)
        elif type(x) is list:
            for v in x: visit(v)
    visit(graph['root'])
    assert seen == set(graph['nodes']), 'unreachable graph node'
    counters = Counter()
    def count(x):
        if type(x) is dict:
            for tag in ('binary64', 'fraction'):
                if set(x) == {tag}: counters[tag] += 1
            for k, v in x.items():
                if k in ('qualification', 'classification', 'material_qualified',
                         'full_inverse_liquid_direction_certified', 'full_inverse_direction_certified'):
                    counters['qualification_fields'] += 1
                count(v)
        elif type(x) is list:
            for v in x: count(v)
        else:
            counters['primitive_values'] += 1
    count(graph)
    return dict(counters, nodes=len(seen), references=references,
                arrays=sum(n['type'] == 'numpy.ndarray' for n in graph['nodes'].values()))


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
    assert differences(cases[0], cases[1]) == [('/profile',
        'source_multicell_wet_to_dry_heos_v1', 'source_multicell_wet_to_dry_heos_rhs_v2')]
    descriptors = [n['53']['fields']['canonical_descriptor'] for n in nodes]
    old_desc, new_desc = map(json.loads, descriptors)
    manifests = [raw(REPO/'data/sandbox/water'/name) for name in
                 ('heos-8.0.0-approved-manifest.json', 'heos-8.0.0-rhs-v2-manifest.json')]
    assert old_desc['real_fluid']['runtime'] == manifests[0]
    assert new_desc['real_fluid']['runtime'] == manifests[1]
    old_runtime = raw(BASE/'rhs01/RESULT.json')['runtime_before']['modules']
    new_runtime = raw(BASE/'rhs02/RESULT.json')['runtime']['modules']
    assert old_desc['wrapper_sha256'] == old_runtime['water_heos.py']
    assert old_desc['real_fluid']['runtime']['adapter_sha256'] == old_runtime['_heos_kernel.py']
    assert new_desc['wrapper_sha256'] == new_runtime['water_heos.py'] == sha((REPO/'src/sludge_sandbox/water_heos.py').read_bytes())
    assert manifests[1]['adapter_sha256'] == new_runtime['_heos_kernel.py'] == sha((REPO/'src/sludge_sandbox/_heos_kernel.py').read_bytes())
    execution = manifests[1]['execution_sources']
    assert set(execution) == {'_heos_rhs_scope.py', 'exact_source_column.py', 'source_managed_worker.py'}
    for name, value in execution.items():
        assert value == new_runtime[name] == sha((REPO/'src/sludge_sandbox'/name).read_bytes())
    expected_manifest = deepcopy(manifests[0])
    expected_manifest.update(adapter_sha256=manifests[1]['adapter_sha256'], execution_sources=execution,
        execution_contract='explicit_managed_single_rhs_v1_default_per_call_preserved')
    assert json_bytes(expected_manifest) == json_bytes(manifests[1])
    expected_desc = deepcopy(old_desc)
    expected_desc['wrapper_sha256'] = new_desc['wrapper_sha256']
    expected_desc['real_fluid']['runtime'] = expected_manifest
    assert json_bytes(expected_desc).decode() == descriptors[1]
    changes = verify_pair(*events, allowed_changes(ids, descriptors))
    counts = [graph_counts(e['payload']) for e in events]
    assert counts[0] == counts[1]
    # Independent reject controls: no tolerant equality or wildcard removal.
    adverse = []
    for name, node, field, value in (
        ('pressure_one_ulp', '29', 'pressure_pa', {'binary64': '0x1.0000000000000p+0'}),
        ('event_qualification_upgrade', '23', 'full_inverse_liquid_direction_certified', True),
        ('energy_identity_forged', '14', 'energy_model_identity', '0'*64),
    ):
        altered = deepcopy(events[1])
        altered['payload']['nodes'][node]['fields'][field] = value
        try:
            verify_pair(events[0], altered, allowed_changes(ids, descriptors))
        except AssertionError:
            adverse.append({'case': name, 'rejected': True})
        else:
            raise AssertionError(name)
    old_result, new_result = raw(BASE/'rhs01/RESULT.json'), raw(BASE/'rhs02/RESULT.json')
    assert old_result['status'] == new_result['status'] == 'completed'
    assert old_result['accepted_steps'] == new_result['accepted_steps'] == 0
    assert new_result['source_resume_authorized'] is new_result['material_qualified'] is False
    audit = new_result['managed_audit']
    assert audit['closed'] is True and len(audit['rhs']) == 1
    one = audit['rhs'][0]
    assert one['status'] == 'verified' and one['native_operations'] == 2045
    assert one['primary_error'] is None and one['exit_errors'] == []
    assert [v['stage'] for v in one['checks']] == ['entry']*4 + ['exit']*4
    for check in one['checks']:
        assert check['status'] == 'verified'
        assert check['fluid_sha256'] == manifests[0]['fluid_sha256'] == manifests[1]['fluid_sha256']
        assert check['config_sha256'] == sha(json.dumps(manifests[1]['config'], sort_keys=True).encode())
    expected_kernel = sha(json.dumps(new_desc['real_fluid'], sort_keys=True).encode())
    assert all(v['kernel_identity'] == expected_kernel for v in one['checks'])
    for i, p in enumerate(paths):
        (OUT/('original-rhs.json' if i == 0 else 'managed-rhs.json')).write_bytes(p.read_bytes())
    result.update(status='PASS', graph_counts=counts[0], exact_graph_changes=changes,
        descriptor_changes=[{'path': p, 'before': a, 'after': b} for p, a, b in (
            ('/wrapper_sha256', old_desc['wrapper_sha256'], new_desc['wrapper_sha256']),
            ('/real_fluid/runtime/adapter_sha256', manifests[0]['adapter_sha256'], manifests[1]['adapter_sha256']),
            ('/real_fluid/runtime/execution_sources', None, execution),
            ('/real_fluid/runtime/execution_contract', None, manifests[1]['execution_contract']))],
        adverse_controls=adverse, input_sha256={str(p): sha(p.read_bytes()) for p in paths},
        full_graph_structure_reference_aliases_preserved=True,
        complete_numeric_and_qualification_fields_exact=True,
        provider_constructions=0, EOS_calls=0,
        timing_scope='one matched RHS only; different reconstruction workflows not compared',
        old_rhs_seconds=old_result['rhs_profiled_seconds'], new_rhs_seconds=new_result['rhs_profiled_seconds'],
        elapsed_seconds=perf_counter()-start)
    (OUT/'COMPARISON.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'graph_counts', 'adverse_controls',
        'old_rhs_seconds', 'new_rhs_seconds', 'elapsed_seconds')}, indent=2))


if __name__ == '__main__':
    main()
