"""Research model for the newly qualified static inventory domain.

Rigid pressure bounds and U inversion inherit the existing physical brackets.
Their qualification in this wider domain is a separate research stage.
"""
from sludge_sandbox.recorded_carbon_calcium_pressure import RecordedCarbonCalciumPressure

from carbon_calcium_inventory_prototype import at_temperature_pressure
from carbon_calcium_inventory_caloric_prototype import caloric_response


class InventoryPrototype(RecordedCarbonCalciumPressure):
    def at_temperature_pressure(self, temperature_k, pressure_pa,
                                calcium_atoms_mol, carbon_atoms_mol,
                                oxygen_atoms_mol, nitrogen_molecules_mol):
        inventory = {'calcium_atoms_mol': calcium_atoms_mol,
            'carbon_atoms_mol': carbon_atoms_mol, 'oxygen_atoms_mol': oxygen_atoms_mol,
            'nitrogen_molecules_mol': nitrogen_molecules_mol}
        state = at_temperature_pressure(self, temperature_k, pressure_pa, inventory)
        state.update(caloric_response(self, state))
        return state
