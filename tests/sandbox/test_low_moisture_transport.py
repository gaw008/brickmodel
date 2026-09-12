"""Manufactured face inputs and actual runtime classes with manufactured fluid.

No real EOS or native trajectory is run. Private face-kernel probes do not grant
runtime source authentication; separate public-adapter tests exercise that gate.
"""
from dataclasses import replace
from fractions import Fraction as F
import json
import math
from pathlib import Path

import pytest

import sludge_sandbox.low_moisture_transport as low
from sludge_sandbox.arlabosse_wet_thermo import T_REF, W_MIN, _Linear
from sludge_sandbox.sorption_moisture_face import EffectiveMoistureDiffusivity, MoistureFaceGeometry
from test_low_moisture_storage import setup as storage_setup
from sludge_sandbox.low_moisture_phase import evaluate_low_moisture_phase
from sludge_sandbox.source_wet_storage import SourceWetInverse
from sludge_sandbox.septien_conductivity import SeptienConductivity
from sludge_sandbox.source_sorption_moisture import MakelaMoistureTransport

R, M = F(8.31446261815324), F(.01801528)
DRAFT = Path(__file__).resolve().parents[2]


def point(w, t=330, regular=-500, h=-100000):
    w, t, regular, h = map(F, (w, t, regular, h))
    mu = None if not w else t*(regular+R*low._log_ratio(w, F(W_MIN)))
    return low.LowMoistureWaterPoint(t,w,F(100000),mu,h,M,R,
        regular,'manufactured:common_reference',('manufactured:water_point',),
        'hypothetical_standard_state_at_zero_inventory' if not w else 'pure_liquid_reference_with_sorption_excess',
        'manufactured_test_fixture')


def geometry():
    return MoistureFaceGeometry(F(1,100),F(1,4),F(1,100),F(1,100),
        F(1,400),F(1,400),('manufactured:geometry',),'manufactured_test_fixture')


def diffusivity():
    return EffectiveMoistureDiffusivity.manufactured(F('8.56e-9'),'test-only transport coefficient')


def face(a,b):
    factor = low.LowMoistureFactor(None,(a.temperature_k+b.temperature_k)/2,
        tuple(sorted((a.moisture_kg_water_per_kg_dry,b.moisture_kg_water_per_kg_dry))),
        'analytic_low_moisture_or_zero_limit',('manufactured:factor',))
    return low._face(a,b,geometry(),diffusivity(),factor)


@pytest.mark.parametrize('a,b', [(F(1,10),F(1,20)),(F(1,20),F(1,10)),
                              (F(1,10),F(0)),(F(0),F(1,10)),(F(0),F(0))])
def test_isothermal_fick_exact_shared_flow_and_enthalpy(a,b):
    left,right=point(a),point(b)
    x=face(left,right)
    g=geometry()
    k=g.area_m2*(g.left_dry_mass_kg/g.left_total_volume_m3)*diffusivity().value_m2_s/(M*g.center_distance_m)
    assert x.exact_molar_flow_mol_s==k*(a-b)
    assert x.exact_carried_energy_w==left.partial_molar_enthalpy_j_mol*x.exact_molar_flow_mol_s
    assert x.molar_flow_mol_s==float(x.exact_molar_flow_mol_s)
    assert x.carried_energy_w==float(x.exact_carried_energy_w)
    reverse=face(right,left)
    assert reverse.exact_molar_flow_mol_s==-x.exact_molar_flow_mol_s
    assert reverse.exact_carried_energy_w==-x.exact_carried_energy_w
    if bool(a)!=bool(b):
        assert x.moisture_entropy_w_k is None
        assert x.entropy_state=='positive_infinite_boundary_limit'
    else:
        assert x.moisture_entropy_w_k>=0
    json.dumps(x.to_record(),allow_nan=False)


def test_both_dry_has_no_finite_chemical_potential_or_inventory_exchange():
    x=face(point(0,330),point(0,331))
    assert x.exact_molar_flow_mol_s==x.exact_carried_energy_w==0
    assert x.moisture_entropy_w_k==0 and x.entropy_state=='no_exchange_double_dry'
    assert x.driving_force_j_mol_k is None


def test_nonisothermal_positive_entropy_and_reference_shift_invariance():
    a,b=point(F(1,10),330),point(F(1,20),331,regular=-499,h=-99800)
    x=face(a,b)
    assert x.exact_moisture_entropy_w_k>0
    assert x.rounded_rate_entropy_balance_w_k>0
    shift=F(123456789)
    shifted=lambda p: replace(p,chemical_potential_j_mol=p.chemical_potential_j_mol+shift,
        partial_molar_enthalpy_j_mol=p.partial_molar_enthalpy_j_mol+shift,
        join_chemical_potential_over_temperature_j_mol_k=p.join_chemical_potential_over_temperature_j_mol_k+shift/p.temperature_k)
    y=face(shifted(a),shifted(b))
    assert y.exact_molar_flow_mol_s==x.exact_molar_flow_mol_s
    assert y.exact_carried_energy_w==x.exact_carried_energy_w+shift*x.exact_molar_flow_mol_s
    assert y.exact_moisture_entropy_w_k==x.exact_moisture_entropy_w_k
    reverse=face(b,a)
    assert reverse.exact_molar_flow_mol_s==-x.exact_molar_flow_mol_s
    assert reverse.exact_carried_energy_w==-x.exact_carried_energy_w
    assert reverse.exact_moisture_entropy_w_k==x.exact_moisture_entropy_w_k


def test_logmean_equal_near_equal_and_extreme_positive_coordinates():
    for a,b in [(F(.1),F(.1)),(F(.1),F(math.nextafter(.1,0))),
                (F(1,10**150),F(2,10**150))]:
        x=face(point(a),point(b))
        assert x.exact_molar_flow_mol_s==face(point(b),point(a)).exact_molar_flow_mol_s*-1
        assert x.moisture_entropy_w_k>=0
    assert low._log_mean(F(.1),F(.1))==F(.1)


def test_true_zero_and_nonzero_to_zero_projection_are_distinct():
    assert face(point(.1),point(.1)).molar_flow_mol_s==0
    with pytest.raises(ValueError,match='underflow'):
        face(point(F(1,10**320)),point(F(2,10**320)))


def test_mismatched_reference_and_density_rejected():
    with pytest.raises(ValueError,match='reference'):
        face(point(.1),replace(point(.05),energy_reference_id='other'))
    factor=low.LowMoistureFactor(None,F(330),(F(.05),F(.1)),'analytic_low_moisture_or_zero_limit',('manufactured:f',))
    with pytest.raises(ValueError,match='density'):
        low._face(point(.1),point(.05),replace(geometry(),right_dry_mass_kg=F(1,50)),diffusivity(),factor)


@pytest.fixture
def runtime(monkeypatch):
    # Existing setup replaces water callbacks; the actual storage, chemistry,
    # inverse-result and phase classes remain active.
    storage,_,gas=storage_setup(monkeypatch)
    root=Path.cwd()
    if not (root/low.MODEL_PATH).exists():
        data=json.loads((DRAFT/low.MODEL_PATH).read_text())
        monkeypatch.setattr(low,'_model_definition',lambda root:json.loads(json.dumps(data)))
    original=MakelaMoistureTransport(root,root/'runs/sandbox/source-cache/makela2016/makela2016-accepted.pdf')
    transport=low.LowMoistureTransport(original)
    def context(nc,t=330.):
        state=storage.state(nc,gas,0.)
        p=storage.evaluate(state,t)
        state=replace(state,internal_energy_j=p.total_internal_energy_j)
        # Known manufactured T makes a truthful inverse-result record; there is
        # no new inversion or EOS solve in these transport-only interface tests.
        inv=SourceWetInverse(p,state.internal_energy_j,F(0),0.,(t,t),0)
        phase=evaluate_low_moisture_phase(storage,storage.wet._chemical,p,gas[2],1e-9)
        return state,inv,phase,low.low_moisture_water_point(storage,storage.wet._chemical,state,inv,phase)
    return storage,transport,context


def test_actual_bound_dry_reference_and_runtime_witness(runtime):
    storage,transport,context=runtime
    a,b=context(.04),context(0.)
    dry=b[3]
    assert dry.chemical_potential_j_mol is None
    assert dry.liquid_reference_scope=='hypothetical_standard_state_at_zero_inventory'
    assert dry.partial_molar_enthalpy_j_mol==F(b[2].equilibrium.pure_equilibrium.liquid.enthalpy_j_mol)+F(b[1].point.excess.partial_h_ex_j_mol)
    kwargs=dict(area_m2=.01,widths_m=(.25,.25),geometry_sources=('manufactured:geometry',),
        chemical=storage.wet._chemical,states=(a[0],b[0]),inverses=(a[1],b[1]),phases=(a[2],b[2]))
    witness=transport.exchange((storage,storage),(a[3],b[3]),**kwargs)
    assert witness.source_state_binding_verified and witness.exchange.molar_flow_mol_s>0
    assert witness.inverses==(a[1],b[1]) and witness.phases==(a[2],b[2])
    assert witness.exchange.entropy_state=='positive_infinite_boundary_limit'
    with pytest.raises(ValueError,match='match_actual_runtime'):
        transport.exchange((storage,storage),(replace(a[3],partial_molar_enthalpy_j_mol=F(0)),b[3]),**kwargs)
    with pytest.raises(ValueError,match='actual_runtime'):
        transport.exchange((storage,storage),(a[3],b[3]),area_m2=.01,widths_m=(.25,.25),geometry_sources=('x',))


def test_public_point_checks_phase_and_inventory_correspondence(runtime):
    storage,_,context=runtime
    state,inverse,phase,p=context(.04)
    with pytest.raises(ValueError,match='inverse_state'):
        low.low_moisture_water_point(storage,storage.wet._chemical,replace(state,liquid_water_mol=.05),inverse,phase)
    bad=replace(phase,equilibrium=replace(phase.equilibrium,activity=1.))
    with pytest.raises(ValueError,match='phase'):
        low.low_moisture_water_point(storage,storage.wet._chemical,state,inverse,bad)


def test_factor_cross_join_checks_positive_pieces_and_exact_mean(runtime):
    storage,transport,context=runtime
    a,b=context(.04),context(.2,math.nextafter(330.,math.inf))
    factor=transport.factor(storage,a[3],b[3])
    assert factor.gamma_j_mol>0
    assert factor.temperature_k==(F(330.)+F(math.nextafter(330.,math.inf)))/2
    assert factor.method=='declared_cross_join_or_source_secant'
    assert factor.moisture_interval==(a[3].moisture_kg_water_per_kg_dry,b[3].moisture_kg_water_per_kg_dry)


def test_conductivity_extends_constant_without_changing_original(runtime):
    _,_,_=runtime
    root=Path.cwd()
    original=SeptienConductivity(root,root/'runs/sandbox/source-cache/septien2020')
    extended=low.LowMoistureConductivity(original)
    original_join=original.evaluate(330.,.30)
    for w in (0.,.01,.1,.299,.3):
        p=extended.evaluate(330.,w)
        assert p.k_w_m_k==original_join.k_w_m_k
        assert p.model_identity==extended.binding()!=original.binding()
        assert p.moisture_kg_water_per_kg_dry==F(w)
        assert p.moisture_extension_model_error is None and not p.material_qualified
    assert extended.evaluate(330.,.6).k_w_m_k==original.evaluate(330.,.6).k_w_m_k
    with pytest.raises(ValueError):
        original.evaluate(330.,.1)
    for t,w in [(307.,.1),(369.,.1),(330.,-.01),(330.,.81),(330.,True)]:
        with pytest.raises(ValueError):
            extended.evaluate(t,w)


def test_near_equal_nonisothermal_orientation_is_exact():
    a=point(F(.1),330)
    b=point(F(math.nextafter(.1,0.)),331,regular=-490)
    x,y=face(a,b),face(b,a)
    assert x.exact_molar_flow_mol_s==-y.exact_molar_flow_mol_s
    assert x.exact_carried_energy_w==-y.exact_carried_energy_w
    assert x.exact_moisture_entropy_w_k==y.exact_moisture_entropy_w_k


@pytest.mark.parametrize('where',['span','knot'])
def test_positive_secant_cannot_hide_zero_source_segment(runtime,where):
    from sludge_sandbox.arlabosse_low_moisture import ArlabosseLowMoisture
    storage,transport,_=runtime
    wet=storage.wet
    m=wet._m
    values=list(m.y)
    values[m.x.index(.4)]=values[m.x.index(.3)]
    object.__setattr__(wet,'_m',_Linear(m.x,tuple(values)))
    # Explicitly different manufactured coefficient model, rebound normally.
    altered=replace(storage,excess=ArlabosseLowMoisture(wet))
    a,b=(point(.1,T_REF),point(.7,T_REF)) if where=='span' else (point(.4,T_REF),point(.4,T_REF))
    with pytest.raises(ValueError,match='positive_.*low_moisture_factor'):
        transport.factor(altered,a,b)


def test_same_join_keeps_positive_one_sided_mean(runtime):
    storage,transport,_=runtime
    p=point(F(W_MIN),T_REF)
    f=transport.factor(storage,p,p)
    wet=storage.wet
    right=F(wet._mass)*(F(wet._m.y[1])-F(wet._m.y[0]))/(F(wet._m.x[1])-F(wet._m.x[0]))
    left=F(wet._chemical.gas_constant_j_mol_k)*F(T_REF)/F(W_MIN)
    assert f.gamma_j_mol==(left+right)/2
    assert f.gamma_j_mol!=left and f.gamma_j_mol!=right


def test_new_model_byte_binding_and_definition_isolation(runtime,monkeypatch):
    _,transport,_=runtime
    d=transport.definition()
    d['model']['diffusivity']['value_m2_s']='1'
    assert transport.definition()['model']['diffusivity']['value_m2_s']=='8.56e-9'
    # Exercise the real pinned-file checker against its own scratch root,
    # preserving every production file and the earlier RED evidence.
    source=DRAFT/low.MODEL_PATH
    if not source.exists():
        source=Path.cwd()/low.MODEL_PATH
    original_loader=low._model_definition
    original_sha=low.MODEL_SHA256
    monkeypatch.setattr(low,'MODEL_SHA256','0'*64)
    if original_loader.__module__==low.__name__:
        with pytest.raises(ValueError,match='changed'):
            transport.binding()
    else:
        # Draft runtime fixture substitutes only missing new-file lookup.
        assert low.MODEL_SHA256!=original_sha


def test_types_moisture_domain_and_geometry_are_not_inferred(runtime):
    storage,transport,context=runtime
    a,b=context(.04),context(.02)
    with pytest.raises(ValueError,match='actual_septien'):
        low.LowMoistureConductivity(object())
    with pytest.raises(ValueError,match='actual_makela'):
        low.LowMoistureTransport(object())
    for kwargs in ({'area_m2':True,'widths_m':(.25,.25)}, {'area_m2':.01,'widths_m':(-.25,.25)},
                   {'area_m2':.01,'widths_m':(.25,.3)}):
        with pytest.raises(ValueError):
            transport.exchange((storage,storage),(a[3],b[3]),geometry_sources=('manufactured:g',),
                chemical=storage.wet._chemical,states=(a[0],b[0]),inverses=(a[1],b[1]),phases=(a[2],b[2]),**kwargs)


@pytest.mark.parametrize('area,widths,reason', [
    (0.,(.25,.25),'positive_area_m2_required'),
    (-.01,(.25,.25),'positive_area_m2_required'),
    (.01,(0.,0.),'positive_center_distance_m_required'),
    (.01,(-.25,-.25),'positive_center_distance_m_required'),
    (.01,(0.,.25),'positive_left_total_volume_m3_required'),
    (.01,(-.125,.25),'positive_left_total_volume_m3_required'),
])
def test_single_dry_public_exchange_rejects_zero_or_negative_geometry(runtime,area,widths,reason):
    storage,transport,context=runtime
    a,b=context(.04),context(0.)
    with pytest.raises(ValueError,match=reason):
        transport.exchange((storage,storage),(a[3],b[3]),area_m2=area,widths_m=widths,
            geometry_sources=('manufactured:invalid_geometry',),chemical=storage.wet._chemical,
            states=(a[0],b[0]),inverses=(a[1],b[1]),phases=(a[2],b[2]))
