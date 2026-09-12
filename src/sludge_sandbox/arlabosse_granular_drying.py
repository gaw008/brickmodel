"""Source granular contact-drying law with an explicit isothermal heat budget.

This is a conditional preprocessing experiment, not internal brick transport.
The mass ODE is solved analytically; moisture sampling only selects report
locations. Total H is updated from integrated heat and signed outgoing vapor H,
then inverted through the common wet model. Temperature is never overwritten.
"""
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import time

from .arlabosse_wet_thermo import ArlabosseWetThermodynamics

SOURCE_PATH = 'data/sandbox/research/arlabosse-granular-drying-v1/source.json'
SOURCE_SHA256 = '7c29b68de800ba52c7dac2565d5d4edf8ddaf259da8aa6a6c5aef66f430b3c9e'


class GranularDryingError(ValueError):
    """Invalid experiment, changed source, or unresolved numerical evaluation."""


def _number(value, name, low, high=math.inf, *, strict_low=False):
    if type(value) not in (int, float):
        raise GranularDryingError('finite_numeric_input_required_' + name)
    try:
        value = float(value)
    except OverflowError as exc:
        raise GranularDryingError('finite_numeric_input_required_' + name) from exc
    if not math.isfinite(value) or not low <= value <= high or (strict_low and value == low):
        raise GranularDryingError('outside_declared_domain_' + name)
    return value


def _finite(value):
    if not math.isfinite(value):
        raise GranularDryingError('unrepresentable_model_result')
    return value


def _positive(value):
    if _finite(value) <= 0:
        raise GranularDryingError('unrepresentable_strictly_positive_quantity')
    return value


def _load_source(root):
    root = Path(root).resolve()
    path = root / SOURCE_PATH
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise GranularDryingError('granular_source_definition_changed')
    source = json.loads(raw)
    for asset in [*source['assets'], source['thermal_upstream']]:
        target = (root / asset['path']).resolve()
        if not target.is_relative_to(root):
            raise GranularDryingError('source_asset_outside_repository')
        if hashlib.sha256(target.read_bytes()).hexdigest() != asset['sha256']:
            raise GranularDryingError('source_asset_changed')
    return source


class ArlabosseGranularFlux:
    """Published aW+b, including the intercept omitted by printed Eq6."""

    def __init__(self, repository_root):
        self.repository_root = Path(repository_root).resolve()
        self.definition()

    def definition(self):
        return _load_source(self.repository_root)

    def _coefficients(self):
        source = self.definition()
        return tuple(float(source['parameters'][name]['value']) for name in ('a', 'b'))

    def flux_kg_water_m2_h(self, moisture):
        w = _number(moisture, 'source_moisture', .05, .32)
        a, b = self._coefficients()
        return _finite(a*w+b)

    def elapsed_seconds(self, initial_moisture, final_moisture, *, dry_mass_kg, contact_area_m2):
        wi = _number(initial_moisture, 'initial_source_moisture', .05, .32)
        wf = _number(final_moisture, 'final_source_moisture', .05, wi)
        md = _number(dry_mass_kg, 'dry_mass_kg', 0., strict_low=True)
        area = _number(contact_area_m2, 'contact_area_m2', 0., strict_low=True)
        a, b = self._coefficients()
        log_ratio = math.log1p(a*(wi-wf)/(a*wf+b))
        # Form the final scale before binary64 conversion; intermediate md*3600
        # may overflow even when md/area and the final clock are representable.
        try:
            result = _finite(float(Fraction(3600)*Fraction(md)*Fraction(log_ratio)/
                                   (Fraction(area)*Fraction(a))))
        except OverflowError as exc:
            raise GranularDryingError('unrepresentable_model_result') from exc
        if wi > wf and result <= 0:
            raise GranularDryingError('unresolvable_positive_drying_time')
        return result


def run_isothermal_drying(repository_root, water_directory, *, dry_mass_kg,
                          contact_area_m2, temperature_k, ambient_vapor_pressure_pa,
                          initial_moisture, final_moisture, intervals=16,
                          wall_seconds=30., temperature_tolerance_k=1e-6,
                          energy_tolerance_j=1e-5, water_tolerance_kg=1e-12, cancel=None):
    """Return actual accepted observations, including a prefix on known failure.

    Area, mass, material temperature and externally maintained vapor pressure
    are explicit design inputs. Source rate sensitivity to that environment is
    unknown. A low enough boundary vapor pressure is necessary, not sufficient,
    to validate applying the empirical rate at the chosen conditions.
    """
    md = _number(dry_mass_kg, 'dry_mass_kg', 0., strict_low=True)
    area = _number(contact_area_m2, 'contact_area_m2', 0., strict_low=True)
    temp = _number(temperature_k, 'temperature_k', 308.15, 368.15)
    pv = _number(ambient_vapor_pressure_pa, 'ambient_vapor_pressure_pa', 0., 100000.)
    wi = _number(initial_moisture, 'initial_moisture', .15, .32)
    wf = _number(final_moisture, 'final_moisture', .15, .32)
    if wf >= wi:
        raise GranularDryingError('strictly_decreasing_moisture_required')
    if type(intervals) is not int or not 1 <= intervals <= 128:
        raise GranularDryingError('output_intervals_must_be_integer_1_to_128')
    limit = _number(wall_seconds, 'wall_seconds', 0., strict_low=True)
    t_limit = _number(temperature_tolerance_k, 'temperature_tolerance_k', 0., strict_low=True)
    e_limit = _number(energy_tolerance_j, 'energy_tolerance_j', 0., strict_low=True)
    w_limit = _number(water_tolerance_kg, 'water_tolerance_kg', 0., strict_low=True)
    if cancel is not None and not callable(cancel):
        raise GranularDryingError('cancel_must_be_callable')
    inputs = dict(dry_mass_kg=md, contact_area_m2=area, temperature_k=temp,
                  ambient_vapor_pressure_pa=pv, initial_moisture=wi, final_moisture=wf,
                  intervals=intervals, wall_seconds=limit)
    result = dict(schema='arlabosse_granular_drying_run_v1', status='running', reason=None,
                  inputs=inputs, observations=[], pending_observation=None,
                  source=None, thermodynamic_definition=None,
                  numerical_policy=dict(temperature_tolerance_k=t_limit, energy_tolerance_j=e_limit,
                      water_tolerance_kg=w_limit, inverse_temperature_tolerance_k=1e-10,
                      inverse_maximum_iterations=80, classification='numerical_policy',
                      scope='absolute_arithmetic_acceptance_not_experimental_uncertainty'),
                  method='analytic_mass_and_exact_isothermal_heat_increments_with_enthalpy_inverse',
                  spatial_model=False, source_protocol_temperature_and_gas_match=None,
                  rate_condition_transfer_model_error=None, experimental_uncertainty=None,
                  material_qualified=False, training_eligible=False, full_firing_cycle=False,
                  qualification='conditional_contact_drying_exploration_not_validated_drying_time',
                  numerical_scope='output_sampling_is_not_an_ODE_time_step_convergence_test')
    started = time.monotonic()

    def stop_requested():
        if time.monotonic()-started >= limit:
            result.update(status='time_budget_exceeded', reason='wall_seconds_exhausted')
            return True
        if cancel is not None:
            requested = cancel()
            if type(requested) is not bool:
                raise GranularDryingError('cancel_must_return_bool')
            if requested:
                result.update(status='cancelled', reason='cancel_requested_between_observations')
                return True
        return False

    try:
        if stop_requested():
            return result
        law = ArlabosseGranularFlux(repository_root)
        result['source'] = law.definition()
        thermal = ArlabosseWetThermodynamics(repository_root, water_directory)
        result['thermodynamic_definition'] = thermal.definition()
        # At fixed T the model's admitted activity increases with W; the driest
        # endpoint is the minimum equilibrium vapor pressure on this path.
        driest = thermal.evaluate(temp, wf)
        if pv >= driest.model_equilibrium_vapor_pressure_pa:
            raise GranularDryingError('vapor_boundary_does_not_support_evaporation_over_full_path')
        initial = thermal.evaluate(temp, wi)
        result['initial'] = initial.to_record()
        _positive(md*wi)
        _positive(md*wf)
        initial_h = _finite(md*initial.specific_enthalpy_j_kg_dry)
        result['initial_total_enthalpy_j'] = initial_h
        heat_steps, vapor_steps, water_steps = [], [], []
        previous_w, previous_t, previous_target, previous_recovered = wi, -1., initial_h, initial_h
        for i in range(intervals+1):
            if stop_requested():
                return result
            # W is the chosen parameter of the analytic trajectory. Explicit
            # endpoints are requested coordinates, not clipped ODE states.
            w = wi if i == 0 else wf if i == intervals else wi+(wf-wi)*(i/intervals)
            if i and w >= previous_w:
                raise GranularDryingError('unresolvable_decreasing_output_moisture')
            when = law.elapsed_seconds(wi, w, dry_mass_kg=md, contact_area_m2=area)
            if when <= previous_t:
                raise GranularDryingError('unresolvable_increasing_output_time')
            result['pending_observation'] = dict(index=i, time_s=when, moisture_kg_water_kg_dry=w)
            step_q = step_vapor = step_water = 0.
            if i:
                heat = thermal.isothermal_drying_heat(temp, previous_w, w, dry_mass_kg=md)
                step_q, step_vapor, step_water = heat.heat_j, heat.vapor_carried_enthalpy_j, heat.removed_water_kg
                result['pending_observation'].update(step_heat_j=step_q,
                    step_vapor_enthalpy_j=step_vapor, step_water_out_kg=step_water)
                _positive(step_water)
                _positive(step_q)
            heat_steps.append(step_q)
            vapor_steps.append(step_vapor)
            water_steps.append(step_water)
            q, hout, mout = map(math.fsum, (heat_steps, vapor_steps, water_steps))
            target = _finite(math.fsum((initial_h, q, -hout)))
            result['pending_observation'] = dict(index=i, time_s=when, moisture_kg_water_kg_dry=w,
                target_total_enthalpy_j=target, step_heat_j=step_q, step_vapor_enthalpy_j=step_vapor,
                step_water_out_kg=step_water, cumulative_net_heat_j=q,
                cumulative_vapor_enthalpy_j=hout, cumulative_water_out_kg=mout)
            inverse = thermal.inverse_enthalpy(target, dry_mass_kg=md, moisture=w,
                                               temperature_tolerance_k=1e-10, maximum_iterations=80)
            recovered = _finite(md*inverse.state.specific_enthalpy_j_kg_dry)
            result['pending_observation'].update(inverse=inverse.to_record(),
                                                 recovered_total_enthalpy_j=recovered)
            at_control = thermal.evaluate(temp, w)
            flow = float(Fraction(area)*Fraction(law.flux_kg_water_m2_h(w))/3600)
            result['pending_observation']['water_out_kg_s'] = flow
            _positive(flow)
            power = flow*at_control.total_desorption_heat_j_kg_water
            result['pending_observation']['required_net_heat_w'] = power if math.isfinite(power) else None
            if not math.isfinite(power):
                result['pending_observation']['invalid_computed_values'] = {'required_net_heat_w': repr(power)}
            _positive(power)
            row = dict(index=i, time_s=when, moisture_kg_water_kg_dry=w,
                       water_out_kg_s=flow,
                       required_net_heat_w=power,
                       step_heat_j=step_q, step_vapor_enthalpy_j=step_vapor,
                       step_water_out_kg=step_water, cumulative_net_heat_j=q,
                       cumulative_vapor_enthalpy_j=hout, cumulative_water_out_kg=mout,
                       target_total_enthalpy_j=target, recovered_total_enthalpy_j=recovered,
                       inverse=inverse.to_record(),
                       recovered_temperature_difference_k=inverse.state.temperature_k-temp,
                       step_energy_residual_j=math.fsum((recovered, -previous_recovered, -step_q, step_vapor)),
                       target_step_energy_residual_j=math.fsum((target, -previous_target, -step_q, step_vapor)),
                       open_energy_residual_j=math.fsum((recovered, -initial_h, -q, hout)),
                       water_balance_residual_kg=math.fsum((md*w, mout, -md*wi)))
            result['pending_observation'] = row
            if not all(math.isfinite(v) for v in row.values() if type(v) is float):
                raise GranularDryingError('unrepresentable_observation')
            if abs(row['recovered_temperature_difference_k']) > t_limit:
                raise GranularDryingError('numerical_gate_isothermal_temperature')
            if max(abs(row[key]) for key in ('step_energy_residual_j',
                    'target_step_energy_residual_j', 'open_energy_residual_j')) > e_limit:
                raise GranularDryingError('numerical_gate_energy_balance')
            if abs(row['water_balance_residual_kg']) > w_limit:
                raise GranularDryingError('numerical_gate_water_balance')
            result['observations'].append(row)
            result['pending_observation'] = None
            previous_w, previous_t, previous_target, previous_recovered = w, when, target, recovered
        if stop_requested():
            return result
        law.definition()
        thermal.definition()
        if stop_requested():
            return result
        result.update(status='completed', reason='requested_moisture_endpoint_reached')
    except (ValueError, ArithmeticError, OSError) as exc:
        result.update(status='failed', reason=str(exc), error_type=type(exc).__name__)
    finally:
        result['elapsed_seconds'] = time.monotonic()-started
        if result['status'] == 'completed' and result['elapsed_seconds'] >= limit:
            result.update(status='time_budget_exceeded', reason='wall_seconds_exhausted')
    return result
