"""Exact-argument memoization for separate calcite audit instances.

The source records are copied, and original standard-state methods are retained
behind bounded caches. Consumers in these audits read returned dictionaries;
they do not edit them. Inventory/phase/surface solutions are never cached.
"""
from dataclasses import replace
from functools import lru_cache


def cached_thermochemistry(reaction, nitrogen, phase_entries, reaction_entries):
    def phase_copy(phase):
        copied = replace(phase)
        object.__setattr__(copied, 'standard', lru_cache(maxsize=phase_entries)(copied.standard))
        return copied

    copied_reaction = replace(reaction, phases={name: phase_copy(phase) for name, phase in reaction.phases.items()})
    object.__setattr__(copied_reaction, 'standard', lru_cache(maxsize=reaction_entries)(copied_reaction.standard))
    return copied_reaction, phase_copy(nitrogen)
