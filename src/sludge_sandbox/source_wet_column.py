"""N-cell fixed source-mass wet column using shared phase and face kernels.

This path currently has two explicit closed boundaries and manufactured
transport/geometry. It is not an exact-event host or a qualified sludge model.
Solid mass stays fixed; no A/B network or separate latent heat is introduced.
"""
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
import time

from .deforming_solid_storage import _digest
from .gas_transport import ideal_gas_state
from .integration import DomainExit
from .mass_storage_bridge import require
from .mass_wet_storage import WetMixedState
from .mass_wet_transport import (
    WetFace, evaluate_wet_phase, evaluate_wet_face, check_thermal_chemical_sources, represented,
)
from .phase_storage import InversePolicy
from .source_wet_storage import SourceWetStorage, _binary
from .water_chemical_potential import WaterChemicalPotential


@dataclass(frozen=True)
class SourceColumnCell:
    inverse: object
    phase: object
    chemistry: object


@dataclass(frozen=True)
class ColumnFaceRate:
    face_id: int
    left_cell: int | None
    right_cell: int | None
    gas_mol_s: tuple
    energy_w: float
    conduction_w: float
    diffusive_enthalpy_w: tuple
    advective_enthalpy_w: tuple
    shared_evaluation: object | None


@dataclass(frozen=True)
class SourceColumnRates:
    cells: tuple
    gas_states: tuple
    faces: tuple
    model_identity: str
    source_ids: tuple
    material_qualified: bool = False


@dataclass(frozen=True)
class SourceWetColumn:
    storages: tuple
    inverse_policies: tuple
    chemical: WaterChemicalPotential
    transfer_coefficients_mol_s_pa: tuple
    faces: tuple
    cell_widths_m: tuple
    face_area_m2: float
    interface_modes: tuple
    coefficient_source_ids: tuple
    boundary_conditions: tuple = ('closed_no_flux', 'closed_no_flux')
    transport_classification: str = 'manufactured_test_fixture'
    _identity: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, '_identity', self.binding())

    @property
    def cell_count(self):
        return len(self.storages)

    @property
    def gas_ids(self):
        return self.storages[0].gas_ids

    def binding(self):
        require(type(self.storages) is tuple and bool(self.storages) and
                all(type(s) is SourceWetStorage for s in self.storages), 'actual_source_wet_storages')
        require(type(self.chemical) is WaterChemicalPotential, 'actual_water_chemical_provider')
        n = len(self.storages)
        require(type(self.inverse_policies) is tuple and len(self.inverse_policies) == n and
                all(type(p) is InversePolicy for p in self.inverse_policies), 'per_cell_inverse_policies')
        require(type(self.transfer_coefficients_mol_s_pa) is tuple and len(self.transfer_coefficients_mol_s_pa) == n,
                'per_cell_phase_coefficients')
        for value in self.transfer_coefficients_mol_s_pa:
            require(_binary(value) >= 0, 'negative_phase_coefficient')
        require(type(self.faces) is tuple and len(self.faces) == n-1 and
                all(type(f) is WetFace for f in self.faces), 'N_minus_one_internal_faces')
        require(type(self.cell_widths_m) is tuple and len(self.cell_widths_m) == n, 'per_cell_widths')
        area = _binary(self.face_area_m2, positive=True)
        widths = tuple(_binary(v, positive=True) for v in self.cell_widths_m)
        require(type(self.interface_modes) is tuple and len(self.interface_modes) == n and
                all(type(v) is str and v in ('existing_liquid', 'depleted_no_nucleation') for v in self.interface_modes),
                'per_cell_interface_modes')
        require(self.boundary_conditions == ('closed_no_flux', 'closed_no_flux'), 'only_explicit_closed_boundaries')
        require(self.transport_classification == 'manufactured_test_fixture', 'source_transport_not_yet_admitted')
        require(type(self.coefficient_source_ids) is tuple and bool(self.coefficient_source_ids) and
                all(type(s) is str and bool(s.strip()) for s in self.coefficient_source_ids), 'transport_sources')
        for i, face in enumerate(self.faces):
            require(F(face.area_m2) == F(area) and type(face.half_widths_m) is tuple and
                    tuple(map(F, face.half_widths_m)) == (F(widths[i])/2, F(widths[i+1])/2),
                    'face_geometry_mismatch')
        first = self.storages[0]
        for i, storage in enumerate(self.storages):
            storage._check()
            require(storage.gas_ids == first.gas_ids and storage.caloric.binding() == first.caloric.binding(),
                    'common_source_material_and_gas_layout')
            require(_digest(storage.fluid_template.gas_phases) == _digest(first.fluid_template.gas_phases),
                    'common_gas_caloric_source')
            require(F(storage.volume.value_m3)+F(storage.volume.error_m3) <= F(area)*F(widths[i]),
                    'available_fluid_volume_exceeds_cell_geometry')
            check_thermal_chemical_sources(storage, self.chemical)
        self.chemical._check_identity()
        c = self.chemical
        backends = tuple((type(w).__module__, type(w).__qualname__, w.implementation)
                         for w in (c.water, c.vapor._water))
        return _digest(('source_wet_closed_column_v1', tuple(s.binding() for s in self.storages),
            self.inverse_policies, c, backends, (c.reference_pressure_pa, c.method_id, c.caloric_method_id,
            c.gas_constant_j_mol_k, c.temperature_range_k), self.transfer_coefficients_mol_s_pa,
            self.faces, self.cell_widths_m, self.face_area_m2, self.interface_modes,
            self.coefficient_source_ids, self.boundary_conditions, self.transport_classification))

    def _check(self):
        require(self.binding() == self._identity, 'source_column_content_changed')

    @property
    def model_identity(self):
        self._check()
        return self._identity

    def _check_states(self, states):
        self._check()
        require(type(states) is tuple and len(states) == self.cell_count, 'column_state_layout')
        for storage, state, mode in zip(self.storages, states, self.interface_modes):
            storage.check(state)
            if mode == 'depleted_no_nucleation' and state.liquid_water_mol != 0:
                raise DomainExit('dry_interface_requires_exact_zero_liquid')

    def with_depleted_cells(self, states, cell_indices):
        """Switch explicit exact-zero inventories; does not locate an event."""
        self._check_states(states)
        require(type(cell_indices) is tuple and bool(cell_indices) and len(set(cell_indices)) == len(cell_indices)
                and all(type(i) is int and 0 <= i < self.cell_count for i in cell_indices), 'unique_depleted_indices')
        modes = list(self.interface_modes)
        for i in cell_indices:
            require(states[i].liquid_water_mol == 0 and modes[i] == 'existing_liquid', 'exact_zero_liquid_for_mode_change')
            modes[i] = 'depleted_no_nucleation'
        return replace(self, interface_modes=tuple(modes))

    def evaluate(self, states):
        self._check_states(states)
        # Refuse invalid modes over the whole column before doing any inverse.
        for state, mode in zip(states, self.interface_modes):
            if mode == 'existing_liquid' and state.liquid_water_mol <= 0:
                raise DomainExit('existing_liquid_interface_requires_positive_inventory')
        cells, gases = [], []
        sources = set(self.coefficient_source_ids+self.chemical.source_ids)
        for i, (storage, state, policy) in enumerate(zip(self.storages, states, self.inverse_policies)):
            inverse = storage.invert(state, policy)
            point = inverse.point
            chemistry = storage.chemistry.evaluate(state.solid_mass_kg, state.gas_amounts_mol)
            phase = evaluate_wet_phase(self.chemical, point, state.gas_amounts_mol[2],
                                      self.transfer_coefficients_mol_s_pa[i], self.interface_modes[i])
            cells.append(SourceColumnCell(inverse, phase, chemistry))
            gases.append(ideal_gas_state(dict(zip(self.gas_ids, state.gas_amounts_mol)),
                temperature_k=point.temperature_k, gas_volume_m3=point.gas_volume_m3,
                molar_masses_kg_mol={k: storage.fluid_template.gas_phases[k].molar_mass_kg_mol for k in self.gas_ids},
                gas_constant_j_mol_k=self.chemical.gas_constant_j_mol_k))
            sources.update(point.source_ids)
            sources.update(phase.equilibrium.source_ids)
        zeros = (0.,)*len(self.gas_ids)
        faces = [ColumnFaceRate(0, None, 0, zeros, 0., 0., zeros, zeros, None)]
        for i, face in enumerate(self.faces, 1):
            shared = evaluate_wet_face(face, (gases[i-1], gases[i]), self.gas_ids,
                                       self.storages[0].fluid_template.gas_phases)
            faces.append(ColumnFaceRate(i, i-1, i, tuple(shared.exchange.net_mol_s[k] for k in self.gas_ids),
                shared.face_energy_w, shared.conduction_w, shared.diffusive_enthalpy_w,
                shared.advective_enthalpy_w, shared))
            sources.update(face.source_ids)
        faces.append(ColumnFaceRate(self.cell_count, self.cell_count-1, None, zeros, 0., 0., zeros, zeros, None))
        self._check_states(states)
        return SourceColumnRates(tuple(cells), tuple(gases), tuple(faces), self._identity, tuple(sorted(sources)))

    def provenance(self):
        self._check()
        return {'schema': 'source_wet_column_v1', 'model_identity': self._identity,
            'cells': tuple(s.provenance() for s in self.storages),
            'boundary_conditions': self.boundary_conditions, 'cell_widths_m': self.cell_widths_m,
            'face_area_m2': self.face_area_m2, 'internal_face_adjacency': tuple((i, i-1, i) for i in range(1, self.cell_count)),
            'transport_classification': self.transport_classification, 'coefficient_source_ids': self.coefficient_source_ids,
            'material_qualified': False, 'scope': 'fixed source mass, fixed slab, closed boundaries; no exact event or furnace boundary admission'}


@dataclass(frozen=True)
class ColumnFaceIntegral:
    face_id: int
    gas_mol: tuple
    energy_j: F
    conduction_j: F
    diffusive_enthalpy_j: tuple
    advective_enthalpy_j: tuple
    energy_decomposition_roundoff_j: F


@dataclass(frozen=True)
class ColumnRoundoff:
    liquid_mol: tuple
    gas_mol: tuple
    energy_j: tuple

    @property
    def absolute_inventory_mol(self):
        return sum(map(abs, self.liquid_mol), F())+sum((abs(x) for row in self.gas_mol for x in row), F())

    @property
    def absolute_energy_j(self):
        return sum(map(abs, self.energy_j), F())


@dataclass(frozen=True)
class ColumnStepLedger:
    duration_s: F
    faces: tuple
    phase_water_mol: tuple
    roundoff: ColumnRoundoff
    predictor_roundoff: ColumnRoundoff
    midpoint_states: tuple


@dataclass(frozen=True)
class SourceColumnRun:
    status: str
    reason: str | None
    times_s: tuple
    states: tuple
    observations: tuple
    ledgers: tuple
    evaluations_attempted: int
    evaluations_completed: int
    elapsed_seconds: float
    model_identity: str
    energy_roundoff_used_j: F
    inventory_roundoff_used_mol: F
    energy_roundoff_budget_j: float
    inventory_roundoff_budget_mol: float
    material_qualified: bool = False


def _integrals(rates, duration):
    faces = []
    for face in rates.faces:
        q = duration*F(face.energy_w)
        conduction = duration*F(face.conduction_w)
        diff = tuple(duration*F(x) for x in face.diffusive_enthalpy_w)
        adv = tuple(duration*F(x) for x in face.advective_enthalpy_w)
        faces.append(ColumnFaceIntegral(face.face_id, tuple(duration*F(x) for x in face.gas_mol_s),
                     q, conduction, diff, adv, q-conduction-sum(diff, F())-sum(adv, F())))
    return tuple(faces), tuple(duration*F(c.phase.phase_water_mol_s) for c in rates.cells)


def _advance(column, old, faces, phase):
    """One exact aggregation and one binary64 projection per cell quantity."""
    result, liquid_errors, gas_errors, energy_errors = [], [], [], []
    for i, (storage, state, mode) in enumerate(zip(column.storages, old, column.interface_modes)):
        liquid = F(state.liquid_water_mol)-phase[i]
        gas = tuple(F(value)+faces[i].gas_mol[k]-faces[i+1].gas_mol[k]+(phase[i] if k == 2 else 0)
                    for k, value in enumerate(state.gas_amounts_mol))
        energy = F(state.internal_energy_j)+faces[i].energy_j-faces[i+1].energy_j
        if not all(v >= 0 for v in (liquid, *gas)):
            raise DomainExit('column_inventory_domain_exit')
        if not (liquid > 0 if mode == 'existing_liquid' else liquid == 0):
            raise DomainExit('column_liquid_mode_exit_no_event_localization')
        liquid_float = represented(liquid)
        gas_float = tuple(map(represented, gas))
        energy_float = represented(energy)
        result.append(storage.state(liquid_float, gas_float, energy_float))
        liquid_errors.append(F(liquid_float)-liquid)
        gas_errors.append(tuple(F(a)-b for a, b in zip(gas_float, gas)))
        energy_errors.append(F(energy_float)-energy)
    return tuple(result), ColumnRoundoff(tuple(liquid_errors), tuple(gas_errors), tuple(energy_errors))


def integrate_source_column(column, initial, *, duration_s, steps, maximum_wall_seconds=30.,
                            energy_roundoff_budget_j=1e-8, inventory_roundoff_budget_mol=1e-12, cancel=None):
    """Bounded midpoint segment; accepted ledger excludes predictor exchanges.

    Budgets bound accumulated projection/decomposition arithmetic, not temporal
    truncation, inverse propagation or physical fit error. Predictor roundoff
    is recorded separately and never added to conserved-inventory balances.
    """
    require(type(column) is SourceWetColumn and type(steps) is int and steps > 0, 'explicit_column_steps')
    duration = F(_binary(duration_s, positive=True))
    h = duration/steps
    wall = _binary(maximum_wall_seconds, positive=True)
    energy_budget = _binary(energy_roundoff_budget_j, positive=True)
    inventory_budget = _binary(inventory_roundoff_budget_mol, positive=True)
    identity = column.model_identity
    start = time.monotonic()
    states, times, observations, ledgers = [initial], [F()], [], []
    attempted = completed = 0
    used_energy = used_inventory = F()

    def evaluate(state):
        nonlocal attempted, completed
        if cancel is not None and cancel():
            raise InterruptedError('cancel_requested')
        if time.monotonic()-start > wall:
            raise TimeoutError('wall_budget_exceeded')
        attempted += 1
        output = column.evaluate(state)
        completed += 1
        if time.monotonic()-start > wall:
            raise TimeoutError('wall_budget_exceeded')
        return output

    status, reason = 'completed', None
    try:
        for i in range(steps):
            first = evaluate(states[-1])
            predictor_faces, predictor_phase = _integrals(first, h/2)
            midpoint, predictor_error = _advance(column, states[-1], predictor_faces, predictor_phase)
            middle = evaluate(midpoint)
            faces, phase = _integrals(middle, h)
            # Full step always starts from the prior accepted state.
            new, error = _advance(column, states[-1], faces, phase)
            candidate_energy = used_energy+error.absolute_energy_j+predictor_error.absolute_energy_j
            candidate_energy += sum((abs(f.energy_decomposition_roundoff_j) for f in (*predictor_faces, *faces)), F())
            candidate_inventory = used_inventory+error.absolute_inventory_mol+predictor_error.absolute_inventory_mol
            require(candidate_energy <= F(energy_budget), 'column_energy_roundoff_budget_exceeded')
            require(candidate_inventory <= F(inventory_budget), 'column_inventory_roundoff_budget_exceeded')
            last = evaluate(new)
            ledger = ColumnStepLedger(h, faces, phase, error, predictor_error, midpoint)
            states.append(new)
            times.append((i+1)*h)
            observations.append(last)
            ledgers.append(ledger)
            used_energy, used_inventory = candidate_energy, candidate_inventory
    except DomainExit as exc:
        status, reason = 'domain_exit', str(exc)
    except InterruptedError as exc:
        status, reason = 'cancelled', str(exc)
    except TimeoutError as exc:
        status, reason = 'resource_limit', str(exc)
    except (ValueError, OverflowError) as exc:
        status, reason = 'failed', str(exc)
    return SourceColumnRun(status, reason, tuple(times), tuple(states), tuple(observations), tuple(ledgers),
        attempted, completed, time.monotonic()-start, identity, used_energy, used_inventory,
        energy_budget, inventory_budget)
