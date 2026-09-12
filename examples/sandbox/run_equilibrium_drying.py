"""Source-bound two-cell, one-second equilibrium drying research example.

Requires installed sludge-vme and local source assets. Geometry, inventories and
boundary controls are virtual design choices; this is not a complete firing cycle.
"""
import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction as F
import json
from pathlib import Path
import time
from typing import Callable

IDS = ('O2', 'N2', 'H2O')
FIXTURE_ID = 'manufactured:arlabosse-equilibrium-transport-n2-v1'
# Keep the original binary64 component constants; do not split rounded totals.
INITIAL_CELLS = ((0., (.0000714, .0002686, .000001), 330.),
                 (.06, (.0000672, .0002528, .000001), 333.))


def json_value(value: object) -> object:
    """Only the existing result dataclasses, exact fractions, and mappings."""
    if isinstance(value, F):
        return {'numerator': value.numerator, 'denominator': value.denominator}
    if is_dataclass(value):
        return {item.name: getattr(value, item.name) for item in fields(value)}
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f'Unsupported result value: {type(value).__name__}')


def save(stream, record: dict) -> None:
    # Serialization failure preserves previous bytes; later I/O failure may not.
    content = json.dumps(record, default=json_value, ensure_ascii=False,
                         allow_nan=False, indent=2)
    stream.seek(0)
    stream.write(content+'\n')
    stream.truncate()
    stream.flush()


def load_runtime() -> tuple:
    """Load the installed host and exactly the original nominal flash policy."""
    from sludge_sandbox.equilibrium_transport import initialize_equilibrium, integrate_equilibrium_transport
    from sludge_sandbox.low_moisture_equilibrium import FlashPolicy
    from sludge_sandbox.phase_storage import InversePolicy
    policy = FlashPolicy(InversePolicy(1e-5, 1e-6, 40), (325., 338.), 1., 1e-11,
                         1e-12, 1e-5, 1e-5, 4, 40, 500, 50.)
    return initialize_equilibrium, integrate_equilibrium_transport, policy


def make_case(root: Path, progress: Callable[[dict], None] | None = None) -> tuple:
    """Original actual source construction, with caller-selected asset root."""
    from sludge_sandbox.septien_conductivity import SeptienConductivity
    from sludge_sandbox.source_sorption_moisture import MakelaMoistureTransport
    from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
    from sludge_sandbox.arlabosse_wet_thermo import ArlabosseWetThermodynamics
    from sludge_sandbox.arlabosse_low_moisture import ArlabosseLowMoisture
    from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
    from sludge_sandbox.low_moisture_transport import LowMoistureConductivity, LowMoistureTransport
    from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn, VaporBoundaryControl
    from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
    from sludge_sandbox.source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume
    from sludge_sandbox.source_wet_column import LowMoistureSorptionColumn
    from sludge_sandbox.low_moisture_fast_inverse import NUMERICAL_POLICY_ID
    from sludge_sandbox.mass_wet_storage import WaterElementConvention
    from sludge_sandbox.mass_wet_transport import WetFace
    from sludge_sandbox.rigid_storage import RigidStorage, DeclaredNumericalEnvelope
    from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
    from sludge_sandbox.phase_storage import IdealGasPhase, InversePolicy
    from sludge_sandbox.thermochemistry import load_thermochemistry

    wet = ArlabosseWetThermodynamics(root, root/'data/sandbox/water')
    chemical = wet._chemical  # Exactly the same actual water/caloric implementation.
    water, vapor = chemical.water, chemical.vapor
    facts = json.loads((root/'data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json').read_bytes())
    rows = {row['species_id']: row for row in facts}
    thermo = load_thermochemistry(root/'data/sandbox/thermochemistry/nist_gases_v1.json')
    phases = {key: IdealGasPhase(thermo.species(key), rows[key]['nominal_molar_mass_kg_mol'],
        0, (rows[key]['source_id'], rows[key]['cache_sha256'])) for key in IDS[:2]}
    phases['H2O'] = IdealGasPhase(vapor, vapor.molar_mass_kg_mol)
    mechanical = RigidWaterGas(water, IDS, 1e-5, (80000., 120000.),
        'planar_interface_no_capillary_pressure', PressurePolicy(1e-12, .1, 100,
        strategy='guarded_liquid_endpoint_interpolation_v1'))
    envelope = DeclaredNumericalEnvelope((325., 338.), (80000., 120000.),
        1e-8, 1e-16, 1e-4, {k: 1e-7 for k in IDS}, {k: 20. for k in IDS},
        'explicit_conditional_numerical_test_envelope_not_independent_eos_certificate',
        (FIXTURE_ID,))
    fluid = RigidStorage(mechanical, phases, envelope)
    caloric = ArlabosseMassCaloric(ArlabosseDryCaloric(
        root/'data/sandbox/research/arlabosse2005/source.json', root), F('313.15'))
    chemistry = ReactionDisabled((caloric.component_id,), IDS,
        'Fixed-composition source-sorption integration; reactions unsupported')
    volume = ManufacturedFixedFluidVolume(1e-5, 1e-12,
        'Manufactured fixed available liquid-plus-gas volume, not measured brick porosity')
    elements = WaterElementConvention.load(root/'data/sandbox/research/water-element-convention-v1/facts.json')
    base = SourceWetStorage(caloric, .01, fluid, volume, (325., 338.), chemistry, elements)
    storage = LowMoistureSorptionStorage(base, wet, (90000., 110000.), excess=ArlabosseLowMoisture(wet))
    source = (FIXTURE_ID,)
    face = WetFace(.001, (.01, .01), (.5, .7), (1e-5, 2e-5, 1.5e-5), 1e-15, 1.8e-5, source)
    column = LowMoistureSorptionColumn((storage, storage), (InversePolicy(1e-5, 1e-8, 100),)*2,
        chemical, (0., 0.), (face,), (.02, .02), .001,
        ('reversible_sorption',)*2, source)
    provider = SeptienConductivity(root, root/'runs/sandbox/source-cache/septien2020')
    column = replace(column, thermal_provider=LowMoistureConductivity(provider),
        faces=(replace(face, conductivities_w_m_k=(0., 0.), diffusivities_m2_s=(0.,)*3, permeability_m2=0.),),
        moisture_transport=LowMoistureTransport(MakelaMoistureTransport(root, root/'runs/sandbox/source-cache/makela2016/makela2016-accepted.pdf')),
        transport_classification='mixed_source_exploratory', inverse_strategy=NUMERICAL_POLICY_ID)
    opened=ControlledVaporColumn(column,VaporBoundaryControl(0.,1e-8,333.,.1,
        ('virtual:equilibrium-transport-selective-vapor-and-333K-heat-bath',)))
    if progress is not None:
        progress({'model_provenance': opened.provenance()})
    initial, points = [], []
    for liquid, gas, temperature in INITIAL_CELLS:
        state = storage.state(liquid, gas, 0.)
        if progress is not None:
            progress({'pending_initial_inventory': state, 'pending_temperature_k': temperature})
        point = storage.evaluate(state, temperature)
        initial.append(replace(state, internal_energy_j=point.total_internal_energy_j))
        points.append(point)
        if progress is not None:
            progress({'construction_prefix': {'states': tuple(initial), 'points': tuple(points)},
                      'last_completed_construction_point': point,
                      'pending_initial_inventory': None, 'pending_temperature_k': None})
    return opened, tuple(initial), tuple(points)


def observables(run) -> dict:
    """All dynamic ledgers contribute to cumulative output; initialization is separate."""
    fields_to_sum = ('boundary_water_mol', 'boundary_heat_j', 'boundary_enthalpy_j',
                     'boundary_energy_decomposition_j')
    result = {name: sum((getattr(row, name) for row in run.ledgers), F())
              for name in fields_to_sum}
    result['signed_outward_energy_j'] = sum((row.faces[-1].energy_j for row in run.ledgers), F())
    result['final_cells'] = tuple({'temperature_k': cell.fixed_composition_inverse.point.temperature_k,
        'pressure_pa': cell.fixed_composition_inverse.point.pressure_pa,
        'condensed_water_mol': state.liquid_water_mol, 'vapor_water_mol': state.gas_amounts_mol[2],
        'internal_energy_j': state.internal_energy_j}
        for state, cell in zip(run.states[-1], run.ledgers[-1].cells))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='运行两格、1秒的有来源平衡排湿研究示例；几何与边界为虚拟设计，材料未验证。')
    parser.add_argument('--source-root', type=Path, required=True,
                        help='含 data/sandbox 和原件缓存的项目根目录')
    parser.add_argument('--output', type=Path, required=True,
                        help='新建 JSON 结果文件；父目录须存在，拒绝覆盖')
    parser.add_argument('--steps', type=int, choices=(1, 2, 4), default=1,
                        help='固定1秒内的步数，仅1/2/4，默认1；每次完整初始化')
    args = parser.parse_args(argv)
    root = args.source_root.expanduser().resolve()
    if not root.is_dir():
        parser.error('--source-root 必须是已有目录。')
    started = time.monotonic()
    record = {'example': 'two_cell_one_second_equilibrium_drying', 'status': 'prepared',
        'source_root': str(root), 'material_qualified': False, 'training_eligible': False,
        'qualification': 'one_second_exploratory_research_not_material_or_full_firing_validation',
        'full_equilibrium_temperature_error_bound_k': None,
        'unknown_errors': ['equilibrium composition/log error', 'source material transfer',
                           'low-moisture extension', 'instantaneous equilibrium timescale'],
        'inputs': {'classification': 'virtual_design_choice', 'duration_s': 1., 'steps': args.steps,
            'initial_cells': INITIAL_CELLS, 'initial_cell_tuple_units': ['Nc_mol', ['O2_mol', 'N2_mol', 'Nv_mol'], 'T_K'],
            'dry_mass_kg_each': .01, 'available_fluid_volume_m3_each': 1e-5,
            'width_m_each': .02, 'area_m2': .001, 'boundary_vapor_pressure_pa': 0.,
            'boundary_vapor_conductance_mol_s_pa': 1e-8, 'bath_temperature_k': 333.,
            'boundary_thermal_conductance_w_k': .1, 'phase_kinetic_coefficients': (0., 0.),
            'phase_meaning': 'old kinetic branch disabled; instantaneous equilibrium projection',
            'temperature_domain_k': (325., 338.), 'complete_pressure_domain_pa': (90000., 110000.)},
        'budgets': {'initialization_s': 40., 'integration_s': 100., 'driver_s': 150.,
            'energy_roundoff_j': 1e-8, 'inventory_roundoff_mol': 1e-12,
            'scope': 'checked around provider calls; cannot interrupt an in-flight EOS; no external supervisor supplied by this CLI'},
        'construction_prefix': {'states': (), 'points': ()}, 'model_provenance': None,
        'initial_states': None, 'initial_points': None, 'initialization': None, 'run': None}
    try:
        stream = args.output.expanduser().open('x', encoding='utf-8')
    except OSError as exc:
        parser.error(f'无法新建输出文件，已有文件不会覆盖：{exc}')
    with stream:
        try:
            save(stream, record)
        except (TypeError, ValueError, OSError) as exc:
            print(f'无法保存输入快照：{exc}')
            return 2

        def guard() -> None:
            if time.monotonic()-started > 150.:
                raise TimeoutError('driver_wall_budget')

        def progress(update: dict) -> None:
            record.update(update)
            save(stream, record)  # Keep actual returned construction data before the guard.
            guard()

        try:
            initialize, integrate, policy = load_runtime()
            record['flash_policy'] = policy.definition()
            record['stage'] = 'runtime_loaded'
            save(stream, record)
            guard()
            record['stage'] = 'source_and_initial_state_construction'
            column, initial, points = make_case(root, progress)
            record.update(initial_states=initial, initial_points=points, stage='initialization')
            save(stream, record)
            guard()
            initialized = initialize(column, initial, (policy, policy), maximum_wall_seconds=40.,
                energy_roundoff_budget_j=1e-8, inventory_roundoff_budget_mol=1e-12,
                cancel=lambda: time.monotonic()-started > 150.)
            record['initialization'] = initialized
            save(stream, record)
            guard()
            if initialized.status != 'completed':
                raise ValueError('initialization_'+initialized.status+':'+str(initialized.reason))
            record['stage'] = 'integration'
            run = integrate(column, initialized, duration_s=1., steps=args.steps,
                maximum_wall_seconds=100., energy_roundoff_budget_j=1e-8,
                inventory_roundoff_budget_mol=1e-12, cancel=lambda: time.monotonic()-started > 150.)
            record['run'] = run
            save(stream, record)
            guard()
            if run.status != 'completed':
                raise ValueError('integration_'+run.status+':'+str(run.reason))
            if (len(run.ledgers) != args.steps or len(run.states) != args.steps+1
                    or run.times_s != tuple(F(i, args.steps) for i in range(args.steps+1))
                    or run.energy_roundoff_used_j > F(1e-8)
                    or run.inventory_roundoff_used_mol > F(1e-12)):
                raise ValueError('completed_run_shape_or_cumulative_budget_mismatch')
            record.update(status='completed', stage='complete', observables=observables(run))
        except Exception as exc:
            record.update(status='resource_limit' if isinstance(exc, TimeoutError) else 'failed',
                          error_type=type(exc).__name__, reason=str(exc))
            record['cause'] = None if exc.__cause__ is None else repr(exc.__cause__)
        record['elapsed_seconds'] = time.monotonic()-started
        if record['status'] == 'completed' and record['elapsed_seconds'] > 150.:
            record.update(status='resource_limit', reason='driver_wall_budget')
        try:
            save(stream, record)
            finished = time.monotonic()-started
            if record['status'] == 'completed' and finished > 150.:
                record.update(status='resource_limit', reason='driver_wall_budget', elapsed_seconds=finished)
                save(stream, record)
        except (TypeError, ValueError, OSError) as exc:
            print(f'无法完整保存结果，输出文件可能不完整：{exc}')
            return 2
    if record['status'] == 'completed':
        print(f'已完成两格1秒研究示例，完整结果已保存：{args.output}；材料仍未验证。')
        return 0
    print(f'计算未完成，输入及已返回结果已保存：{args.output}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
