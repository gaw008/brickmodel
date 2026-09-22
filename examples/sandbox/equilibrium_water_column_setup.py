"""One physical construction shared by explicit and implicit column drivers."""
from dataclasses import dataclass, replace
import json

from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.equilibrium_water_cell import EquilibriumWaterCell
from sludge_sandbox.equilibrium_water_column import BallastWaterCell
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.gibbs_water_table import GibbsWaterTable
from sludge_sandbox.open_gas_boundary import GasBoundaryTransfer, open_gas_boundary_rate
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.recorded_water import RecordedWaterProperties
from sludge_sandbox.thermochemistry import load_thermochemistry
from sludge_sandbox.surface_balance import solve_surface_balance
from sludge_sandbox.water_properties import NumericalLimits


@dataclass
class ColumnSetup:
    hosts: tuple
    host_indices: tuple
    volumes: tuple
    solid_amounts: tuple
    roles: tuple
    internal_transfers: tuple
    surface_transfer: object
    wall_distance_m: float
    wall_conductivity_w_m_k: float
    water: object
    solid: dict
    thermochemistry: object
    rates: object

    def host_for_cell(self, index):
        return self.hosts[self.host_indices[index]]

    def record_geometry(self):
        from dataclasses import asdict
        return {
            'cell_fluid_volumes_m3': list(self.volumes),
            'cell_solid_amounts_mol': list(self.solid_amounts),
            'cell_roles': list(self.roles),
            'cell_host_indices': list(self.host_indices),
            'face_transfers': [asdict(p) for p in (*self.internal_transfers, self.surface_transfer)],
            'wall_distance_m': self.wall_distance_m,
            'wall_conductivity_w_m_k': self.wall_conductivity_w_m_k,
        }


def build_column(root, config, count):
    water = RecordedWaterProperties(root/config['water_facts_file'], NumericalLimits(**config['numerics']['water']))
    representation = config['liquid_evaluation']
    water = {
        'direct': lambda: water,
        'gibbs_table': lambda: GibbsWaterTable(water, json.loads((root/representation['table_file']).read_text())),
    }[representation['method']]()
    thermo = load_thermochemistry(root/config['thermochemistry_file'])
    solid = json.loads((root/config['solid_facts_file']).read_text())
    geometry = config['geometry']
    transfer = config['transfer']
    if config['schema'] == 'equilibrium_water_column_v1':
        bulk_count = count
        dx = geometry['length_m']/bulk_count
        group_volumes = (geometry['area_m2']*dx,)
        group_solids = (config['solid']['total_mol']/bulk_count,)
        host_indices = (0,)*count
        roles = ('bulk',)*count
        half_distances = (dx/2,)*count
        conductivities = (transfer['conductivity_w_m_k'],)*count
        wall_distance = dx/2
        wall_conductivity = transfer['conductivity_w_m_k']
    elif config['schema'] == 'fixed_surface_storage_column_v1':
        storage = config['surface_storage']
        bulk_count = count-1
        dx = geometry['length_m']/bulk_count
        group_volumes = (geometry['area_m2']*dx, storage['fluid_volume_m3'])
        group_solids = (config['solid']['total_mol']/bulk_count, storage['solid_mol'])
        host_indices = (0,)*bulk_count+(1,)
        roles = ('bulk',)*bulk_count+('surface_storage',)
        half_distances = (dx/2,)*bulk_count+(storage['contact_distance_m'],)
        conductivities = (transfer['conductivity_w_m_k'],)*bulk_count+(storage['conductivity_w_m_k'],)
        wall_distance = storage['wall_distance_m']
        wall_conductivity = storage['conductivity_w_m_k']
    else:
        raise ValueError('unknown spatial model schema: '+config['schema'])
    hosts = tuple(BallastWaterCell(
        EquilibriumWaterCell(water, thermo, config['molar_masses_kg_mol'], volume,
                             config['reference_pressure_pa'], config['numerics']),
        solid, amount, config['solid']['segment_index'], config['solid']['reference_temperature_k'],
        config['numerics']['warm_temperature_inverse'])
        for volume, amount in zip(group_volumes, group_solids, strict=True))
    volumes = tuple(group_volumes[i] for i in host_indices)
    solid_amounts = tuple(group_solids[i] for i in host_indices)
    internal = tuple(GasBoundaryTransfer(
        area_m2=geometry['area_m2'], cell_distance_m=half_distances[i],
        reservoir_distance_m=half_distances[i+1], cell_conductivity_w_m_k=conductivities[i],
        reservoir_conductivity_w_m_k=conductivities[i+1], **transfer['gas'])
        for i in range(count-1))
    surface = GasBoundaryTransfer(
        area_m2=geometry['area_m2'], cell_distance_m=wall_distance,
        reservoir_distance_m=transfer['external_distance_m'],
        cell_conductivity_w_m_k=wall_conductivity,
        reservoir_conductivity_w_m_k=transfer['external_conductivity_w_m_k'],
        **transfer['gas'])
    fluid = hosts[0].fluid
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
        faces = [open_gas_boundary_rate(left, right, link, fluid.gas_enthalpy_j_mol)
                 for left, right, link in zip(gases[:-1], gases[1:], internal, strict=True)]
        faces.append(open_gas_boundary_rate(gases[-1], reservoir, surface, fluid.gas_enthalpy_j_mol))
        surface_t, heat, conducted, residual, limit, iterations, status = solve_surface_balance(
            cell_temperature_k=gases[-1].temperature_k, gas_temperature_k=boundary.gas_temperature_k,
            radiation_temperature_k=boundary.radiation_temperature_k, area_m2=geometry['area_m2'],
            convection_w_m2_k=transfer['external_conductivity_w_m_k']/transfer['external_distance_m'],
            emissivity=radiation['effective_emissivity'],
            stefan_boltzmann_w_m2_k4=radiation['stefan_boltzmann_w_m2_k4'], policy=surface_policy,
            conductive_into_cell=lambda ts: wall_conductivity*geometry['area_m2']*(
                ts-gases[-1].temperature_k)/wall_distance,
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

    return ColumnSetup(hosts, host_indices, volumes, solid_amounts, roles, internal, surface,
                       wall_distance, wall_conductivity, water, solid, thermo, rates)
