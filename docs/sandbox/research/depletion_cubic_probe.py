"""Independent nonlinear event probe; does not change registered project gates."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests/sandbox'))
from test_depletion_integration import policies,oracle
from sludge_sandbox.depletion_integration import integrate_depletion
from sludge_sandbox.integration import ConservedState


def run(scale):
    p,e=policies();base=oracle();original=base.evaluate_callback
    p=replace(p,relative_tolerance=p.relative_tolerance*scale,
        amount_absolute_tolerance_mol=p.amount_absolute_tolerance_mol*scale)
    def evaluate(state,t,modes):
        out=original(state,t,modes)
        if modes[0]=='existing_liquid':
            rate=.001+.003*t*t
            out=replace(out,rates=replace(out.rates,reaction_species_mol_s=np.array([[-rate,rate]])),
                evaporation_mol_s=(rate,))
        return out
    result=integrate_depletion(ConservedState([[1e-4,0.]],[600.]),
        replace(base,evaluate_callback=evaluate),start_s=0,end_s=.2,integration_policy=p,event_policy=e)
    # Exact primitive of prescribed r(t), independent of candidate event solve.
    reference=brentq(lambda t:.001*t+.001*t**3-1e-4,0,.2,xtol=1e-15)
    dt=result.events[0].time_s-reference if result.events else None
    du=float(result.states[-1].internal_energy_j[0])-(600+2*(.2-reference))
    return dict(ordinary_tolerance_scale=scale,status=result.status,reason=result.reason,
        event_reference_s=reference,event_error_s=dt,final_energy_error_j=du,
        accepted_trial_panels=result.accepted_trial_panels,rejected_trials=result.rejected_trials,
        event_refinement_indicator_s=result.events[0].event_time_difference_s if result.events else None,
        exploratory_gates=dict(event_absolute_s=1e-7,energy_absolute_j=2e-7),
        passes_exploratory_gates=result.status=='completed' and dt is not None and abs(dt)<1e-7 and abs(du)<2e-7)


if __name__=='__main__':
    output=Path(sys.argv[1])
    if output.exists():raise SystemExit('Refusing overwrite')
    paths=[Path(__file__),*sorted((ROOT/'src/sludge_sandbox').glob('*.py')),
        ROOT/'tests/sandbox/test_depletion_integration.py']
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before=hashes();runs=[run(1.),run(.01)];after=hashes()
    record=dict(qualification='manufactured_cubic_probe_local_event_indicator_not_full_trajectory_bound',
        provenance='Saved rerun after initial exploratory commands; both original gate failure and tightened-policy outcome retained.',
        runs=runs,sha256_before=before,sha256_after=after,sources_unchanged=before==after)
    output.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    print(json.dumps(runs))
