"""Build the source-qualified positive-inventory decoder explicitly."""
from carbon_calcium_pressure_setup import build as build_restricted
from sludge_sandbox.recorded_carbon_calcium_inventory import RecordedCarbonCalciumInventory


def build(root, settings):
    base, sources, standard = build_restricted(root, settings)
    return RecordedCarbonCalciumInventory(base.phases, base.r, base.p0,
        base.volumes, base.parameters), sources, standard
