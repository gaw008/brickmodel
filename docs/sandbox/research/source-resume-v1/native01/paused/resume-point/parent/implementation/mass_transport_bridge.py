"""Two rigid dry manufactured cells; kg solids, mol gases, shared total-U flux.

No liquid, boundary reservoir, moving mesh, event, adaptive or resume admission.
Diffusion uses face-temperature enthalpy, Darcy uses donor-temperature enthalpy.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
import math
from sludge_sandbox.mass_storage_bridge import MixedCell, MixedState, number, require
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.gas_transport import ideal_gas_state, face_exchange
from sludge_sandbox.exchanges import conduction_rate_w


@dataclass(frozen=True)
class SharedFace:
    area_m2: float
    half_widths_m: tuple
    conductivities_w_m_k: tuple
    diffusivities_m2_s: tuple
    permeability_m2: float
    viscosity_pa_s: float
    source_ids: tuple

    def __post_init__(self):
        number(self.area_m2, positive=True); number(self.viscosity_pa_s, positive=True)
        for values, positive in ((self.half_widths_m, True), (self.conductivities_w_m_k, False), (self.diffusivities_m2_s, False)):
            require(type(values) is tuple and len(values)==2, 'two_face_values')
            for v in values:
                require(number(v, positive=positive)>=0, 'negative_coefficient')
        require(number(self.permeability_m2)>=0, 'negative_permeability')
        require(type(self.source_ids) is tuple and self.source_ids and all(type(x) is str and x for x in self.source_ids), 'explicit_manufactured_face_sources')


@dataclass(frozen=True)
class PairRates:
    reactions: tuple
    gas_states: tuple
    exchange: object
    diffusive_enthalpy_w: tuple
    advective_enthalpy_w: tuple
    conduction_w: float
    face_energy_w: float
    solid_kg_s: tuple
    gas_mol_s: tuple
    energy_w: tuple


@dataclass(frozen=True)
class MixedPair:
    cells: tuple
    face: SharedFace
    _binding: str = field(init=False, repr=False)

    def __post_init__(self):
        require(type(self.cells) is tuple and len(self.cells)==2 and all(type(c) is MixedCell for c in self.cells), 'two_actual_mixed_cells')
        require(type(self.face) is SharedFace, 'typed_face_required')
        a,b=(c.storage for c in self.cells)
        require(a.reference==b.reference and a.solids==b.solids, 'shared_material_reference_required')
        require(_digest(a.fluid_template.gas_phases)==_digest(b.fluid_template.gas_phases), 'shared_gas_enthalpy_reference_required')
        require(a.fluid_template.mechanical.gas_constant_j_mol_k==b.fluid_template.mechanical.gas_constant_j_mol_k, 'shared_gas_constant')
        object.__setattr__(self,'_binding',self.binding())

    def binding(self):
        return _digest((tuple((c.storage.binding(), c.inverse_policy, c.rate_constant_per_s, c.oxygen_reference_mol, c.rate_source_ids) for c in self.cells), self.face))

    def evaluate(self, states: tuple) -> PairRates:
        require(type(states) is tuple and len(states)==2 and all(type(s) is MixedState for s in states), 'two_mixed_states')
        require(self.binding()==self._binding, 'pair_source_changed')
        reactions=tuple(c.evaluate(s) for c,s in zip(self.cells,states))
        gases=[]
        for c,s,r in zip(self.cells,states,reactions):
            st=c.storage; point=r.inverse.point
            masses={k:st.fluid_template.gas_phases[k].molar_mass_kg_mol for k in st.gas_ids}
            gases.append(ideal_gas_state(dict(zip(st.gas_ids,s.fluid_amounts_mol)),temperature_k=point.temperature_k,
                gas_volume_m3=point.pore_volume_m3,molar_masses_kg_mol=masses,gas_constant_j_mol_k=st.fluid_template.mechanical.gas_constant_j_mol_k))
        f=self.face; dl,dr=f.half_widths_m; names=self.cells[0].storage.gas_ids
        exchange=face_exchange(*gases,area_m2=f.area_m2,distance_m=dl+dr,face_left_weight=dr/(dl+dr),
            effective_diffusivities_m2_s=dict(zip(names,f.diffusivities_m2_s)),permeability_m2=f.permeability_m2,relative_permeability=1.,viscosity_pa_s=f.viscosity_pa_s)
        # Same actual source-bound gas curves used by the total-U inverse.
        phases=self.cells[0].storage.fluid_template.gas_phases
        diffuse=tuple(exchange.diffusive_mol_s[k]*phases[k].evaluate(exchange.face_temperature_k,gases[0].pressure_pa).enthalpy_j_mol for k in names)
        advect=tuple(0. if exchange.advective_mol_s[k]==0 else exchange.advective_mol_s[k]*phases[k].evaluate(exchange.advective_donor_temperature_k,gases[0].pressure_pa).enthalpy_j_mol for k in names)
        heat=conduction_rate_w(gases[0].temperature_k,gases[1].temperature_k,area_m2=f.area_m2,left_distance_m=dl,right_distance_m=dr,left_conductivity_w_m_k=f.conductivities_w_m_k[0],right_conductivity_w_m_k=f.conductivities_w_m_k[1])
        power=math.fsum((heat,*diffuse,*advect)); number(power)
        gas=tuple(tuple(math.fsum((r.gas_mol_s[j],sign*exchange.net_mol_s[k])) for j,k in enumerate(names)) for sign,r in zip((-1,1),reactions))
        require(self.binding()==self._binding, 'pair_source_changed')
        return PairRates(reactions,tuple(gases),exchange,diffuse,advect,heat,power,tuple(r.solid_kg_s for r in reactions),gas,(-power,power))


@dataclass(frozen=True)
class PairLedger:
    duration_s: F
    solid_kg: tuple
    reaction_gas_mol: tuple
    face_mol: tuple
    conduction_j: float
    diffusive_enthalpy_j: tuple
    advective_enthalpy_j: tuple
    face_energy_j: float


@dataclass(frozen=True)
class PairRun:
    status: str
    reason: str | None
    times_s: tuple
    states: tuple
    observations: tuple
    ledgers: tuple


def integrate_pair(pair: MixedPair, initial: tuple, *, duration_s: float, steps: int) -> PairRun:
    """Fixed midpoint verification path; failed trial leaves the accepted prefix.

    Shared face integrals are represented once then applied with opposite signs.
    Exact rational time partitions cover the requested represented duration.
    Physical inventories remain binary64, with explicit ledger roundoff to audit.
    """
    require(type(pair) is MixedPair and type(steps) is int and steps>0, 'explicit_pair_steps')
    h=F(number(duration_s,positive=True))/steps
    states=[initial]; times=[F()]; observations=[]; ledgers=[]
    def ledger(rate,dt):
        return PairLedger(dt,tuple(tuple(float(dt*F(v)) for v in row) for row in rate.solid_kg_s),
            tuple(tuple(float(dt*F(v)) for v in r.gas_mol_s) for r in rate.reactions),
            tuple(float(dt*F(rate.exchange.net_mol_s[k])) for k in pair.cells[0].storage.gas_ids),
            float(dt*F(rate.conduction_w)),tuple(float(dt*F(x)) for x in rate.diffusive_enthalpy_w),tuple(float(dt*F(x)) for x in rate.advective_enthalpy_w),float(dt*F(rate.face_energy_w)))
    def advance(old,l):
        return tuple(c.storage.state(tuple(float(F(a)+F(b)) for a,b in zip(s.solid_mass_kg,l.solid_kg[i])),
            tuple(float(F(a)+F(b)+sign*F(f)) for a,b,f in zip(s.fluid_amounts_mol,l.reaction_gas_mol[i],l.face_mol)),
            float(F(s.internal_energy_j)+sign*F(l.face_energy_j))) for i,(c,s,sign) in enumerate(zip(pair.cells,old,(-1,1))))
    try:
        for i in range(steps):
            first=pair.evaluate(states[-1]); mid=advance(states[-1],ledger(first,h/2)); rate=pair.evaluate(mid)
            l=ledger(rate,h); new=advance(states[-1],l); end=pair.evaluate(new)
            states.append(new);times.append((i+1)*h);observations.append(end);ledgers.append(l)
        return PairRun('completed',None,tuple(times),tuple(states),tuple(observations),tuple(ledgers))
    except (ValueError,OverflowError) as exc:
        return PairRun('failed',str(exc),tuple(times),tuple(states),tuple(observations),tuple(ledgers))
