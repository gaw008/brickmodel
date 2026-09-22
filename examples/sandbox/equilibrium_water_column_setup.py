"""One physical construction shared by explicit and implicit column drivers."""
from dataclasses import dataclass, replace
import json

from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.equilibrium_water_cell import EquilibriumWaterCell
from sludge_sandbox.equilibrium_water_column import BallastWaterCell, column_face_rates
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.open_gas_boundary import GasBoundaryTransfer
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.recorded_water import RecordedWaterProperties
from sludge_sandbox.thermochemistry import load_thermochemistry
from sludge_sandbox.surface_balance import solve_surface_balance
from sludge_sandbox.water_properties import NumericalLimits


@dataclass
class ColumnSetup:
    host: BallastWaterCell
    volume: float
    water: object
    solid: dict
    thermochemistry: object
    rates: object


def build_column(root, config, count):
    water = RecordedWaterProperties(root/config['water_facts_file'], NumericalLimits(**config['numerics']['water']))
    thermo = load_thermochemistry(root/config['thermochemistry_file'])
    solid = json.loads((root/config['solid_facts_file']).read_text())
    geometry = config['geometry']
    dx = geometry['length_m']/count
    volume = geometry['area_m2']*dx
    fluid = EquilibriumWaterCell(water, thermo, config['molar_masses_kg_mol'], volume,
                                 config['reference_pressure_pa'], config['numerics'])
    host = BallastWaterCell(fluid, solid, config['solid']['total_mol']/count,
                           config['solid']['segment_index'], config['solid']['reference_temperature_k'],
                           config['numerics']['warm_temperature_inverse'])
    transfer = config['transfer']
    internal = GasBoundaryTransfer(
        area_m2=geometry['area_m2'], cell_distance_m=dx/2, reservoir_distance_m=dx/2,
        cell_conductivity_w_m_k=transfer['conductivity_w_m_k'],
        reservoir_conductivity_w_m_k=transfer['conductivity_w_m_k'],
        **transfer['gas'])
    surface = GasBoundaryTransfer(
        area_m2=geometry['area_m2'], cell_distance_m=dx/2,
        reservoir_distance_m=transfer['external_distance_m'],
        cell_conductivity_w_m_k=transfer['conductivity_w_m_k'],
        reservoir_conductivity_w_m_k=transfer['external_conductivity_w_m_k'],
        **transfer['gas'])
    program = BoundaryProgram(identity=ProgramIdentity(**config['boundary_program']['identity']),
                               **config['boundary_program']['values'])
    radiation = config['radiation']
    surface_policy = SurfacePolicy(**config['numerics']['surface_balance'])

    def rates(gases, at_time):
        boundary = program.at(float(at_time))
        reservoir = ideal_gas_reservoir(
            temperature_k=boundary.gas_temperature_k, pressure_pa=boundary.total_pressure_pa,
            mole_fractions=boundary.mole_fractions, molar_masses_kg_mol=fluid.molar_masses_kg_mol,
            gas_constant_j_mol_k=thermo.gas_constant_j_mol_k)
        faces = column_face_rates(gases, reservoir, internal, surface, fluid.gas_enthalpy_j_mol)
        surface_t, heat, conducted, residual, limit, iterations, status = solve_surface_balance(
            cell_temperature_k=gases[-1].temperature_k, gas_temperature_k=boundary.gas_temperature_k,
            radiation_temperature_k=boundary.radiation_temperature_k, area_m2=geometry['area_m2'],
            convection_w_m2_k=transfer['external_conductivity_w_m_k']/transfer['external_distance_m'],
            emissivity=radiation['effective_emissivity'],
            stefan_boltzmann_w_m2_k4=radiation['stefan_boltzmann_w_m2_k4'], policy=surface_policy,
            conductive_into_cell=lambda ts: transfer['conductivity_w_m_k']*geometry['area_m2']*(
                ts-gases[-1].temperature_k)/(dx/2),
            zero_conductivity=False, error_type=ValueError)
        original = faces[-1]
        # Replace the original two-resistance heat path with the resolved
        # film/radiation balance; gas enthalpy remains a separate flux.
        faces[-1] = replace(original, conduction_out_w=-heat.convective_in_w,
            energy_out_w=-heat.convective_in_w+sum(original.diffusive_enthalpy_out_w.values())+
                         sum(original.advective_enthalpy_out_w.values()))
        surface_point = {'temperature_k': surface_t, 'heat_into_cell_w': conducted,
                         'convective_in_w': heat.convective_in_w, 'radiative_in_w': heat.radiative_in_w,
                         'balance_residual_w': residual, 'balance_limit_w': limit,
                         'iterations': iterations, 'status': status}
        return faces, -heat.radiative_in_w, boundary, surface_point

    return ColumnSetup(host, volume, water, solid, thermo, rates)
