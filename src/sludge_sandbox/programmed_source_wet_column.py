"""Exact furnace program on a fixed source-mass column's outward boundary.

The center is closed. The outer reservoir is prescribed, not a finite gas tank.
Gas enthalpy uses the existing face/donor convention; its interpolation
temperature is not the separately solved solid surface temperature.
Geometry/transport remain manufactured and no material admission is granted.
"""
from dataclasses import dataclass, field, replace
from fractions import Fraction as F
import math

from .boundary_program import BoundaryProgram
from .deforming_solid_storage import _digest
from .exact_boundary_program import ExactBoundaryState, ExactProgramView
from .exact_event_clock import ExactEventTime
from .exchanges import BoundaryHeat, conduction_rate_w
from .gas_transport import GasState, ideal_gas_reservoir
from .integration import DomainExit
from .mass_storage_bridge import require
from .mass_wet_transport import WetFace, evaluate_wet_face, represented
from .programmed_gas_heat import SurfacePolicy
from .source_wet_column import ColumnFaceRate, ColumnStepLedger, SourceColumnRates, SourceWetColumn
from .source_wet_storage import _binary
from .surface_balance import solve_surface_balance


@dataclass(frozen=True)
class SourceSurfaceObservation:
    temperature_k: float
    heat: BoundaryHeat
    conductive_into_cell_w: float
    balance_residual_w: float
    balance_limit_w: float
    iterations: int
    status: str


@dataclass(frozen=True, kw_only=True)
class ProgrammedSourceRates(SourceColumnRates):
    boundary: ExactBoundaryState
    reservoir: GasState
    surface: SourceSurfaceObservation
    closed_base_identity: str


@dataclass(frozen=True)
class SourceBoundaryIntegral:
    """Accepted midpoint boundary terms; surface residual is not a second heat."""
    boundary: ExactBoundaryState
    surface: SourceSurfaceObservation
    convective_in_j: F
    radiative_in_j: F
    conductive_into_cell_j: F
    exact_surface_balance_defect_j: F
    reported_surface_residual_j: F
    surface_balance_limit_j: F


@dataclass(frozen=True, kw_only=True)
class ProgrammedColumnStepLedger(ColumnStepLedger):
    boundary_integral: SourceBoundaryIntegral


@dataclass(frozen=True)
class ProgrammedSourceWetColumn:
    base: SourceWetColumn
    program: ExactProgramView
    outer_conductivity_w_m_k: float
    convection_w_m2_k: float
    emissivity: float
    stefan_boltzmann_w_m2_k4: float
    gas_diffusivities_m2_s: tuple
    gas_permeability_m2: float
    gas_viscosity_pa_s: float
    coefficient_source_ids: tuple
    surface_policy: SurfacePolicy
    coefficient_classification: str = 'manufactured_test_fixture'
    _identity: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, '_identity', self.binding())

    @property
    def storages(self): return self.base.storages
    @property
    def interface_modes(self): return self.base.interface_modes
    @property
    def gas_ids(self): return self.base.gas_ids
    @property
    def cell_count(self): return self.base.cell_count

    def binding(self):
        require(type(self.base) is SourceWetColumn, 'actual_source_column_required')
        base_identity = self.base.model_identity
        require(type(self.program) is ExactProgramView and type(self.program.program) is BoundaryProgram,
                'exact_boundary_program_required')
        require(self.program.program.species_order == self.gas_ids, 'complete_ordered_boundary_gases_required')
        require(type(self.surface_policy) is SurfacePolicy, 'explicit_surface_policy_required')
        require(self.coefficient_classification == 'manufactured_test_fixture', 'source_boundary_material_not_admitted')
        require(type(self.coefficient_source_ids) is tuple and bool(self.coefficient_source_ids)
                and len(set(self.coefficient_source_ids)) == len(self.coefficient_source_ids)
                and all(type(s) is str and s and s == s.strip() for s in self.coefficient_source_ids),
                'unique_boundary_coefficient_sources')
        for value in (self.outer_conductivity_w_m_k, self.convection_w_m2_k, self.emissivity, self.gas_permeability_m2):
            require(_binary(value) >= 0, 'nonnegative_boundary_coefficient')
        require(self.emissivity <= 1, 'emissivity_exceeds_one')
        _binary(self.stefan_boltzmann_w_m2_k4, positive=True)
        _binary(self.gas_viscosity_pa_s, positive=True)
        require(type(self.gas_diffusivities_m2_s) is tuple and len(self.gas_diffusivities_m2_s) == len(self.gas_ids),
                'complete_boundary_diffusivities')
        for value in self.gas_diffusivities_m2_s:
            require(_binary(value) >= 0, 'nonnegative_boundary_diffusivity')
        # All program gas temperatures must be supported even before a donor
        # changes. Radiation temperature is not a material storage temperature.
        for phase in self.storages[0].fluid_template.gas_phases.values():
            low, high = phase.temperature_range_k
            require(all(low <= t <= high for t in self.program.program.gas_temperature_k),
                    'boundary_gas_temperature_outside_caloric_domain')
        face = self._gas_face()
        return _digest(('programmed_source_wet_column_v1', base_identity, self.program,
            self.outer_conductivity_w_m_k, self.convection_w_m2_k, self.emissivity,
            self.stefan_boltzmann_w_m2_k4, face, self.surface_policy,
            self.coefficient_classification, self.coefficient_source_ids))

    def _check(self):
        require(self.binding() == self._identity, 'programmed_source_column_content_changed')

    @property
    def model_identity(self):
        self._check()
        return self._identity

    def _gas_face(self):
        # Two numerical quarter distances give the actual outer half-cell
        # distance. Zero k removes a duplicate gas-to-cell Fourier heat path.
        quarter = _binary(F(self.base.cell_widths_m[-1])/4, positive=True)
        return WetFace(self.base.face_area_m2, (quarter, quarter), (0., 0.),
            self.gas_diffusivities_m2_s, self.gas_permeability_m2,
            self.gas_viscosity_pa_s, self.coefficient_source_ids)

    def breakpoints(self, start, end):
        self._check()
        try:
            return self.program.breakpoints(start, end)
        except ValueError as exc:
            if str(exc) == 'time_outside_program_domain': raise DomainExit(str(exc)) from exc
            raise

    def evaluate(self, states, time: ExactEventTime):
        self._check()
        require(type(time) is ExactEventTime, 'exact_boundary_evaluation_time_required')
        try:
            boundary = self.program.at(time)
        except ValueError as exc:
            if str(exc) == 'time_outside_program_domain': raise DomainExit(str(exc)) from exc
            raise
        base = self.base.evaluate(states)
        phases = self.storages[0].fluid_template.gas_phases
        reservoir = ideal_gas_reservoir(pressure_pa=boundary.total_pressure_pa,
            temperature_k=boundary.gas_temperature_k, mole_fractions=boundary.mole_fractions,
            molar_masses_kg_mol={k: phases[k].molar_mass_kg_mol for k in self.gas_ids},
            gas_constant_j_mol_k=self.base.chemical.gas_constant_j_mol_k)
        cell_temperature = base.gas_states[-1].temperature_k
        face = self._gas_face()
        def into(surface_temperature):
            return conduction_rate_w(surface_temperature, cell_temperature, area_m2=face.area_m2,
                left_distance_m=face.half_widths_m[0], right_distance_m=face.half_widths_m[1],
                left_conductivity_w_m_k=self.outer_conductivity_w_m_k,
                right_conductivity_w_m_k=self.outer_conductivity_w_m_k)
        surface = SourceSurfaceObservation(*solve_surface_balance(
            cell_temperature_k=cell_temperature, gas_temperature_k=boundary.gas_temperature_k,
            radiation_temperature_k=boundary.radiation_temperature_k, area_m2=face.area_m2,
            convection_w_m2_k=self.convection_w_m2_k, emissivity=self.emissivity,
            stefan_boltzmann_w_m2_k4=self.stefan_boltzmann_w_m2_k4, policy=self.surface_policy,
            conductive_into_cell=into, zero_conductivity=self.outer_conductivity_w_m_k == 0,
            error_type=ValueError))
        exchange = evaluate_wet_face(face, (base.gas_states[-1], reservoir), self.gas_ids, phases)
        outward_heat = -surface.conductive_into_cell_w
        outward_energy = represented(math.fsum((*exchange.diffusive_enthalpy_w,
                                                *exchange.advective_enthalpy_w, outward_heat)))
        outer = ColumnFaceRate(self.cell_count, self.cell_count-1, None,
            tuple(exchange.exchange.net_mol_s[k] for k in self.gas_ids), outward_energy, outward_heat,
            exchange.diffusive_enthalpy_w, exchange.advective_enthalpy_w, exchange)
        self._check()
        return ProgrammedSourceRates(cells=base.cells, gas_states=base.gas_states,
            faces=(*base.faces[:-1], outer), model_identity=self._identity,
            source_ids=tuple(sorted(set(base.source_ids+self.program.program.identity.source_ids+self.coefficient_source_ids))),
            boundary=boundary, reservoir=reservoir, surface=surface, closed_base_identity=base.model_identity)

    def step_ledger(self, duration, faces, phase, error, predictor_error, midpoint, middle):
        surface = middle.surface
        convection = duration*F(surface.heat.convective_in_w)
        radiation = duration*F(surface.heat.radiative_in_w)
        into = duration*F(surface.conductive_into_cell_w)
        boundary = SourceBoundaryIntegral(middle.boundary, surface, convection, radiation, into,
            into-convection-radiation, duration*F(surface.balance_residual_w), duration*F(surface.balance_limit_w))
        return ProgrammedColumnStepLedger(duration_s=duration, faces=faces, phase_water_mol=phase,
            roundoff=error, predictor_roundoff=predictor_error, midpoint_states=midpoint, boundary_integral=boundary)

    def with_depleted_cells(self, states, cell_indices):
        self._check()
        return replace(self, base=self.base.with_depleted_cells(states, cell_indices))

    def provenance(self):
        self._check()
        return {'schema': 'programmed_source_wet_column_v1', 'model_identity': self._identity,
            'base': self.base.provenance(), 'program': self.program,
            'boundary_conditions': ('closed_no_flux', 'prescribed_infinite_gas_reservoir_and_surface_film'),
            'gas_face_temperature_policy': 'linear_cell_reservoir_interpolation_not_solid_surface_temperature',
            'energy_boundary': 'outward_gas_enthalpy_minus_surface_to_cell_conduction',
            'coefficient_source_ids': self.coefficient_source_ids, 'coefficient_classification': self.coefficient_classification,
            'material_qualified': False, 'scope': 'fixed geometry and dry mass; no automatic depletion event or full firing domain'}
