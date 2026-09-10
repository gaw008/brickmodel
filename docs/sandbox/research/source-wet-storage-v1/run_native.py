"""Real water/source gas coupling with explicitly manufactured fixed volume."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import time

from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
from sludge_sandbox.source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume
from sludge_sandbox.mass_wet_storage import WaterElementConvention
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy
from sludge_sandbox.rigid_storage import RigidStorage, DeclaredNumericalEnvelope
from sludge_sandbox.phase_storage import IdealGasPhase, InversePolicy
from sludge_sandbox.thermochemistry import load_thermochemistry


def make_case(root):
    root = Path(root)
    waterdir = root/'data/sandbox/water'
    selection = {'backend': 'heos', 'backend_manifest': waterdir/'heos-8.0.0-approved-manifest.json'}
    water = load_water_properties(waterdir, **selection)
    vapor = IdealWaterVapor(waterdir, **selection)
    thermochemistry = load_thermochemistry(root/'data/sandbox/thermochemistry/nist_gases_v1.json')
    facts = json.loads((root/'data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json').read_text())
    rows = {row['species_id']: row for row in facts}
    phases = {key: IdealGasPhase(thermochemistry.species(key), rows[key]['nominal_molar_mass_kg_mol'],
                                0, (rows[key]['source_id'], rows[key]['cache_sha256'])) for key in ('O2', 'N2')}
    phases['H2O'] = IdealGasPhase(vapor, vapor.molar_mass_kg_mol)
    mechanical = RigidWaterGas(water, ('O2', 'N2', 'H2O'), .001, (1e5, 1e7),
        'planar_interface_no_capillary_pressure', PressurePolicy(1e-12, 1e-5, 100))
    envelope = DeclaredNumericalEnvelope((310., 350.), (1e5, 1e7), 1e-8, 1e-16, 1e-4,
        {k: 1e-7 for k in phases}, {k: 20. for k in phases},
        'explicit_conditional_numerical_test_envelope_not_independent_eos_certificate',
        ('manufactured:source-wet-native-test-envelope-v1',))
    fluid = RigidStorage(mechanical, phases, envelope)
    caloric = ArlabosseMassCaloric(ArlabosseDryCaloric(root/'data/sandbox/research/arlabosse2005/source.json', root), F('313.15'))
    disabled = ReactionDisabled((caloric.component_id,), mechanical.gas_species_ids,
        'Low-temperature fixed-composition numerical storage test; no chemical conversion')
    geometry = ManufacturedFixedFluidVolume(.001, 1e-12, 'Test-only constant available liquid-plus-gas volume; no source material density supplied')
    convention = WaterElementConvention.load(root/'data/sandbox/research/water-element-convention-v1/facts.json')
    model = SourceWetStorage(caloric, .2, fluid, geometry, (310., 350.), disabled, convention)
    return model, model.state(.25, (.125, .25, .00390625), 0.)


def rational(x):
    x = F(x)
    return {'numerator': x.numerator, 'denominator': x.denominator}


def main(root, output):
    started = time.monotonic()
    model, state = make_case(root)
    before = model.evaluate(state, 331.25)
    state = replace(state, internal_energy_j=before.total_internal_energy_j)
    policy = InversePolicy(1e-5, 1e-6, 100)
    inverse = model.invert(state, policy)
    delta = 1/1024
    shifted = replace(state, liquid_water_mol=state.liquid_water_mol-delta,
                      gas_amounts_mol=(*state.gas_amounts_mol[:2], state.gas_amounts_mol[2]+delta))
    after = model.invert(shifted, policy)
    assert after.point.temperature_k < inverse.point.temperature_k
    water_delta = F(shifted.liquid_water_mol)+F(shifted.gas_amounts_mol[2])-F(state.liquid_water_mol)-F(state.gas_amounts_mol[2])
    assert water_delta == 0
    assert abs(F(inverse.point.temperature_k)-F(331.25)) <= F(inverse.temperature_error_bound_k)
    result = {'schema': 'source_wet_native_storage_example_v1', 'seconds': time.monotonic()-started,
        'model_identity': model.model_identity, 'temperature_k': 331.25,
        'dry_mass_kg_exact_binary64': rational(model.dry_mass_kg),
        'initial_liquid_water_mol': state.liquid_water_mol, 'initial_gas_mol': state.gas_amounts_mol,
        'total_internal_energy_j': before.total_internal_energy_j,
        'solid_internal_energy_j_exact': rational(before.solid_internal_energy_j),
        'fluid_internal_energy_j': before.fluid.internal_energy_j,
        'pressure_pa': before.pressure_pa, 'pressure_error_pa': before.pressure_error_pa,
        'closed_heat_capacity_j_k': before.closed_heat_capacity_j_k,
        'minimum_heat_capacity_j_k': before.minimum_heat_capacity_j_k,
        'numerical_energy_error_j': before.energy_error_j,
        'inverse_temperature_k': inverse.point.temperature_k, 'inverse_iterations': inverse.iterations,
        'inverse_temperature_bound_k': inverse.temperature_error_bound_k,
        'phase_transfer_mol': delta, 'phase_shift_temperature_k': after.point.temperature_k,
        'phase_shift_pressure_pa': after.point.pressure_pa, 'phase_shift_iterations': after.iterations,
        'phase_shift_energy_residual_j_exact': rational(after.energy_residual_j),
        'phase_shift_temperature_bound_k': after.temperature_error_bound_k,
        'water_inventory_change_mol_exact': rational(water_delta),
        'material_qualified': before.material_qualified, 'fit_error': before.fit_error,
        'total_enthalpy_j': before.total_enthalpy_j, 'solid_volume_m3': before.solid_volume_m3,
        'provenance': model.provenance()}
    Path(output).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'provenance'}, indent=2))


if __name__ == '__main__':
    import sys
    main(sys.argv[1], sys.argv[2])
