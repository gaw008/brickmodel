"""Dynamic reservoir and series surface-film boundary for the rigid gas model.

No material coefficients are supplied here. Convection/radiation are balanced
against the actual outer half-cell conduction before assembling shared rates.
"""
from dataclasses import dataclass, replace
import math
from numbers import Real

from .boundary_program import BoundaryProgram, BoundaryProgramError, BoundaryState
from .exchanges import BoundaryHeat, ExchangeError, boundary_heat, conduction_rate_w
from .gas_heat_model import GasHeatModel
from .gas_transport import GasState, GasTransportError, ideal_gas_reservoir
from .integration import ConservedState, DomainExit, IntegrationError, Rates


class ProgrammedGasHeatError(IntegrationError):
    """Invalid configuration or unresolved numerical boundary balance."""


def _number(value, name, *, positive=False):
    try:
        value = float(value) if isinstance(value, Real) and not isinstance(value, bool) else math.nan
    except (ValueError, OverflowError):
        value = math.nan
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ProgrammedGasHeatError(f'invalid_{name}')
    return value


def _label(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


@dataclass(frozen=True, kw_only=True)
class SurfacePolicy:
    absolute_residual_w: float
    relative_residual: float
    maximum_iterations: int

    def __post_init__(self):
        for name in ('absolute_residual_w', 'relative_residual'):
            object.__setattr__(self, name, _number(getattr(self, name), name, positive=True))
        if type(self.maximum_iterations) is not int or self.maximum_iterations < 1:
            raise ProgrammedGasHeatError('invalid_maximum_iterations')


@dataclass(frozen=True, kw_only=True)
class ProgrammedEvaluation:
    rates: Rates
    boundary: BoundaryState
    reservoir: GasState
    surface_temperature_k: float
    heat: BoundaryHeat
    conductive_into_cell_w: float
    surface_balance_residual_w: float
    surface_balance_limit_w: float
    surface_iterations: int
    surface_status: str


@dataclass(frozen=True, kw_only=True)
class ProgrammedGasHeat:
    base_model: GasHeatModel
    program: BoundaryProgram
    convection_w_m2_k: float
    emissivity: float
    stefan_boltzmann_w_m2_k4: float
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    coefficient_source_ids: tuple[str, ...]
    surface_policy: SurfacePolicy
    allow_manufactured: bool = False

    def __post_init__(self):
        if not isinstance(self.base_model, GasHeatModel) or not isinstance(self.program, BoundaryProgram):
            raise ProgrammedGasHeatError('validated_base_and_program_required')
        if not isinstance(self.surface_policy, SurfacePolicy):
            raise ProgrammedGasHeatError('explicit_surface_policy_required')
        base = self.base_model
        if base.outer_reservoir is not None or base.outer_surface_temperature_k is not None:
            raise ProgrammedGasHeatError('existing_outer_boundary_would_be_duplicated')
        if base.species_order != self.program.species_order:
            raise ProgrammedGasHeatError('complete_ordered_boundary_species_must_match_model')
        if type(self.allow_manufactured) is not bool:
            raise ProgrammedGasHeatError('invalid_manufactured_gate')
        if self.coefficient_classification not in ('manufactured', 'literature_candidate'):
            raise ProgrammedGasHeatError('invalid_coefficient_classification')
        manufactured = (base.coefficient_classification == 'manufactured'
                        or base.thermochemistry.contains_manufactured_models
                        or (base.reaction_network is not None and base.reaction_network.contains_manufactured)
                        or self.coefficient_classification == 'manufactured')
        if manufactured and not self.allow_manufactured:
            raise ProgrammedGasHeatError('manufactured_requires_explicit_test_mode')
        if not _label(self.coefficient_set_id) or not _label(self.coefficient_version):
            raise ProgrammedGasHeatError('coefficient_identity_required')
        sources = self.coefficient_source_ids
        if (not isinstance(sources, (tuple, list)) or not sources
                or any(not _label(value) for value in sources) or len(set(sources)) != len(sources)):
            raise ProgrammedGasHeatError('unique_coefficient_sources_required')
        object.__setattr__(self, 'coefficient_source_ids', tuple(sources))
        for name in ('convection_w_m2_k', 'emissivity', 'stefan_boltzmann_w_m2_k4'):
            object.__setattr__(self, name, _number(getattr(self, name), name,
                                                 positive=name == 'stefan_boltzmann_w_m2_k4'))
        if self.emissivity > 1:
            raise ProgrammedGasHeatError('emissivity_exceeds_one')

    @property
    def source_ids(self):
        return tuple(sorted(set(self.base_model.source_ids + self.program.identity.source_ids
                                + self.coefficient_source_ids)))

    @property
    def scientific_status(self):
        return 'programmed_rigid_gas_boundary_not_material_qualified'

    @property
    def material_qualified(self):
        return False

    def breakpoints_s(self, start_s, end_s):
        return self.program.breakpoints_s(start_s, end_s)

    def _surface(self, cell_temperature, boundary):
        base = self.base_model
        policy = self.surface_policy

        def balance(surface):
            heat = boundary_heat(
                surface_temperature_k=surface, gas_temperature_k=boundary.gas_temperature_k,
                radiation_temperature_k=boundary.radiation_temperature_k, area_m2=base.face_area_m2,
                convection_w_m2_k=self.convection_w_m2_k, emissivity=self.emissivity,
                stefan_boltzmann_w_m2_k4=self.stefan_boltzmann_w_m2_k4)
            # Identical half-cell resistance as base model, with reversed sign.
            into = conduction_rate_w(
                surface, cell_temperature, area_m2=base.face_area_m2,
                left_distance_m=base.cell_widths_m[-1]/4, right_distance_m=base.cell_widths_m[-1]/4,
                left_conductivity_w_m_k=base.conductivities_w_m_k[-1],
                right_conductivity_w_m_k=base.conductivities_w_m_k[-1])
            residual = math.fsum((into, -heat.convective_in_w, -heat.radiative_in_w))
            scale = max(abs(into), abs(heat.convective_in_w), abs(heat.radiative_in_w))
            limit = policy.absolute_residual_w + policy.relative_residual*scale
            if not math.isfinite(residual) or not math.isfinite(limit):
                raise ProgrammedGasHeatError('nonfinite_surface_balance')
            return heat, into, residual, limit

        if self.convection_w_m2_k == 0 and self.emissivity == 0:
            return cell_temperature, *balance(cell_temperature), 0, (
                'insulated_surface_undetermined' if base.conductivities_w_m_k[-1] == 0 else 'adiabatic')
        low = min(cell_temperature, boundary.gas_temperature_k, boundary.radiation_temperature_k)
        high = max(cell_temperature, boundary.gas_temperature_k, boundary.radiation_temperature_k)
        for endpoint in (low, high):
            values = balance(endpoint)
            if abs(values[2]) <= values[3]:
                return endpoint, *values, 0, 'balanced'
        for iteration in range(1, policy.maximum_iterations+1):
            middle = low/2 + high/2
            if middle == low or middle == high:
                raise ProgrammedGasHeatError('surface_root_unresolvable_in_float')
            values = balance(middle)
            if abs(values[2]) <= values[3]:
                return middle, *values, iteration, 'balanced'
            if values[2] < 0:
                low = middle
            else:
                high = middle
        raise ProgrammedGasHeatError('surface_iteration_limit')

    def evaluate(self, state: ConservedState, time_s: float) -> ProgrammedEvaluation:
        # Check the original caloric signature before replace() copies wrappers.
        temperatures = self.base_model.temperatures_k(state)
        try:
            boundary = self.program.at(time_s)
        except BoundaryProgramError as exc:
            if str(exc) == 'time_outside_program_domain':
                raise DomainExit(str(exc)) from exc
            raise ProgrammedGasHeatError(str(exc)) from exc
        try:
            reservoir = ideal_gas_reservoir(
                pressure_pa=boundary.total_pressure_pa, temperature_k=boundary.gas_temperature_k,
                mole_fractions=boundary.mole_fractions,
                molar_masses_kg_mol=self.base_model.molar_masses_kg_mol,
                gas_constant_j_mol_k=self.base_model.thermochemistry.gas_constant_j_mol_k)
            surface, heat, into, residual, limit, iterations, status = self._surface(temperatures[-1], boundary)
            operator = replace(self.base_model, outer_reservoir=reservoir,
                               outer_reservoir_source_ids=self.program.identity.source_ids,
                               outer_surface_temperature_k=surface,
                               outer_heat_source_ids=tuple(sorted(set(self.program.identity.source_ids
                                                                    + self.coefficient_source_ids))))
            rates = operator(state, time_s)
        except (GasTransportError, ExchangeError, OverflowError) as exc:
            raise ProgrammedGasHeatError(str(exc)) from exc
        return ProgrammedEvaluation(rates=rates, boundary=boundary, reservoir=reservoir,
                                    surface_temperature_k=surface, heat=heat, conductive_into_cell_w=into,
                                    surface_balance_residual_w=residual, surface_balance_limit_w=limit,
                                    surface_iterations=iterations, surface_status=status)

    def __call__(self, state: ConservedState, time_s: float) -> Rates:
        return self.evaluate(state, time_s).rates
