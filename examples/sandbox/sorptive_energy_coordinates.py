"""An explicit linear change of solver variables, leaving physical U intact."""
import numpy as np


class GasReferenceEnergy:
    def __init__(self,host,species,settings):
        self.width=len(species)+1
        self.references=np.array([host.fluid.gas_enthalpy_j_mol(k,settings['reference_temperature_k']) for k in species])
        self.record={'settings':settings,'reference_enthalpies_j_mol':dict(zip(species,map(float,self.references),strict=True)),
            'definition':'Solver E=U-sum(h_ref_i*N_i), including each exterior integral. Saved states and dense coefficients are physical U.',
            'classification':'linear_numerical_coordinate_change_not_a_physical_reference_shift'}

    def to_solver(self,values):
        result=np.array(values,copy=True)
        blocks=result.reshape(*result.shape[:-1],-1,self.width)
        blocks[...,-1]-=blocks[...,:-1]@self.references
        return result

    def to_physical(self,values):
        result=np.array(values,copy=True)
        blocks=result.reshape(*result.shape[:-1],-1,self.width)
        blocks[...,-1]+=blocks[...,:-1]@self.references
        return result
