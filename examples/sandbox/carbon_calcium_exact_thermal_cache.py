"""Exact-temperature phase caches on an independent inventory model instance.

The pressure, composition, phase selection and derivative solves remain live.
Phase standard-state dictionaries are read-only inputs for these consumers.
"""
from dataclasses import replace
from functools import lru_cache

from sludge_sandbox.recorded_carbon_calcium_inventory import RecordedCarbonCalciumInventory


def cached_inventory_model(model, phase_entries):
    phases = {}
    for name, original in model.phases.items():
        phase = replace(original)
        object.__setattr__(phase, 'standard', lru_cache(maxsize=phase_entries)(phase.standard))
        phases[name] = phase
    return RecordedCarbonCalciumInventory(phases, model.r, model.p0, model.volumes, model.parameters)
