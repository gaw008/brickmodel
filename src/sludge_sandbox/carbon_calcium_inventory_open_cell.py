"""Open positive-inventory cell using the qualified caloric response only."""
import numpy as np

from .carbon_calcium_open_cell import CarbonCalciumOpenCell
from .carbon_calcium_caloric_inventory import caloric_inventory_tangent


class CarbonCalciumInventoryOpenCell(CarbonCalciumOpenCell):
    def rates(self, at, values):
        state, face = self.observe(values)
        inventories = np.array([face['inventory_flows_mol_s'][key]
                                for key in self.face_parameters['transferred_inventory_order']])
        tangent = caloric_inventory_tangent(self.model, state, self.volume, self.calcium,
                                            float(values[0]), float(values[1]))
        du = np.array(tangent['internal_energy_derivatives'])
        temperature_rate = (face['energy_flow_w'] - du[1:] @ inventories) / du[0]
        return np.array([
            *inventories, temperature_rate, face['energy_flow_w'],
            face['left_entropy_rate_w_k'], face['entropy_production_w_k']])
