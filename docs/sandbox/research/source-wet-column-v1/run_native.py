"""Small closed source-wet column; geometry and transport are test fixtures."""
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
import importlib.util
import json
import time

from sludge_sandbox.source_wet_column import SourceWetColumn, integrate_source_column
from sludge_sandbox.mass_wet_transport import WetFace
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.phase_storage import InversePolicy


def make_column(root):
    root = Path(root)
    location = root/'docs/sandbox/research/source-wet-storage-v1/run_native.py'
    spec = importlib.util.spec_from_file_location('source_storage_example', location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    storage, _ = module.make_case(root)
    widths = (.25, .3125, .375)
    source = ('manufactured:source-wet-column-native-transport-v1',)
    faces = tuple(WetFace(.01, (widths[i]/2, widths[i+1]/2), (.5, .7),
        (1e-5, 2e-5, 1.5e-5), 1e-13, 1.8e-5, source) for i in range(2))
    chemical = WaterChemicalPotential(root/'data/sandbox/water', backend='heos',
        backend_manifest=root/'data/sandbox/water/heos-8.0.0-approved-manifest.json')
    column = SourceWetColumn((storage,)*3, (InversePolicy(1e-5, 1e-6, 100),)*3,
        chemical, (1e-9,)*3, faces, widths, .01, ('existing_liquid',)*3, source)
    initial = []
    for i in range(3):
        state = storage.state(.25, (.125+.03125*i, .25, .00390625*(i+1)), 0.)
        initial.append(replace(state, internal_energy_j=storage.evaluate(state, 331.25+1.25*i).total_internal_energy_j))
    return column, tuple(initial)


def exact(x):
    value = F(x)
    return {'numerator': value.numerator, 'denominator': value.denominator}


def serialize(value):
    from dataclasses import is_dataclass, fields
    from collections.abc import Mapping
    if isinstance(value, F): return exact(value)
    if is_dataclass(value): return {f.name: serialize(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping): return {key: serialize(v) for key, v in value.items()}
    if isinstance(value, (tuple, list)): return [serialize(v) for v in value]
    return value


def audit(run):
    checks = 0
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        for i in range(3):
            assert old[i].solid_mass_kg == new[i].solid_mass_kg
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i]
            assert F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol) == -ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i]
            for k in range(3):
                assert F(new[i].gas_amounts_mol[k])-F(old[i].gas_amounts_mol[k]) == ledger.faces[i].gas_mol[k]-ledger.faces[i+1].gas_mol[k]+(ledger.phase_water_mol[i] if k == 2 else 0)+ledger.roundoff.gas_mol[i][k]
                checks += 1
            checks += 3
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == sum(ledger.roundoff.energy_j)
        total_water = lambda states: sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in states)
        assert total_water(new)-total_water(old) == sum(ledger.roundoff.liquid_mol)+sum(row[2] for row in ledger.roundoff.gas_mol)
        checks += 2
    return checks


def main(root, output, mode):
    start = time.monotonic()
    column, initial = make_column(root)
    built = time.monotonic()
    if mode == 'probe':
        value = column.evaluate(initial)
        result = {'mode': mode, 'build_seconds': built-start, 'evaluation_seconds': time.monotonic()-built,
                  'model_identity': column.model_identity, 'initial': serialize(initial), 'evaluation': serialize(value)}
        print(json.dumps({k: v for k, v in result.items() if k not in ('initial', 'evaluation')}))
    elif mode == 'one-step':
        run = integrate_source_column(column, initial, duration_s=1/1024, steps=1, maximum_wall_seconds=45.)
        result = {'mode': mode, 'build_seconds': built-start, 'run': serialize(run), 'ledger_checks': audit(run)}
        print(json.dumps({'mode': mode, 'status': run.status, 'reason': run.reason, 'elapsed': run.elapsed_seconds,
            'accepted_steps': len(run.ledgers), 'checks': result['ledger_checks'],
            'energy_roundoff_j': float(run.energy_roundoff_used_j), 'inventory_roundoff_mol': float(run.inventory_roundoff_used_mol)}))
    else:
        raise ValueError('unsupported_mode')
    Path(output).write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
