"""Explicit low-water/zero-inventory extension retaining the dry excess reference.

Only the existing rigid zero-excess-volume model is extended. The same source
dry mass, gas/liquid energy and inverse policies remain in use. A zero water
inventory does not remove the finite dry-end excess energy or entropy.
"""
from dataclasses import dataclass, field, fields
from fractions import Fraction as F

from .arlabosse_low_moisture import ArlabosseLowMoisture, LowMoistureExcessPoint
from .arlabosse_rigid_sorption import ArlabosseSorptionStorage
from .arlabosse_wet_thermo import T_REF, W_REF
from .deforming_solid_storage import _digest
from .mass_storage_bridge import number, require, upper
from .source_wet_storage import SourceWetPoint, _binary


STORAGE_ID = 'ARLABOSSE_LOW_MOISTURE_RIGID_STORAGE_V1'
QUALIFICATION = 'conditional_low_water_extension_with_unknown_model_errors'


@dataclass(frozen=True, kw_only=True)
class LowMoistureSorptionPoint(SourceWetPoint):
    excess: LowMoistureExcessPoint
    excess_internal_energy_j: F
    excess_entropy_j_k: F
    excess_helmholtz_energy_j: F
    training_eligible: bool = False
    qualification: str = QUALIFICATION

    @property
    def moisture_kg_water_per_kg_dry(self):
        return float(self.excess.moisture_kg_water_per_kg_dry)


@dataclass(frozen=True)
class LowMoistureSorptionStorage(ArlabosseSorptionStorage):
    """A separately identified extension; old states and old hosts stay distinct.

    The inherited state checker and full-U bisection call these explicit new
    moisture/evaluate operations. No target subtraction or tolerance change is
    used. This class alone grants no phase, transport or dry-event semantics.
    """
    excess: ArlabosseLowMoisture = field(kw_only=True)

    def binding(self):
        require(type(self.excess) is ArlabosseLowMoisture, 'actual_low_moisture_excess_required')
        require(self.excess.wet is self.wet, 'same_actual_low_moisture_wet_provider_required')
        return _digest((STORAGE_ID, super().binding(), self.excess.binding()))

    @property
    def source_ids(self):
        self._check()
        return tuple(sorted(set(super().source_ids+self.excess.source_ids+(STORAGE_ID,))))

    def _moisture(self, state):
        w = F(state.liquid_water_mol)*F(self.wet._mass)/F(self.dry_mass_kg)
        require(0 <= w <= F(W_REF), 'low_sorption_moisture_domain_exit')
        return w

    def evaluate(self, state, temperature_k):
        self.check(state)
        t = _binary(temperature_k, positive=True)
        require(self.temperature_domain_k[0] <= t <= self.temperature_domain_k[1],
                'low_sorption_temperature_domain_exit')
        w = self._moisture(state)
        excess = self.excess.evaluate(t,w)
        base = self.base.evaluate(self._base_state(state),t)
        p, error = F(base.pressure_pa), F(base.pressure_error_pa)
        lo, hi = map(F,self.pressure_domain_pa)
        require(lo <= p-error and p+error <= hi, 'low_sorption_pressure_domain_exit')
        mass = F(self.dry_mass_kg)
        u, s = mass*excess.h_ex_j_kg_dry, mass*excess.s_ex_j_kg_dry_k
        total = F(base.total_internal_energy_j)+u
        energy = number(total)
        numerical_error = F(base.energy_error_j)+abs(F(energy)-total)
        values = {f.name:getattr(base,f.name) for f in fields(SourceWetPoint)}
        values.update(total_internal_energy_j=energy,energy_error_j=upper(numerical_error),
            model_identity=self._identity,qualification=QUALIFICATION,
            source_ids=tuple(sorted(set(base.source_ids+excess.source_ids+(STORAGE_ID,)))))
        result = LowMoistureSorptionPoint(**values,excess=excess,
            excess_internal_energy_j=u,excess_entropy_j_k=s,
            excess_helmholtz_energy_j=u-F(t)*s)
        self.check(state)
        return result

    def provenance(self):
        self._check()
        result = super().provenance()
        endpoint = self.excess.evaluate(T_REF,F())
        u0 = F(self.dry_mass_kg)*endpoint.h_ex_j_kg_dry
        s0 = F(self.dry_mass_kg)*endpoint.s_ex_j_kg_dry_k
        result.update(schema='arlabosse_low_moisture_rigid_storage_v1',
            qualification=QUALIFICATION,low_moisture_definition=self.excess.definition(),
            moisture_domain_kg_kg_dry=(0.,W_REF),
            dry_endpoint_excess_internal_energy_j=[u0.numerator,u0.denominator],
            dry_endpoint_excess_entropy_j_k=[s0.numerator,s0.denominator],
            dry_endpoint_policy='retain finite inherited excess reference at zero water; do not switch to base U',
            numerical_scope='exact represented-input excess U plus base conditional U bound and final projection; low-W logarithmic S/mu readouts have unquantified numerical error',
            storage_scope='fixed dry mass and volume; separate phase/transport interfaces required at zero inventory')
        result['equations'].update(hex='source branch above join; hj+bj*(W-Wj) below including zero',
            sex='source branch above join; sj+cj*(W-Wj)-Rs*(W*ln(W/Wj)-W+Wj) below; analytic zero limit',
            dry='U_base+md*h0 and S_base+md*s0; no water inventory deletion')
        return result
