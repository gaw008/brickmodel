"""Source-polynomial standard thermochemistry and a single-gas affinity.

Enthalpy uses formation enthalpy at Tref plus Cp integration; entropy uses
the absolute source entropy at Tref plus Cp/T integration. Elemental
reference terms cancel only in the explicitly balanced reaction. This
module supplies no rate law, mineral inventory or solid volume EOS.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RecordedThermalPhase:
    coefficients: tuple
    reference_temperature_k: float
    reference_enthalpy_j_mol: float
    reference_entropy_j_mol_k: float
    temperature_domain_k: tuple

    def standard(self, temperature_k):
        t=temperature_k;t0=self.reference_temperature_k
        if not self.temperature_domain_k[0]<=t<=self.temperature_domain_k[1]:
            raise ValueError('temperature outside the selected source phase domain')
        a,b,c,d,e=self.coefficients
        cp=a+b*t+c/t**2+d/math.sqrt(t)+e*t**2
        dh=a*(t-t0)+b*(t*t-t0*t0)/2+c*(1/t0-1/t)+2*d*(math.sqrt(t)-math.sqrt(t0))+e*(t**3-t0**3)/3
        ds=a*math.log(t/t0)+b*(t-t0)+c*(1/t0**2-1/t**2)/2+2*d*(1/math.sqrt(t0)-1/math.sqrt(t))+e*(t*t-t0*t0)/2
        h=self.reference_enthalpy_j_mol+dh;s=self.reference_entropy_j_mol_k+ds
        return {'temperature_k':t,'cp_j_mol_k':cp,'enthalpy_j_mol':h,'entropy_j_mol_k':s,
            'gibbs_j_mol':h-t*s,'sensible_enthalpy_j_mol':dh}


@dataclass(frozen=True)
class RecordedSingleGasReaction:
    phases: dict
    stoichiometry: dict
    gas_phase: str
    gas_constant_j_mol_k: float
    standard_pressure_pa: float
    total_pressure_pa: float

    def standard(self, temperature_k):
        states={k:p.standard(temperature_k) for k,p in self.phases.items()}
        totals={key:math.fsum(self.stoichiometry[k]*s[key] for k,s in states.items())
            for key in ('cp_j_mol_k','enthalpy_j_mol','entropy_j_mol_k','gibbs_j_mol')}
        return {'temperature_k':temperature_k,'phases':states,'reaction':totals}

    def affinity(self, temperature_k, gas_partial_pressure_pa):
        if not 0<gas_partial_pressure_pa<=self.total_pressure_pa:
            raise ValueError('gas partial pressure must be positive and no greater than the declared total pressure')
        record=self.standard(temperature_k);r=self.gas_constant_j_mol_k
        nu=self.stoichiometry[self.gas_phase];dg=record['reaction']['gibbs_j_mol']
        actual=dg+nu*r*temperature_k*math.log(gas_partial_pressure_pa/self.standard_pressure_pa)
        equilibrium=self.standard_pressure_pa*math.exp(-dg/(nu*r*temperature_k))
        return {**record,'gas_partial_pressure_pa':gas_partial_pressure_pa,
            'reaction_gibbs_j_mol_extent':actual,'affinity_j_mol_extent':-actual,
            'equilibrium_gas_pressure_pa':equilibrium,
            'equilibrium_pressure_within_total_pressure':equilibrium<=self.total_pressure_pa}
