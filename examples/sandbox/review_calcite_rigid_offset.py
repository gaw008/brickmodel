"""Resolve tiny carbon offsets against independently recomposed decimal balances."""
import argparse
from decimal import Decimal, localcontext
import json
from pathlib import Path

from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_offset import OffsetRigidCalciteMixture


def reference(cell,t,offset,nitrogen_mol,settings):
    d = lambda x:Decimal(str(x))
    with localcontext() as ctx:
        ctx.prec = settings['decimal_precision']
        temp,dc,n,r,a,v,vc,vl,p0 = [d(x) for x in (t,offset,nitrogen_mol,cell.reaction.gas_constant_j_mol_k,cell.calcium,cell.volume,cell.vc,cell.vl,cell.p0)]
        rt = r*temp;c = a+dc;dv = vc-vl;base = v-a*vc-dc*dv
        standards = [phase.standard(t) for phase in (cell.reactant,cell.product,cell.gas,cell.nitrogen)]
        dg = d(cell.reaction.standard(t)['reaction']['gibbs_j_mol'])
        def score(g):
            vg = base+g*dv;p = (g+n)*rt/vg;pc = g*rt/vg
            return dg-(p-p0)*dv+rt*(pc/p0).ln()
        if score(c)<=0:
            g,calcite,lime,phase = c,Decimal(0),a,'lime'
        elif dc>0 and score(dc)>=0:
            g,calcite,lime,phase = dc,a,Decimal(0),'calcite'
        else:
            lower = dc.ln() if dc>0 else d(settings['decimal_lower_log_gas']);upper = c.ln()
            if not score(lower.exp())<0<score(upper.exp()):
                raise ValueError('Declared decimal log-gas bracket does not enclose equilibrium')
            for _ in range(settings['decimal_bisection_iterations']):
                middle = (lower+upper)/2
                if score(middle.exp())>0:
                    upper = middle
                else:
                    lower = middle
            g = ((lower+upper)/2).exp();lime = g-dc;calcite = a-lime;phase = 'coexistence'
        amounts = [calcite,lime,g,n];vg = v-calcite*vc-lime*vl;pc,pn = g*rt/vg,n*rt/vg
        u = sum(q*(d(s['enthalpy_j_mol'])-correction) for q,s,correction in zip(amounts,standards,(p0*vc,p0*vl,rt,rt),strict=True))
        entropy = sum(q*d(s['entropy_j_mol_k']) for q,s in zip(amounts,standards,strict=True))-r*(g*(pc/p0).ln()+n*(pn/p0).ln())
        return {'co2_mol':float(g),'co2_decimal_mol':str(g),'calcite_decimal_mol':str(calcite),'lime_decimal_mol':str(lime),
            'phase':phase,'internal_energy_j':float(u),'entropy_j_k':float(entropy),'pressure_pa':float(pc+pn)}


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text());config = json.loads((root/settings['model_parameters']).read_text())
    reaction,nitrogen,_,_,_,_,volume = build_rigid(root,config);cell = OffsetRigidCalciteMixture(reaction,nitrogen,volume,config,settings['cell']);records = []
    for t,n in settings['temperature_nitrogen_pairs']:
        for offset in settings['carbon_offsets_mol']:
            state = cell.at_carbon_offset(t,offset,n);ref = reference(cell,t,offset,n,settings);back = cell.offset_inventory_state(offset,n,state['internal_energy_j'])
            errors = {'relative_gas_mol':abs(state['co2_mol']/ref['co2_mol']-1),'energy_j':abs(state['internal_energy_j']-ref['internal_energy_j']),
                'entropy_j_k':abs(state['entropy_j_k']-ref['entropy_j_k']),'pressure_pa':abs(state['pressure_pa']-ref['pressure_pa']),
                'carbon_offset_closure_mol':abs(state['carbon_offset_closure_residual_mol']),'inverse_temperature_k':abs(back['temperature_k']-t)}
            flags = {k:v<=settings['budgets'][k] for k,v in errors.items()};flags['same_phase']=state['phase']==ref['phase']
            records.append({'temperature_k':t,'nitrogen_mol':n,'carbon_offset_mol':offset,'state':state,'decimal_reference':ref,'errors':errors,'within_budgets':flags,
                'offset_recovered_from_total_carbon_mol':state['carbon_mol']-cell.calcium})
    result = {'settings':settings,'records':records,'all_requested_numerical_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as out:json.dump(result,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'states':len(records)}))


if __name__=='__main__':main()
