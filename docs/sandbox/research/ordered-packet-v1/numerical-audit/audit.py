"""Read saved failed capture only; no model imports or EOS."""
import hashlib
import json
from pathlib import Path
import traceback

SOURCE=Path('/private/tmp/brick-four-cell-ordered-packet-v1/attempt01')
HERE=Path(__file__).resolve().parent


def main():
    report={'status':'started','qualification':'Failed-capture diagnostic audit, not accepted packet/order/convergence proof'}
    try:
        names=('core-result.json','runtime-before.json','runtime-after.json','actual-depletion-policy.json',
               'original-integration-policy.json','initial.json','final.json','final-interfaces.json','runner.json','case.json')
        raw={name:(SOURCE/name).read_bytes() for name in names}
        report['input_sha256']={name:hashlib.sha256(value).hexdigest() for name,value in raw.items()}
        data={name:json.loads(value) for name,value in raw.items()}
        before,after=data['runtime-before.json'],data['runtime-after.json']
        assert before==after
        assert before['modules']['depletion_integration.py']=='3866f15b11f0e78c4e77591ffb8fe156bafefe05a379165ff78e635fe52c3223'
        result=data['core-result.json']['result'];refs=result['refinements']
        report.update(core_status=result['status'],core_reason=result['reason'],evaluations=result['evaluations'],
                      attempted_steps=result['attempted_steps'],accepted_steps=len(result['steps']),
                      last_accepted_time_s=result['times_s'][-1],events=len(result['events']),packets=len(result['packets']),
                      corrections=len(result['corrections']),refinements=refs,phase_costs=result['phase_costs'])
        assert result['status']=='failed' and result['reason']=='correction_exceeds_evaporation_fraction'
        assert not result['events'] and not result['packets'] and not result['corrections']
        assert len(refs)==1 and refs[0]['level']==0 and refs[0]['differences'] is None
        assert refs[0]['phase_costs']['comparison']['evaluations']==0
        assert refs[0]['phase_costs']['comparison']['endpoint_attempts']==0
        assert result['states'][-1]==data['final.json']
        assert all(mode=='existing_liquid' for mode in data['final-interfaces.json'])
        report['comparison_gate_audit']='not_available_no_comparison_was_executed'
        report['root_order_audit']='not_available_discarded_proposal_root_frames_not_serialized'
        report['per_member_correction_ratio']='not_available_failed_delta_and_gross_not_serialized'
        report['original_roundoff_policy']=data['actual-depletion-policy.json']['roundoff_policy']
        report['status']='failed_capture_consistency_checked'
    except BaseException:
        report['status']='audit_failed';report['traceback']=traceback.format_exc()
    (HERE/'audit-result.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return 0 if report['status']=='failed_capture_consistency_checked' else 1


if __name__=='__main__':raise SystemExit(main())
