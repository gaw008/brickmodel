"""Uniform conservative spatial subdivision of the recorded sorptive cell."""
from copy import deepcopy
from dataclasses import dataclass

from sorptive_gas_cell_setup import build_sorptive_cell, restore_sorptive_cell
from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.open_gas_boundary import GasBoundaryTransfer, open_gas_boundary_rate
from sludge_sandbox.recorded_condensed_transport import condensed_exchange,combine_faces
from sludge_sandbox.recorded_sorptive_surface import SorptiveEvaporatingSurface


def cell_parameters(config,count):
    cell_config=deepcopy(config)
    for key in ('available_fluid_volume_m3','dry_mass_kg'):
        cell_config['cell'][key]/=count
    return cell_config


@dataclass(frozen=True)
class SorptiveColumn:
    host: object
    count: int
    config: dict
    internal_transfer: GasBoundaryTransfer
    boundary_transfer: GasBoundaryTransfer
    program: BoundaryProgram
    condensed_transfer: dict | None
    evaporating_surface: object | None

    def rates(self,gases,at_time,states):
        face=lambda left,right,transfer:open_gas_boundary_rate(left,right,transfer,self.host.fluid.gas_enthalpy_j_mol)
        rates=[face(left,right,self.internal_transfer) for left,right in zip(gases[:-1],gases[1:],strict=True)]
        if self.condensed_transfer is not None:
            rates=[combine_faces(gas_rate,condensed_exchange(left,right,
                area_m2=self.config['geometry']['face_area_m2'],distance_m=self.config['geometry']['length_m']/self.count,
                mobility_density_mol2_k_j_s_m=self.condensed_transfer['mobility_density_mol2_k_j_s_m']))
                for gas_rate,left,right in zip(rates,states[:-1],states[1:],strict=True)]
        boundary=self.program.at(float(at_time))
        reservoir=ideal_gas_reservoir(temperature_k=boundary.gas_temperature_k,pressure_pa=boundary.total_pressure_pa,
            mole_fractions=boundary.mole_fractions,molar_masses_kg_mol=self.config['molar_masses_kg_mol'],
            gas_constant_j_mol_k=self.host.fluid.thermochemistry.gas_constant_j_mol_k)
        rates.append(self.evaporating_surface.rate(gases[-1],states[-1],reservoir) if self.evaporating_surface is not None
                     else face(gases[-1],reservoir,self.boundary_transfer))
        return rates,boundary

    def geometry(self):
        config=self.config;dx=config['geometry']['length_m']/self.count
        result={'cell_count':self.count,'cell_width_m':dx,'cell_centers_m':[(i+.5)*dx for i in range(self.count)],
            'available_fluid_volume_m3_per_cell':self.host.fluid.available_fluid_volume_m3,
            'dry_mass_kg_per_cell':self.host.dry_mass_kg,
            'internal_transfer':self.internal_transfer.__dict__,'boundary_transfer':self.boundary_transfer.__dict__}
        if self.condensed_transfer is not None:
            result['condensed_internal_transfer']=self.condensed_transfer
        if self.evaporating_surface is not None:
            result['surface_internal_transfer']=self.evaporating_surface.inside.__dict__
            result['surface_external_transfer']=self.evaporating_surface.outside.__dict__
        return result


def build_column(root,config,count):
    host=build_sorptive_cell(root,cell_parameters(config,count))
    return column_with_host(host,config,count)


def restore_column(header,directory):
    single={**header,'parameters':header['cell_parameters']}
    host=restore_sorptive_cell(single,directory)
    return column_with_host(host,header['parameters'],header['cell_count'])


def column_with_host(host,config,count):
    half=config['geometry']['length_m']/count/2
    inner={**config['transfer'],'area_m2':config['geometry']['face_area_m2'],
           'cell_distance_m':half,'reservoir_distance_m':half,
           'reservoir_conductivity_w_m_k':config['transfer']['cell_conductivity_w_m_k']}
    boundary={**config['transfer'],'area_m2':config['geometry']['face_area_m2'],'cell_distance_m':half}
    program=BoundaryProgram(identity=ProgramIdentity(**config['boundary_program']['identity']),
                            **config['boundary_program']['values'])
    condensed=config['condensed_transfer'] if config['schema'] in ('source_sorptive_mobile_column_v1','sorptive_evaporating_surface_column_v1') else None
    surface=SorptiveEvaporatingSurface(host,config,count) if config['schema']=='sorptive_evaporating_surface_column_v1' else None
    return SorptiveColumn(host,count,config,GasBoundaryTransfer(**inner),GasBoundaryTransfer(**boundary),program,condensed,surface)
