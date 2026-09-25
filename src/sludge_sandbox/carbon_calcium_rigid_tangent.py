"""Same-assemblage derivatives of rigid Ca/C/O equilibrium constraints.

Coordinates are T,C atoms,O atoms,N2 molecules, with fixed volume and calcium.
This module differentiates the simultaneous logarithmic gas/pressure equations;
it does not alter the qualified equilibrium flash or continue a phase branch.
"""
import math

import numpy as np


def rigid_tangent(model,state,volume_m3,calcium_atoms_mol,carbon_atoms_mol,oxygen_atoms_mol):
    t,p=state['temperature_k'],state['pressure_pa'];r=model.r;n=state['amounts_mol']
    rt=r*t;ca,ct,ot=calcium_atoms_mol,carbon_atoms_mol,oxygen_atoms_mol
    names=['CO','CO2','O2'];gas_names=names+['N2'];ng=math.fsum(n[k] for k in gas_names)
    coexist=state['calcium_phase']=='coexistence';present=state['carbon_phase']=='graphite_present'
    thermal={k:phase.standard(t) for k,phase in model.phases.items()};v=model.volumes
    entropy={k:thermal[k]['entropy_j_mol_k']-(r*math.log(p/model.p0*n[k]/ng) if k in gas_names else 0.) for k in n}
    oxygen_row=[n['CO']/ot,2*n['CO2']/ot,2*n['O2']/ot]+([2*ca/ot] if coexist else [])+[0.]
    if present:
        first=[int(k=='CO')-.5*int(k=='O2')-n[k]/(2*ng) for k in names]+([0.] if coexist else [])+[.5-p*v['C']/rt]
        second=[int(k=='CO2')-int(k=='O2') for k in names]+([0.] if coexist else [])+[-p*v['C']/rt]
        matrix=[first,second,oxygen_row]
        rhs=[[(entropy['CO']-entropy['C']-entropy['O2']/2)/rt,0.,0.,1/(2*ng)],
             [(entropy['CO2']-entropy['C']-entropy['O2'])/rt,0.,0.,0.],
             [0.,0.,1/ot,0.]]
    else:
        carbon_row=[n['CO']/ct,n['CO2']/ct,0.]+([ca/ct] if coexist else [])+[0.]
        reaction=[int(k=='CO2')-int(k=='CO')-.5*int(k=='O2')+n[k]/(2*ng) for k in names]+([0.] if coexist else [])+[-.5]
        matrix=[carbon_row,oxygen_row,reaction]
        rhs=[[0.,1/ct,0.,0.],[0.,0.,1/ot,0.],[(entropy['CO2']-entropy['CO']-entropy['O2']/2)/rt,0.,0.,-1/(2*ng)]]
    if coexist:
        matrix.append([int(k=='CO2')-n[k]/ng for k in names]+[0.,1+p*(v['lime']-v['calcite'])/rt])
        rhs.append([(entropy['lime']+entropy['CO2']-entropy['calcite'])/rt,0.,0.,1/ng])
    volume_row=[n[k]*(rt/p-(v['C'] if present and k in ['CO','CO2'] else 0.)) for k in names]
    if coexist:volume_row.append(ca*(v['calcite']-v['lime']-(v['C'] if present else 0.)))
    volume_row.append(-ng*rt/p)
    matrix.append([x/volume_m3 for x in volume_row])
    rhs.append([-ng*r/p/volume_m3,-v['C']/volume_m3 if present else 0.,0.,-rt/p/volume_m3])
    logarithmic=np.linalg.solve(np.array(matrix),np.array(rhs))
    dn={name:n[name]*logarithmic[i] for i,name in enumerate(names)}
    dn['N2']=np.array([0.,0.,0.,1.]);dn['calcite']=ca*logarithmic[3] if coexist else np.zeros(4)
    dn['lime']=-dn['calcite']
    dn['C']=np.array([0.,1.,0.,0.])-dn['calcite']-dn['CO']-dn['CO2'] if present else np.zeros(4)
    dp=p*logarithmic[-1]
    u={k:thermal[k]['enthalpy_j_mol']-(model.p0*v[k] if k in v else rt) for k in n}
    du=sum(dn[k]*u[k] for k in n)
    du[0]+=math.fsum(n[k]*thermal[k]['cp_j_mol_k'] for k in n)-ng*r
    ds=sum(dn[k]*entropy[k] for k in n)-ng*r/p*dp
    ds[0]+=math.fsum(n[k]*thermal[k]['cp_j_mol_k'] for k in n)/t
    # Chain rule from (C,O,N2,U) to (T,C,O,N2), all at fixed V and Ca.
    coordinate=np.zeros((4,4));coordinate[0,:3]=-du[1:]/du[0];coordinate[0,3]=1/du[0]
    coordinate[1:,:3]=np.eye(3)
    partial_p={k:p*(dn[k]/ng-n[k]/ng**2*sum(dn[j] for j in gas_names))+n[k]/ng*dp for k in gas_names}
    dmu={k:-entropy[k]*np.array([1.,0.,0.,0.])+rt/ state['partial_pressures_pa'][k]*partial_p[k] for k in gas_names}
    return {'coordinate_order':['temperature_k','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol'],
        'conserved_coordinate_order':['carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol','internal_energy_j'],
        'amount_derivatives':{k:x.tolist() for k,x in dn.items()},'pressure_derivatives':dp.tolist(),
        'internal_energy_derivatives':du.tolist(),'entropy_derivatives':ds.tolist(),
        'gas_chemical_potential_derivatives':{k:x.tolist() for k,x in dmu.items()},
        'physical_from_conserved_derivative':coordinate.tolist(),
        'amount_conserved_derivatives':{k:(x@coordinate).tolist() for k,x in dn.items()},
        'pressure_conserved_derivatives':(dp@coordinate).tolist(),
        'gas_chemical_potential_conserved_derivatives':{k:(x@coordinate).tolist() for k,x in dmu.items()},
        'same_phase_only':True}
