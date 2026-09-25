"""Reconstruct the explicit column kind from a saved trajectory header."""
from carbon_calcium_inventory_setup import build
from sludge_sandbox.carbon_calcium_open_column import CarbonCalciumOpenColumn
from sludge_sandbox.carbon_calcium_surface_column import CarbonCalciumSurfaceColumn


def recorded_column(root, header, kind):
    model, _, _ = build(root, header['pressure_parameters'])
    arguments = (model, header['settings'], header['cell_settings'],
                 header['exterior_parameters'], header['rigid_parameters']['numerics'],
                 header['cell_count'])
    return {'direct': lambda: CarbonCalciumOpenColumn(*arguments),
            'surface': lambda: CarbonCalciumSurfaceColumn(*arguments, header['surface_parameters'])}[kind]()
