"""Runtime binding of conditional moisture transport to the actual sorption host.

Reuses the liquid EOS state already obtained for local phase exchange. This is
an in-process adapter, not authentication of arbitrary serialized EOS results.
No second water inventory or volumetric latent heat source is introduced.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
from pathlib import Path

from .arlabosse_rigid_sorption import ArlabosseSorptionStorage, _value
from .arlabosse_sorption_phase import SorptionEquilibrium, check_sorption_point
from .arlabosse_wet_thermo import T_REF
from .deforming_solid_storage import _digest
from .mass_storage_bridge import require
from .mass_wet_transport import WetPhaseEvaluation
from .source_wet_storage import SourceWetInverse
from .sorption_moisture_face import (
    CondensedWaterPoint, MoistureFaceGeometry, MoistureThermodynamicFactor,
    MoistureFaceExchange, load_makela_diffusivity, sorption_moisture_face,
)


ADAPTER_ID = 'ARLABOSSE_MAKELA_CONDITIONAL_MOISTURE_ADAPTER_V1'


def condensed_water_point(storage, chemical, state, inverse, phase):
    """Bind the decoded inventory and full source μ/h without another EOS call."""
    require(type(storage) is ArlabosseSorptionStorage, 'actual_moisture_sorption_storage')
    storage.check(state)
    require(type(inverse) is SourceWetInverse, 'actual_moisture_inverse')
    point = inverse.point
    mechanical = point.fluid.mechanical
    require(inverse.target_energy_j == state.internal_energy_j and
            mechanical.liquid_inventory_mol == state.liquid_water_mol and
            mechanical.gas_inventory_mol == dict(zip(storage.gas_ids, state.gas_amounts_mol)) and
            inverse.energy_residual_j == F(point.total_internal_energy_j)-F(state.internal_energy_j),
            'moisture_inverse_state_mismatch')
    check_sorption_point(storage, chemical, point)
    require(type(phase) is WetPhaseEvaluation and type(phase.equilibrium) is SorptionEquilibrium,
            'actual_moisture_sorption_phase')
    eq = phase.equilibrium
    pure = eq.pure_equilibrium.liquid
    require(pure.state.temperature_k == point.temperature_k and
            pure.state.pressure_pa == point.pressure_pa and
            chemical._liquid(pure.state) == pure and eq.activity == point.activity and
            eq.excess_partial_water_enthalpy_j_mol == point.excess_partial_water_enthalpy_j_mol,
            'moisture_pure_liquid_state_or_reference_mismatch')
    w = F(point.moisture_kg_water_per_kg_dry)
    require(F(.30) <= w <= F(.80), 'moisture_adapter_moisture_domain')
    reference = _digest((chemical.reference, chemical.water.implementation,
        chemical.method_id, pure.entropy_reference, chemical.source_asset_sha256))
    return CondensedWaterPoint(F(point.temperature_k), w, F(point.pressure_pa),
        F(pure.chemical_potential_j_mol)+F(point.excess_chemical_potential_j_mol),
        F(pure.enthalpy_j_mol)+F(point.excess_partial_water_enthalpy_j_mol), F(storage.wet._mass),
        reference, tuple(sorted(set(point.source_ids+pure.source_ids+(ADAPTER_ID,)))),
        'derived_from_evidence')


def _slopes(curve, w):
    """One slope inside a piece, two at an interior knot, one at an endpoint."""
    result = []
    for a, b, ya, yb in zip(curve.x, curve.x[1:], curve.y, curve.y[1:]):
        if F(a) <= w <= F(b):
            result.append((F(yb)-F(ya))/(F(b)-F(a)))
    require(bool(result), 'moisture_factor_curve_domain')
    return tuple(result)


@dataclass(frozen=True)
class SourceMoistureWitness:
    points: tuple[CondensedWaterPoint, CondensedWaterPoint]
    factor: MoistureThermodynamicFactor
    exchange: MoistureFaceExchange
    storage_identities: tuple[str, str]
    isothermal_fick_drive_residual_j_mol: F | None
    inverses: tuple[SourceWetInverse, SourceWetInverse]
    phases: tuple[WetPhaseEvaluation, WetPhaseEvaluation]
    source_state_binding_verified: bool = False
    material_qualified: bool = False
    training_eligible: bool = False


@dataclass(frozen=True)
class MakelaMoistureTransport:
    repository_root: Path
    original_pdf_path: Path
    _diffusivity: object = field(init=False, repr=False)
    _identity: str = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, 'repository_root', Path(self.repository_root))
        object.__setattr__(self, 'original_pdf_path', Path(self.original_pdf_path))
        object.__setattr__(self, '_diffusivity', load_makela_diffusivity(
            self.repository_root, self.original_pdf_path))
        object.__setattr__(self, '_identity', self.binding())

    def binding(self):
        current = load_makela_diffusivity(self.repository_root, self.original_pdf_path)
        require(current == self._diffusivity, 'moisture_diffusivity_source_changed')
        return _digest((ADAPTER_ID, current, self._choices()))

    def _check(self):
        require(self.binding() == self._identity, 'moisture_transport_content_changed')

    @property
    def source_ids(self):
        self._check()
        return self._diffusivity.source_ids+(ADAPTER_ID,)

    @staticmethod
    def _choices():
        return {'factor': 'exact secant on represented m/q nodes at exact arithmetic mean T',
            'same_W': 'piece slope; at interior knots symmetric average of positive one-sided factors; endpoints one-sided',
            'W_convention': 'represented storage point W; inventory-to-W projection remains that of storage',
            'mu_factor_rounding': 'full mu uses represented source readouts; factor uses exact represented-node interpolation; equal T/P drive residual retained',
            'energy': 'pure liquid actual T/P plus existing molar sorption excess; symmetric face partial enthalpy',
            'geometry': 'uniform dry density from controlled total slab volume; not available fluid volume',
            'path_allocation': 'apparent total-loss D assigned to condensed inventory; all gas face diffusion and Darcy disabled',
            'cross_effects': 'zero off-diagonal in heat/moisture representation is an unmeasured constitutive assumption',
            'qualification': 'conditional cross-material exploration; total model and transfer errors unknown'}

    def definition(self):
        self._check()
        return {'adapter_id': ADAPTER_ID, 'identity': self._identity,
            'diffusivity': self._diffusivity.to_record(), 'choices': self._choices(),
            'material_qualified': False, 'training_eligible': False}

    def factor(self, storage, left, right):
        self._check()
        require(type(storage) is ArlabosseSorptionStorage, 'actual_moisture_factor_storage')
        storage._check()
        wet = storage.wet
        a, b = sorted((left.moisture_kg_water_per_kg_dry, right.moisture_kg_water_per_kg_dry))
        tf = (left.temperature_k+right.temperature_k)/2
        r, mass = tf/F(T_REF), F(wet._mass)
        if a != b:
            edges = (a,*sorted({F(x) for curve in (wet._m,wet._q) for x in curve.x if a < F(x) < b}),b)
            require(all(mass*(r*(_value(wet._m,hi)-_value(wet._m,lo))-
                (1-r)*(_value(wet._q,hi)-_value(wet._q,lo)))/(hi-lo) > 0
                for lo,hi in zip(edges,edges[1:])), 'positive_piecewise_moisture_factor_required')
            gamma = mass*(r*(_value(wet._m,b)-_value(wet._m,a))-
                (1-r)*(_value(wet._q,b)-_value(wet._q,a)))/(b-a)
            method = 'declared_secant'
        else:
            # m/q grids can differ. A missing knot on one curve contributes
            # its same piece slope to both sides of the other's knot.
            ms, qs = _slopes(wet._m,a), _slopes(wet._q,a)
            count = max(len(ms),len(qs))
            gs = tuple(mass*(r*ms[min(i,len(ms)-1)]-(1-r)*qs[min(i,len(qs)-1)])
                       for i in range(count))
            require(all(g > 0 for g in gs), 'positive_one_sided_moisture_factor_required')
            gamma = sum(gs,F())/len(gs)
            method = 'declared_same_W_limit'
        require(gamma > 0, 'positive_source_moisture_factor_required')
        return MoistureThermodynamicFactor(gamma,tf,(a,b),method,
            storage.source_ids+(ADAPTER_ID,), 'derived_from_evidence')

    def exchange(self, storages, points, *, area_m2, widths_m, geometry_sources,
                 chemical=None, states=None, inverses=None, phases=None):
        """Only actual checked runtime contexts can obtain a bound witness."""
        self._check()
        require(all(type(v) is tuple and len(v) == 2
                    for v in (storages,points,states,inverses,phases)),
                'moisture_actual_runtime_context_required')
        checked = tuple(condensed_water_point(s,chemical,state,inverse,phase)
            for s,state,inverse,phase in zip(storages,states,inverses,phases))
        require(checked == points, 'moisture_points_do_not_match_actual_runtime')
        left, right = storages
        require((left.wet._m,left.wet._q,left.wet._mass,left.wet._latent_reference) ==
                (right.wet._m,right.wet._q,right.wet._mass,right.wet._latent_reference),
                'common_moisture_thermodynamic_model')
        area = F(area_m2)
        dl, dr = map(F,widths_m)
        geometry = MoistureFaceGeometry(area,(dl+dr)/2,F(left.dry_mass_kg),F(right.dry_mass_kg),
            area*dl,area*dr,geometry_sources,'manufactured_test_fixture')
        factor = self.factor(left,*points)
        a, b = points
        drive_residual = None
        if a.temperature_k == b.temperature_k and a.pressure_pa == b.pressure_pa:
            dw = a.moisture_kg_water_per_kg_dry-b.moisture_kg_water_per_kg_dry
            require(dw == 0 or (a.chemical_potential_j_mol-b.chemical_potential_j_mol)*dw > 0,
                    'moisture_chemical_drive_resolution_failure')
            drive_residual = a.chemical_potential_j_mol-b.chemical_potential_j_mol-factor.gamma_j_mol*dw
        exchange = sorption_moisture_face(*points,geometry,self._diffusivity,factor)
        return SourceMoistureWitness(points,factor,exchange,
            (left.model_identity,right.model_identity),drive_residual,inverses,phases,
            source_state_binding_verified=True)
