"""Actual class with manufactured source/water seams; no EOS or material validation."""
from dataclasses import FrozenInstanceError
from fractions import Fraction as F
import json
import math
from pathlib import Path
import shutil

import pytest

import sludge_sandbox.arlabosse_low_moisture as low
from sludge_sandbox.arlabosse_wet_thermo import T_MIN, T_REF, W_MIN, W_REF, _Linear
from test_arlabosse_wet_thermo import factory  # Actual wet class, manufactured seams.


REPOSITORY = Path(__file__).resolve().parents[2]
if not (REPOSITORY/'src/sludge_sandbox/arlabosse_wet_thermo.py').exists():
    REPOSITORY = Path.cwd()
DRAFT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def make(factory):
    def create(edit=None):
        wet = factory()
        if edit is not None:
            edit(wet)
        definition = json.loads((DRAFT_ROOT/low.MODEL_PATH).read_bytes())
        for entry in definition['upstream']:
            dst = wet.repository_root/entry['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPOSITORY/entry['path'], dst)
        dst = wet.repository_root/low.MODEL_PATH
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DRAFT_ROOT/low.MODEL_PATH, dst)
        return low.ArlabosseLowMoisture(wet)
    return create


@pytest.fixture
def model(make):
    return make()


@pytest.mark.parametrize('t', (T_MIN, 337., T_REF))
def test_join_connects_energy_mu_and_retains_distinct_gamma_sides(model, t):
    j = model.evaluate(t, W_MIN)
    a = model.evaluate(t, math.nextafter(W_MIN, 0.))
    b = model.evaluate(t, math.nextafter(W_MIN, 1.))
    for x in (a, b):
        assert float(x.h_ex_j_kg_dry-j.h_ex_j_kg_dry) == pytest.approx(0., abs=2e-10)
        assert float(x.s_ex_j_kg_dry_k-j.s_ex_j_kg_dry_k) == pytest.approx(0., abs=1e-12)
        assert float(x.f_ex_j_kg_dry-j.f_ex_j_kg_dry) == pytest.approx(0., abs=2e-10)
        assert x.mu_ex_j_mol == pytest.approx(j.mu_ex_j_mol, abs=3e-11)
        assert x.partial_h_ex_j_mol == pytest.approx(j.partial_h_ex_j_mol, abs=1e-11)
    r = model.wet._chemical.gas_constant_j_mol_k
    assert j.gamma_left_j_mol == pytest.approx(r*t/W_MIN, rel=2e-15)
    assert j.gamma_right_j_mol > 0
    assert j.gamma_left_j_mol != pytest.approx(j.gamma_right_j_mol, rel=.1)
    assert j.gamma_state == 'finite_one_sided_join'


@pytest.mark.parametrize('w', (0., .035, .10, W_MIN, .355, W_REF))
def test_energy_identity_exact_nominal_algebra_and_zero_excess_cp(model, w):
    points = [model.evaluate(t, w) for t in (T_MIN, 339., T_REF)]
    for p in points:
        assert p.f_ex_j_kg_dry == p.h_ex_j_kg_dry-F(p.temperature_k)*p.s_ex_j_kg_dry_k
        assert p.excess_cp_j_kg_dry_k == 0
        assert p.excess_volume_m3_kg_dry == 0
    assert points[0].h_ex_j_kg_dry == points[1].h_ex_j_kg_dry == points[2].h_ex_j_kg_dry
    assert points[0].s_ex_j_kg_dry_k == points[1].s_ex_j_kg_dry_k == points[2].s_ex_j_kg_dry_k


@pytest.mark.parametrize('w', (.035, .10, .255, .455))
def test_free_energy_partial_derivatives_and_molar_units(model, w):
    t, dw, dt = 340., 1e-6, .05
    p = model.evaluate(t, w)
    wm, wp = model.evaluate(t, w-dw), model.evaluate(t, w+dw)
    tm, tp = model.evaluate(t-dt, w), model.evaluate(t+dt, w)
    mass = model.wet._mass
    assert float(wp.f_ex_j_kg_dry-wm.f_ex_j_kg_dry)*mass/(2*dw) == pytest.approx(p.mu_ex_j_mol, rel=2e-9, abs=1e-5)
    assert float(wp.h_ex_j_kg_dry-wm.h_ex_j_kg_dry)*mass/(2*dw) == pytest.approx(p.partial_h_ex_j_mol, abs=1e-6)
    assert -float(tp.f_ex_j_kg_dry-tm.f_ex_j_kg_dry)/(2*dt) == pytest.approx(float(p.s_ex_j_kg_dry_k), abs=1e-8)
    assert p.mu_ex_j_mol-t*(tp.mu_ex_j_mol-tm.mu_ex_j_mol)/(2*dt) == pytest.approx(p.partial_h_ex_j_mol, abs=1e-7)
    assert (wp.mu_ex_j_mol-wm.mu_ex_j_mol)/(2*dw) == pytest.approx(p.gamma_right_j_mol, rel=4e-9)


def test_zero_uses_analytic_xlogx_limit_and_preserves_nonzero_reference(model):
    t, j, mass = 339., F(W_MIN), F(model.wet._mass)
    join, dry = model.evaluate(t, j), model.evaluate(t, 0)
    b = F(model.wet._latent_reference)-F(model.wet._q.y[0])
    c = (b-F(model.wet._m.y[0]))/F(T_REF)
    rs = F(model.wet._chemical.gas_constant_j_mol_k)/mass
    assert dry.h_ex_j_kg_dry == join.h_ex_j_kg_dry-b*j
    assert dry.s_ex_j_kg_dry_k == join.s_ex_j_kg_dry_k-c*j-rs*j
    assert dry.h_ex_j_kg_dry != 0 and dry.s_ex_j_kg_dry_k != 0
    assert dry.mu_ex_j_mol is None and dry.mu_state == 'minus_infinity_at_zero_inventory'
    assert dry.gamma_left_j_mol is None and dry.gamma_right_j_mol is None
    assert dry.gamma_state == 'positive_infinite_boundary_limit'
    assert dry.activity == 0
    near = model.evaluate(t, 1e-12)
    assert float(near.h_ex_j_kg_dry-dry.h_ex_j_kg_dry) == pytest.approx(0, abs=1e-6)
    assert float(near.s_ex_j_kg_dry_k-dry.s_ex_j_kg_dry_k) == pytest.approx(0, abs=2e-8)
    assert near.activity > 0 and near.mu_ex_j_mol is not None
    json.dumps(dry.to_record(), allow_nan=False)


def test_fraction_moisture_is_not_projected_before_energy(model):
    w = F(.04)+F(1, 10**50)
    a, b = model.evaluate(337., F(.04)), model.evaluate(337., w)
    assert a.moisture_kg_water_per_kg_dry != b.moisture_kg_water_per_kg_dry
    assert b.moisture_kg_water_per_kg_dry == w
    slope = F(model.wet._latent_reference)-F(model.wet._q.y[0])
    assert b.h_ex_j_kg_dry-a.h_ex_j_kg_dry == slope*(w-F(.04))
    w = F(.4)+F(1, 10**50)
    a, b = model.evaluate(337., F(.4)), model.evaluate(337., w)
    assert a.h_ex_j_kg_dry != b.h_ex_j_kg_dry


def test_activity_linear_in_low_moisture_held_out_point_not_used(model, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('evaluation must not fit new points or run water EOS')
    monkeypatch.setattr(type(model.wet._desorption), 'at_moisture', forbidden)
    monkeypatch.setattr(type(model.wet._chemical), 'equilibrium_at_liquid_tp', forbidden)
    for t in (T_MIN, T_REF):
        j = model.evaluate(t, W_MIN)
        for w in (.1, .075, .001):
            x = model.evaluate(t, w)
            assert x.activity == pytest.approx(j.activity*w/W_MIN, rel=3e-15)
    definition = model.definition()
    assert definition['held_out']['moisture_kg_water_per_kg_dry'] == .1
    assert definition['held_out']['used_for_fitting'] is False
    assert all(float(x) >= W_MIN for x in model.wet._m.x)


@pytest.mark.parametrize('w', (W_MIN, .2, .355, .4, .6, .8))
def test_original_nominal_mu_and_activity_are_continued_to_readout_roundoff(model, w):
    for t in (T_MIN, T_REF):
        p = model.evaluate(t, w)
        old_mu, old_b, old_aw, _ = model.wet._excess(t, w)
        assert p.mu_ex_j_mol == pytest.approx(old_mu*model.wet._mass, abs=2e-11)
        assert p.partial_h_ex_j_mol == pytest.approx(old_b*model.wet._mass, abs=2e-11)
        assert p.activity == pytest.approx(old_aw, rel=3e-15)
        assert p.log_numerical_error is None
        assert p.model_error is None and not p.material_qualified and not p.training_eligible


@pytest.mark.parametrize('t,w', [(307., .1), (369., .1), (330., -.1), (330., .81),
                               (True, .1), (330., False), (math.nan, .1),
                               (330., math.inf), ('330', .1)])
def test_bad_inputs_and_domain_exit(model, t, w):
    with pytest.raises(low.LowMoistureError):
        model.evaluate(t, w)


@pytest.mark.parametrize('w', [math.nextafter(0., 1.), F(1, 10**1000)])
def test_unrepresentable_positive_state_is_never_reported_as_dry(model, w):
    with pytest.raises(low.LowMoistureError, match='represent|overflow|underflow'):
        model.evaluate(340., w)


@pytest.mark.parametrize('entry', ['model', 'facts', 'code'])
def test_public_entrances_reject_source_file_drift(model, entry):
    paths = {'model': low.MODEL_PATH,
             'facts': 'data/sandbox/research/arlabosse95/facts.json',
             'code': 'src/sludge_sandbox/arlabosse_wet_thermo.py'}
    path = model.wet.repository_root/paths[entry]
    path.write_bytes(path.read_bytes()+b'\n')
    for call in (lambda: model.evaluate(330., .1), model.binding, model.definition,
                 lambda: model.source_ids):
        with pytest.raises(low.LowMoistureError, match='changed'):
            call()


def test_actual_coefficient_drift_and_mutable_metadata_leaks(model):
    definition = model.definition()
    definition['held_out']['used_for_fitting'] = True
    assert model.definition()['held_out']['used_for_fitting'] is False
    point = model.evaluate(330., .1)
    with pytest.raises(FrozenInstanceError):
        point.activity = 1.
    q = model.wet._q
    object.__setattr__(model.wet, '_q', _Linear(q.x, (q.y[0]+1., *q.y[1:])))
    with pytest.raises(low.LowMoistureError, match='changed'):
        model.evaluate(330., .1)


def test_exact_source_class_required():
    with pytest.raises(low.LowMoistureError, match='actual_arlabosse'):
        low.ArlabosseLowMoisture(object())


def test_upper_curve_integrals_against_independent_constant_curve_oracle(make):
    # Deliberately manufactured curves have a closed-form integral, including
    # a non-binary64 input W. This checks the integral anchor and both signs.
    def edit(wet):
        object.__setattr__(wet, '_m', _Linear(wet._m.x, (-100_000.,)*len(wet._m.x)))
        object.__setattr__(wet, '_q', _Linear(wet._q.x, (2_700_000.,)*len(wet._q.x)))
    model = make(edit)
    for w in (F(W_MIN), F(.355)+F(1, 10**50), F(W_REF)):
        p = model.evaluate(330., w)
        displacement = w-F(W_REF)
        expected_h = (F(model.wet._latent_reference)-2_700_000)*displacement
        expected_s = (expected_h+100_000*displacement)/F(T_REF)
        assert p.h_ex_j_kg_dry == expected_h
        assert p.s_ex_j_kg_dry_k == expected_s
        assert p.f_ex_j_kg_dry == expected_h-330*expected_s


def test_upper_one_sided_gamma_uses_distinct_m_and_q_node_grids(make):
    def edit(wet):
        object.__setattr__(wet, '_m', _Linear(wet._m.x,
                           tuple(-150_000.+10_000.*i*i for i in range(len(wet._m.x)))))
    model = make(edit)
    t, w = F(330.), F(.5)  # m node; q has no .5 or .6 node.
    point = model.evaluate(t, w)
    m, q, mass = model.wet._m, model.wet._q, F(model.wet._mass)
    qi = q.x.index(.4)
    dq = (F(q.y[qi+1])-F(q.y[qi]))/(F(q.x[qi+1])-F(q.x[qi]))
    mi = m.x.index(.5)
    left = (F(m.y[mi])-F(m.y[mi-1]))/(F(m.x[mi])-F(m.x[mi-1]))
    right = (F(m.y[mi+1])-F(m.y[mi]))/(F(m.x[mi+1])-F(m.x[mi]))
    ratio = t/F(T_REF)
    assert point.gamma_left_j_mol == float(mass*(ratio*left-(1-ratio)*dq))
    assert point.gamma_right_j_mol == float(mass*(ratio*right-(1-ratio)*dq))
    assert point.gamma_left_j_mol != point.gamma_right_j_mol


def test_metadata_uses_contract_classifications_and_strict_json(model):
    allowed = {'physical_law_or_constant', 'measured_public_data',
               'literature_constitutive_model', 'derived_from_evidence',
               'virtual_design_choice', 'numerical_policy', 'manufactured_test_fixture', 'unknown'}
    definition = model.definition()
    assert set(definition['input_classifications'].values()) <= allowed
    assert definition['model_error'] is None
    assert definition['log_numerical_error'] is None
    assert definition['activity_numerical_error'] is None
    assert not definition['material_qualified']
    for w in (0, .1, W_MIN, .8):
        record = model.evaluate(330., w).to_record()
        record['source_ids'] = []
        assert model.evaluate(330., w).source_ids
        json.dumps(record, allow_nan=False)
