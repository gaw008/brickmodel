"""Fresh-Jacobian BDF nonlinear-stage diagnostic at a recorded failed state."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.integrate._ivp.bdf import BDF,change_D,solve_bdf_system
from scipy.integrate._ivp.common import norm

from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--jacobian-point',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    context=json.loads((root/settings['failure_context']).read_text())
    with (root/settings['trajectory']).open() as stream:header=json.loads(next(stream))
    policy=header['settings'];config=header['model_parameters'];surface=header['surface_parameters']
    reaction,nitrogen,_,_,_,_,volume=build_rigid(root,config)
    column=OpenRigidReactiveColumn(reaction,nitrogen,volume,config,policy,surface,header['cell_count'],header['cell_widths_m'])
    accepted=context['accepted'];failed=context['failed_trial'];dense=accepted['dense_output'];at=accepted['time_s'];segment=accepted['segment_index']
    values=np.array(accepted['integration_values']);step=failed['solver_time_s'];order=len(dense['differences'])-1
    with args.output.open('x') as output:
        def emit(row):output.write(json.dumps(row,allow_nan=False)+'\n');output.flush()
        calls=0
        def rates(t,y):
            nonlocal calls
            calls+=1;emit({'kind':'stage_evaluation','index':calls,'time_s':at+t,'integration_values':y.tolist()})
            return column.rates(at+t,y,segment)
        solver=BDF(lambda t,y:column.rates(at+t,y,segment),0.,values,step,
            jac=lambda t,y:column.jacobian(at+t,y,segment),rtol=header['relative_tolerance'],atol=header['absolute_tolerances'],first_step=step,max_step=step)
        differences=np.zeros_like(solver.D);differences[:order+1]=np.array(dense['differences'])
        change_D(differences,order,step/dense['denominators_s'][0]);predictor=np.sum(differences[:order+1],axis=0)
        scale=solver.atol+solver.rtol*np.abs(predictor);psi=np.dot(differences[1:order+1].T,solver.gamma[1:order+1])/solver.alpha[order]
        coefficient=step/solver.alpha[order]
        location={'last_accepted':(at,values),'predictor':(at+step,predictor)}[args.jacobian_point]
        matrix=column.jacobian(*location,segment);lu=solver.lu(solver.I-coefficient*matrix)
        emit({'kind':'input','settings':settings,'jacobian_point':args.jacobian_point,'order':order,'step_s':step,'newton_tolerance':solver.newton_tol,'predictor':predictor.tolist(),
            'material_qualified':False,'training_eligible':False})
        converged,iterations,state,correction=solve_bdf_system(rates,step,predictor,coefficient,psi,lu,solver.solve_lu,scale,solver.newton_tol)
        accuracy_scale=solver.atol+solver.rtol*np.abs(state);error_norm=norm(solver.error_const[order]*correction/accuracy_scale)
        result={'kind':'summary','nonlinear_converged':bool(converged),'iterations':iterations,'local_error_norm':float(error_norm),'local_error_acceptable':bool(error_norm<=1),
            'state':state.tolist(),'scope':settings['scope']};emit(result);print(json.dumps({k:v for k,v in result.items() if k!='state'}))


if __name__=='__main__':main()
