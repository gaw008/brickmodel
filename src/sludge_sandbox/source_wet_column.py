"""N-cell fixed source-mass wet column using shared phase and face kernels.

This path has two explicit closed boundaries and manufactured geometry and
transport, with an explicit optional donor-conductivity branch. It is not an
exact-event host or a qualified sludge model.
Solid mass stays fixed; no A/B network or separate latent heat is introduced.
"""
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
import math
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
from .arlabosse_rigid_sorption import ArlabosseSorptionStorage
from .arlabosse_sorption_phase import evaluate_sorption_phase
from .septien_conductivity import SeptienConductivity
from .water_chemical_potential import WaterChemicalPotential
from .solid_fluid_heat import LiquidTransportConfig
from .liquid_transport import LiquidTransportDomainError, liquid_face_exchange
from .liquid_transport_state import decoded_liquid_state


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


@dataclass(frozen=True, kw_only=True)
class LiquidColumnFaceRate(ColumnFaceRate):
    liquid_mol_s: float
    liquid_enthalpy_w: float
    liquid_enthalpy_projection_w: F
    liquid_exchange: object


@dataclass(frozen=True)
class ConductivityFaceWitness:
    conductivity_points: tuple
    conductance_w_k: float
    conduction_w: float
    conduction_arithmetic_residual_w: F
    entropy_production_w_k: float
    material_qualified: bool = False


@dataclass(frozen=True, kw_only=True)
class ConductivityColumnFaceRate(ColumnFaceRate):
    conductivity_witness: ConductivityFaceWitness


@dataclass(frozen=True)
class SourceColumnRates:
    cells: tuple
    gas_states: tuple
    faces: tuple
    model_identity: str
    source_ids: tuple
    material_qualified: bool = False


@dataclass(frozen=True, kw_only=True)
class LiquidSourceColumnRates(SourceColumnRates):
    liquid_states: tuple
    liquid_pressure_interval_scope: str = 'fixed_decoded_temperature'
    full_inverse_liquid_direction_certified: bool = False


@dataclass(frozen=True, kw_only=True)
class ConductivitySourceColumnRates(SourceColumnRates):
    conductivity_points: tuple


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
    liquid_transport: LiquidTransportConfig | None = None
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
                all(type(s) in (SourceWetStorage, ArlabosseSorptionStorage) for s in self.storages),
                'actual_source_wet_storages')
        sorption = type(self.storages[0]) is ArlabosseSorptionStorage
        require(sorption == (type(self) is ArlabosseSorptionColumn),
                'explicit_sorption_column_type_required')
        require(all(type(s) is type(self.storages[0]) for s in self.storages),
                'common_source_storage_model_required')
        thermal = self.thermal_provider if sorption else None
        if thermal is not None:
            require(type(thermal) is SeptienConductivity, 'actual_source_conductivity_required')
            thermal.binding()
        if sorption:
            require(self.liquid_transport is None, 'sorption_liquid_transport_not_supported')
            require(all(mode == 'existing_liquid' for mode in self.interface_modes),
                    'sorption_dry_interface_not_supported')
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
        expected_classification = ('mixed_source_exploratory' if thermal is not None
                                   else 'manufactured_test_fixture')
        require(self.transport_classification == expected_classification,
                'explicit_transport_classification')
        require(type(self.coefficient_source_ids) is tuple and bool(self.coefficient_source_ids) and
                all(type(s) is str and bool(s.strip()) for s in self.coefficient_source_ids), 'transport_sources')
        for i, face in enumerate(self.faces):
            require(F(face.area_m2) == F(area) and type(face.half_widths_m) is tuple and
                    tuple(map(F, face.half_widths_m)) == (F(widths[i])/2, F(widths[i+1])/2),
                    'face_geometry_mismatch')
            if thermal is not None:
                require(face.conductivities_w_m_k == (0., 0.),
                        'static_conduction_must_be_disabled')
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
        model_kind = 'arlabosse_sorption_closed_column_v1' if sorption else 'source_wet_closed_column_v1'
        content = (model_kind, tuple(s.binding() for s in self.storages),
            self.inverse_policies, c, backends, (c.reference_pressure_pa, c.method_id, c.caloric_method_id,
            c.gas_constant_j_mol_k, c.temperature_range_k), self.transfer_coefficients_mol_s_pa,
            self.faces, self.cell_widths_m, self.face_area_m2, self.interface_modes,
            self.coefficient_source_ids, self.boundary_conditions, self.transport_classification)
        if thermal is not None:
            content = (content, 'dynamic_septien_conductivity_v1', thermal.binding())
        if self.liquid_transport is not None:
            config = self.liquid_transport
            require(type(config) is LiquidTransportConfig, 'actual_liquid_transport_configuration')
            config.__post_init__()
            require(len(config.relations) == n and len(config.connections) == n-1,
                    'per_cell_liquid_relations_and_internal_connections')
            require(config.allow_manufactured and all(v.classification == 'manufactured_test_fixture'
                    for v in (*config.relations, *config.connections)), 'source_liquid_material_not_admitted')
            content = (content, 'explicit_internal_liquid_transport_v1', config)
        return _digest(content)

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
            if type(storage) is ArlabosseSorptionStorage:
                phase = evaluate_sorption_phase(storage, self.chemical, point,
                    state.gas_amounts_mol[2], self.transfer_coefficients_mol_s_pa[i], self.interface_modes[i])
            else:
                phase = evaluate_wet_phase(self.chemical, point, state.gas_amounts_mol[2],
                    self.transfer_coefficients_mol_s_pa[i], self.interface_modes[i])
            cells.append(SourceColumnCell(inverse, phase, chemistry))
            gases.append(ideal_gas_state(dict(zip(self.gas_ids, state.gas_amounts_mol)),
                temperature_k=point.temperature_k, gas_volume_m3=point.gas_volume_m3,
                molar_masses_kg_mol={k: storage.fluid_template.gas_phases[k].molar_mass_kg_mol for k in self.gas_ids},
                gas_constant_j_mol_k=self.chemical.gas_constant_j_mol_k))
            sources.update(point.source_ids)
            sources.update(phase.equilibrium.source_ids)
        liquids = ()
        thermal = self.thermal_provider if type(self) is ArlabosseSorptionColumn else None
        conductivity_points = ()
        if thermal is not None:
            # Validate every decoded cell even for N=1, which has no faces.
            conductivity_points = tuple(thermal.evaluate(cell.inverse.point.temperature_k,
                cell.inverse.point.moisture_kg_water_per_kg_dry) for cell in cells)
            sources.update(thermal.source_ids)
        if self.liquid_transport is not None:
            liquids = tuple(decoded_liquid_state(cell.inverse.point.fluid.mechanical, storage.water,
                available_pore_volume_m3=cell.inverse.point.available_pore_volume_m3,
                pressure_error_pa=cell.inverse.point.pressure_error_pa)
                for cell, storage in zip(cells, self.storages))
            sources.update(self.liquid_transport.source_ids)
        zeros = (0.,)*len(self.gas_ids)
        faces = [ColumnFaceRate(0, None, 0, zeros, 0., 0., zeros, zeros, None)]
        for i, face in enumerate(self.faces, 1):
            actual_face = face
            if thermal is not None:
                pair = conductivity_points[i-1:i+1]
                actual_face = replace(face, conductivities_w_m_k=tuple(p.k_w_m_k for p in pair),
                    source_ids=tuple(sorted(set(face.source_ids+thermal.source_ids))))
            shared = evaluate_wet_face(actual_face, (gases[i-1], gases[i]), self.gas_ids,
                                       self.storages[0].fluid_template.gas_phases)
            if thermal is not None:
                tl, tr = (F(p.temperature_k) for p in pair)
                kl, kr = (F(p.k_w_m_k) for p in pair)
                resistance = F(face.half_widths_m[0])/kl+F(face.half_widths_m[1])/kr
                conductance = F(face.area_m2)/resistance
                exact_heat = conductance*(tl-tr)
                require(shared.conduction_w != 0 or exact_heat == 0,
                        'nonzero_source_conduction_underflow')
                entropy = F(shared.conduction_w)*(1/tr-1/tl)
                require(entropy >= 0, 'negative_conduction_entropy')
                witness = ConductivityFaceWitness(pair, represented(conductance),
                    shared.conduction_w, F(shared.conduction_w)-exact_heat,
                    represented(entropy))
                faces.append(ConductivityColumnFaceRate(face_id=i, left_cell=i-1, right_cell=i,
                    gas_mol_s=tuple(shared.exchange.net_mol_s[k] for k in self.gas_ids),
                    energy_w=shared.face_energy_w, conduction_w=shared.conduction_w,
                    diffusive_enthalpy_w=shared.diffusive_enthalpy_w,
                    advective_enthalpy_w=shared.advective_enthalpy_w, shared_evaluation=shared,
                    conductivity_witness=witness))
            elif self.liquid_transport is None:
                faces.append(ColumnFaceRate(i, i-1, i, tuple(shared.exchange.net_mol_s[k] for k in self.gas_ids),
                    shared.face_energy_w, shared.conduction_w, shared.diffusive_enthalpy_w,
                    shared.advective_enthalpy_w, shared))
            else:
                config = self.liquid_transport
                try:
                    liquid = liquid_face_exchange(liquids[i-1], liquids[i],
                        left_relation=config.relations[i-1], right_relation=config.relations[i],
                        connection=config.connections[i-1], area_m2=face.area_m2,
                        left_distance_m=face.half_widths_m[0], right_distance_m=face.half_widths_m[1],
                        allow_manufactured=config.allow_manufactured)
                except LiquidTransportDomainError as exc:
                    raise DomainExit(str(exc)) from exc
                donor = liquids[i-1] if liquid.donor == 'left' else liquids[i] if liquid.donor == 'right' else None
                projection = (F(liquid.enthalpy_flow_w)-F(liquid.molar_flow_mol_s)*F(donor.enthalpy_j_mol)
                              if donor is not None else F())
                total = represented(math.fsum((shared.conduction_w, *shared.diffusive_enthalpy_w,
                                               *shared.advective_enthalpy_w, liquid.enthalpy_flow_w)))
                faces.append(LiquidColumnFaceRate(face_id=i, left_cell=i-1, right_cell=i,
                    gas_mol_s=tuple(shared.exchange.net_mol_s[k] for k in self.gas_ids), energy_w=total,
                    conduction_w=shared.conduction_w, diffusive_enthalpy_w=shared.diffusive_enthalpy_w,
                    advective_enthalpy_w=shared.advective_enthalpy_w, shared_evaluation=shared,
                    liquid_mol_s=liquid.molar_flow_mol_s, liquid_enthalpy_w=liquid.enthalpy_flow_w,
                    liquid_enthalpy_projection_w=projection, liquid_exchange=liquid))
                sources.update(liquid.source_ids)
            sources.update(face.source_ids)
        faces.append(ColumnFaceRate(self.cell_count, self.cell_count-1, None, zeros, 0., 0., zeros, zeros, None))
        self._check_states(states)
        if thermal is not None:
            return ConductivitySourceColumnRates(cells=tuple(cells), gas_states=tuple(gases),
                faces=tuple(faces), model_identity=self._identity, source_ids=tuple(sorted(sources)),
                conductivity_points=conductivity_points)
        if self.liquid_transport is None:
            return SourceColumnRates(tuple(cells), tuple(gases), tuple(faces), self._identity, tuple(sorted(sources)))
        return LiquidSourceColumnRates(cells=tuple(cells), gas_states=tuple(gases), faces=tuple(faces),
            model_identity=self._identity, source_ids=tuple(sorted(sources)), liquid_states=liquids)

    def provenance(self):
        self._check()
        result = {'schema': 'source_wet_column_v1', 'model_identity': self._identity,
            'cells': tuple(s.provenance() for s in self.storages),
            'boundary_conditions': self.boundary_conditions, 'cell_widths_m': self.cell_widths_m,
            'face_area_m2': self.face_area_m2, 'internal_face_adjacency': tuple((i, i-1, i) for i in range(1, self.cell_count)),
            'transport_classification': self.transport_classification, 'coefficient_source_ids': self.coefficient_source_ids,
            'material_qualified': False, 'scope': 'fixed source mass, fixed slab, closed boundaries; no exact event or furnace boundary admission'}
        if type(self) is ArlabosseSorptionColumn and self.thermal_provider is not None:
            result.update(thermal_provider=self.thermal_provider.definition(),
                thermal_policy='evaluate every decoded cell at every operator call; no static conduction contribution',
                remaining_transport_classification='manufactured_test_fixture',
                midpoint_thermal_witness='retained on each accepted conductivity face integral')
        if self.liquid_transport is not None:
            result.update(liquid_transport=self.liquid_transport, liquid_boundary_conditions=('no_flux', 'no_flux'),
                liquid_saturation_definition='liquid_volume / available_liquid_plus_gas_volume',
                liquid_pressure_interval_scope='fixed_decoded_temperature', full_inverse_liquid_direction_certified=False,
                liquid_property_and_saturation_uncertainty_propagated=False)
        return result


@dataclass(frozen=True)
class ArlabosseSorptionColumn(SourceWetColumn):
    """Explicit new energy/phase semantics, outside old saved/exact protocols.

    Only the direct midpoint integrator currently admits this conditional
    branch. The original exact class guards reject it before record creation.
    """
    thermal_provider: SeptienConductivity | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class ColumnFaceIntegral:
    face_id: int
    gas_mol: tuple
    energy_j: F
    conduction_j: F
    diffusive_enthalpy_j: tuple
    advective_enthalpy_j: tuple
    energy_decomposition_roundoff_j: F


@dataclass(frozen=True, kw_only=True)
class LiquidColumnFaceIntegral(ColumnFaceIntegral):
    liquid_mol: F
    liquid_enthalpy_j: F
    liquid_enthalpy_projection_j: F


@dataclass(frozen=True, kw_only=True)
class ConductivityColumnFaceIntegral(ColumnFaceIntegral):
    conductivity_witness: ConductivityFaceWitness


def _liquid_integral(face):
    return face.liquid_mol if type(face) is LiquidColumnFaceIntegral else F()


def _liquid_energy_projection(face):
    return face.liquid_enthalpy_projection_j if type(face) is LiquidColumnFaceIntegral else F()


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
        gas = tuple(duration*F(x) for x in face.gas_mol_s)
        decomposition = q-conduction-sum(diff, F())-sum(adv, F())
        if type(face) is ConductivityColumnFaceRate:
            faces.append(ConductivityColumnFaceIntegral(face_id=face.face_id, gas_mol=gas,
                energy_j=q, conduction_j=conduction, diffusive_enthalpy_j=diff,
                advective_enthalpy_j=adv, energy_decomposition_roundoff_j=decomposition,
                conductivity_witness=face.conductivity_witness))
        elif type(face) is LiquidColumnFaceRate:
            liquid_h = duration*F(face.liquid_enthalpy_w)
            faces.append(LiquidColumnFaceIntegral(face_id=face.face_id, gas_mol=gas, energy_j=q,
                conduction_j=conduction, diffusive_enthalpy_j=diff, advective_enthalpy_j=adv,
                energy_decomposition_roundoff_j=decomposition-liquid_h,
                liquid_mol=duration*F(face.liquid_mol_s), liquid_enthalpy_j=liquid_h,
                liquid_enthalpy_projection_j=duration*face.liquid_enthalpy_projection_w))
        else:
            faces.append(ColumnFaceIntegral(face.face_id, gas, q, conduction, diff, adv, decomposition))
    return tuple(faces), tuple(duration*F(c.phase.phase_water_mol_s) for c in rates.cells)


def _advance(column, old, faces, phase):
    """One exact aggregation and one binary64 projection per cell quantity."""
    result, liquid_errors, gas_errors, energy_errors = [], [], [], []
    for i, (storage, state, mode) in enumerate(zip(column.storages, old, column.interface_modes)):
        liquid = F(state.liquid_water_mol)+_liquid_integral(faces[i])-_liquid_integral(faces[i+1])-phase[i]
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
                            energy_roundoff_budget_j=1e-8, inventory_roundoff_budget_mol=1e-12, cancel=None,
                            start_time=None):
    """Bounded midpoint segment; accepted ledger excludes predictor exchanges.

    Budgets bound accumulated projection/decomposition arithmetic, not temporal
    truncation, inverse propagation or physical fit error. Predictor roundoff
    is recorded separately and never added to conserved-inventory balances.
    Exact program knots split nominal steps; accepted ledger count can exceed
    ``steps``. No float conversion is used for stage times or knot ordering.
    """
    from .exact_event_clock import ExactEventTime
    from .programmed_source_wet_column import ProgrammedSourceWetColumn
    require(type(column) in (SourceWetColumn, ArlabosseSorptionColumn, ProgrammedSourceWetColumn)
            and type(steps) is int and steps > 0, 'explicit_column_steps')
    require(start_time is None or type(start_time) is ExactEventTime, 'explicit_exact_column_start_time')
    origin = F() if start_time is None else start_time.seconds
    programmed = type(column) is ProgrammedSourceWetColumn
    duration = F(_binary(duration_s, positive=True))
    h = duration/steps
    wall = _binary(maximum_wall_seconds, positive=True)
    energy_budget = _binary(energy_roundoff_budget_j, positive=True)
    inventory_budget = _binary(inventory_roundoff_budget_mol, positive=True)
    identity = column.model_identity
    start = time.monotonic()
    states, times, observations, ledgers = [initial], [origin], [], []
    attempted = completed = 0
    used_energy = used_inventory = F()

    def evaluate(state, when):
        nonlocal attempted, completed
        if cancel is not None and cancel():
            raise InterruptedError('cancel_requested')
        if time.monotonic()-start > wall:
            raise TimeoutError('wall_budget_exceeded')
        attempted += 1
        output = column.evaluate(state, ExactEventTime(when)) if programmed else column.evaluate(state)
        completed += 1
        if time.monotonic()-start > wall:
            raise TimeoutError('wall_budget_exceeded')
        return output

    status, reason = 'completed', None
    try:
        knots = (tuple(t.seconds for t in column.breakpoints(ExactEventTime(origin), ExactEventTime(origin+duration)))
                 if programmed else ())
        def endpoints():
            position = 0
            for i in range(steps):
                target = origin+(i+1)*h
                while position < len(knots) and knots[position] < target:
                    yield knots[position]
                    position += 1
                if position < len(knots) and knots[position] == target:
                    position += 1
                yield target
        for endpoint in endpoints():
            delta = endpoint-times[-1]
            first = evaluate(states[-1], times[-1])
            predictor_faces, predictor_phase = _integrals(first, delta/2)
            midpoint, predictor_error = _advance(column, states[-1], predictor_faces, predictor_phase)
            middle = evaluate(midpoint, times[-1]+delta/2)
            faces, phase = _integrals(middle, delta)
            # Full step always starts from the prior accepted state.
            new, error = _advance(column, states[-1], faces, phase)
            candidate_energy = used_energy+error.absolute_energy_j+predictor_error.absolute_energy_j
            candidate_energy += sum((abs(f.energy_decomposition_roundoff_j) for f in (*predictor_faces, *faces)), F())
            candidate_energy += sum((abs(_liquid_energy_projection(f)) for f in (*predictor_faces, *faces)), F())
            candidate_inventory = used_inventory+error.absolute_inventory_mol+predictor_error.absolute_inventory_mol
            require(candidate_energy <= F(energy_budget), 'column_energy_roundoff_budget_exceeded')
            require(candidate_inventory <= F(inventory_budget), 'column_inventory_roundoff_budget_exceeded')
            last = evaluate(new, endpoint)
            ledger = (column.step_ledger(delta, faces, phase, error, predictor_error, midpoint, middle) if programmed
                      else ColumnStepLedger(delta, faces, phase, error, predictor_error, midpoint))
            states.append(new)
            times.append(endpoint)
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
