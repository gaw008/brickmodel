"""Run one explicitly virtual, source-bound low-water equilibrium example.

Requires the installed sludge-vme package and its local source assets. This is
a nominal closed-cell flash, not a drying-time or material-validation result.
"""
import argparse
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction as F
import json
import math
from pathlib import Path


def positive_carrier(value: str) -> float:
    try:
        total = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('总载气必须是正有限数。') from exc
    if not math.isfinite(total) or total <= 0:
        raise argparse.ArgumentTypeError('总载气必须是正有限数。')
    if any(float(F(total)*part/100) == 0 for part in (21, 79)):
        raise argparse.ArgumentTypeError('载气组分低于可表示范围。')
    return total


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
    # Serialization failure leaves existing contents unchanged; a later I/O failure may not.
    content = json.dumps(record, default=json_value, ensure_ascii=False, allow_nan=False, indent=2)
    stream.seek(0)
    stream.write(content+'\n')
    stream.truncate()
    stream.flush()


def make_storage(root: Path) -> tuple:
    """Same actual source construction/envelopes as the reviewed native example."""
    from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
    from sludge_sandbox.arlabosse_wet_thermo import ArlabosseWetThermodynamics
    from sludge_sandbox.arlabosse_low_moisture import ArlabosseLowMoisture
    from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
    from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
    from sludge_sandbox.source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume
    from sludge_sandbox.mass_wet_storage import WaterElementConvention
    from sludge_sandbox.rigid_storage import RigidStorage, DeclaredNumericalEnvelope
    from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
    from sludge_sandbox.phase_storage import IdealGasPhase
    from sludge_sandbox.thermochemistry import load_thermochemistry

    ids, fixture = ('O2', 'N2', 'H2O'), 'manufactured:arlabosse-low-water-long-n2-v1'
    wet = ArlabosseWetThermodynamics(root, root/'data/sandbox/water')
    chemical, vapor = wet._chemical, wet._chemical.vapor
    rows = {row['species_id']: row for row in json.loads(
        (root/'data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json').read_bytes())}
    thermo = load_thermochemistry(root/'data/sandbox/thermochemistry/nist_gases_v1.json')
    phases = {key: IdealGasPhase(thermo.species(key), rows[key]['nominal_molar_mass_kg_mol'],
        0, (rows[key]['source_id'], rows[key]['cache_sha256'])) for key in ids[:2]}
    phases['H2O'] = IdealGasPhase(vapor, vapor.molar_mass_kg_mol)
    mechanical = RigidWaterGas(chemical.water, ids, 1e-5, (80000., 120000.),
        'planar_interface_no_capillary_pressure', PressurePolicy(1e-12, .1, 100,
        strategy='guarded_liquid_endpoint_interpolation_v1'))
    envelope = DeclaredNumericalEnvelope((325., 338.), (80000., 120000.),
        1e-8, 1e-16, 1e-4, {k: 1e-7 for k in ids}, {k: 20. for k in ids},
        'explicit_conditional_numerical_test_envelope_not_independent_eos_certificate', (fixture,))
    caloric = ArlabosseMassCaloric(ArlabosseDryCaloric(
        root/'data/sandbox/research/arlabosse2005/source.json', root), F('313.15'))
    chemistry = ReactionDisabled((caloric.component_id,), ids,
        'Fixed-composition source-sorption integration; reactions unsupported')
    volume = ManufacturedFixedFluidVolume(1e-5, 1e-12,
        'Manufactured fixed available liquid-plus-gas volume, not measured brick porosity')
    elements = WaterElementConvention.load(root/'data/sandbox/research/water-element-convention-v1/facts.json')
    base = SourceWetStorage(caloric, .01, RigidStorage(mechanical, phases, envelope),
        volume, (325., 338.), chemistry, elements)
    return LowMoistureSorptionStorage(base, wet, (90000., 110000.),
        excess=ArlabosseLowMoisture(wet)), chemical


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='运行有来源的单胞名义平衡示例；初态和21/79载气为虚拟设计。')
    parser.add_argument('--source-root', type=Path, required=True, help='含 data/sandbox 和原件缓存的项目根目录')
    parser.add_argument('--output', type=Path, required=True, help='新建 JSON 结果文件；父目录须存在，拒绝覆盖')
    parser.add_argument('--carrier-mol', type=positive_carrier, default=.00032,
        help='正有限总载气 mol，默认0.00032；按 O2/N2=21/79 的虚拟设计分配')
    args = parser.parse_args(argv)
    root = args.source_root.expanduser().resolve()
    if not root.is_dir():
        parser.error('--source-root 必须是已有目录。')
    carrier = tuple(float(F(args.carrier_mol)*part/100) for part in (21, 79))
    record = {'schema': 'low_moisture_equilibrium_example_v1', 'status': 'prepared',
        'qualification': 'nominal_equilibrium_candidate_not_certified_inverse',
        'material_qualified': False, 'training_eligible': False,
        'source_root': str(root), 'inputs': {'classification': 'virtual_design_choice',
            'temperature_k': 333., 'condensed_water_mol': .06, 'water_vapor_mol': 1e-6,
            'dry_mass_kg': .01, 'available_fluid_volume_m3': 1e-5,
            'temperature_domain_k': (325., 338.), 'full_pressure_domain_pa': (90000., 110000.),
            'requested_carrier_mol': args.carrier_mol, 'carrier_O2_N2_mol': carrier,
            'carrier_split': '21/100 O2 and 79/100 N2; virtual two-species carrier',
            'carrier_projection_residual_mol': sum(map(F, carrier), F())-F(args.carrier_mol)},
        'initial_state': None, 'initial_point': None, 'model_provenance': None, 'result': None}
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
        flash_failure_type = None
        try:
            from sludge_sandbox.low_moisture_equilibrium import FlashFailure, FlashPolicy, flash
            from sludge_sandbox.phase_storage import InversePolicy
            flash_failure_type = FlashFailure
            policy = FlashPolicy(InversePolicy(1e-5, 1e-6, 40), (325., 338.), 1.,
                1e-11, 1e-12, 1e-5, 1e-5, 4, 40, 500, 50.)
            record['numerical_policy'] = policy.definition()
            storage, chemical = make_storage(root)
            record['model_provenance'] = storage.provenance()
            state = storage.state(.06, (*carrier, 1e-6), 0.)
            record['initial_inventory_before_energy_evaluation'] = state
            save(stream, record)
            point = storage.evaluate(state, 333.)
            state = replace(state, internal_energy_j=point.total_internal_energy_j)
            record.update(initial_state=state, initial_point=point, status='initial_state_evaluated')
            save(stream, record)
            result = flash(storage, chemical, F(state.liquid_water_mol)+F(state.gas_amounts_mol[2]),
                carrier, state.internal_energy_j, policy)
            record.update(status='nominal_candidate', result=result)
        except Exception as exc:
            record.update(status='failed', error_type=type(exc).__name__, reason=str(exc))
            # Import/construction failures also retain the input snapshot.
            if flash_failure_type is not None and isinstance(exc, flash_failure_type):
                record['failure'] = {'trials': exc.trials, 'counts': exc.counts,
                    'last_completed_provider_result': exc.last_completed_provider_result,
                    'last_completed_provider_context': exc.last_completed_provider_context}
            record['cause'] = None if exc.__cause__ is None else repr(exc.__cause__)
        try:
            save(stream, record)
        except (TypeError, ValueError, OSError) as exc:
            print(f'无法完整保存结果，输出文件可能不完整：{exc}')
            return 2
    if record['status'] == 'nominal_candidate':
        print(f'已保存名义平衡候选：{args.output}；材料资格仍为未验证。')
        return 0
    print(f'计算未完成，失败记录已保存：{args.output}')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
