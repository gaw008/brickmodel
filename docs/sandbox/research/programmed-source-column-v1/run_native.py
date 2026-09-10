"""Bounded source-column furnace example; geometry and transport are tests."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import importlib.util
import json
import time

from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.exact_boundary_program import ExactProgramView
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.programmed_source_wet_column import ProgrammedSourceWetColumn
from sludge_sandbox.source_wet_column import integrate_source_column


def construct(root):
    location = Path(root)/'docs/sandbox/research/source-wet-column-v1/run_native.py'
    spec = importlib.util.spec_from_file_location('closed_source_column_example', location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base, initial = module.make_column(root)
    program = BoundaryProgram(identity=ProgramIdentity(program_id='source-open-native-example', version='1',
        classification='virtual_design_choice', source_ids=('design:source-open-native-furnace',)),
        knot_times_s=(0., 1/1024), gas_temperature_k=(340., 346.),
        radiation_temperature_k=(350., 355.), total_pressure_pa=(9e5, 1.3e6),
        species_order=base.gas_ids, mole_fractions=((.25, .6875, .0625), (.125, .75, .125)))
    model = ProgrammedSourceWetColumn(base, ExactProgramView(program), .5, 10., .8, 5.670374419e-8,
        (1e-5, 2e-5, 1.5e-5), 1e-13, 1.8e-5, ('manufactured:source-open-native-coefficients',),
        SurfacePolicy(absolute_residual_w=1e-10, relative_residual=1e-12, maximum_iterations=100))
    return model, initial, module.serialize


def audit(run):
    checks = 0
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        for i in range(len(old)):
            assert old[i].solid_mass_kg == new[i].solid_mass_kg
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i]
            assert F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol) == -ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i]
            for k in range(3):
                assert F(new[i].gas_amounts_mol[k])-F(old[i].gas_amounts_mol[k]) == ledger.faces[i].gas_mol[k]-ledger.faces[i+1].gas_mol[k]+(ledger.phase_water_mol[i] if k == 2 else 0)+ledger.roundoff.gas_mol[i][k]
                checks += 1
            checks += 3
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == ledger.faces[0].energy_j-ledger.faces[-1].energy_j+sum(ledger.roundoff.energy_j)
        checks += 1
        for k in (0, 1):
            assert sum(F(s.gas_amounts_mol[k]) for s in new)-sum(F(s.gas_amounts_mol[k]) for s in old) == ledger.faces[0].gas_mol[k]-ledger.faces[-1].gas_mol[k]+sum(row[k] for row in ledger.roundoff.gas_mol)
            checks += 1
        water = lambda states: sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states)
        assert water(new)-water(old) == ledger.faces[0].gas_mol[2]-ledger.faces[-1].gas_mol[2]+sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol)
        b = ledger.boundary_integral
        assert b.conductive_into_cell_j == -ledger.faces[-1].conduction_j
        assert b.exact_surface_balance_defect_j == b.conductive_into_cell_j-b.convective_in_j-b.radiative_in_j
        assert abs(b.reported_surface_residual_j) <= b.surface_balance_limit_j
        checks += 4
    return checks


def main(root, output, mode):
    start = time.monotonic()
    model, initial, serialize = construct(root)
    built = time.monotonic()
    if mode == 'probe':
        observation = model.evaluate(initial, ExactEventTime(F()))
        result = {'mode': mode, 'build_seconds': built-start, 'evaluation_seconds': time.monotonic()-built,
            'initial': serialize(initial), 'observation': serialize(observation), 'provenance': serialize(model.provenance())}
        brief = {k: result[k] for k in ('mode', 'build_seconds', 'evaluation_seconds')}
    elif mode == 'one-step':
        run = integrate_source_column(model, initial, duration_s=1/1024, steps=1, maximum_wall_seconds=45.)
        result = {'mode': mode, 'build_seconds': built-start, 'run': serialize(run), 'ledger_checks': audit(run),
            'provenance': serialize(model.provenance())}
        brief = {'mode': mode, 'status': run.status, 'reason': run.reason, 'accepted_steps': len(run.ledgers),
            'elapsed_seconds': run.elapsed_seconds, 'ledger_checks': result['ledger_checks']}
    else:
        raise ValueError('unsupported_mode')
    Path(output).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(brief))


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
