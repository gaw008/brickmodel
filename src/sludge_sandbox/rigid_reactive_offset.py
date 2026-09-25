"""The same rigid equilibrium expressed with C minus the fixed Ca inventory.

Keeping the carbon offset separately resolves trace gas / last solid amounts
that cannot be recovered by subtracting two nearby total inventories.
"""
import math

from scipy.optimize import brentq

from .equilibrium_calcite_rigid import RigidCalciteMixture


class OffsetRigidCalciteMixture(RigidCalciteMixture):
    def at_carbon_offset(self,t,offset,nitrogen_mol,total_carbon_mol=None):
        c = self.calcium+offset if total_carbon_mol is None else total_carbon_mol
        rt = self.reaction.gas_constant_j_mol_k*t
        dg = self.reaction.standard(t)['reaction']['gibbs_j_mol'];policy = self.config['numerics']
        base = self.volume-self.calcium*self.vc-offset*self.dv
        def pressure(g):
            vg = base+g*self.dv
            return (g+nitrogen_mol)*rt/vg,g*rt/vg
        def score(g):
            p,pc = pressure(g)
            return dg-(p-self.p0)*self.dv+rt*math.log(pc/self.p0)
        if score(c)<=0.:
            g = c;calcite = 0.;lime = self.calcium;phase = 'lime'
        elif offset>0. and score(offset)>=0.:
            g = offset;calcite = self.calcium;lime = 0.;phase = 'calcite'
        else:
            if offset>0.:
                log_left = math.log(offset)
            else:
                p_left = nitrogen_mol*rt/base;p_right = pressure(c)[0]
                log_left = math.log(self.p0*base/rt)-dg/rt+(min(p_left,p_right)-self.p0)*self.dv/rt-policy['log_gas_bracket_padding']
            g = math.exp(brentq(lambda value:score(math.exp(value)),log_left,math.log(c),
                xtol=policy['log_gas_root_absolute_tolerance'],rtol=policy['log_gas_root_relative_tolerance'],maxiter=policy['log_gas_root_iterations']))
            lime = g-offset
            calcite = self.calcium-lime if total_carbon_mol is None else c-g
            phase = 'coexistence'
        state = self.inventory_partition(t,c,nitrogen_mol,g,calcite,lime,phase)
        state['carbon_offset_mol'] = offset
        state['carbon_offset_closure_residual_mol'] = math.fsum((g,-lime,-offset))
        return state

    def offset_inventory_state(self,carbon_offset_mol,nitrogen_mol,internal_energy_j,total_carbon_mol=None):
        p = self.config['numerics']
        t = brentq(lambda value:self.at_carbon_offset(value,carbon_offset_mol,nitrogen_mol,total_carbon_mol)['internal_energy_j']-internal_energy_j,*self.domain,
            xtol=p['temperature_inverse_absolute_k'],rtol=p['temperature_inverse_relative'],maxiter=p['temperature_inverse_iterations'])
        state = self.at_carbon_offset(t,carbon_offset_mol,nitrogen_mol,total_carbon_mol)
        state['constitutive_internal_energy_j'] = state['internal_energy_j'];state['internal_energy_j'] = internal_energy_j
        return state
