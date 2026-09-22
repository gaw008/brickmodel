"""Uniform conservative spatial subdivision of the recorded sorptive cell."""
from copy import deepcopy
from dataclasses import dataclass

from sorptive_gas_cell_setup import build_sorptive_cell
from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.open_gas_boundary import GasBoundaryTransfer, open_gas_boundary_rate


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

    def rates(self,gases,at_time):
        face=lambda left,right,transfer:open_gas_boundary_rate(left,right,transfer,self.host.fluid.gas_enthalpy_j_mol)
        rates=[face(left,right,self.internal_transfer) for left,right in zip(gases[:-1],gases[1:],strict=True)]
        boundary=self.program.at(float(at_time))
        reservoir=ideal_gas_reservoir(temperature_k=boundary.gas_temperature_k,pressure_pa=boundary.total_pressure_pa,
            mole_fractions=boundary.mole_fractions,molar_masses_kg_mol=self.config['molar_masses_kg_mol'],
            gas_constant_j_mol_k=self.host.fluid.thermochemistry.gas_constant_j_mol_k)
        rates.append(face(gases[-1],reservoir,self.boundary_transfer))
        return rates,boundary

    def geometry(self):
        config=self.config;dx=config['geometry']['length_m']/self.count
        return {'cell_count':self.count,'cell_width_m':dx,'cell_centers_m':[(i+.5)*dx for i in range(self.count)],
            'available_fluid_volume_m3_per_cell':self.host.fluid.available_fluid_volume_m3,
            'dry_mass_kg_per_cell':self.host.dry_mass_kg,
            'internal_transfer':self.internal_transfer.__dict__,'boundary_transfer':self.boundary_transfer.__dict__}


def build_column(root,config,count):
    host=build_sorptive_cell(root,cell_parameters(config,count))
    half=config['geometry']['length_m']/count/2
    inner={**config['transfer'],'area_m2':config['geometry']['face_area_m2'],
           'cell_distance_m':half,'reservoir_distance_m':half,
           'reservoir_conductivity_w_m_k':config['transfer']['cell_conductivity_w_m_k']}
    boundary={**config['transfer'],'area_m2':config['geometry']['face_area_m2'],'cell_distance_m':half}
    program=BoundaryProgram(identity=ProgramIdentity(**config['boundary_program']['identity']),
                            **config['boundary_program']['values'])
    return SorptiveColumn(host,count,config,GasBoundaryTransfer(**inner),GasBoundaryTransfer(**boundary),program)
