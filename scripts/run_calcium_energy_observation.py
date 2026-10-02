"""Persist original P45 energy arithmetic from two native RHS calls, offline."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import ast, importlib, json, sys, types
import numpy as np

snapshot = Path(sys.argv[1]).resolve()
root = json.loads(snapshot.read_text())
contract = root['public_reference_cases']['ca_energy_operation_observation']
directory = snapshot.parent
original = json.loads((directory / contract['original_root_file']).read_text())
parameters = original['parameters']
ca = original['public_reference_cases']['ca_coordinate']
physical = original['public_reference_cases'][ca['physical_case']]
indices = root['parameters'][contract['indices_parameter']]['value']
field_contract = contract['observation_fields']
phase = 'imports'
active = None
counts = {}
events = []
capture = {}
observations = []

def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value

def write(name, value):
    (directory / name).write_text(json.dumps(plain(value), ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def persist_counts():
    write('call-counts.json', {'counts_by_mode_phase': counts, 'events': events,
        'logical_constructor_instances': sum(v.get('construction', {}).get('ThermoelasticFullCycle.__init__', 0) for v in counts.values()),
        'native_RHS_calls': sum(v.get('RHS', {}).get('FiniteGasFullCycle.rhs', 0) for v in counts.values()),
        'inherited_init_and_rhs_entries_not_extra_instances': True, 'independent_extra_operators': 0})

def report_failure(kind, error, traceback):
    sys.setprofile(None)
    persist_counts()
    write('failure.json', {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'mode': active,
        'phase': phase, 'exception_type': kind.__name__, 'exception': str(error),
        'retry': False, 'partial_saved_observations': len(observations)})
    sys.__excepthook__(kind, error, traceback)

sys.excepthook = report_failure

def profiler(frame, event, value):
    namespace = frame.f_globals.get('__name__', '')
    if namespace.startswith('p56_'):
        name = frame.f_code.co_name
        qualified = frame.f_code.co_qualname
        if event == 'call':
            bucket = counts.setdefault(active, {}).setdefault(phase, {})
            bucket[qualified] = bucket.get(qualified, 0) + 1
            if name in ['make_cycle', 'rhs']:
                events.append({'mode': active, 'phase': phase, 'entry': qualified, 'UTC': datetime.now(timezone.utc).isoformat()})
            if phase == 'RHS' and name == 'mechanical_rates':
                capture['mechanical_args'] = tuple(frame.f_locals[k] for k in ['f', 'T', 'ns', 'ng', 'bulk', 'pore', 'cap', 'pressure', 'dns', 'dng', 'heat', 'flow', 'us', 'ug'])
        elif event == 'return' and phase == 'RHS':
            capture[name] = value
            if name in ['rates', 'porous_mechanical_rates', 'rhs']:
                capture[qualified + '_locals'] = dict(frame.f_locals)

source = (directory / contract['original_probe_file']).read_text()
parsed = ast.parse(source)
assignments = {node.targets[0].id: node for node in ast.walk(parsed)
               if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)}
u_tree = deepcopy(assignments['Udot'])
operation_values = {}
operation_sources = {}
expression_labels = contract['original_operation_expression_labels']

def observe(label, value):
    operation_values[label] = value
    return value

class ObserveOriginalExpression(ast.NodeTransformer):
    def visit_BinOp(self, node):
        expression = ast.unparse(node)
        node = self.generic_visit(node)
        if expression in expression_labels:
            label = expression_labels[expression]
            operation_sources[label] = expression
            return ast.copy_location(ast.Call(func=ast.Name(id='observe', ctx=ast.Load()), args=[ast.Constant(label), node], keywords=[]), node)
        return node

    def visit_Call(self, node):
        expression = ast.unparse(node)
        node = self.generic_visit(node)
        if expression in expression_labels:
            label = expression_labels[expression]
            operation_sources[label] = expression
            return ast.copy_location(ast.Call(func=ast.Name(id='observe', ctx=ast.Load()), args=[ast.Constant(label), node], keywords=[]), node)
        return node

observed_tree = ast.fix_missing_locations(ast.Module(body=[ObserveOriginalExpression().visit(u_tree)], type_ignores=[]))
compiled_u = compile(observed_tree, str(directory / contract['original_probe_file']), 'exec')
sys.setprofile(profiler)
for mode in ca['modes']:
    active = mode['id']
    phase = 'imports'
    capture = {}
    package_name = 'p56_' + active + '_sludge_vme'
    package = types.ModuleType(package_name)
    package.__path__ = [str(directory / contract['frozen_source_directories'][active] / 'sludge_vme')]
    sys.modules[package_name] = package
    module = importlib.import_module(package_name + '.models.full_cycle')
    case = deepcopy(original)
    for target, key in physical['common_override_parameters'].items():
        case['parameters'][target] = deepcopy(parameters[key])
    case['stages'] = physical['stages']
    case['direct_carbonation'] = deepcopy(physical['channel'])
    case['parameters']['numerics.cells'] = deepcopy(parameters[ca['cells_parameter']])
    case['parameters']['numerics.initial_partition_mode']['value'] = ca['profile_mode']
    case['parameters'][ca['representation_parameter']]['value'] = mode['mode']
    phase = 'construction'
    model = module.make_cycle(case)
    phase = 'initialization'
    y = model.initial_state()
    phase = 'RHS'
    dy = model.rhs(model.times[0], y)
    phase = 'original_diagnostic_arithmetic'
    rr = capture['rates']
    fields, T, ns, ng, bulk, pore, surface_cap, pressure, dns, dng, heat, flow, us, ug = capture['mechanical_args']
    df = dy[:model.gas_offset].reshape(-1, model.n)
    sc = np.broadcast_to(model.chemical_scale, (model.n,))
    decoded = dns.copy()
    decoded[:, model.portlandite] = sc * df[model.hydroxide_coordinate]
    selected = model.calcite if mode['mode'] == 0 else model.lime
    remainder = model.lime if mode['mode'] == 0 else model.calcite
    decoded[:, selected] = model.calcium_pool * df[3]
    decoded[:, remainder] = -decoded[:, selected] - decoded[:, model.portlandite]
    elastic = capture['elastic_response']
    K = elastic['modulus']
    eps = elastic['eps']
    _, bp, bpp, _ = capture['thermal_strain']
    C = capture['state_caloric_capacity']
    xdot = capture['liquid_order'][2] * df[model.liquid_coordinate]
    phase_rate = capture['phase_reference_volume'][1] * decoded[:, model.matrix] + capture['phase_reference_volume'][2] * xdot
    Kdot = elastic['kv'] * rr['db'] + elastic['kd'] * (decoded @ model.dry_v) - model.phase_modulus_contrast * K * phase_rate
    Bdot = capture['phase_eigenstrain'][1] * decoded[:, model.matrix] + capture['phase_eigenstrain'][2] * xdot
    edot = rr['db'] / model.b0 - bp * rr['dT'] - df[6] - Bdot
    EUdot = model.b0 * (Kdot * (eps**2 / 2 + T * bp * eps) + K * eps * edot + K * (rr['dT'] * bp * eps + T * bpp * rr['dT'] * eps + T * bp * edot))
    dh, ds = capture['liquid_contrast']
    amount = model.liquid_active * ns[:, model.matrix]
    PUdot = amount * dh * xdot
    operation_values = {}
    exec(compiled_u, globals())
    values = {
        'original_native_state': y, 'original_native_dy': dy, 'fields': fields, 'ns_mol': ns,
        'chemical_scale_mol': sc, 'calcium_pool_mol': model.calcium_pool,
        'cached_dns_mol_s': dns, 'decoded_dns_mol_s': decoded,
        'C_cal_J_K': C, 'us_J_mol': us, 'ug_J_mol': ug, 'surface_cap_J_m3': surface_cap,
        'dT_K_s': rr['dT'], 'dng_mol_s': dng, 'dpore_m3_s': rr['dpore'], 'db_m3_s': rr['db'],
        'elastic_Udot_W': EUdot, 'phase_Udot_W': PUdot, 'complete_Udot_W': Udot,
        **operation_values,
    }
    selected_values = {k: {'unit': field_contract[k]['unit'], 'raw': plain(value[indices])} for k, value in values.items()
                       if k not in ['original_native_state', 'original_native_dy', 'fields']}
    selected_values['fields'] = {'unit': field_contract['fields']['unit'], 'raw': plain(fields[:, indices])}
    observation = {
        'id': 'declared_zero_' + active, 'coordinate_mode': mode['mode'], 'cells': model.n,
        'time_s': model.times[0], 'observation_indices_zero_based': indices,
        'Ca_species_order': [model.ns[j] for j in [model.calcite, model.lime, model.portlandite]],
        'solid_species_order': model.ns, 'gas_species_order': model.ng,
        'Ca_column_indices': [model.calcite, model.lime, model.portlandite],
        'selected_fields': selected_values, 'all12_complete_Udot_W': Udot,
        'original_native_state': y, 'original_native_dy': dy,
        'raw_Ca_state_mol_all12': ns[:, [model.calcite, model.lime, model.portlandite]],
        'cached_Ca_dns_mol_s_all12': dns[:, [model.calcite, model.lime, model.portlandite]],
        'decoded_Ca_dns_mol_s_all12': decoded[:, [model.calcite, model.lime, model.portlandite]],
        'native_RHS_calls': model.rhs_calls,
        'operation_sources': operation_sources,
        'native_rates_and_mechanical_frame_sources': ['rates return after binding', 'mechanical_rates input', 'state_caloric_capacity return', 'last original RHS elastic/thermal/phase returns, as P45 capture'],
        'initial_U_S_independent_reference_operator_not_called': True,
        'independent_potential_derivative_qualification': False,
    }
    observations.append(plain(observation))
    write('result.json', {'schema': 'P56_original_declared_zero_energy_operations_v1',
        'recorded_utc': datetime.now(timezone.utc).isoformat(), 'observations': observations,
        'original_Udot_AST': ast.unparse(assignments['Udot']), 'observed_Udot_AST': ast.unparse(observed_tree),
        'single_evaluation_original_order_dtype_and_np_sum_axis_preserved': True,
        'no_cached_dns_substitution': True, 'whole_project_complete': False})
    persist_counts()
sys.setprofile(None)
print(json.dumps({'saved_observations': len(observations), 'indices': indices, 'actual_logical_instances': len(observations),
    'actual_native_RHS_calls': sum(v['native_RHS_calls'] for v in observations), 'whole_project_complete': False}))
