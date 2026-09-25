"""Finite-inventory C/CO/CO2/O2/N2 equilibrium at source standard pressure.

Pure reference graphite, ideal gases, inert nitrogen and instantaneous restricted
chemical equilibrium. No char kinetics, ignition, other chemical species or
solid pressure/volume extension is supplied.
"""
import math

import numpy as np
from scipy.optimize import brentq


class RecordedCarbonGasEquilibrium:
    def __init__(self,phases,gas_constant_j_mol_k,standard_pressure_pa,numerics):
        self.phases=phases;self.r=gas_constant_j_mol_k;self.p0=standard_pressure_pa;self.numerics=numerics

    def from_enthalpy(self,enthalpy_j,carbon_atoms_mol,oxygen_atoms_mol,nitrogen_molecules_mol,inverse_numerics):
        inputs=(carbon_atoms_mol,oxygen_atoms_mol,nitrogen_molecules_mol)
        temperature=brentq(lambda t:self.at_temperature(t,*inputs)['enthalpy_j']-enthalpy_j,
            *self.phases['C'].temperature_domain_k,xtol=inverse_numerics['temperature_absolute_tolerance_k'],
            rtol=inverse_numerics['temperature_relative_tolerance'],maxiter=inverse_numerics['maximum_root_iterations'])
        return self.at_temperature(temperature,*inputs)

    def at_temperature(self,temperature_k,carbon_atoms_mol,oxygen_atoms_mol,nitrogen_molecules_mol):
        t=temperature_k;rt=self.r*t
        states={name:phase.standard(t) for name,phase in self.phases.items()}
        g={name:state['gibbs_j_mol'] for name,state in states.items()}
        ln_k1=-(g['CO']-g['C']-g['O2']/2)/rt
        ln_k2=-(g['CO2']-g['C']-g['O2'])/rt
        k1,k2=math.exp(ln_k1),math.exp(ln_k2)
        c=carbon_atoms_mol/nitrogen_molecules_mol;o=oxygen_atoms_mol/nitrogen_molecules_mol
        a=(o+2)*(k2+1);b=(o+1)*k1
        q=2*o/(b+math.sqrt(b*b+4*a*o))
        pressures={'CO':k1*q,'CO2':k2*q*q,'O2':q*q}
        pressures['N2']=(pressures['CO']+2*pressures['CO2']+2*pressures['O2'])/o
        gas={name:nitrogen_molecules_mol*value/pressures['N2'] for name,value in pressures.items()}
        gas['N2']=nitrogen_molecules_mol
        carbon_required=math.fsum((gas['CO'],gas['CO2']))
        if carbon_atoms_mol>=carbon_required:
            carbon_solid=carbon_atoms_mol-carbon_required;phase='graphite_present'
        else:
            phase='graphite_exhausted';carbon_solid=0.;delta=o-c;ln_k3=ln_k2-ln_k1
            # The stoichiometric oxygen excess bounds this monotone scalar root.
            # At the lower bound, the CO2 contribution and 2*z each use at most
            # delta/4; at z=delta/2 the residual is the positive CO2 contribution.
            lower=min(math.log(delta/8),2*math.log(delta)+math.log1p(c)-math.log(16)-2*math.log(c)-2*ln_k3)
            upper=math.log(delta/2)
            def residual(log_z):
                z=math.exp(log_z);w=math.exp(ln_k3)*math.sqrt(z/(1+c+z))
                return c*(1+w/(1+w))+2*z-o
            z=math.exp(brentq(residual,lower,upper,xtol=self.numerics['log_oxygen_absolute_tolerance'],
                rtol=self.numerics['log_oxygen_relative_tolerance'],maxiter=self.numerics['maximum_root_iterations']))
            q=math.sqrt(z/(1+c+z));w=math.exp(ln_k3)*q
            gas={'CO':carbon_atoms_mol/(1+w),'CO2':carbon_atoms_mol*w/(1+w),
                 'O2':nitrogen_molecules_mol*z,'N2':nitrogen_molecules_mol}
            pressures={'N2':1/(1+c+z),'O2':z/(1+c+z),'CO':c/((1+c+z)*(1+w)),
                       'CO2':c*w/((1+c+z)*(1+w))}
        amounts={'C':carbon_solid,**gas}
        entropy=carbon_solid*states['C']['entropy_j_mol_k']
        mu={'C':g['C']}
        for name,value in pressures.items():
            logarithm=math.log(value)
            entropy+=gas[name]*(states[name]['entropy_j_mol_k']-self.r*logarithm)
            mu[name]=g[name]+rt*logarithm
        enthalpy=math.fsum(amounts[name]*state['enthalpy_j_mol'] for name,state in states.items())
        reaction_gibbs={'C_halfO2_to_CO':mu['CO']-mu['C']-mu['O2']/2,
                        'C_O2_to_CO2':mu['CO2']-mu['C']-mu['O2'],
                        'CO_halfO2_to_CO2':mu['CO2']-mu['CO']-mu['O2']/2}
        h={name:state['enthalpy_j_mol'] for name,state in states.items()};ng=math.fsum(gas.values())
        frozen_cp=math.fsum(amounts[name]*state['cp_j_mol_k'] for name,state in states.items())
        if phase=='graphite_present':
            # C+CO2 -> 2CO and C+O2 -> CO2 separate the small-O2 direction.
            # This avoids subtracting two enormous entries of the oxygen mode.
            matrix=rt*np.array([[4/gas['CO']+1/gas['CO2']-1/ng,-1/gas['CO2']],
                [-1/gas['CO2'],1/gas['CO2']+1/gas['O2']]])
            delta_h=np.array([2*h['CO']-h['CO2']-h['C'],h['CO2']-h['O2']-h['C']])
            b_rate,o_rate=map(float,np.linalg.solve(matrix,delta_h/t))
            derivatives={'C':-b_rate-o_rate,'CO':2*b_rate,'CO2':-b_rate+o_rate,'O2':-o_rate,'N2':0.}
            reaction_cp=float(delta_h@np.array([b_rate,o_rate]))
        else:
            curvature=rt*(1/gas['CO']+1/gas['CO2']+.25/gas['O2']-.25/ng)
            delta_h=h['CO2']-h['CO']-h['O2']/2;extent_rate=delta_h/(t*curvature)
            derivatives={'C':0.,'CO':-extent_rate,'CO2':extent_rate,'O2':-extent_rate/2,'N2':0.}
            reaction_cp=delta_h*extent_rate
        return {'temperature_k':t,'pressure_pa':self.p0,'phase':phase,'amounts_mol':amounts,
            'partial_pressures_pa':{name:self.p0*value for name,value in pressures.items()},
            'chemical_potentials_j_mol':mu,'reaction_gibbs_j_mol_extent':reaction_gibbs,
            'enthalpy_j':enthalpy,'entropy_j_k':entropy,'gibbs_j':enthalpy-t*entropy,
            'gas_volume_m3':ng*rt/self.p0,
            'frozen_cp_j_k':frozen_cp,'equilibrium_cp_j_k':frozen_cp+reaction_cp,
            'reaction_capacity_j_k':reaction_cp,'amount_temperature_derivatives_mol_k':derivatives,
            'graphite_branch_required_carbon_mol':carbon_required,
            'ln_equilibrium_constants':{'C_halfO2_to_CO':ln_k1,'C_O2_to_CO2':ln_k2},
            'element_amounts_mol':{'C':math.fsum((carbon_solid,gas['CO'],gas['CO2'])),
                'O':math.fsum((gas['CO'],2*gas['CO2'],2*gas['O2'])),'N':2*gas['N2']}}
