"""Local equilibrium-chart derivatives mapped back to conserved N/U.

Central differences act on T/P/W/carrier composition without a nested
inventory or caloric inverse. The ODE, accepted states and U reference stay
unchanged. Each shared face is assembled with opposite signs.
"""
import numpy as np
from scipy.sparse import lil_matrix


class PrimitiveColumnJacobian:
    def __init__(self, model, decode, species, policy):
        self.model=model;self.decode=decode;self.species=species;self.policy=policy
        self.width=len(species)+1;self.calls=0
        self.steps=np.array([policy['central_steps'][k] for k in ('temperature_k','pressure_pa','moisture_kg_kg','carrier_oxygen_fraction')])
        self.coordinate_scales=np.array([policy['coordinate_scales'][k] for k in ('temperature_k','pressure_pa','moisture_kg_kg','carrier_oxygen_fraction')])
        self.transform=np.eye(self.width)
        self.transform[-1,:-1]=[-model.host.fluid.gas_enthalpy_j_mol(k,policy['energy_reference_temperature_k']) for k in species]
        self.row_scales=np.array([policy['whole_column_inventory_scale_mol']/model.count]*len(species)+
                                 [policy['whole_column_energy_scale_j']/model.count])
        self.transform/=self.row_scales[:,None]
        self.record={'policy':policy,'feedback_variables':model.count*self.width,
            'nonfeedback_ledger_variables':self.width,
            'implementation':'Local central T/P/W/carrier differences; capacity chain rule into original N/U; face assembly.',
            'ledger_derivative':'Only the external boundary face; ledger columns exactly zero.',
            'physical_parameters_changed':False}

    def coordinates(self, gas, state):
        x=gas.mole_fractions
        return np.array([state['temperature_k'],state['pressure_pa'],state['moisture_kg_kg_dry'],x['O2']/(x['O2']+x['N2'])])

    def direct(self, coordinates):
        t,p,w,x=map(float,coordinates)
        return self.model.host.at_tp_moisture(t,p,w,{'O2':x,'N2':1-x})

    def conserved(self, state):
        return np.array([state['inventories_mol'][k] for k in self.species]+[state['constitutive_internal_energy_j']])

    def flux(self, rate):
        return np.array([rate.exchange.net_mol_s[k] for k in self.species]+[rate.energy_out_w])

    def local_chart(self, gas, state):
        q=self.coordinates(gas,state);pairs=[];capacity=np.empty((self.width,self.width))
        for k,step in enumerate(self.steps):
            plus=q.copy();minus=q.copy();plus[k]+=step;minus[k]-=step
            pair=self.direct(plus),self.direct(minus);pairs.append(pair)
            capacity[:,k]=(self.conserved(pair[0][1])-self.conserved(pair[1][1]))/(2*step)
        scaled=self.transform@capacity*self.coordinate_scales[None,:]
        # A row transformation improves conditioning without changing U.
        inverse=np.linalg.solve(scaled,self.transform)
        return pairs,capacity,inverse,float(np.linalg.cond(scaled))

    def face_derivative(self, pairs, evaluate, inverse):
        derivative=np.column_stack([(self.flux(evaluate(*plus))-self.flux(evaluate(*minus)))/(2*step)
            for (plus,minus),step in zip(pairs,self.steps,strict=True)])
        return (derivative*self.coordinate_scales[None,:])@inverse

    def __call__(self, at_time, vector):
        gases,states=self.decode(vector);n=self.model.count;w=self.width
        result=lil_matrix(((n+1)*w,(n+1)*w))
        for i,(gas,state) in enumerate(zip(gases,states,strict=True)):
            pairs,_,inverse,_=self.local_chart(gas,state)
            column=slice(i*w,(i+1)*w)
            if i>0:
                derivative=self.face_derivative(pairs,
                    lambda g,s:self.model.internal_rate(gases[i-1],g,states[i-1],s),inverse)
                result[(i-1)*w:i*w,column]-=derivative
                result[i*w:(i+1)*w,column]+=derivative
            if i<n-1:
                derivative=self.face_derivative(pairs,
                    lambda g,s:self.model.internal_rate(g,gases[i+1],s,states[i+1]),inverse)
                result[i*w:(i+1)*w,column]-=derivative
                result[(i+1)*w:(i+2)*w,column]+=derivative
            else:
                derivative=self.face_derivative(pairs,lambda g,s:self.model.boundary_rate(g,s,at_time)[0],inverse)
                result[i*w:(i+1)*w,column]-=derivative
                result[n*w:(n+1)*w,column]+=derivative
        self.calls+=1
        return result.tocsc()
