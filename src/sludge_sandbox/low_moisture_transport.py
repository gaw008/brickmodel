"""Explicit low-W donor transport with actual storage/phase correspondence.

Pure-liquid references at zero water are hypothetical standard states, not
inventories. Finite fluxes use analytical limits; singular entropy is named.
No EOS, new water pool, parallel vapor diffusion, or latent source is added.
"""
from dataclasses import dataclass, field
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

from .arlabosse_low_moisture import _log_ratio as _positive_log_ratio, _value
from .arlabosse_low_moisture_storage import LowMoistureSorptionStorage
from .arlabosse_wet_thermo import T_MIN, T_REF, W_MIN, W_REF
from .deforming_solid_storage import _digest
from .low_moisture_phase import (
    LowMoistureEquilibrium, LowMoisturePhaseEvaluation, check_low_moisture_point,
)
from .septien_conductivity import SeptienConductivity, ConductivityPoint, _coordinate
from .source_sorption_moisture import MakelaMoistureTransport, _slopes
from .source_wet_storage import SourceWetInverse
from .sorption_moisture_face import (
    EffectiveMoistureDiffusivity, MoistureFaceGeometry, QuantityProjection,
    _metadata, _project, _rat, _require, _scalar,
)


MODEL_ID = 'ARLABOSSE_LOW_MOISTURE_TRANSPORT_V1'
CONDUCTIVITY_ID = 'SEPTIEN_LOW_MOISTURE_CONSTANT_EXTENSION_V1'
MODEL_PATH = 'data/sandbox/research/arlabosse-low-moisture-transport-v1/model.json'
MODEL_SHA256 = '853ef0731172d091d965896a28d463464bb2d0c59ecc714228e012dbb0826b16'


def _log_ratio(a: F, b: F) -> F:
    """One canonical orientation keeps represented left/right swaps exact."""
    _require(a > 0 and b > 0,'positive_log_ratio_inputs_required')
    return -_positive_log_ratio(b,a) if a < b else _positive_log_ratio(a,b)


def _model_definition(root: Path) -> dict:
    root = Path(root).resolve()
    try:
        raw = (root/MODEL_PATH).read_bytes()
        _require(hashlib.sha256(raw).hexdigest() == MODEL_SHA256, 'low_transport_model_changed')
        model = json.loads(raw)
        for asset in model['upstream']:
            path = (root/asset['path']).resolve()
            _require(path.is_relative_to(root), 'low_transport_source_path')
            _require(hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256'],
                     'low_transport_upstream_changed')
        return model
    except OSError as exc:
        raise ValueError('low_transport_source_unavailable') from exc


@dataclass(frozen=True)
class LowMoistureConductivityPoint:
    temperature_k: F
    moisture_kg_water_per_kg_dry: F
    k_w_m_k: float
    nominal_k_w_m_k: F
    binary64_projection_error_w_m_k: F
    model_identity: str
    source_ids: tuple[str, ...]
    original_point: ConductivityPoint
    branch: str
    moisture_extension_model_error: None = None
    total_model_uncertainty: None = None
    material_qualified: bool = False
    training_eligible: bool = False

    def to_record(self) -> dict:
        return {'temperature_k_exact': _rat(self.temperature_k),
            'moisture_kg_water_per_kg_dry_exact': _rat(self.moisture_kg_water_per_kg_dry),
            'k_w_m_k': self.k_w_m_k, 'nominal_k_w_m_k_exact': _rat(self.nominal_k_w_m_k),
            'binary64_projection_error_w_m_k_exact': _rat(self.binary64_projection_error_w_m_k),
            'model_identity': self.model_identity, 'source_ids': list(self.source_ids),
            'original_evaluation': self.original_point.to_record(), 'branch': self.branch,
            'moisture_extension_model_error': None, 'total_model_uncertainty': None,
            'source_confidence_intervals_are_total_model_bounds': False,
            'material_qualified': False, 'training_eligible': False}


@dataclass(frozen=True)
class LowMoistureConductivity:
    original: SeptienConductivity
    _identity: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, '_identity', self.binding())

    def binding(self) -> str:
        _require(type(self.original) is SeptienConductivity, 'actual_septien_provider_required')
        model = _model_definition(self.original.repository_root)
        identity = _digest((CONDUCTIVITY_ID, model, self.original.binding()))
        _require(not hasattr(self, '_identity') or identity == self._identity,
                 'low_conductivity_provider_changed')
        return identity

    @property
    def source_ids(self) -> tuple[str, ...]:
        self.binding()
        return tuple(sorted(set(self.original.source_ids+(CONDUCTIVITY_ID, MODEL_ID, MODEL_SHA256))))

    def definition(self) -> dict:
        self.binding()
        return {'model': _model_definition(self.original.repository_root),
            'identity': self._identity, 'original': self.original.definition(),
            'material_qualified': False, 'training_eligible': False}

    def evaluate(self, temperature_k, moisture_kg_water_per_kg_dry) -> LowMoistureConductivityPoint:
        self.binding()
        t, w = _coordinate(temperature_k), _coordinate(moisture_kg_water_per_kg_dry)
        _require(F(T_MIN) <= t <= F(T_REF) and 0 <= w <= F(W_REF), 'low_conductivity_domain_exit')
        at = max(w, F(.30))  # Explicit new constant extension, recorded below.
        original = self.original.evaluate(t, at)
        return LowMoistureConductivityPoint(t,w,original.k_w_m_k,original.nominal_k_w_m_k,
            original.binary64_projection_error_w_m_k,self._identity,self.source_ids,original,
            'constant_low_W_extension' if w < F(.30) else 'original_source_domain')


@dataclass(frozen=True)
class LowMoistureWaterPoint:
    temperature_k: F
    moisture_kg_water_per_kg_dry: F
    pressure_pa: F
    chemical_potential_j_mol: F | None
    partial_molar_enthalpy_j_mol: F
    water_molar_mass_kg_mol: F
    gas_constant_j_mol_k: F
    join_chemical_potential_over_temperature_j_mol_k: F
    energy_reference_id: str
    source_ids: tuple[str, ...]
    liquid_reference_scope: str
    input_classification: str

    def __post_init__(self) -> None:
        for name in ('temperature_k','moisture_kg_water_per_kg_dry','pressure_pa',
                     'partial_molar_enthalpy_j_mol','water_molar_mass_kg_mol','gas_constant_j_mol_k',
                     'join_chemical_potential_over_temperature_j_mol_k'):
            object.__setattr__(self,name,_scalar(getattr(self,name),name))
        w = self.moisture_kg_water_per_kg_dry
        _require(F(T_MIN) <= self.temperature_k <= F(T_REF) and 0 <= w <= F(W_REF)
                 and 90000 <= self.pressure_pa <= 110000, 'low_water_point_domain')
        _require(self.water_molar_mass_kg_mol > 0 and self.gas_constant_j_mol_k > 0,
                 'low_water_positive_constants')
        _require((w == 0) == (self.chemical_potential_j_mol is None), 'low_water_mu_limit_correspondence')
        if w:
            object.__setattr__(self,'chemical_potential_j_mol',
                               _scalar(self.chemical_potential_j_mol,'complete_chemical_potential'))
        expected = ('hypothetical_standard_state_at_zero_inventory' if not w
                    else 'pure_liquid_reference_with_sorption_excess')
        _require(self.liquid_reference_scope == expected, 'low_water_standard_state_scope')
        _metadata(self.source_ids,self.input_classification)
        _require(type(self.energy_reference_id) is str and bool(self.energy_reference_id), 'low_water_reference_required')

    def to_record(self) -> dict:
        return {**{name: _rat(getattr(self,name)) for name in (
            'temperature_k','moisture_kg_water_per_kg_dry','pressure_pa','partial_molar_enthalpy_j_mol',
            'water_molar_mass_kg_mol','gas_constant_j_mol_k','join_chemical_potential_over_temperature_j_mol_k')},
            'chemical_potential_j_mol': None if self.chemical_potential_j_mol is None else _rat(self.chemical_potential_j_mol),
            'chemical_potential_state': 'minus_infinity_at_zero_inventory' if self.chemical_potential_j_mol is None else 'finite',
            'energy_reference_id': self.energy_reference_id,'source_ids': list(self.source_ids),
            'liquid_reference_scope': self.liquid_reference_scope,'input_classification':self.input_classification}


def low_moisture_water_point(storage, chemical, state, inverse, phase) -> LowMoistureWaterPoint:
    """Check actual runtime storage/inventory/phase references without a new EOS call."""
    _require(type(storage) is LowMoistureSorptionStorage, 'actual_low_moisture_storage_required')
    storage.check(state)
    _require(type(inverse) is SourceWetInverse, 'actual_low_moisture_inverse_required')
    p = inverse.point
    check_low_moisture_point(storage,chemical,p)
    mechanical = p.fluid.mechanical
    _require(inverse.target_energy_j == state.internal_energy_j and
        mechanical.liquid_inventory_mol == state.liquid_water_mol and
        mechanical.gas_inventory_mol == dict(zip(storage.gas_ids,state.gas_amounts_mol)) and
        inverse.energy_residual_j == F(p.total_internal_energy_j)-F(state.internal_energy_j),
        'low_moisture_inverse_state_mismatch')
    _require(type(phase) is LowMoisturePhaseEvaluation and type(phase.equilibrium) is LowMoistureEquilibrium,
             'actual_low_moisture_phase_required')
    eq = phase.equilibrium
    pure = eq.pure_equilibrium.liquid
    w, t = p.excess.moisture_kg_water_per_kg_dry, F(p.temperature_k)
    expected_scope = ('hypothetical_standard_state_at_zero_inventory' if not w
                      else 'pure_liquid_reference_with_sorption_excess')
    pv = F(state.gas_amounts_mol[storage.gas_ids.index('H2O')])*F(chemical.gas_constant_j_mol_k)*t/F(p.gas_volume_m3)
    _require(pure.state.temperature_k == p.temperature_k and pure.state.pressure_pa == p.pressure_pa and
        chemical._liquid(pure.state) == pure and eq.activity == p.excess.activity and
        eq.excess_partial_water_enthalpy_j_mol == p.excess.partial_h_ex_j_mol and
        eq.equilibrium_partial_pressure_pa == _project(F(eq.pure_equilibrium.equilibrium_partial_pressure_pa)*F(eq.activity),'peq') and
        eq.phase_enthalpy_difference_j_mol == _project(F(eq.pure_equilibrium.phase_enthalpy_difference_j_mol)-F(p.excess.partial_h_ex_j_mol),'phase_heat') and
        phase.water_partial_pressure_pa == _project(pv,'vapor_pressure') and
        eq.liquid_reference_scope == expected_scope, 'low_moisture_phase_reference_mismatch')
    wet = storage.wet
    bj = F(wet._latent_reference)-_value(wet._q,F(W_MIN))
    cj = (bj-_value(wet._m,F(W_MIN)))/F(T_REF)
    regular = F(pure.chemical_potential_j_mol)/t+F(wet._mass)*(bj-t*cj)/t
    mu = None if not w else F(pure.chemical_potential_j_mol)+F(p.excess.mu_ex_j_mol)
    reference = _digest((chemical.reference,chemical.water.implementation,chemical.method_id,
                         pure.entropy_reference,chemical.source_asset_sha256))
    return LowMoistureWaterPoint(t,w,F(p.pressure_pa),mu,
        F(pure.enthalpy_j_mol)+F(p.excess.partial_h_ex_j_mol),F(wet._mass),
        F(chemical.gas_constant_j_mol_k),regular,reference,
        tuple(sorted(set(p.source_ids+pure.source_ids+(MODEL_ID,)))),expected_scope,'derived_from_evidence')


@dataclass(frozen=True)
class LowMoistureFactor:
    gamma_j_mol: F | None
    temperature_k: F
    moisture_interval: tuple[F,F]
    method: str
    source_ids: tuple[str,...]
    log_numerical_error: None = None

    def to_record(self) -> dict:
        return {'gamma_j_mol': None if self.gamma_j_mol is None else _rat(self.gamma_j_mol),
            'temperature_k': _rat(self.temperature_k), 'moisture_interval': [_rat(w) for w in self.moisture_interval],
            'method': self.method,'source_ids':list(self.source_ids),'log_numerical_error':None}


@dataclass(frozen=True)
class LowMoistureFaceExchange:
    molar_flow_mol_s: float
    carried_energy_w: float
    moisture_entropy_w_k: float | None
    exact_molar_flow_mol_s: F
    exact_carried_energy_w: F
    exact_moisture_entropy_w_k: F | None
    rounded_rate_entropy_balance_w_k: F | None
    dry_density_kg_m3: F
    driving_force_j_mol_k: F | None
    complete_mu_readout_drive_j_mol_k: F | None
    drive_readout_residual_j_mol_k: F | None
    entropy_state: str
    numerical_projections: tuple[QuantityProjection,...]
    source_ids: tuple[str,...]
    _input_provenance_json: str = field(repr=False)
    model_error: None = None
    log_numerical_error: None = None
    material_qualified: bool = False
    training_eligible: bool = False

    def to_record(self) -> dict:
        quantities = ('exact_molar_flow_mol_s','exact_carried_energy_w','exact_moisture_entropy_w_k',
            'rounded_rate_entropy_balance_w_k','dry_density_kg_m3','driving_force_j_mol_k',
            'complete_mu_readout_drive_j_mol_k','drive_readout_residual_j_mol_k')
        return {**{name: None if getattr(self,name) is None else _rat(getattr(self,name)) for name in quantities},
            'molar_flow_mol_s':self.molar_flow_mol_s,'carried_energy_w':self.carried_energy_w,
            'moisture_entropy_w_k':self.moisture_entropy_w_k,'entropy_state':self.entropy_state,
            'numerical_projections':[p.to_record() for p in self.numerical_projections],
            'source_ids':list(self.source_ids),'input_provenance':json.loads(self._input_provenance_json),
            'conduction_included':False,'additional_latent_source_w':0,
            'model_error':None,'log_numerical_error':None,'material_qualified':False,'training_eligible':False}


def _log_mean(a: F, b: F) -> F:
    _require(a > 0 and b > 0,'positive_logmean_inputs_required')
    return a if a == b else (a-b)/_log_ratio(a,b)


def _face(left, right, geometry, diffusivity, factor) -> LowMoistureFaceExchange:
    """Pure bounded algebra; only the public adapter authenticates runtime inputs."""
    for value, cls in ((left,LowMoistureWaterPoint),(right,LowMoistureWaterPoint),
                       (geometry,MoistureFaceGeometry),(diffusivity,EffectiveMoistureDiffusivity),
                       (factor,LowMoistureFactor)):
        _require(type(value) is cls,'explicit_low_moisture_face_records')
    _require(left.energy_reference_id == right.energy_reference_id,'low_moisture_reference_mismatch')
    _require((left.water_molar_mass_kg_mol,left.gas_constant_j_mol_k) ==
             (right.water_molar_mass_kg_mol,right.gas_constant_j_mol_k),'low_moisture_water_constants_mismatch')
    rho = geometry.left_dry_mass_kg/geometry.left_total_volume_m3
    _require(rho == geometry.right_dry_mass_kg/geometry.right_total_volume_m3,'low_moisture_uniform_dry_density_required')
    wl,wr = left.moisture_kg_water_per_kg_dry,right.moisture_kg_water_per_kg_dry
    tf = (left.temperature_k+right.temperature_k)/2
    _require(factor.temperature_k == tf and factor.moisture_interval == tuple(sorted((wl,wr))),
             'low_moisture_factor_state_correspondence')
    k = geometry.area_m2*rho*diffusivity.value_m2_s/(left.water_molar_mass_kg_mol*geometry.center_distance_m)
    hf = (left.partial_molar_enthalpy_j_mol+right.partial_molar_enthalpy_j_mol)/2
    xt = 1/right.temperature_k-1/left.temperature_k
    drive = readout = residual = entropy = rounded = None
    if wl == 0 or wr == 0:
        n = k*(wl-wr)
        state = 'no_exchange_double_dry' if wl == wr == 0 else 'positive_infinite_boundary_limit'
        if wl == wr == 0:
            entropy = rounded = F(0)
    else:
        xmu = left.chemical_potential_j_mol/left.temperature_k-right.chemical_potential_j_mol/right.temperature_k
        readout = xmu+hf*xt
        if max(wl,wr) <= F(W_MIN) and factor.method == 'analytic_low_moisture_or_zero_limit':
            logarithm = F(0) if wl == wr else _log_ratio(wl,wr)
            mean = _log_mean(wl,wr)
            r = left.gas_constant_j_mol_k
            c = left.join_chemical_potential_over_temperature_j_mol_k-right.join_chemical_potential_over_temperature_j_mol_k+hf*xt
            drive = r*logarithm+c
            n = k*((wl-wr)+mean*c/r)
        else:
            _require(factor.gamma_j_mol is not None and factor.gamma_j_mol > 0,'positive_low_moisture_factor_required')
            drive = readout
            n = tf*k/factor.gamma_j_mol*drive
        entropy = n*drive
        _require(entropy >= 0,'negative_low_moisture_entropy')
        residual = readout-drive
        state = 'no_exchange' if n == 0 else 'finite'
    carried = hf*n
    values = [('molar_flow_mol_s',n),('carried_energy_w',carried)]
    if entropy is not None:
        values.append(('moisture_entropy_w_k',entropy))
    projections = tuple(QuantityProjection(name,v,f,abs(F(f)-v))
                        for name,v in values for f in (_project(v,name),))
    nf,ef = projections[0].binary64,projections[1].binary64
    if wl and wr:
        rounded = F(ef)*xt+F(nf)*xmu
        _require(rounded >= 0,'rounded_low_moisture_entropy_negative')
        _require(entropy == 0 or rounded > 0,'rounded_low_moisture_entropy_unresolved')
    sources = tuple(sorted(set(left.source_ids+right.source_ids+geometry.source_ids+
                               diffusivity.source_ids+factor.source_ids+(MODEL_ID,MODEL_SHA256))))
    trace = {'left':left.to_record(),'right':right.to_record(),'geometry':geometry.to_record(),
             'diffusivity':diffusivity.to_record(),'factor':factor.to_record(),
             'input_authentication':'private algebra only; public runtime adapter supplies the separate witness'}
    return LowMoistureFaceExchange(nf,ef,None if entropy is None else projections[2].binary64,
        n,carried,entropy,rounded,rho,drive,readout,residual,state,projections,sources,
        json.dumps(trace,sort_keys=True,separators=(',',':'),allow_nan=False))


@dataclass(frozen=True)
class LowMoistureTransportWitness:
    points: tuple[LowMoistureWaterPoint,LowMoistureWaterPoint]
    factor: LowMoistureFactor
    exchange: LowMoistureFaceExchange
    storage_identities: tuple[str,str]
    inverses: tuple[SourceWetInverse,SourceWetInverse]
    phases: tuple[LowMoisturePhaseEvaluation,LowMoisturePhaseEvaluation]
    isothermal_fick_drive_residual_j_mol: F | None = field(default=None,kw_only=True)
    source_state_binding_verified: bool = True
    material_qualified: bool = False
    training_eligible: bool = False


@dataclass(frozen=True)
class LowMoistureTransport:
    original: MakelaMoistureTransport
    _identity: str = field(init=False,repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self,'_identity',self.binding())

    def binding(self) -> str:
        _require(type(self.original) is MakelaMoistureTransport,'actual_makela_transport_required')
        model = _model_definition(self.original.repository_root)
        self.original._check()
        _require(self.original._diffusivity.value_m2_s == F('8.56e-9'),'low_moisture_original_D_changed')
        identity = _digest((MODEL_ID,model,self.original.binding()))
        _require(not hasattr(self,'_identity') or identity == self._identity,'low_moisture_transport_changed')
        return identity

    @property
    def source_ids(self) -> tuple[str,...]:
        self.binding()
        return tuple(sorted(set(self.original.source_ids+(MODEL_ID,MODEL_SHA256))))

    def definition(self) -> dict:
        self.binding()
        return {'identity':self._identity,'model':_model_definition(self.original.repository_root),
                'original':self.original.definition(),'material_qualified':False,'training_eligible':False}

    def factor(self, storage, left, right) -> LowMoistureFactor:
        self.binding()
        _require(type(storage) is LowMoistureSorptionStorage,'actual_low_moisture_factor_storage')
        storage._check()
        a,b = sorted((left.moisture_kg_water_per_kg_dry,right.moisture_kg_water_per_kg_dry))
        _require(0 <= a <= b <= F(W_REF),'low_moisture_factor_domain')
        tf = (left.temperature_k+right.temperature_k)/2
        _require(F(T_MIN) <= tf <= F(T_REF),'low_moisture_factor_temperature_domain')
        ratio,mass = tf/F(T_REF),F(storage.wet._mass)
        r,j = F(storage.wet._chemical.gas_constant_j_mol_k),F(W_MIN)
        wet = storage.wet
        def source_sides(w):
            ms,qs = _slopes(wet._m,w),_slopes(wet._q,w)
            return tuple(mass*(ratio*ms[min(i,len(ms)-1)]-(1-ratio)*qs[min(i,len(qs)-1)])
                         for i in range(max(len(ms),len(qs))))
        if a == b:
            sides = ((r*tf/a,) if 0 < a < j else () if a == 0 else source_sides(a))
            if a == j:
                sides = (r*tf/j,)+sides
            _require(all(g > 0 for g in sides),'positive_one_sided_low_moisture_factor_required')
            gamma = sum(sides,F())/len(sides) if sides else None
        else:
            lo = max(a,j)
            edges = (lo,*sorted({F(x) for curve in (wet._m,wet._q) for x in curve.x if lo < F(x) < b}),b)
            if b > j:
                _require(all(mass*(ratio*(_value(wet._m,hi)-_value(wet._m,x))-
                    (1-ratio)*(_value(wet._q,hi)-_value(wet._q,x)))/(hi-x) > 0
                    for x,hi in zip(edges,edges[1:])),'positive_piecewise_low_moisture_factor_required')
            def mu(w):
                bj = F(wet._latent_reference)-_value(wet._q,j)
                if w < j:
                    return mass*(ratio*_value(wet._m,j)+(1-ratio)*bj)+r*tf*_log_ratio(w,j)
                return mass*(ratio*_value(wet._m,w)+(1-ratio)*(F(wet._latent_reference)-_value(wet._q,w)))
            gamma = (r*tf*_log_ratio(b,a)/(b-a) if 0 < a < b <= j else
                     (mu(b)-mu(a))/(b-a) if a else None)
            _require(gamma is None or gamma > 0,'positive_low_moisture_secant_required')
        # At the join itself the explicit positive two-side mean is retained;
        # all other two-low states use the stable logarithmic-mean closure.
        method = ('analytic_low_moisture_or_zero_limit' if a == 0 or b <= j and a != j
                  else 'declared_same_W_join_or_source_limit' if a == b
                  else 'declared_cross_join_or_source_secant')
        return LowMoistureFactor(gamma,tf,(a,b),method,self.source_ids+storage.source_ids)

    def exchange(self, storages, points, *, area_m2, widths_m, geometry_sources,
                 chemical=None, states=None, inverses=None, phases=None) -> LowMoistureTransportWitness:
        self.binding()
        _require(all(type(v) is tuple and len(v) == 2 for v in (storages,points,states,inverses,phases,widths_m)),
                 'low_moisture_actual_runtime_context_required')
        checked = tuple(low_moisture_water_point(s,chemical,state,inv,phase)
                        for s,state,inv,phase in zip(storages,states,inverses,phases))
        _require(checked == points,'low_moisture_points_do_not_match_actual_runtime')
        _require(storages[0].excess.binding() == storages[1].excess.binding(),
                 'common_low_moisture_thermodynamic_model_required')
        area = _scalar(area_m2,'area')
        dl,dr = (_scalar(x,'width') for x in widths_m)
        geometry = MoistureFaceGeometry(area,(dl+dr)/2,F(storages[0].dry_mass_kg),F(storages[1].dry_mass_kg),
            area*dl,area*dr,geometry_sources,'manufactured_test_fixture')
        factor = self.factor(storages[0],*points)
        left,right = points
        isothermal_residual = None
        if (left.temperature_k == right.temperature_k and left.pressure_pa == right.pressure_pa
                and left.moisture_kg_water_per_kg_dry > 0 and right.moisture_kg_water_per_kg_dry > 0):
            dw = left.moisture_kg_water_per_kg_dry-right.moisture_kg_water_per_kg_dry
            dmu = left.chemical_potential_j_mol-right.chemical_potential_j_mol
            if factor.method != 'analytic_low_moisture_or_zero_limit':
                _require(dw == 0 or dmu*dw > 0,'low_moisture_chemical_drive_resolution_failure')
            # This source-secant discrepancy is distinct from the leaf's
            # complete-mu versus stable-low-W drive readout discrepancy.
            isothermal_residual = dmu-factor.gamma_j_mol*dw
        result = _face(*points,geometry,self.original._diffusivity,factor)
        self.binding()
        return LowMoistureTransportWitness(points,factor,result,
            (storages[0].model_identity,storages[1].model_identity),inverses,phases,
            isothermal_fick_drive_residual_j_mol=isothermal_residual)
