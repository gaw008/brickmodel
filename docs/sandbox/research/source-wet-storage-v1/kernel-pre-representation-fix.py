"""Explicit kg-solid/mol-liquid/mol-gas rigid wet storage, manufactured solids.

Source water supplies its common liquid/vapor energy reference. No separate
latent-heat or reaction-heat source is added to total internal energy.
"""
from dataclasses import dataclass, replace, field
from fractions import Fraction as F
import math
from sludge_sandbox.mass_storage_bridge import MassSolid, MixedError, number, upper, require
from sludge_sandbox.rigid_storage import RigidStorage, ClosedStorageState
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.reaction_reference import ReferenceSolution
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.deforming_solid_storage import _digest


def lower(v: F) -> float:
    x=number(v,positive=True)
    return math.nextafter(x,-math.inf) if F(x)>v else x


def inventory(value):
    converted=number(value)
    require(F(value)>=0,'negative_inventory')
    require(F(value)==0 or converted>0,'inventory_underflow')
    return converted


def inventories(values):
    require(type(values) is tuple and bool(values),'explicit_inventory_tuple')
    return tuple(inventory(value) for value in values)


@dataclass(frozen=True)
class WetFluidEvaluation:
    """Actual fluid closure and outward-rounded volume-induced pressure bounds."""
    fluid_template: RigidStorage
    point: ClosedStorageState
    global_pressure_error_pa: F
    extra_pressure_error_pa: F
    pressure_error_pa: float


def evaluate_wet_fluid(
    template: RigidStorage, gas_ids: tuple[str, ...], liquid_mol: float,
    gas_amounts: tuple[float, ...], temperature_k: float,
    nominal_available_m3: float, available_error_m3: F,
) -> WetFluidEvaluation:
    """Close a prescribed available volume without changing solid accounting.

    The caller supplies its nominal volume and exact nonnegative error, and
    certifies the positive-volume interval. No solid law or material admission
    is inferred here. Global then local gas-compliance bounds retain the
    existing outward rounding, including the zero-volume-error case.
    """
    require(type(template) is RigidStorage, 'explicit_fluid_template')
    require(type(gas_ids) is tuple and gas_ids == tuple(template.mechanical.gas_species_ids), 'fluid_gas_order')
    require(type(gas_amounts) is tuple and len(gas_amounts) == len(gas_ids), 'fluid_inventory_shape')
    inventory(liquid_mol)
    inventories(gas_amounts)
    t=number(temperature_k,positive=True)
    number(nominal_available_m3,positive=True)
    number(available_error_m3)
    require(F(available_error_m3)>=0, 'negative_available_volume_error')
    available_error_m3=F(available_error_m3)
    fluid=replace(template,mechanical=replace(template.mechanical,available_pore_volume_m3=nominal_available_m3))
    out=fluid.evaluate_at_temperature(t,liquid_mol,dict(zip(gas_ids,gas_amounts)))
    p=F(out.mechanical.pressure_pa);ng=sum(map(F,gas_amounts),F());rt=F(fluid.mechanical.gas_constant_j_mol_k)*F(t)
    require(ng>0,'no_positive_gas_compliance')
    extra=F(upper(available_error_m3/(ng*rt/F(fluid.envelope.pressure_range_pa[1])**2)))
    global_error=F(upper(F(out.pressure_error_bound_pa)+extra))
    plo,phi=map(F,fluid.mechanical.pressure_bracket_pa)
    require(plo<=p-global_error<=p+global_error<=phi,'global_pressure_uncertainty_outside_domain')
    certified_upper=min(F(fluid.envelope.pressure_range_pa[1]),p+global_error)
    extra=F(upper(available_error_m3/(ng*rt/certified_upper**2)))
    pressure_error=upper(F(out.pressure_error_bound_pa)+extra)
    require(plo<=p-F(pressure_error)<=p+F(pressure_error)<=phi,'local_pressure_uncertainty_outside_domain')
    return WetFluidEvaluation(fluid,out,global_error,extra,pressure_error)


def check_wet_water(fluid_template: RigidStorage, water_element_convention: "WaterElementConvention") -> None:
    """Require the existing shared liquid/vapor source, mass, and R convention."""
    vapor=fluid_template.gas_phases['H2O'].caloric
    require(type(vapor) is IdealWaterVapor,'source_bound_low_water_bridge_required')
    w=fluid_template.mechanical.water;vw=vapor._water
    require(vapor.reference==w.reference and vapor.source_asset_sha256==w.source_asset_sha256,'same_liquid_vapor_water_source')
    require(type(vw) is type(w) and vw.implementation==w.implementation,'same_actual_water_backend')
    require(vapor.molar_mass_kg_mol==w.reference.molar_mass_kg_mol and vapor.gas_constant_j_mol_k==fluid_template.mechanical.gas_constant_j_mol_k,'same_water_molar_and_R')
    require(type(water_element_convention) is WaterElementConvention,'explicit_water_element_convention')


@dataclass(frozen=True)
class WetMixedState:
    solid_mass_kg: tuple
    liquid_water_mol: float
    gas_amounts_mol: tuple
    internal_energy_j: float
    energy_model_identity: str

    def __post_init__(self):
        object.__setattr__(self,'solid_mass_kg',inventories(self.solid_mass_kg))
        object.__setattr__(self,'gas_amounts_mol',inventories(self.gas_amounts_mol))
        liquid=inventory(self.liquid_water_mol)
        object.__setattr__(self,'liquid_water_mol',liquid)
        object.__setattr__(self,'internal_energy_j',number(self.internal_energy_j))
        require(type(self.energy_model_identity) is str and len(self.energy_model_identity)==64,'wet_model_identity')


@dataclass(frozen=True)
class WetMixedPoint:
    fluid: ClosedStorageState
    total_internal_energy_j: float
    total_enthalpy_j: float
    solid_internal_energy_j: tuple
    solid_volume_m3: float
    available_pore_volume_m3: float
    available_volume_error_m3: float
    global_pressure_error_pa: float
    extra_pressure_error_pa: float
    pressure_error_pa: float
    energy_error_j: float
    closed_heat_capacity_j_k: float
    minimum_heat_capacity_j_k: float
    model_identity: str
    qualification: str='manufactured_solids_and_conditional_declared_water_numerical_envelope_not_material_admission'

    @property
    def temperature_k(self):return self.fluid.mechanical.temperature_k

    @property
    def pressure_pa(self):return self.fluid.mechanical.pressure_pa

    @property
    def gas_volume_m3(self):return self.fluid.mechanical.gas_volume_m3


@dataclass(frozen=True)
class WetMixedInverse:
    point: WetMixedPoint
    target_energy_j: float
    energy_residual_j: float
    temperature_error_bound_k: float
    final_temperature_bracket_k: tuple
    iterations: int


@dataclass(frozen=True)
class WetMixedStorage:
    fluid_template: RigidStorage
    solids: tuple
    reference: ReferenceSolution
    temperature_domain_k: tuple
    bulk_volume_m3: float
    water_element_convention: object
    bulk_volume_error_m3: float=0.
    _identity: str=field(init=False,repr=False)

    def __post_init__(self):
        require(type(self.fluid_template) is RigidStorage and self.fluid_template.allow_manufactured,'explicit_opted_in_fluid')
        require(type(self.solids) is tuple and self.solids and all(type(s) is MassSolid for s in self.solids),'mass_solid_providers')
        require(type(self.reference) is ReferenceSolution and self.reference.network.solve()==self.reference,'recomputed_reference_required')
        net=self.reference.network
        require(net.input_classification=='manufactured_test_fixture' and not self.reference.nullspace_h0_j_kg,'fully_anchored_manufactured_reference')
        require(net.reference_convention=='nist_298.15K_element_standard_formation','common_formation_reference')
        require(self.gas_ids==('O2','N2','H2O'),'explicit_three_gas_order')
        require(self.solid_ids+self.gas_ids==self.reference.component_ids,'complete_mass_reference_layout')
        require(type(self.temperature_domain_k) is tuple and len(self.temperature_domain_k)==2,'temperature_domain')
        lo,hi=(number(t,positive=True) for t in self.temperature_domain_k)
        elo,ehi=self.fluid_template.envelope.temperature_range_k
        require(elo<=lo<float(net.reference_temperature_k)<hi<=ehi,'reference_inside_caloric_domain')
        number(self.bulk_volume_m3,positive=True)
        require(number(self.bulk_volume_error_m3)>=0,'negative_bulk_error')
        for i,c in enumerate(net.components):require(c.phase==('solid' if i<len(self.solids) else 'gas'),'phase_reference_mismatch')
        for key,element in (('O2','O'),('N2','N')):
            require(element in net.elements,'missing_gas_element')
            c=net.components[self.reference.component_ids.index(key)]
            require(c.element_mass_fractions==tuple(F(x==element) for x in net.elements),'named_gas_element_mismatch')
        self.check_water()
        require(all(r.mass_change_kg_per_kg_extent[-1]==0 for r in net.reactions),'water_chemical_reactions_not_admitted')
        expected=self.water_element_convention.fractions(net.elements,self.water.reference.molar_mass_kg_mol)
        c=net.components[self.reference.component_ids.index('H2O')]
        require(c.element_mass_fractions==expected,'water_element_composition_mismatch')
        t,p=float(net.reference_temperature_k),float(net.reference_pressure_pa)
        for i,k in enumerate(self.gas_ids,len(self.solids)):
            phase=self.fluid_template.gas_phases[k]
            require(self.reference.particular_h0_j_kg[i]==F(phase.evaluate(t,p).enthalpy_j_mol)/F(phase.molar_mass_kg_mol),'actual_gas_reference_anchor_mismatch')
        object.__setattr__(self,'_identity',self.binding())

    @property
    def solid_ids(self):return tuple(s.component_id for s in self.solids)

    @property
    def gas_ids(self):return tuple(self.fluid_template.mechanical.gas_species_ids)

    @property
    def water(self):return self.fluid_template.mechanical.water

    def check_water(self):
        check_wet_water(self.fluid_template,self.water_element_convention)

    def binding(self):
        self.water_element_convention.check()
        vapor=self.fluid_template.gas_phases['H2O'].caloric
        providers=tuple((type(w).__module__,type(w).__qualname__,w.implementation) for w in (self.water,vapor._water))
        return _digest((self.fluid_template,providers,self.solids,self.reference,self.temperature_domain_k,self.bulk_volume_m3,self.bulk_volume_error_m3,(self.water_element_convention.facts_sha256,self.water_element_convention.facts_json)))

    @property
    def source_ids(self):
        values=self.fluid_template.envelope.source_ids+self.fluid_template.mechanical.constant_source_ids+self.reference.network.source_ids+tuple(x for s in self.solids for x in s.source_ids)+tuple(x for p in self.fluid_template.gas_phases.values() for x in p.metadata.source_ids)+self.water.source_ids
        return tuple(sorted(set(values+('ciaaw-2024-abridged-atomic-weights',self.water_element_convention.facts_sha256))))

    def state(self,masses,liquid,moles,energy):
        return WetMixedState(masses,liquid,moles,energy,self._identity)

    def check(self,state):
        require(type(state) is WetMixedState and state.energy_model_identity==self._identity,'wet_state_identity')
        require(len(state.solid_mass_kg)==len(self.solids) and len(state.gas_amounts_mol)==3,'wet_inventory_shape')
        require(self.binding()==self._identity,'wet_provider_content_changed')
        self.check_water()

    def evaluate(self,state,temperature_k):
        self.check(state);t=number(temperature_k,positive=True)
        require(self.temperature_domain_k[0]<=t<=self.temperature_domain_k[1],'wet_temperature_domain_exit')
        vs=sum((F(m)*F(s.volume_m3_kg) for m,s in zip(state.solid_mass_kg,self.solids)),F())
        available=F(self.bulk_volume_m3)-vs
        require(available>0,'no_positive_fluid_volume')
        nominal=number(available,positive=True)
        error_v=F(self.bulk_volume_error_m3)+abs(F(nominal)-available)
        require(error_v<available,'volume_uncertainty_excludes_positive_domain')
        evaluation=evaluate_wet_fluid(self.fluid_template,self.gas_ids,state.liquid_water_mol,state.gas_amounts_mol,t,nominal,error_v)
        fluid=evaluation.fluid_template;out=evaluation.point
        p=F(out.mechanical.pressure_pa)
        global_error=evaluation.global_pressure_error_pa;extra=evaluation.extra_pressure_error_pa;pressure_error=evaluation.pressure_error_pa
        net=self.reference.network;tref=net.reference_temperature_k;pref=net.reference_pressure_pa
        terms=tuple(F(m)*(h+F(s.cp_j_kg_k)*(F(t)-tref)-pref*F(s.volume_m3_kg)) for m,s,h in zip(state.solid_mass_kg,self.solids,self.reference.particular_h0_j_kg))
        total=F(out.internal_energy_j)+sum(terms,F());energy=number(total)
        err=F(out.energy_error_bound_j)+abs(F(energy)-total)+F(state.liquid_water_mol)*F(fluid.envelope.liquid_abs_du_dp_bound_j_mol_pa)*extra
        cp=sum((F(m)*F(s.cp_j_kg_k) for m,s in zip(state.solid_mass_kg,self.solids)),F())
        cmin=lower(F(out.minimum_heat_capacity_j_k)+cp);capacity=number(F(out.closed_heat_capacity_j_k)+cp,positive=True)
        require(cmin<=capacity,'wet_capacity_lower_violation')
        point=WetMixedPoint(out,energy,number(F(out.enthalpy_j)+sum(terms,F())+p*vs),tuple(map(float,terms)),float(vs),nominal,upper(error_v),float(global_error),float(extra),pressure_error,upper(err),capacity,cmin,self._identity)
        self.check(state)
        return point

    def invert(self,state,policy):
        require(type(policy) is InversePolicy,'explicit_inverse_policy')
        lo,hi=self.temperature_domain_k;a=self.evaluate(state,lo);b=self.evaluate(state,hi);target=F(state.internal_energy_j)
        require(F(a.total_internal_energy_j)+F(a.energy_error_j)<=target<=F(b.total_internal_energy_j)-F(b.energy_error_j),'wet_energy_target_outside_domain_or_resolution')
        for iteration in range(1,policy.maximum_iterations+1):
            t=(lo+hi)/2;out=self.evaluate(state,t);res=F(out.total_internal_energy_j)-target;err=F(out.energy_error_j)
            bound=upper((abs(res)+err)/F(out.minimum_heat_capacity_j_k))
            if abs(res)+err<=F(policy.energy_tolerance_j) and F(bound)<=F(policy.temperature_tolerance_k):
                return WetMixedInverse(out,float(target),float(res),bound,(lo,hi),iteration)
            require(abs(res)>err,'wet_inverse_sign_unresolved')
            if res>0:hi=t
            else:lo=t
            require(hi-lo>math.ulp(t),'wet_unresolvable_temperature')
        raise MixedError('wet_inverse_iteration_limit')


@dataclass(frozen=True)
class WaterElementConvention:
    """Pinned CIAAW nominal fraction convention, not an EOS mass replacement."""
    facts_path: str
    facts_json: str
    facts_sha256: str

    def __post_init__(self):
        self.check()

    @classmethod
    def load(cls,path):
        from pathlib import Path
        import hashlib
        p=Path(path).resolve();raw=p.read_bytes()
        return cls(str(p),raw.decode('utf-8'),hashlib.sha256(raw).hexdigest())

    def check(self):
        from pathlib import Path
        import hashlib,json
        expected='a9b5bec83df94504346a5f93f3008a0029653f24bfc085babeb65bbdbb919838'
        require(type(self.facts_path) is str and type(self.facts_json) is str and self.facts_sha256==expected,'registered_water_element_facts_required')
        require(hashlib.sha256(self.facts_json.encode()).hexdigest()==expected and Path(self.facts_path).read_bytes()==self.facts_json.encode(),'water_element_source_changed')
        d=json.loads(self.facts_json)
        require(d['id']=='ciaaw_2024_abridged_H2O_mass_fraction_nominal_v1' and d['formula']=='H2O','water_convention_identity')
        require(d['atomic_weights']=={'H':{'nominal_decimal':'1.0080','reported_plus_minus_decimal':'0.0002'},'O':{'nominal_decimal':'15.999','reported_plus_minus_decimal':'0.001'}},'water_atomic_source_values')
        require(F(d['mass_fractions']['H'])==F('2.0160')/F('18.0150') and F(d['mass_fractions']['O'])==F('15.999')/F('18.0150'),'water_fraction_derivation')

    def fractions(self,elements,actual_molar_mass_kg_mol):
        self.check();number(actual_molar_mass_kg_mol,positive=True)
        require(type(elements) is tuple and len(set(elements))==len(elements) and 'H' in elements and 'O' in elements,'water_elements_required')
        return tuple(F(672,6005) if x=='H' else F(5333,6005) if x=='O' else F() for x in elements)
