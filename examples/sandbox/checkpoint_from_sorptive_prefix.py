"""Derive a labeled checkpoint from a closed, interrupted accepted-state trace.

The original file is untouched. Every original line must parse; partial JSON
is reported as an error rather than discarded. Run only after its writer stops.
"""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trajectory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();accepted=0;last_accepted=None
    with args.trajectory.open() as source,args.output.open('x') as output:
        for line in source:
            row=json.loads(line)
            if row['kind']=='summary':
                raise ValueError('this command requires an interrupted prefix without a terminal summary')
            output.write(line)
            if row['kind']=='accepted':
                accepted+=1;last_accepted=row
        if last_accepted is None:
            raise ValueError('the interrupted prefix contains no accepted physical state')
        emit=lambda row:output.write(json.dumps(row,allow_nan=False)+'\n')
        emit({'kind':'accepted_prefix_recovery','source_trajectory':str(args.trajectory),
            'time_s':last_accepted['time_s'],'definition':'Derived record after the original writer stopped. Original parsed lines retained verbatim; no interpolated or rejected trial state used.'})
        emit({'kind':'checkpoint','time_s':last_accepted['time_s'],
            'conserved_state':last_accepted['conserved_state'],
            'temperature_seeds_k':[p['temperature_k'] for p in last_accepted['states']],
            'accepted_steps':accepted,'reason':['explicit_recovery_of_closed_accepted_prefix']})
        emit({'kind':'summary','status':'stopped_at_checkpoint','time_s':last_accepted['time_s'],
            'accepted_steps':accepted,'record_origin':'derived checkpoint, not the original run terminal status'})
    print(json.dumps({'status':'derived_checkpoint','time_s':last_accepted['time_s'],'accepted_steps':accepted}))


if __name__=='__main__':
    main()
