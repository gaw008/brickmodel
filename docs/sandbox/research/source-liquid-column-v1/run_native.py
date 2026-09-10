"""Prepared bounded HEOS liquid-column run; no EOS at import/config stage."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
INNER_SECONDS = 45.
OUTER_SECONDS = 60.
DURATION = F(1, 1024)


def load_example(root):
    path = Path(root)/'docs/sandbox/research/programmed-source-column-v1/run_native.py'
    spec = importlib.util.spec_from_file_location('frozen_programmed_source_example', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configuration():
    from sludge_sandbox.liquid_transport import SaturationMobilityTable, LiquidConnection
    from sludge_sandbox.solid_fluid_heat import LiquidTransportConfig
    raw = (HERE/'mobility.json').read_bytes()
    data = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    kwargs = {k: tuple(data[k]) for k in ('saturation_knots', 'permeability_m2',
        'relative_permeability', 'viscosity_pa_s', 'temperature_range_k', 'pressure_range_pa', 'source_ids')}
    kwargs.update({k: data[k] for k in ('model_id', 'version', 'classification', 'relation_kind')})
    table = SaturationMobilityTable(**kwargs, source_asset_sha256=(('mobility.json', digest),))
    links = tuple(LiquidConnection(status='connected',
        connection_id='manufactured:source-column-native-liquid-link-'+str(i), version='1',
        classification='manufactured_test_fixture',
        source_ids=('manufactured:source-column-native-liquid-links',)) for i in range(2))
    return LiquidTransportConfig(relations=(table,)*3, connections=links, allow_manufactured=True), digest


def construct(root):
    example = load_example(root)
    original, initial, serialize = example.construct(root)
    config, digest = configuration()
    model = replace(original, base=replace(original.base, liquid_transport=config))
    return model, initial, serialize, digest


def liquid(face):
    return F(getattr(face, 'liquid_mol', 0))


def liquid_h(face):
    return F(getattr(face, 'liquid_enthalpy_j', 0))


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def audit_observation(observation):
    checks = 0
    require(len(observation.liquid_states) == 3, 'three_actual_liquid_states')
    require(not observation.full_inverse_liquid_direction_certified, 'no_full_inverse_certificate')
    require(observation.liquid_pressure_interval_scope == 'fixed_decoded_temperature', 'pressure_scope')
    for face in (observation.faces[0], observation.faces[-1]):
        require(getattr(face, 'liquid_mol_s', 0.) == 0., 'closed_liquid_boundary')
    checks += 5
    for i, face in enumerate(observation.faces[1:-1]):
        left, right = observation.liquid_states[i:i+2]
        donor = left if face.liquid_exchange.donor == 'left' else right if face.liquid_exchange.donor == 'right' else None
        expected = (F(face.liquid_enthalpy_w)-F(face.liquid_mol_s)*F(donor.enthalpy_j_mol)) if donor else F()
        require(face.liquid_enthalpy_projection_w == expected, 'actual_donor_enthalpy_projection')
        require(face.energy_w == math.fsum((face.conduction_w, *face.diffusive_enthalpy_w,
            *face.advective_enthalpy_w, face.liquid_enthalpy_w)), 'face_energy_decomposition')
        require(face.liquid_mol_s != 0., 'active_internal_liquid_demonstration')
        checks += 3
    return checks


def audit(run, captures):
    """Independent exact local/global ledger; includes liquid and donor energy."""
    require(len(captures) == run.evaluations_completed, 'captured_completed_evaluations')
    checks = sum(audit_observation(c['observation']) for c in captures)
    for index, (old, new, ledger) in enumerate(zip(run.states, run.states[1:], run.ledgers)):
        first, middle, last = captures[3*index:3*index+3]
        require(first['states'] == old and middle['states'] == ledger.midpoint_states and last['states'] == new,
                'actual_integrator_stage_states')
        dt = ledger.duration_s
        for boundary in (ledger.faces[0], ledger.faces[-1]):
            require(liquid(boundary) == 0 and liquid_h(boundary) == 0, 'boundary_liquid_integral_zero')
        for j, face in enumerate(ledger.faces):
            rate = middle['observation'].faces[j]
            require(face.energy_j == dt*F(rate.energy_w), 'midpoint_total_face_energy')
            require(face.energy_decomposition_roundoff_j == face.energy_j-face.conduction_j
                -sum(face.diffusive_enthalpy_j, F())-sum(face.advective_enthalpy_j, F())-liquid_h(face),
                'physical_energy_plus_explicit_decomposition_roundoff')
            if j not in (0, len(ledger.faces)-1):
                require(face.liquid_mol == dt*F(rate.liquid_mol_s), 'midpoint_liquid_integral')
                require(face.liquid_enthalpy_j == dt*F(rate.liquid_enthalpy_w), 'midpoint_liquid_enthalpy_integral')
                require(face.liquid_enthalpy_projection_j == dt*rate.liquid_enthalpy_projection_w,
                        'midpoint_liquid_enthalpy_projection')
                donor_index = j-1 if rate.liquid_exchange.donor == 'left' else j
                donor_h = F(middle['observation'].liquid_states[donor_index].enthalpy_j_mol)
                require(face.liquid_enthalpy_j == face.liquid_mol*donor_h+face.liquid_enthalpy_projection_j,
                        'independent_donor_energy_integral')
                checks += 4
            checks += 2
        for i in range(len(old)):
            a, b = ledger.faces[i:i+2]
            require(old[i].solid_mass_kg == new[i].solid_mass_kg, 'fixed_source_dry_mass')
            require(F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol) == liquid(a)-liquid(b)
                -ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i], 'cell_liquid_inventory')
            require(F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == a.energy_j-b.energy_j
                +ledger.roundoff.energy_j[i], 'cell_total_U')
            for k in range(3):
                require(F(new[i].gas_amounts_mol[k])-F(old[i].gas_amounts_mol[k]) == a.gas_mol[k]-b.gas_mol[k]
                    +(ledger.phase_water_mol[i] if k == 2 else 0)+ledger.roundoff.gas_mol[i][k], 'cell_gas_inventory')
                checks += 1
            old_water = F(old[i].liquid_water_mol)+F(old[i].gas_amounts_mol[2])
            new_water = F(new[i].liquid_water_mol)+F(new[i].gas_amounts_mol[2])
            require(new_water-old_water == liquid(a)-liquid(b)+a.gas_mol[2]-b.gas_mol[2]
                +ledger.roundoff.liquid_mol[i]+ledger.roundoff.gas_mol[i][2], 'cell_total_water')
            checks += 4
        water = lambda states: sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states), F())
        require(water(new)-water(old) == ledger.faces[0].gas_mol[2]-ledger.faces[-1].gas_mol[2]
            +sum(ledger.roundoff.liquid_mol, F())+sum((row[2] for row in ledger.roundoff.gas_mol), F()), 'global_water')
        require(sum((F(s.internal_energy_j) for s in new), F())-sum((F(s.internal_energy_j) for s in old), F())
            == ledger.faces[0].energy_j-ledger.faces[-1].energy_j+sum(ledger.roundoff.energy_j, F()), 'global_U')
        for k in (0, 1):
            require(sum((F(s.gas_amounts_mol[k]) for s in new), F())-sum((F(s.gas_amounts_mol[k]) for s in old), F())
                == ledger.faces[0].gas_mol[k]-ledger.faces[-1].gas_mol[k]
                +sum((row[k] for row in ledger.roundoff.gas_mol), F()), 'global_dry_species')
        boundary = ledger.boundary_integral
        require(boundary.conductive_into_cell_j == -ledger.faces[-1].conduction_j, 'furnace_conduction_sign')
        require(boundary.exact_surface_balance_defect_j == boundary.conductive_into_cell_j
                -boundary.convective_in_j-boundary.radiative_in_j, 'surface_balance_decomposition')
        require(abs(boundary.reported_surface_residual_j) <= boundary.surface_balance_limit_j, 'surface_tolerance')
        checks += 10
    return checks


def main(root, output, mode):
    """Persist started/constructed/evaluation/run/failure before returning."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    result = {'mode': mode, 'status': 'started', 'material_qualified': False,
              'inner_seconds': INNER_SECONDS, 'outer_seconds': OUTER_SECONDS,
              'duration_s': {'numerator': 1, 'denominator': 1024}, 'steps': 1}
    def save():
        result['wall_seconds'] = time.monotonic()-start
        temporary = output.with_suffix(output.suffix+'.pending')
        temporary.write_text(json.dumps(result, indent=2)+'\n')
        temporary.replace(output)
    def timeout(*args):
        raise TimeoutError('outer_60s_budget_exceeded')
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, OUTER_SECONDS)
    save()
    try:
        if mode not in ('probe', 'one-step'):
            raise ValueError('unsupported_mode')
        model, initial, serialize, digest = construct(root)
        result.update(status='constructed', build_seconds=time.monotonic()-start,
            mobility_sha256=digest, initial=serialize(initial), provenance=serialize(model.provenance()))
        save()
        from sludge_sandbox.exact_event_clock import ExactEventTime
        from sludge_sandbox.source_wet_column import integrate_source_column
        if mode == 'probe':
            observation = model.evaluate(initial, ExactEventTime(F()))
            result.update(status='evaluated', observation=serialize(observation))
            save()
            result['audit_checks'] = audit_observation(observation)
            result['status'] = 'completed'
        else:
            # Observe existing stage calls; no extra EOS evaluation or model mutation.
            cls = type(model)
            original = cls.evaluate
            captures = []
            def observed(self, states, when):
                out = original(self, states, when)
                captures.append({'states': states, 'when': when, 'observation': out})
                result.update(status='integrating', completed_stage_observations=serialize(captures))
                save()
                return out
            cls.evaluate = observed
            try:
                run = integrate_source_column(model, initial, duration_s=float(DURATION), steps=1,
                                              maximum_wall_seconds=INNER_SECONDS)
            finally:
                cls.evaluate = original
            result.update(status=run.status, reason=run.reason, run=serialize(run))
            save()
            result['audit_checks'] = audit(run, captures)
            require(run.status == 'completed' and len(run.ledgers) == 1, 'one_complete_step_required')
        save()
        print(json.dumps({k: result.get(k) for k in ('mode', 'status', 'wall_seconds', 'audit_checks')}))
        return 0
    except Exception as exc:
        result.update(status='failed', exception_type=type(exc).__name__, exception=str(exc))
        save()
        print(json.dumps({k: result.get(k) for k in ('mode', 'status', 'exception_type', 'exception', 'wall_seconds')}))
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous)


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
