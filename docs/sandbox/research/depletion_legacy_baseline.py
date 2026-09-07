"""Preserve the legacy finite-time depletion obstruction on a manufactured sink."""
from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from sludge_sandbox.integration import ConservedState,DomainExit,IntegrationPolicy,Rates,integrate


def run():
    initial=ConservedState([[1e-4,.01]],[0.])
    def wet(state,time):
        if state.amounts_mol[0,0]==0:
            raise DomainExit('manufactured_no_existing_liquid_interface')
        return Rates([[0.,0.],[0.,0.]],[0.,0.],[[-1e-3,1e-3]],[0.])
    policy=IntegrationPolicy(initial_step_s=.01,maximum_step_s=.02,minimum_step_s=1e-12,
        relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-8,
        amount_scale_mol=1e-4,energy_scale_j=1.,maximum_steps=500,maximum_rejections=100,
        maximum_wall_seconds=10.)
    result=integrate(initial,wet,start_s=0.,end_s=.2,policy=policy)
    output=dict(classification='manufactured_test_fixture',purpose='legacy_obstruction_not_new_event_success',
        expected_event_time_s=1e-4/1e-3,requested_end_s=.2,status=result.status,reason=result.reason,
        times_s=result.times_s,liquid_mol=[float(s.amounts_mol[0,0]) for s in result.states],
        vapor_mol=[float(s.amounts_mol[0,1]) for s in result.states],evaluations=result.evaluations,
        rejected_trials=result.rejected_trials,elapsed_seconds=result.elapsed_seconds,policy=vars(policy),
        source_sha256={str(p):sha256((ROOT/p).read_bytes()).hexdigest() for p in
            (Path(__file__).relative_to(ROOT),Path('src/sludge_sandbox/integration.py'))})
    Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:output[k] for k in ('status','reason','expected_event_time_s','evaluations','rejected_trials','elapsed_seconds')}))
    print('last_time',result.times_s[-1],'last_liquid',output['liquid_mol'][-1])


if __name__=='__main__':run()
