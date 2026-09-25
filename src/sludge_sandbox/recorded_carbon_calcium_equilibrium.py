"""Coupled finite Ca/C/O inventory equilibrium at source standard pressure.

The declared input domain has Ctotal>Catotal, Ototal>3Catotal and N2>0.
Pure calcite/lime/graphite and ideal CO/CO2/O2/N2 only; no reaction rates.
"""
import math

import numpy as np
from scipy.optimize import brentq


class RecordedCarbonCalciumEquilibrium:
    def __init__(self,carbon_model,calcite_phase,lime_phase,parameters):
        self.carbon=carbon_model;self.phases={**carbon_model.phases,'calcite':calcite_phase,'lime':lime_phase}
        self.parameters=parameters;self.r=carbon_model.r;self.p0=carbon_model.p0

    def at_temperature(self,temperature_k,calcium_atoms_mol,carbon_atoms_mol,oxygen_atoms_mol,nitrogen_molecules_mol):
        t=temperature_k;ca=calcium_atoms_mol;ct=carbon_atoms_mol;ot=oxygen_atoms_mol;nn=nitrogen_molecules_mol
        thermal={name:phase.standard(t) for name,phase in self.phases.items()}
        def partition(fraction):
            a=ca*fraction;gas=self.carbon.at_temperature(t,ct-a,ot-ca-2*a,nn)
            affinity=thermal['lime']['gibbs_j_mol']+gas['chemical_potentials_j_mol']['CO2']-thermal['calcite']['gibbs_j_mol']
            return gas,affinity
        gas,affinity=partition(1.)
        if affinity>=0:
            fraction=1.;calcium_phase='calcite'
        else:
            gas,affinity=partition(0.)
            if affinity<=0:
                fraction=0.;calcium_phase='lime'
            else:
                policy=self.parameters['equilibrium_numerics'];calcium_phase='coexistence'
                fraction=brentq(lambda value:partition(value)[1],0.,1.,xtol=policy['calcite_fraction_absolute_tolerance'],
                    rtol=policy['calcite_fraction_relative_tolerance'],maxiter=policy['maximum_root_iterations'])
                gas,affinity=partition(fraction)
        amounts={'calcite':ca*fraction,'lime':ca*(1-fraction),**gas['amounts_mol']}
        enthalpy=math.fsum(n*thermal[name]['enthalpy_j_mol'] for name,n in amounts.items())
        entropy=math.fsum((gas['entropy_j_k'],amounts['calcite']*thermal['calcite']['entropy_j_mol_k'],amounts['lime']*thermal['lime']['entropy_j_mol_k']))
        frozen_cp=math.fsum(n*thermal[name]['cp_j_mol_k'] for name,n in amounts.items())
        if calcium_phase=='coexistence':
            names=self.parameters['phase_order'];basis=self.parameters['coexistence_basis'][gas['phase']]
            stoichiometry=np.array([[self.parameters['reaction_stoichiometry'][reaction][name] for reaction in basis] for name in names])
            gas_names=['CO','CO2','O2','N2'];gas_stoichiometry=np.array([stoichiometry[names.index(name)] for name in gas_names])
            gas_amounts=np.array([amounts[name] for name in gas_names]);gas_change=np.sum(gas_stoichiometry,axis=0)
            matrix=self.r*t*(gas_stoichiometry.T@np.diag(1/gas_amounts)@gas_stoichiometry-np.outer(gas_change,gas_change)/sum(gas_amounts))
            reaction_h=stoichiometry.T@np.array([thermal[name]['enthalpy_j_mol'] for name in names])
            extent_rates=np.linalg.solve(matrix,reaction_h/t)
            derivatives=dict(zip(names,map(float,stoichiometry@extent_rates),strict=True));reaction_cp=float(reaction_h@extent_rates)
        else:
            derivatives={'calcite':0.,'lime':0.,**gas['amount_temperature_derivatives_mol_k']};reaction_cp=gas['reaction_capacity_j_k'];basis=[]
        elements={'Ca':amounts['calcite']+amounts['lime'],
            'C':math.fsum(amounts[name] for name in ['calcite','C','CO','CO2']),
            'O':math.fsum((3*amounts['calcite'],amounts['lime'],amounts['CO'],2*amounts['CO2'],2*amounts['O2'])),'N':2*amounts['N2']}
        return {'temperature_k':t,'pressure_pa':self.p0,'calcium_phase':calcium_phase,'carbon_phase':gas['phase'],
            'amounts_mol':amounts,'calcite_fraction':fraction,'partial_pressures_pa':gas['partial_pressures_pa'],
            'chemical_potentials_j_mol':{**gas['chemical_potentials_j_mol'],'calcite':thermal['calcite']['gibbs_j_mol'],'lime':thermal['lime']['gibbs_j_mol']},
            'calcination_gibbs_j_mol':affinity,'carbon_reaction_gibbs_j_mol':gas['reaction_gibbs_j_mol_extent'],
            'enthalpy_j':enthalpy,'entropy_j_k':entropy,'gibbs_j':enthalpy-t*entropy,'gas_volume_m3':gas['gas_volume_m3'],
            'frozen_cp_j_k':frozen_cp,'reaction_capacity_j_k':reaction_cp,'equilibrium_cp_j_k':frozen_cp+reaction_cp,
            'amount_temperature_derivatives_mol_k':derivatives,'coexistence_reaction_basis':basis,'element_amounts_mol':elements}
