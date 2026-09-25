"""Isothermal binary DGM with explicitly sourced cross-section ratio A*."""
from .chapman_enskog_binary_viscosity import (
    binary_viscosity_pa_s, interaction_viscosity_from_molar_diffusion,
)
from .dusty_gas_entropy_face import DustyGasEntropyFace
from .dusty_gas_isothermal_column import IsothermalDustyGasColumn


class ChapmanEnskogDustyGasFace(DustyGasEntropyFace):
    def __init__(self, temperature, gas_constant, masses, viscosities, products,
                 pore, distance, order, cross_section_ratio):
        super().__init__(temperature, gas_constant, masses, viscosities, products,
                         pore, distance, order)
        self.cross_section_ratio = cross_section_ratio
        rho_d = self.diffusion_pressure[0, 1]/(gas_constant*temperature)
        self.interaction_viscosity = interaction_viscosity_from_molar_diffusion(
            rho_d, masses, cross_section_ratio)

    def mixture_viscosity(self, fractions):
        return binary_viscosity_pa_s(fractions[0], self.viscosities, self.masses,
                                    self.interaction_viscosity, self.cross_section_ratio)


class ChapmanEnskogDustyGasColumn(IsothermalDustyGasColumn):
    def create_face(self, gas_constant, masses, pure_viscosities, diffusion_pressure):
        p = self.parameters
        return ChapmanEnskogDustyGasFace(self.temperature, gas_constant, masses, pure_viscosities,
            diffusion_pressure, p['pore'], self.width, p['face_quadrature_order'],
            float(p['mixture_viscosity']['cross_section_row']['A_star']))
