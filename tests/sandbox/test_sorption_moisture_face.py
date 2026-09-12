"""Analytic declared-input face tests, not source-state or material validation."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

import pytest

from sludge_sandbox.sorption_moisture_face import (
    CondensedWaterPoint, MoistureFaceGeometry, EffectiveMoistureDiffusivity,
    MoistureThermodynamicFactor, SorptionMoistureError, sorption_moisture_face,
)
import sludge_sandbox.sorption_moisture_face as module


SOURCES = ('manufactured:analytic_face',)
CLASS = 'manufactured_test_fixture'
D = F('8.56e-9')
M = F('0.018')


def inputs(*, temperatures=(F(330), F(330)), moistures=(F('.7'), F('.4'))):
    left, right = tuple(CondensedWaterPoint(t, w, F(100000), -200000+1200*w,
        -100000+2000*w, M, 'manufactured:common_reference', SOURCES, CLASS)
        for t, w in zip(temperatures, moistures))
    geometry = MoistureFaceGeometry(F('.01'), F('.01'), F(1), F(1),
                                   F('.001'), F('.001'), SOURCES, CLASS)
    diffusion = EffectiveMoistureDiffusivity.manufactured(D, 'Analytic test parameter')
    method = 'declared_same_W_limit' if moistures[0] == moistures[1] else 'declared_secant'
    factor = MoistureThermodynamicFactor(F(1200), sum(temperatures)/2,
                                       tuple(sorted(moistures)), method, SOURCES, CLASS)
    return left, right, geometry, diffusion, factor


def test_isothermal_equal_pressure_analytical_fick_limit():
    args = inputs()
    out = sorption_moisture_face(*args)
    l, r, g, _, _ = args
    expected = g.area_m2*(g.left_dry_mass_kg/g.left_total_volume_m3)*D/(M*g.center_distance_m)*(
        l.moisture_kg_water_per_kg_dry-r.moisture_kg_water_per_kg_dry)
    assert out.exact_molar_flow_mol_s == expected
    assert out.molar_flow_mol_s == float(expected)
    assert out.exact_carried_energy_w == (l.partial_molar_enthalpy_j_mol+
                                          r.partial_molar_enthalpy_j_mol)/2*expected
    assert out.exact_moisture_entropy_w_k >= 0
    assert out.rounded_rate_entropy_balance_w_k >= 0


def test_left_right_exchange_changes_only_directed_rate_signs():
    args = inputs(temperatures=(F(325), F(355)))
    a = sorption_moisture_face(*args)
    b = sorption_moisture_face(args[1], args[0], *args[2:])
    assert a.molar_flow_mol_s == -b.molar_flow_mol_s
    assert a.carried_energy_w == -b.carried_energy_w
    assert a.exact_moisture_entropy_w_k == b.exact_moisture_entropy_w_k
    assert a.moisture_entropy_w_k == b.moisture_entropy_w_k


def test_true_zero_driving_force_gives_true_zero_rates():
    args = inputs(moistures=(F('.5'), F('.5')))
    out = sorption_moisture_face(*args)
    assert out.driving_force_j_mol_k == 0
    assert out.exact_molar_flow_mol_s == out.exact_carried_energy_w == out.exact_moisture_entropy_w_k == 0
    assert out.molar_flow_mol_s == out.carried_energy_w == out.moisture_entropy_w_k == 0.


def test_nonisothermal_exact_entropy_and_shared_energy_balance():
    args = inputs(temperatures=(F(325), F(355)))
    out = sorption_moisture_face(*args)
    l, r = args[:2]
    xt = 1/r.temperature_k-1/l.temperature_k
    xmu = l.chemical_potential_j_mol/l.temperature_k-r.chemical_potential_j_mol/r.temperature_k
    assert out.exact_carried_energy_w*xt+out.exact_molar_flow_mol_s*xmu == out.exact_moisture_entropy_w_k
    assert out.exact_moisture_entropy_w_k == out.mobility_mol2_k_j_s*out.driving_force_j_mol_k**2 > 0
    assert out.rounded_rate_entropy_balance_w_k == F(out.carried_energy_w)*xt+F(out.molar_flow_mol_s)*xmu
    assert -F(out.molar_flow_mol_s)+F(out.molar_flow_mol_s) == 0
    assert -F(out.carried_energy_w)+F(out.carried_energy_w) == 0


def test_common_energy_reference_shift_preserves_drive_and_entropy():
    args = inputs(temperatures=(F(325), F(355)))
    a = sorption_moisture_face(*args)
    shift = F(123456789)
    changed = [replace(p, chemical_potential_j_mol=p.chemical_potential_j_mol+shift,
                       partial_molar_enthalpy_j_mol=p.partial_molar_enthalpy_j_mol+shift,
                       energy_reference_id='manufactured:shifted_common_reference') for p in args[:2]]
    b = sorption_moisture_face(*changed, *args[2:])
    assert a.driving_force_j_mol_k == b.driving_force_j_mol_k
    assert a.exact_molar_flow_mol_s == b.exact_molar_flow_mol_s
    assert a.exact_moisture_entropy_w_k == b.exact_moisture_entropy_w_k
    assert b.exact_carried_energy_w-a.exact_carried_energy_w == shift*a.exact_molar_flow_mol_s


def test_wrong_enthalpy_is_observable_not_double_latent_corrected():
    args = inputs(temperatures=(F(325), F(355)))
    a = sorption_moisture_face(*args)
    wrong = [replace(p, partial_molar_enthalpy_j_mol=F(0)) for p in args[:2]]
    b = sorption_moisture_face(*wrong, *args[2:])
    assert a.exact_molar_flow_mol_s != b.exact_molar_flow_mol_s
    assert b.exact_carried_energy_w == 0
    assert b.to_record()['additional_latent_source_w'] == 0
    assert b.to_record()['source_state_binding_verified'] is False


@pytest.mark.parametrize('gamma', [F(0), F(-1), True, float('nan'), float('inf')])
def test_bad_thermodynamic_factor_cannot_pass(gamma):
    args = inputs()
    with pytest.raises(ValueError):
        sorption_moisture_face(*args[:-1], replace(args[-1], gamma_j_mol=gamma))


@pytest.mark.parametrize('change', [dict(temperature_k=F(331)), dict(moisture_interval=(F('.3'), F('.7'))),
                                   dict(method='arbitrary_positive_number')])
def test_factor_must_correspond_to_actual_face_states(change):
    args = inputs()
    with pytest.raises(ValueError, match='factor'):
        sorption_moisture_face(*args[:-1], replace(args[-1], **change))


def test_same_W_requires_an_explicit_limit_instead_of_secant():
    args = inputs(moistures=(F('.5'), F('.5')))
    with pytest.raises(ValueError, match='factor'):
        sorption_moisture_face(*args[:-1], replace(args[-1], method='declared_secant'))


def test_density_is_computed_from_total_volume_and_must_match():
    args = inputs()
    with pytest.raises(ValueError, match='density'):
        sorption_moisture_face(args[0], args[1], replace(args[2], right_total_volume_m3=F('.002')),
                               *args[3:])
    valid = replace(args[2], right_dry_mass_kg=F(2), right_total_volume_m3=F('.002'))
    assert sorption_moisture_face(args[0], args[1], valid, *args[3:]).dry_density_kg_m3 == 1000


def test_energy_reference_and_molar_mass_cannot_differ():
    args = inputs()
    for right in (replace(args[1], energy_reference_id='other'),
                  replace(args[1], water_molar_mass_kg_mol=F('.019'))):
        with pytest.raises(ValueError, match='reference|molar_mass'):
            sorption_moisture_face(args[0], right, *args[2:])


@pytest.mark.parametrize('change', [dict(temperature_k=F(380)), dict(pressure_pa=F(120000)),
                                  dict(moisture_kg_water_per_kg_dry=F('.2'))])
def test_declared_source_extension_domain_is_enforced(change):
    args = inputs()
    with pytest.raises(ValueError, match='domain'):
        sorption_moisture_face(replace(args[0], **change), *args[1:])


def test_underflow_cannot_turn_nonzero_transport_into_false_equilibrium():
    args = inputs()
    tiny = EffectiveMoistureDiffusivity.manufactured(math.ulp(0.), 'Underflow negative control')
    small_area = replace(args[2], area_m2=F('1e-6'))
    with pytest.raises(ValueError, match='underflow'):
        sorption_moisture_face(args[0], args[1], small_area, tiny, args[-1])


def test_overflow_in_transport_is_rejected():
    args = inputs()
    huge = EffectiveMoistureDiffusivity.manufactured(1e308, 'Overflow negative control')
    with pytest.raises(ValueError, match='overflow'):
        sorption_moisture_face(*args[:3], huge, args[-1])


def test_input_provenance_and_projection_records_are_truthful():
    out = sorption_moisture_face(*inputs(temperatures=(F(325), F(355))))
    record = out.to_record()
    assert record['source_state_binding_verified'] is False
    assert record['material_qualified'] is False and record['training_eligible'] is False
    assert record['errors']['total_model_uncertainty'] is None
    assert record['conduction_included'] is False
    assert record['additional_latent_source_w'] == 0
    for item in record['numerical_projections']:
        exact = F(*item['exact'])
        assert F(*item['absolute_projection_error']) == abs(F(item['binary64'])-exact)
        assert exact == 0 or item['binary64'] != 0
    json.dumps(record, allow_nan=False)
    record['input_provenance']['left']['energy_reference_id'] = 'changed'
    assert out.to_record()['input_provenance']['left']['energy_reference_id'] != 'changed'


def test_carried_energy_underflow_is_not_silently_zero():
    args = inputs()
    points = [replace(p, partial_molar_enthalpy_j_mol=math.ulp(0.)) for p in args[:2]]
    with pytest.raises(ValueError, match='carried_energy_w_underflow'):
        sorption_moisture_face(*points, *args[2:])


def test_entropy_underflow_cannot_be_reported_as_equilibrium():
    args = inputs()
    left = replace(args[0], chemical_potential_j_mol=F('1e-160'), partial_molar_enthalpy_j_mol=F(0))
    right = replace(args[1], chemical_potential_j_mol=F(0), partial_molar_enthalpy_j_mol=F(0))
    with pytest.raises(ValueError, match='moisture_entropy_w_k_underflow'):
        sorption_moisture_face(left, right, *args[2:])


def test_source_loader_preserves_printed_discrepancy_and_rechecks_files(monkeypatch, tmp_path):
    # Minimal fake PDF bytes and re-pinned copied metadata are test-only seams.
    root = Path(__file__).resolve().parents[2]
    facts = json.loads((root/module.FACTS_PATH).read_text())
    model = json.loads((root/module.MODEL_PATH).read_text())
    pdf = tmp_path/'manufactured.pdf'
    pdf.write_bytes(b'%PDF-1.0 manufactured hash fixture; not an original source')
    pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    facts['original_pdf']['sha256'] = pdf_sha
    facts['original_pdf']['bytes'] = pdf.stat().st_size
    facts_path = tmp_path/module.FACTS_PATH
    facts_path.parent.mkdir(parents=True)
    facts_path.write_text(json.dumps(facts))
    facts_sha = hashlib.sha256(facts_path.read_bytes()).hexdigest()
    model['upstream']['source_facts_sha256'] = facts_sha
    model['upstream']['original_pdf_sha256'] = pdf_sha
    model_path = tmp_path/module.MODEL_PATH
    model_path.write_text(json.dumps(model))
    monkeypatch.setattr(module, 'PDF_SHA256', pdf_sha)
    monkeypatch.setattr(module, 'FACTS_SHA256', facts_sha)
    monkeypatch.setattr(module, 'MODEL_SHA256', hashlib.sha256(model_path.read_bytes()).hexdigest())
    out = module.load_makela_diffusivity(tmp_path, pdf)
    assert out.value_m2_s == F('8.56e-9')
    assert out.input_classification == 'derived_from_evidence'
    trace = out.to_record()['provenance']
    assert trace['source_facts']['alternative_printed_diffusivity_m2_s'] == '8.57e-9'
    assert 'not an uncertainty interval' in trace['source_facts']['discrepancy_kind']
    assert trace['source_facts']['experimental_uncertainty'] is None
    assert 'total drying water loss' in trace['source_facts']['inference']['meaning']
    assert trace['source_state_binding_verified'] is False
    assert trace['material_qualified'] is False and trace['training_eligible'] is False
    for path in (pdf, facts_path, model_path):
        original = path.read_bytes()
        path.write_bytes(original+b' ')
        with pytest.raises(ValueError, match='changed'):
            module.load_makela_diffusivity(tmp_path, pdf)
        path.write_bytes(original)


@pytest.mark.parametrize('payload', ['{"value":NaN}', '{"value":Infinity}',
    '{"value":-Infinity}', '{"nested":[{"value":1e9999}]}', '{"value":'])
def test_diffusivity_provenance_requires_finite_standard_json(payload):
    with pytest.raises(SorptionMoistureError, match='finite_json_provenance'):
        EffectiveMoistureDiffusivity(D, SOURCES, CLASS, payload)


def test_finite_provenance_round_trips_through_strict_export():
    args = inputs()
    payload = '{"unknown":null,"values":[1,1.5,1e308],"status":false}'
    diffusion = EffectiveMoistureDiffusivity(D, SOURCES, CLASS, payload)
    out = sorption_moisture_face(*args[:3], diffusion, args[-1])
    record = out.to_record()
    assert record['input_provenance']['diffusivity']['provenance'] == json.loads(payload)
    json.dumps(record, allow_nan=False)
