"""Local numerical temperature RHS derivatives with an analytic entropy row.

The physical four-coordinate body has nearest-neighbour dependence. Its three
cell colours times four coordinates need twelve perturbation groups regardless
of column length. The cumulative entropy ledger has no feedback into that body.
"""
import numpy as np
from scipy.integrate._ivp.common import num_jac
from scipy.sparse import bmat,csc_matrix

from .carbon_calcium_rigid_exchange import exchange_jacobian
from .carbon_calcium_rigid_tangent import rigid_tangent


def production_gradient(column,values,states):
    tangents=[];maps=[]
    for i,state in enumerate(states):
        tangent=rigid_tangent(column.model,state,column.volume,column.inventories[i]['calcium_atoms_mol'],values[4*i],values[4*i+1])
        du=np.array(tangent['internal_energy_derivatives']);mapping=np.zeros((4,4));mapping[:3,:3]=np.eye(3)
        mapping[3,:3]=du[1:];mapping[3,3]=du[0];maps.append(mapping);tangents.append(tangent)
    result=np.zeros(4*column.count)
    for i in range(column.count-1):
        face=exchange_jacobian(column.model,states[i],states[i+1],tangents[i],tangents[i+1],column.face_parameters)
        result[4*i:4*i+4]+=np.array(face['production'][:4])@maps[i]
        result[4*i+4:4*i+8]+=np.array(face['production'][4:])@maps[i+1]
    return result


class TemperatureColumnJacobian:
    def __init__(self,column,body_absolute_tolerances):
        self.column=column;self.threshold=body_absolute_tolerances;self.factor=None
        self.structure=column.numerical_jacobian_sparsity()[:-1,:-1]
        self.groups=np.arange(4*column.count)%(3*4)

    def __call__(self,at,values):
        rates=self.column.rates(at,values)
        def vectorized(t,columns):
            return np.column_stack([self.column.rates(t,np.append(v,values[-1]))[:-1] for v in columns.T])
        body,self.factor=num_jac(vectorized,at,values[:-1],rates[:-1],self.threshold,self.factor,(self.structure,self.groups))
        gradient=production_gradient(self.column,values,self.column.states(values))
        return bmat([[body,csc_matrix((len(gradient),1))],
                     [csc_matrix(gradient.reshape(1,-1)),csc_matrix((1,1))]],format='csc')
