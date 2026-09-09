"""Two positive-liquid rigid kg/mol cells with source water phase exchange.

Manufactured solids/kinetics/transport only. This is NOT a dry-event integrator.
"""
from dataclasses import dataclass,field
from fractions import Fraction as F
import math,time
from sludge_sandbox.mass_wet_storage import WetMixedStorage,WetMixedState
from sludge_sandbox.mass_storage_bridge import number,require
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.gas_transport import ideal_gas_state,face_exchange
from sludge_sandbox.exchanges import conduction_rate_w


def represented(value):
    """Finite signed integral; never silently underflow a nonzero amount."""
    v=number(value)
    require(value==0 or v!=0,'nonzero_integral_underflow')
    return v


@dataclass(frozen=True)
class WetFace:
    area_m2: float
    half_widths_m: tuple
    conductivities_w_m_k: tuple
    diffusivities_m2_s: tuple
    permeability_m2: float
    viscosity_pa_s: float
    source_ids: tuple
    def __post_init__(self):
        number(self.area_m2,positive=True);number(self.viscosity_pa_s,positive=True)
        for row,n,positive in ((self.half_widths_m,2,True),(self.conductivities_w_m_k,2,False),(self.diffusivities_m2_s,3,False)):
            require(type(row) is tuple and len(row)==n,'explicit_wet_face_layout')
            for v in row:require(number(v,positive=positive)>=0 and v>=0 and (v==0 or represented(v)!=0),'negative_face_coefficient')
        require(represented(self.permeability_m2)>=0 and self.permeability_m2>=0,'negative_permeability')
        require(type(self.source_ids) is tuple and self.source_ids and all(type(v) is str and v for v in self.source_ids),'face_sources')


@dataclass(frozen=True)
class WetCellRate:
    inverse: object
    extent_kg_s: float
    phase_water_mol_s: float
    water_partial_pressure_pa: float
    equilibrium: object
    chemical_driving_force_j_mol: float | None
    entropy_production_w_k: float | None
    solid_kg_s: tuple
    reaction_gas_mol_s: tuple
    chemical_reference_power_w: float


@dataclass(frozen=True)
class WetRates:
    cells: tuple
    gas_states: tuple
    exchange: object
    conduction_w: float
    diffusive_enthalpy_w: tuple
    advective_enthalpy_w: tuple
    face_energy_w: float


@dataclass(frozen=True)
class WetPair:
    storages: tuple
    inverse_policies: tuple
    chemical: WaterChemicalPotential
    rate_constants_per_s: tuple
    oxygen_references_mol: tuple
    transfer_coefficients_mol_s_pa: tuple
    coefficient_source_ids: tuple
    face: WetFace
    _identity: str=field(init=False,repr=False)

    def __post_init__(self):
        require(type(self.storages) is tuple and len(self.storages)==2 and all(type(s) is WetMixedStorage for s in self.storages),'two_actual_wet_storages')
        require(type(self.inverse_policies) is tuple and len(self.inverse_policies)==2 and all(type(p) is InversePolicy for p in self.inverse_policies),'two_inverse_policies')
        require(type(self.chemical) is WaterChemicalPotential and type(self.face) is WetFace,'actual_chemical_and_face_required')
        for row,positive in ((self.rate_constants_per_s,False),(self.oxygen_references_mol,True),(self.transfer_coefficients_mol_s_pa,False)):
            require(type(row) is tuple and len(row)==2,'two_coefficient_values')
            for v in row:require(number(v,positive=positive)>=0 and v>=0 and (v==0 or represented(v)!=0),'negative_rate_coefficient')
        require(type(self.coefficient_source_ids) is tuple and self.coefficient_source_ids and all(type(x) is str and x for x in self.coefficient_source_ids),'rate_sources')
        a,b=self.storages
        require(a.reference==b.reference and a.solids==b.solids,'common_wet_material_reference')
        require(_digest(a.fluid_template.gas_phases)==_digest(b.fluid_template.gas_phases),'common_gas_caloric_source')
        for st in self.storages:
            net=st.reference.network
            require(st.solid_ids==('A','B') and len(net.reactions)==1 and net.reactions[0].mass_change_kg_per_kg_extent==(-1,2,-1,0,0),'explicit_AB_finite_oxygen_reaction')
            w=st.water;c=self.chemical
            require(c.reference==w.reference and c.source_asset_sha256==w.source_asset_sha256 and c.gas_constant_j_mol_k==st.fluid_template.mechanical.gas_constant_j_mol_k,'thermal_chemical_source_mismatch')
            for cw in (c.water,c.vapor._water):
                require(type(cw) is type(w) and cw.implementation==w.implementation,'thermal_chemical_backend_mismatch')
        object.__setattr__(self,'_identity',self.binding())

    def binding(self):
        c=self.chemical
        backends=tuple((type(w).__module__,type(w).__qualname__,w.implementation) for w in (c.water,c.vapor._water))
        return _digest((tuple(s.binding() for s in self.storages),self.inverse_policies,c,backends,(c.reference_pressure_pa,c.method_id,c.caloric_method_id,c.gas_constant_j_mol_k,c.temperature_range_k),self.rate_constants_per_s,self.oxygen_references_mol,self.transfer_coefficients_mol_s_pa,self.coefficient_source_ids,self.face))

    def evaluate(self,states):
        require(type(states) is tuple and len(states)==2 and all(type(s) is WetMixedState for s in states),'two_wet_states')
        require(self.binding()==self._identity,'wet_pair_source_changed')
        rows=[];gases=[]
        for i,(st,s,ip) in enumerate(zip(self.storages,states,self.inverse_policies)):
            require(s.liquid_water_mol>0,'positive_liquid_segment_only')
            inv=st.invert(s,ip);p=inv.point;t=p.temperature_k
            extent=represented(F(self.rate_constants_per_s[i])*F(s.solid_mass_kg[0])*F(s.gas_amounts_mol[0])/F(self.oxygen_references_mol[i]))
            po=represented(F(s.gas_amounts_mol[2])*F(self.chemical.gas_constant_j_mol_k)*F(t)/F(p.gas_volume_m3))
            equilibrium=self.chemical.equilibrium_at_liquid_tp(t,p.fluid.mechanical.liquid_pressure_pa)
            peq=equilibrium.equilibrium_partial_pressure_pa
            phase=represented(F(self.transfer_coefficients_mol_s_pa[i])*(F(peq)-F(po)))
            if po==0:mu=entropy=None
            else:
                log=math.log1p((peq-po)/po) if abs(peq-po)<.5*po else math.log(peq)-math.log(po)
                mu=represented(F(self.chemical.gas_constant_j_mol_k)*F(t)*F(log))
                require(peq==po or mu!=0,'chemical_drive_unresolvable')
                entropy=represented(F(phase)*F(mu)/F(t));require(entropy>=0,'phase_direction_entropy')
            mo=st.fluid_template.gas_phases['O2'].molar_mass_kg_mol
            q=st.reference.identified_value(st.reference.network.reactions[0].mass_change_kg_per_kg_extent)
            rows.append(WetCellRate(inv,extent,phase,po,equilibrium,mu,entropy,(-extent,represented(2*F(extent))),(-represented(F(extent)/F(mo)),0.,0.),represented(q*F(extent))))
            masses={k:st.fluid_template.gas_phases[k].molar_mass_kg_mol for k in st.gas_ids}
            gases.append(ideal_gas_state(dict(zip(st.gas_ids,s.gas_amounts_mol)),temperature_k=t,gas_volume_m3=p.gas_volume_m3,molar_masses_kg_mol=masses,gas_constant_j_mol_k=self.chemical.gas_constant_j_mol_k))
        f=self.face;dl,dr=f.half_widths_m;names=self.storages[0].gas_ids
        ex=face_exchange(*gases,area_m2=f.area_m2,distance_m=dl+dr,face_left_weight=dr/(dl+dr),effective_diffusivities_m2_s=dict(zip(names,f.diffusivities_m2_s)),permeability_m2=f.permeability_m2,relative_permeability=1.,viscosity_pa_s=f.viscosity_pa_s)
        phases=self.storages[0].fluid_template.gas_phases
        diff=tuple(ex.diffusive_mol_s[k]*phases[k]._curve.enthalpy_j_mol(ex.face_temperature_k) for k in names)
        adv=tuple(0. if ex.advective_mol_s[k]==0 else ex.advective_mol_s[k]*phases[k]._curve.enthalpy_j_mol(ex.advective_donor_temperature_k) for k in names)
        heat=conduction_rate_w(gases[0].temperature_k,gases[1].temperature_k,area_m2=f.area_m2,left_distance_m=dl,right_distance_m=dr,left_conductivity_w_m_k=f.conductivities_w_m_k[0],right_conductivity_w_m_k=f.conductivities_w_m_k[1])
        power=number(math.fsum((heat,*diff,*adv)))
        require(self.binding()==self._identity,'wet_pair_source_changed')
        return WetRates(tuple(rows),tuple(gases),ex,heat,diff,adv,power)


@dataclass(frozen=True)
class WetLedger:
    duration_s: F
    solid_kg: tuple
    chemical_gas_mol: tuple
    phase_water_mol: tuple
    face_mol: tuple
    conduction_j: float
    diffusive_enthalpy_j: tuple
    advective_enthalpy_j: tuple
    face_energy_j: float


@dataclass(frozen=True)
class WetRun:
    status: str
    reason: str | None
    times_s: tuple
    states: tuple
    observations: tuple
    ledgers: tuple
    evaluations_attempted: int
    evaluations_completed: int
    elapsed_seconds: float


def integrate_wet_pair(pair,initial,*,duration_s,steps,maximum_wall_seconds=30.,cancel=None):
    """Bounded fixed midpoint segment before depletion; atomic accepted prefixes."""
    require(type(pair) is WetPair and type(steps) is int and steps>0,'explicit_wet_steps')
    h=F(number(duration_s,positive=True))/steps;wall=number(maximum_wall_seconds,positive=True)
    start=time.monotonic();states=[initial];times=[F()];obs=[];ledgers=[];attempted=completed=0
    def evaluate(s):
        nonlocal attempted,completed
        if cancel is not None and cancel():raise InterruptedError('cancel_requested')
        if time.monotonic()-start>wall:raise TimeoutError('wall_budget_exceeded')
        attempted+=1;out=pair.evaluate(s);completed+=1
        if time.monotonic()-start>wall:raise TimeoutError('wall_budget_exceeded')
        return out
    def ledger(r,dt):
        scaled=lambda x:represented(dt*F(x))
        return WetLedger(dt,tuple(tuple(map(scaled,c.solid_kg_s)) for c in r.cells),tuple(tuple(map(scaled,c.reaction_gas_mol_s)) for c in r.cells),tuple(scaled(c.phase_water_mol_s) for c in r.cells),tuple(scaled(r.exchange.net_mol_s[k]) for k in pair.storages[0].gas_ids),scaled(r.conduction_w),tuple(map(scaled,r.diffusive_enthalpy_w)),tuple(map(scaled,r.advective_enthalpy_w)),scaled(r.face_energy_w))
    def advance(old,l):
        result=[]
        for i,(st,s,sign) in enumerate(zip(pair.storages,old,(-1,1))):
            masses=tuple(F(a)+F(b) for a,b in zip(s.solid_mass_kg,l.solid_kg[i]))
            gas=tuple(F(a)+F(b)+sign*F(face)+(F(l.phase_water_mol[i]) if j==2 else 0) for j,(a,b,face) in enumerate(zip(s.gas_amounts_mol,l.chemical_gas_mol[i],l.face_mol)))
            liquid=F(s.liquid_water_mol)-F(l.phase_water_mol[i])
            require(all(v>=0 for v in (*masses,*gas)) and liquid>0,'positive_liquid_segment_or_inventory_exit')
            result.append(st.state(tuple(map(represented,masses)),represented(liquid),tuple(map(represented,gas)),represented(F(s.internal_energy_j)+sign*F(l.face_energy_j))))
        return tuple(result)
    status='completed';reason=None
    try:
        for i in range(steps):
            first=evaluate(states[-1]);mid=advance(states[-1],ledger(first,h/2));middle=evaluate(mid)
            l=ledger(middle,h);new=advance(states[-1],l);last=evaluate(new)
            states.append(new);times.append((i+1)*h);obs.append(last);ledgers.append(l)
    except InterruptedError as exc:status='cancelled';reason=str(exc)
    except TimeoutError as exc:status='resource_limit';reason=str(exc)
    except (ValueError,OverflowError) as exc:status='failed';reason=str(exc)
    return WetRun(status,reason,tuple(times),tuple(states),tuple(obs),tuple(ledgers),attempted,completed,time.monotonic()-start)
