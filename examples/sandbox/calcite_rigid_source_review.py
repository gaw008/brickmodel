"""Source recomposition and separately expanded face matrix for column reviews."""
import math
import numpy as np


def source_cell_errors(cell,state,values):
    c,n,u=values;t=state['temperature_k'];r=cell.reaction.gas_constant_j_mol_k;p0=cell.p0
    a,b,g,carrier=[phase.standard(t) for phase in (cell.reactant,cell.product,cell.gas,cell.nitrogen)]
    na,nb,ng,nn=[state[k] for k in ('calcite_mol','lime_mol','co2_mol','nitrogen_mol')]
    vg=cell.volume-na*cell.vc-nb*cell.vl;pc=ng*r*t/vg;pn=nn*r*t/vg
    ure=math.fsum((na*(a['enthalpy_j_mol']-p0*cell.vc),nb*(b['enthalpy_j_mol']-p0*cell.vl),
        ng*(g['enthalpy_j_mol']-r*t),nn*(carrier['enthalpy_j_mol']-r*t)))
    sre=math.fsum((na*a['entropy_j_mol_k'],nb*b['entropy_j_mol_k'],ng*g['entropy_j_mol_k'],nn*carrier['entropy_j_mol_k']))-r*(ng*math.log(pc/p0)+nn*math.log(pn/p0))
    f=b['gibbs_j_mol']+g['gibbs_j_mol']-a['gibbs_j_mol']-(pc+pn-p0)*cell.dv+r*t*math.log(pc/p0)
    phase=state['phase'];violation=abs(f) if phase=='coexistence' else (max(0.,-f) if phase=='calcite' else max(0.,f))
    return {'elements_mol':max(abs(na+nb-cell.calcium),abs(na+ng-c),abs(nn-n),abs(3*na+nb+2*ng-cell.calcium-2*c)),
        'source_energy_j':abs(ure-u),'source_entropy_j_k':abs(sre-state['entropy_j_k']),
        'source_pressure_pa':abs(pc+pn-state['pressure_pa']),'source_volume_m3':abs(vg-state['gas_volume_m3']),'affinity_j_mol':violation}


def independent_face(left,right,model,parameters):
    tl,tr=left['temperature_k'],right['temperature_k'];r=model.reaction.gas_constant_j_mol_k;p0=model.p0
    h=[];forces=[];mu=[];fractions=[]
    for name,phase in (('co2',model.gas),('nitrogen',model.nitrogen)):
        a,b=phase.standard(tl),phase.standard(tr);hl,hr=a['enthalpy_j_mol'],b['enthalpy_j_mol'];hf=(hl+hr)/2
        sl=a['entropy_j_mol_k']-r*math.log(left[name+'_partial_pressure_pa']/p0)
        sr=b['entropy_j_mol_k']-r*math.log(right[name+'_partial_pressure_pa']/p0)
        h.append(hf);forces.append((hl-hf)/tl-(hr-hf)/tr-sl+sr);mu.append((hl-tl*sl,hr-tr*sr))
        fractions.append((left[name+'_mol']/(left['co2_mol']+left['nitrogen_mol'])+right[name+'_mol']/(right['co2_mol']+right['nitrogen_mol']))/2)
    x,y=fractions;b=parameters['bulk_mobility_mol2_k_j_s'];d=parameters['counter_mobility_mol2_k_j_s']
    nc=(b*x*x+d)*forces[0]+(b*x*y-d)*forces[1];nn=(b*x*y-d)*forces[0]+(b*y*y+d)*forces[1]
    energy=parameters['heat_conductance_w_k']*(tl-tr)+h[0]*nc+h[1]*nn
    entropy_left=(-energy+mu[0][0]*nc+mu[1][0]*nn)/tl
    entropy_right=(energy-mu[0][1]*nc-mu[1][1]*nn)/tr
    return np.array([nc,nn,energy,entropy_left,entropy_right])
