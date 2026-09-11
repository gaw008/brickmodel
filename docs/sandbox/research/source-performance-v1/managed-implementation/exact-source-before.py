"""Exact-time fluid-inventory adapter for a fixed-dry-mass source column.

Dry kg masses remain immutable model parameters, never fictitious mol slots.
Total U still includes their source caloric term. This connects the existing
N-cell integrator; it does not admit the mechanical depletion driver or supply
a transportation-depletion projection or a missing dry-interface law.
"""
from .source_run_observer import emit_source_event, emit_source_failure, is_source_observer_error
from dataclasses import dataclass, field
from fractions import Fraction
import numpy as np

from .exact_event_clock import ExactEventTime
from .integration import ConservedState, Rates, IntegrationError, DomainExit
from .mass_storage_bridge import require
from .source_wet_column import SourceWetColumn
from .programmed_source_wet_column import ProgrammedSourceWetColumn
from .source_mass_caloric import DisabledChemicalRates


@dataclass(frozen=True)
class SourceExactEvaluation:
    time: ExactEventTime
    source_states: tuple
    source_evaluation: object
    rates: Rates
    operator_identity: tuple
    material_qualified: bool = False


@dataclass(frozen=True)
class ExactSourceColumn:
    column: SourceWetColumn | ProgrammedSourceWetColumn
    _identity: tuple = field(init=False, repr=False)

    def __post_init__(self):
        require(type(self.column) in (SourceWetColumn, ProgrammedSourceWetColumn),
                'actual_fixed_source_column_required')
        object.__setattr__(self, '_identity', self._binding())

    @property
    def species_ids(self):
        return ('liquid_water', *self.column.gas_ids)

    @property
    def liquid_index(self): return 0

    @property
    def vapor_index(self): return self.species_ids.index('H2O')

    @property
    def interfaces(self): return self.column.interface_modes

    def _binding(self):
        require(type(self.column) in (SourceWetColumn, ProgrammedSourceWetColumn),
                'actual_fixed_source_column_required')
        return ('exact_source_column_v1', self.column.model_identity, self.species_ids)

    @property
    def operator_identity(self):
        require(self._binding() == self._identity, 'exact_source_column_binding_changed')
        return self._identity

    @property
    def energy_model_identity(self):
        self.operator_identity
        # Storage identities bind mass, caloric reference, source and volume.
        # Transport and wet/dry interface modes do not redefine stored U.
        return ('source_column_fixed_dry_energy_v1',
                tuple(s.model_identity for s in self.column.storages), self.species_ids)

    def _check_states(self, states):
        self.operator_identity
        base = self.column.base if type(self.column) is ProgrammedSourceWetColumn else self.column
        base._check_states(states)

    def pack(self, states):
        """Losslessly place only liquid/gas inventories in the mol array."""
        self._check_states(states)
        return ConservedState(np.array([(s.liquid_water_mol, *s.gas_amounts_mol) for s in states]),
                              np.array([s.internal_energy_j for s in states]), self.energy_model_identity)

    def unpack(self, state):
        require(type(state) is ConservedState, 'actual_conserved_fluid_state_required')
        require(state.energy_model_identity == self.energy_model_identity, 'source_column_energy_binding_mismatch')
        require(state.mechanical_stretches is None, 'fixed_source_column_has_no_dynamic_mechanics')
        n = self.column.cell_count
        require(state.amounts_mol.shape == (n, len(self.species_ids))
                and state.internal_energy_j.shape == (n,), 'source_fluid_inventory_layout')
        result = tuple(storage.state(float(row[0]), tuple(map(float, row[1:])), float(energy))
                       for storage, row, energy in zip(self.column.storages, state.amounts_mol, state.internal_energy_j))
        self._check_states(result)
        return result

    def evaluate(self, state, time):
        evaluation = None
        try:
            emit_source_event('rhs_started', adapter=self, state=state, time=time)
            require(type(time) is ExactEventTime, 'exact_source_column_time_required')
            states = self.unpack(state)
            output = (self.column.evaluate(states, time) if type(self.column) is ProgrammedSourceWetColumn
                      else self.column.evaluate(states))
            n = self.column.cell_count
            local = np.zeros((n, len(self.species_ids)))
            for i, cell in enumerate(output.cells):
                chemistry = cell.chemistry
                require(type(chemistry) is DisabledChemicalRates
                        and type(chemistry.solid_kg_s) is tuple
                        and len(chemistry.solid_kg_s) == len(states[i].solid_mass_kg)
                        and type(chemistry.gas_mol_s) is tuple
                        and len(chemistry.gas_mol_s) == len(states[i].gas_amounts_mol)
                        and all(type(x) is Fraction and x == 0 for x in
                                (*chemistry.solid_kg_s, *chemistry.gas_mol_s, chemistry.chemical_reference_power_w))
                        and chemistry.phase_transfer_included is False,
                        'fixed_source_adapter_cannot_hide_active_chemistry')
                phase = cell.phase.phase_water_mol_s
                local[i, self.liquid_index] = -phase
                local[i, self.vapor_index] = phase
            rates = Rates(np.array([(getattr(face, 'liquid_mol_s', 0.), *face.gas_mol_s) for face in output.faces]),
                          np.array([face.energy_w for face in output.faces]), local, np.zeros(n))
            evaluation = SourceExactEvaluation(time, states, output, rates, self.operator_identity)
            emit_source_event('rhs_returned', adapter=self, state=state, time=time, evaluation=evaluation)
            rates.derivatives(state)
            return evaluation
        except BaseException as exc:
            emit_source_failure('rhs_failed', exc, adapter=self, state=state, time=time, evaluation=evaluation)
            raise

    def __call__(self, state, time):
        try:
            return self.evaluate(state, time).rates
        except (IntegrationError, DomainExit):
            # Preserve explicit DomainExit and other solver classifications.
            raise
        except ValueError as exc:
            if is_source_observer_error(exc):
                raise
            # The common integrator retains prefixes for IntegrationError.
            # Unknown source errors remain numerical failures, not domain claims.
            raise IntegrationError('source_column_callback:'+str(exc)) from exc

    def breakpoints(self, start, end):
        require(type(start) is ExactEventTime and type(end) is ExactEventTime and start < end,
                'ordered_exact_source_interval')
        self.operator_identity
        return self.column.breakpoints(start, end) if type(self.column) is ProgrammedSourceWetColumn else ()

    def with_depleted_cells(self, state, cell_indices):
        """Explicit exact-zero mode change only; no event or mobility inference."""
        states = self.unpack(state)
        return ExactSourceColumn(self.column.with_depleted_cells(states, cell_indices))

    def provenance(self):
        return {'schema': 'exact_source_column_v1', 'operator_identity': self.operator_identity,
                'energy_model_identity': self.energy_model_identity, 'species_ids': self.species_ids,
                'fixed_dry_mass_kg': tuple(s.dry_mass_kg for s in self.column.storages),
                'local_source_meaning': 'liquid-to-vapor phase transfer; no chemical reaction',
                'total_energy_meaning': 'source dry sensible energy plus liquid/gas internal energy',
                'source_column': self.column.provenance(), 'material_qualified': False,
                'scope': 'fixed dry composition; no mechanical-driver or depletion-projection admission'}
