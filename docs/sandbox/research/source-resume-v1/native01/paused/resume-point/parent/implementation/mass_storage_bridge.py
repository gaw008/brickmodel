"""Closed manufactured kg-solid / mol-gas thermal reaction bridge.

One rigid dry cell only. No molecular mass is assigned to solid components.
Measured uncertainty, liquid phase transfer, deformation and transport are not admitted.
"""
from dataclasses import dataclass, replace, field
from fractions import Fraction as F
import math
from sludge_sandbox.rigid_storage import RigidStorage
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.reaction_reference import ReferenceSolution
from sludge_sandbox.deforming_solid_storage import _digest


class MixedError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise MixedError(reason)


def number(x, *, positive=False):
    require(type(x) in (int, float, F), 'finite_numeric_required')
    try:
        v = float(x)
    except (OverflowError, ValueError) as exc:
        raise MixedError('finite_numeric_required') from exc
    require(math.isfinite(v) and (not positive or v > 0), 'invalid_numeric')
    return v


def vector(x):
    require(type(x) is tuple and bool(x), 'explicit_inventory_tuple')
    result = tuple(number(v) for v in x)
    require(all(v >= 0 for v in result), 'negative_inventory')
    return result


def upper(value):
    v = float(value)
    require(math.isfinite(v) and v >= 0, 'bound_overflow')
    return math.nextafter(v, math.inf) if F(v) < value else v


@dataclass(frozen=True)
class MixedState:
    solid_mass_kg: tuple
    fluid_amounts_mol: tuple
    internal_energy_j: float
    energy_model_identity: str

    def __post_init__(self):
        object.__setattr__(self, 'solid_mass_kg', vector(self.solid_mass_kg))
        object.__setattr__(self, 'fluid_amounts_mol', vector(self.fluid_amounts_mol))
        object.__setattr__(self, 'internal_energy_j', number(self.internal_energy_j))
        require(type(self.energy_model_identity) is str and len(self.energy_model_identity) == 64, 'source_identity_required')


@dataclass(frozen=True)
class MassSolid:
    component_id: str
    cp_j_kg_k: float
    volume_m3_kg: float
    source_ids: tuple
    classification: str = 'manufactured_test_fixture'

    def __post_init__(self):
        require(type(self.component_id) is str and self.component_id, 'solid_identity')
        number(self.cp_j_kg_k, positive=True)
        number(self.volume_m3_kg, positive=True)
        require(type(self.source_ids) is tuple and self.source_ids and all(type(x) is str and x for x in self.source_ids), 'solid_sources')
        require(self.classification == 'manufactured_test_fixture', 'only_exact_manufactured_coefficients_supported')


@dataclass(frozen=True)
class MixedPoint:
    temperature_k: float
    pressure_pa: float
    internal_energy_j: float
    enthalpy_j: float
    closed_heat_capacity_j_k: float
    minimum_heat_capacity_j_k: float
    energy_error_j: float
    pressure_error_pa: float
    pore_volume_m3: float
    solid_internal_energy_j: tuple
    fluid_internal_energy_j: float
    model_identity: str
    qualification: str = 'manufactured_constant_mass_caloric_dry_rigid_nominal_reference_not_material_admission'


@dataclass(frozen=True)
class MixedInverse:
    point: MixedPoint
    energy_residual_j: float
    temperature_error_bound_k: float
    iterations: int


@dataclass(frozen=True)
class MixedStorage:
    fluid_template: RigidStorage
    solids: tuple
    reference: ReferenceSolution
    temperature_domain_k: tuple
    bulk_volume_m3: float
    _identity: str = field(init=False, repr=False)

    def __post_init__(self):
        require(type(self.fluid_template) is RigidStorage and self.fluid_template.allow_manufactured, 'actual_opted_in_fluid_storage_required')
        require(type(self.solids) is tuple and self.solids and all(type(s) is MassSolid for s in self.solids), 'mass_solid_providers')
        require(type(self.reference) is ReferenceSolution, 'full_reference_solution_required')
        net = self.reference.network
        require(net.input_classification == 'manufactured_test_fixture', 'measured_reference_uncertainty_not_supported')
        require(net.solve() == self.reference, 'reference_solution_not_recomputed')
        require(not self.reference.nullspace_h0_j_kg, 'explicit_fully_anchored_coordinate_required_for_first_bridge')
        require(net.reference_convention == 'nist_298.15K_element_standard_formation', 'reference_convention_mismatch')
        require(type(self.temperature_domain_k) is tuple and len(self.temperature_domain_k) == 2, 'temperature_domain')
        lo, hi = (number(x, positive=True) for x in self.temperature_domain_k)
        require(lo < hi and lo <= float(net.reference_temperature_k) <= hi, 'reference_outside_caloric_domain')
        elo, ehi = self.fluid_template.envelope.temperature_range_k
        require(elo <= lo < hi <= ehi, 'domain_outside_fluid_envelope')
        number(self.bulk_volume_m3, positive=True)
        ids = self.solid_ids + self.gas_ids
        require(ids == self.reference.component_ids and len(set(ids)) == len(ids), 'complete_disjoint_basis_layout_required')
        for index, component in enumerate(net.components):
            require(component.phase == ('solid' if index < len(self.solids) else 'gas'), 'component_phase_mismatch')
        # This first dry bridge admits only named elemental O2/N2 gases.
        # A balanced algebraic network cannot redefine their chemical identities.
        gas_elements = {'O2': 'O', 'N2': 'N'}
        for key in self.gas_ids:
            require(key in gas_elements, 'gas_element_composition_not_admitted')
            element = gas_elements[key]
            require(element in net.elements, 'gas_element_missing')
            component = net.components[ids.index(key)]
            expected = tuple(F(label == element) for label in net.elements)
            require(component.element_mass_fractions == expected, 'named_gas_element_composition_mismatch')
        t, p = float(net.reference_temperature_k), float(net.reference_pressure_pa)
        for i, key in enumerate(self.gas_ids, len(self.solids)):
            phase = self.fluid_template.gas_phases[key]
            actual = phase.evaluate(t, p).enthalpy_j_mol
            require(self.reference.particular_h0_j_kg[i] == F(actual)/F(phase.molar_mass_kg_mol), 'actual_fluid_reference_anchor_mismatch')
        object.__setattr__(self, '_identity', self.binding())

    @property
    def solid_ids(self):
        return tuple(s.component_id for s in self.solids)

    @property
    def gas_ids(self):
        return tuple(self.fluid_template.mechanical.gas_species_ids)

    def binding(self):
        w = self.fluid_template.mechanical.water
        backend = (type(w).__module__, type(w).__qualname__, w.implementation)
        return _digest((self.fluid_template, backend, self.solids, self.reference,
                        self.temperature_domain_k, self.bulk_volume_m3))

    def state(self, masses, moles, energy):
        return MixedState(masses, moles, energy, self._identity)

    def check(self, state):
        require(type(state) is MixedState and state.energy_model_identity == self._identity, 'mixed_state_identity')
        require(self.binding() == self._identity, 'provider_content_changed')
        require(len(state.solid_mass_kg) == len(self.solids) and len(state.fluid_amounts_mol) == len(self.gas_ids), 'mixed_inventory_shape')

    def evaluate(self, state, temperature_k):
        self.check(state)
        t = number(temperature_k, positive=True)
        require(self.temperature_domain_k[0] <= t <= self.temperature_domain_k[1], 'temperature_domain_exit')
        tref = self.reference.network.reference_temperature_k
        pref = self.reference.network.reference_pressure_pa
        vs = sum((F(m)*F(s.volume_m3_kg) for m,s in zip(state.solid_mass_kg,self.solids)), F())
        exact_pore = F(self.bulk_volume_m3)-vs
        require(exact_pore > 0, 'nonpositive_pore_volume')
        pore = float(exact_pore)
        require(pore > 0 and math.isfinite(pore), 'unrepresentable_pore_volume')
        mechanical = replace(self.fluid_template.mechanical, available_pore_volume_m3=pore)
        fluid = replace(self.fluid_template, mechanical=mechanical).evaluate_at_temperature(t, 0., dict(zip(self.gas_ids,state.fluid_amounts_mol)))
        terms = tuple(F(m)*(h+F(s.cp_j_kg_k)*(F(t)-tref)-pref*F(s.volume_m3_kg))
            for m,s,h in zip(state.solid_mass_kg,self.solids,self.reference.particular_h0_j_kg))
        total = F(fluid.internal_energy_j)+sum(terms,F())
        energy = float(total)
        error = upper(F(fluid.energy_error_bound_j)+abs(F(energy)-total))
        solid_cp = sum((F(m)*F(s.cp_j_kg_k) for m,s in zip(state.solid_mass_kg,self.solids)),F())
        minimum = float(F(fluid.minimum_heat_capacity_j_k)+solid_cp)
        if F(minimum)>F(fluid.minimum_heat_capacity_j_k)+solid_cp:
            minimum=math.nextafter(minimum,-math.inf)
        pressure_error = upper(F(fluid.pressure_error_bound_pa)+abs(F(pore)-exact_pore)/exact_pore*F(fluid.mechanical.pressure_pa))
        enthalpy = float(F(fluid.enthalpy_j)+sum(terms,F())+F(fluid.mechanical.pressure_pa)*vs)
        point = MixedPoint(t,fluid.mechanical.pressure_pa,energy,enthalpy,
            float(F(fluid.closed_heat_capacity_j_k)+solid_cp),minimum,error,pressure_error,pore,
            tuple(float(v) for v in terms),fluid.internal_energy_j,self._identity)
        self.check(state)
        return point

    def invert(self, state, policy):
        require(type(policy) is InversePolicy, 'explicit_inverse_policy')
        lo, hi = self.temperature_domain_k
        a,b = self.evaluate(state,lo),self.evaluate(state,hi)
        target = state.internal_energy_j
        require(F(a.internal_energy_j)+F(a.energy_error_j) <= F(target) <= F(b.internal_energy_j)-F(b.energy_error_j), 'energy_target_outside_domain_or_resolution')
        for iteration in range(1,policy.maximum_iterations+1):
            t=(lo+hi)/2
            out=self.evaluate(state,t)
            exact_residual=F(out.internal_energy_j)-F(target)
            error=F(out.energy_error_j)
            bound=upper((abs(exact_residual)+error)/F(out.minimum_heat_capacity_j_k))
            if abs(exact_residual)+error<=F(policy.energy_tolerance_j) and F(bound)<=F(policy.temperature_tolerance_k):
                return MixedInverse(out,float(exact_residual),bound,iteration)
            require(abs(exact_residual)>error, 'inverse_energy_sign_unresolved')
            if exact_residual>0:hi=t
            else:lo=t
            require(lo<t<hi or hi-lo>math.ulp(t), 'unresolvable_temperature')
        raise MixedError('inverse_iteration_limit')


@dataclass(frozen=True)
class ReactionEvaluation:
    inverse: MixedInverse
    extent_kg_s: float
    solid_kg_s: tuple
    gas_mol_s: tuple
    external_power_w: float
    chemical_reference_power_w: float


@dataclass(frozen=True)
class MixedCell:
    storage: MixedStorage
    inverse_policy: InversePolicy
    rate_constant_per_s: float
    oxygen_reference_mol: float
    rate_source_ids: tuple

    def __post_init__(self):
        number(self.rate_constant_per_s,positive=True);number(self.oxygen_reference_mol,positive=True)
        require(self.storage.solid_ids==('A','B') and self.storage.gas_ids==('O2','N2'), 'explicit_manufactured_AB_oxygen_layout')
        net=self.storage.reference.network
        require(len(net.reactions)==1 and net.reactions[0].mass_change_kg_per_kg_extent==(-1,2,-1,0), 'explicit_balanced_extent_reaction')
        require(type(self.rate_source_ids) is tuple and self.rate_source_ids, 'explicit_rate_source')

    def evaluate(self,state):
        inv=self.storage.invert(state,self.inverse_policy)
        rate=self.rate_constant_per_s*state.solid_mass_kg[0]*state.fluid_amounts_mol[0]/self.oxygen_reference_mol
        mass=self.storage.fluid_template.gas_phases['O2'].molar_mass_kg_mol
        return ReactionEvaluation(inv,rate,(-rate,2*rate),(-rate/mass,0.),0.,
            float(self.storage.reference.identified_value(self.storage.reference.network.reactions[0].mass_change_kg_per_kg_extent))*rate)


@dataclass(frozen=True)
class MixedSegment:
    status: str
    reason: str|None
    states: tuple
    observations: tuple
    ledgers: tuple


def integrate_closed(cell, initial, *, duration_s, steps):
    """Fixed-step midpoint segment, no event/continuation admission. Failed prefix retained."""
    require(type(cell) is MixedCell and type(steps) is int and steps>0, 'explicit_segment_inputs')
    duration=number(duration_s,positive=True);h=duration/steps
    states=[initial];observations=[];ledgers=[]
    def advance(state,rate,dt):
        return cell.storage.state(tuple(a+dt*b for a,b in zip(state.solid_mass_kg,rate.solid_kg_s)),
            tuple(a+dt*b for a,b in zip(state.fluid_amounts_mol,rate.gas_mol_s)),state.internal_energy_j+dt*rate.external_power_w)
    try:
        for index in range(steps):
            a=cell.evaluate(states[-1]);mid=advance(states[-1],a,h/2);b=cell.evaluate(mid)
            new=advance(states[-1],b,h);end=cell.evaluate(new)
            ledger=(h,tuple(h*x for x in b.solid_kg_s),tuple(h*x for x in b.gas_mol_s),h*b.external_power_w)
            states.append(new);ledgers.append(ledger);observations.append(end)
        return MixedSegment('completed',None,tuple(states),tuple(observations),tuple(ledgers))
    except (ValueError,OverflowError) as exc:
        return MixedSegment('failed',str(exc),tuple(states),tuple(observations),tuple(ledgers))
