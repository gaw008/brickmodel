"""Positive-inventory capsule with independently programmed gas and radiation."""
import numpy as np

from .carbon_calcium_program_cell import CarbonCalciumProgramCell
from .carbon_calcium_radiative_cell import black_enclosure_exchange, combined_rates


class CarbonCalciumRadiativeProgram(CarbonCalciumProgramCell):
    def __init__(self, model, settings, face_parameters, rigid_numerics):
        super().__init__(model, settings, face_parameters, rigid_numerics)
        self.initial = np.concatenate((self.initial, [0., 0.]))

    def radiation(self, at, state):
        external = self.program.at(at)
        parameters = dict(self.settings['radiation'],
            reservoir_temperature_k=external.radiation_temperature_k)
        return black_enclosure_exchange(state['temperature_k'], parameters)

    def rates(self, at, values):
        state, _, gas = self.observe(at, values)
        radiation = self.radiation(at, state)
        return combined_rates(self, state, gas, radiation, values)
