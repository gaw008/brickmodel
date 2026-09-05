"""Canonical inputs and full-precision raw trajectories, never invented rows."""
import csv
import json
from pathlib import Path
from model import canonical
from diagnostics import row

TS_FIELDS='scenario_id tau T_K K_tau d_tau a_D b g H S_D S_B Da_O2 u_core u_surface f_mean f_max co2_body co2_generated co2_net_out u_res v_res source_rate'.split()
PROFILE_FIELDS='scenario_id tau cell_index xi_left xi_right u v f'.split()
FLUX_FIELDS='scenario_id tau_left tau_right integral_J_u integral_J_v integral_q_body'.split()


def write_json(path,data):
    path.write_bytes(canonical(data))


def write_csv(path,fields,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n',extrasaction='raise'); w.writeheader()
        for r in rows:
            w.writerow({k:('' if v is None else format(v,'.17g') if isinstance(v,float) else v) for k,v in r.items()})


def write_raw(out,results):
    (out/'inputs').mkdir(exist_ok=True)
    times=[]; profiles=[]; flux=[]; index=[]
    for result in results:
        s=result.scenario; sid=s.id; n=s.to_dict()['numerics']['n_cells']
        (out/'inputs'/f'{sid}.json').write_bytes(s.canonical())
        index.append({'scenario_id':sid,'input_file':f'inputs/{sid}.json','test_only_dirichlet':result.test_only_dirichlet,
                      'execution_status':result.execution_status})
        for t,state in result.records:
            times.append(row(s,t,state,test_only_dirichlet=result.test_only_dirichlet))
            for i,(u,v,f) in enumerate(zip(state.u,state.v,state.f)):
                profiles.append(dict(scenario_id=sid,tau=t,cell_index=i,xi_left=i/n,xi_right=(i+1)/n,u=u,v=v,f=f))
        for (ta,a),(tb,b) in zip(result.records,result.records[1:]):
            flux.append(dict(scenario_id=sid,tau_left=ta,tau_right=tb,integral_J_u=b.net_u-a.net_u,
                             integral_J_v=b.net_v-a.net_v,integral_q_body=b.generated-a.generated))
    write_csv(out/'timeseries.csv',TS_FIELDS,times)
    write_csv(out/'profiles.csv',PROFILE_FIELDS,profiles)
    write_csv(out/'flux_intervals.csv',FLUX_FIELDS,flux)
    write_json(out/'raw_index.json',{'kind':'raw_inventory_exports','cases':index})
