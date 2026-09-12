"""One bounded comparison; each service operation runs in a new process."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

_spec = importlib.util.spec_from_file_location('source_resume_native_verifier',
    Path(__file__).with_name('verify_native.py'))
_verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_verifier)
decode_graph, load_events, verify = _verifier.decode_graph, _verifier.load_events, _verifier.verify

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
SCRATCH = Path('/private/tmp/brick-source-resume-v1')
PYTHON = Path('/private/tmp/brick-water-backend-probe/venv/bin/python')
COUNTERS = ('heos_started','heos_kernel_returned','heos_returned','initial_energy_started',
    'initial_energy_returned','rhs_started','rhs_returned','wet_started','wet_returned')


def main():
    begin = time.monotonic()
    output = SCRATCH/'native01'
    output.mkdir(exist_ok=False)
    case = ROOT/'data/sandbox/cases/source-nonstationary-heos-resume-v5.json'
    other = dict.fromkeys(COUNTERS,0)

    def execute(name, operation, source, **extra):
        remaining = 510. - (time.monotonic()-begin)
        if remaining <= 0:
            raise RuntimeError('comparison_510_seconds_exhausted')
        request = dict(schema='source_execution_request_v1', operation=operation, source=str(source),
            output=str(output/name), cancel_file=str(SCRATCH/'cancel'),
            shared_budget=dict(other_counts=dict(other), outer_remaining_seconds=remaining,
                total_callback_cap=97, wet_pressure_request_cap=16), **extra)
        path=output/(name+'-request.json')
        path.write_text(json.dumps(request,indent=2)+'\n')
        with (output/(name+'-stdout.log')).open('xb') as stdout, (output/(name+'-stderr.log')).open('xb') as stderr:
            process=subprocess.run([str(PYTHON),'-I','-m','sludge_sandbox.source_execution_worker',str(path)],
                cwd='/private/tmp', stdout=stdout, stderr=stderr, timeout=remaining+1.)
        if process.returncode:
            raise RuntimeError(name+'_worker_exit_'+str(process.returncode))
        result=json.loads((output/name/'OUTCOME.json').read_bytes())
        if time.monotonic()-begin >= 510.:
            raise RuntimeError('comparison_510_seconds_exhausted_after_'+name)
        print(json.dumps(dict(phase=name,status=result['status'],counts=result['counts'],
            elapsed_seconds=time.monotonic()-begin)),flush=True)
        return result

    try:
        parent=execute('parent','source-run',case,assets_root=str(SCRATCH/'assets'))
        if parent['status']!='completed' or parent['details']['numerical_event_accepted'] is not True:
            raise RuntimeError('parent_original_numerical_gate_failed')
        parent_dir=output/'parent/run'
        event=next(e for e in load_events(parent_dir) if e['event']=='transition_returned')
        start=decode_graph(event['payload'])['result'].candidates[1].end.seconds
        from fractions import Fraction
        end=start+Fraction(3,64)
        args=dict(end=dict(numerator=end.numerator,denominator=end.denominator),
            step_sizes=dict(initial_step_s=1/64,maximum_step_s=1/64,rationale='Original three-step conduction gate.'))
        continuous=execute('continuous','source-advance',parent_dir,pause_after_steps=0,**args)
        other={k:continuous['counts'][k]-parent['counts'][k] for k in COUNTERS}
        execute('paused','source-advance',parent_dir,pause_after_steps=1,**args)
        resumed=execute('resumed','source-resume',output/'paused/resume-point',pause_after_steps=0)
        checked=verify(output)
        assert resumed['combined_counts']==checked['expected_actual_counts']
        case_raw=case.read_bytes()
        canonical=(parent_dir/'config.json').read_bytes()
        for name in ('parent','continuous','paused','resumed'):
            record=json.loads((output/name/'OUTCOME.json').read_bytes())
            assert record['raw_case_sha256']==hashlib.sha256(case_raw).hexdigest()
            assert record['canonical_config_sha256']==hashlib.sha256(canonical).hexdigest()
        checked.update(elapsed_seconds=time.monotonic()-begin, raw_case_sha256=hashlib.sha256(case_raw).hexdigest(),
            canonical_config_sha256=hashlib.sha256(canonical).hexdigest(),
            separate_process_operations=4, source_lifetime_charge='saved_S_plus_new_A_offline_D_diagnostic_only')
        assert checked['elapsed_seconds']<510.
        (output/'ACCEPTANCE.json').write_text(json.dumps(checked,indent=2)+'\n')
    except BaseException as exc:
        (output/'DRIVER_FAILURE.json').write_text(json.dumps(dict(status='failed',reason=str(exc),
            exception_type=type(exc).__name__,elapsed_seconds=time.monotonic()-begin),indent=2)+'\n')
        raise


if __name__=='__main__':
    main()
