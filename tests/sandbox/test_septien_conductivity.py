"""Manufactured JATS/source seams: no EOS and no measured-material validation."""
from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

import sludge_sandbox.septien_conductivity as conductivity


ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manufactured_xml():
    header = ('<th>Sludge</th><th>Moisture content<break/>(% wet basis)</th>'
              '<th colspan="11">Nutrient content</th><th>Calorific value</th>'
              '<th>Thermal conductivity (W/m/K)</th><th>Heat capacity</th><th>Diffusivity</th>')
    rows = []
    for time, moisture, k in ((25, '47 ± 2', '0.062 ± 0.002'),
                              (40, '23 ± 6', '0.056 ± 0.001')):
        cells = [f'Dried at 30 % MIR, {time} min', moisture]+['irrelevant']*12+[k, 'capacity', 'diffusivity']
        rows.append('<tr>'+''.join(f'<td>{cell}</td>' for cell in cells)+'</tr>')
    return ('<article><front><article-meta><article-id pub-id-type="doi">'
            '10.1016/j.jece.2019.103652</article-id></article-meta></front><body>'
            '<sec id="sec0055"><label>2.5.</label><title>Statistical analysis</title>'
            '<p>All tests in duplicates; Student’s t-distribution in a 90 % confidence interval.</p></sec>'
            '<table-wrap id="tbl0010"><label>Table 2</label><table><thead><tr>'+header+
            '</tr></thead><tbody>'+''.join(rows)+'</tbody></table></table-wrap></body></article>')


@pytest.fixture
def factory(monkeypatch, tmp_path):
    """Repin minimal artificial XML and copied metadata only within this test."""
    repository = tmp_path/'repository'
    directory = repository/'data/sandbox/research/septien-conductivity-v1'
    directory.mkdir(parents=True)
    assets = tmp_path/'assets'
    assets.mkdir()
    xml = assets/'fecal2019-original.xml'
    xml.write_text(manufactured_xml())
    facts = json.loads((ROOT/'data/sandbox/research/septien-conductivity-v1/source.json').read_text())
    model = json.loads((ROOT/'data/sandbox/research/septien-conductivity-v1/model.json').read_text())
    facts_path, model_path = directory/'source.json', directory/'model.json'

    def repin():
        source_sha = hashlib.sha256(xml.read_bytes()).hexdigest()
        facts['primary_asset']['sha256'] = source_sha
        facts['primary_asset']['bytes'] = xml.stat().st_size
        facts_sha = write_json(facts_path, facts)
        model['upstream']['source_facts_sha256'] = facts_sha
        model['upstream']['original_xml_sha256'] = source_sha
        model_sha = write_json(model_path, model)
        monkeypatch.setattr(conductivity, 'SOURCE_SHA256', source_sha)
        monkeypatch.setattr(conductivity, 'FACTS_SHA256', facts_sha)
        monkeypatch.setattr(conductivity, 'MODEL_SHA256', model_sha)
    repin()
    return SimpleNamespace(repository=repository, assets=assets, xml=xml, facts=facts, model=model,
        facts_path=facts_path, model_path=model_path, repin=repin,
        make=lambda: conductivity.SeptienConductivity(repository, assets))


def expected(w):
    return F(7, 125)+(F(31, 500)-F(7, 125))*(w-F(23, 77))/(F(47, 53)-F(23, 77))


def test_nominal_linear_conductivity_uses_dry_basis_conversion(factory):
    provider = factory.make()
    for w in (F(3, 10), F(1, 2), F(4, 5)):
        point = provider.evaluate(330., w)
        assert point.nominal_k_w_m_k == expected(w)
        assert point.k_w_m_k == float(expected(w))
        assert point.k_w_m_k > 0
        assert point.binary64_projection_error_w_m_k == abs(F(point.k_w_m_k)-expected(w))
        wrong_wet_basis = F(7, 125)+F(3, 500)*(w-F(23, 100))/(F(47, 100)-F(23, 100))
        assert point.nominal_k_w_m_k != wrong_wet_basis


def test_original_source_nodes_and_intervals_are_preserved(factory):
    points = factory.make().source_points()
    assert [point.moisture_dry_basis for point in points] == [F(23, 77), F(47, 53)]
    assert [point.conductivity_w_m_k for point in points] == [F('0.056'), F('0.062')]
    assert [point.moisture_wet_percent_half_width for point in points] == [F(6), F(2)]
    assert [point.conductivity_half_width_w_m_k for point in points] == [F('.001'), F('.002')]
    assert all(point.confidence_level == F(9, 10) and point.measurement_temperature_c is None
               for point in points)
    assert points[0].table_id == 'tbl0010' and '40 min' in points[0].row_label


def test_temperature_independence_is_declared_not_measured(factory):
    provider = factory.make()
    a, b = provider.evaluate(308.15, .5), provider.evaluate(368.15, .5)
    assert a.nominal_k_w_m_k == b.nominal_k_w_m_k
    record = a.to_record()
    assert record['provenance']['source_facts']['measurement']['temperature_c'] is None
    choices = record['provenance']['model_definition']['model_choices']
    assert 'assumption' in choices['temperature_dependence']
    assert record['temperature_extension_model_error'] is None
    assert record['cross_material_transfer_error'] is None
    assert record['interpolation_model_error'] is None
    assert record['total_model_uncertainty'] is None
    assert not record['material_qualified'] and not record['training_eligible']
    assert record['source_confidence_intervals_are_total_model_bounds'] is False
    json.dumps(record, allow_nan=False)


def test_machine_classifications_and_reading_date_are_preserved(factory):
    definition = factory.make().definition()
    facts, model = definition['source_facts'], definition['model_definition']
    assert facts['classification'] == 'measured_public_data'
    assert facts['retrieved_on'] == '2026-09-12'
    assert facts['reading_status'] == 'full_original_jats_body_and_table_cells_read'
    assert model['classification'] == 'derived_from_evidence'
    assert model['usage_scope'] == 'hybrid_exploratory_donor_transport'
    assert model['input_classifications'] == {
        'source_table_readings': 'measured_public_data',
        'wet_to_dry_conversion': 'derived_from_evidence',
        'nominal_interpolation': 'derived_from_evidence',
        'temperature_independence': 'virtual_design_choice',
        'exploration_domain': 'virtual_design_choice',
        'cross_material_use': 'virtual_design_choice',
        'numerical_representation': 'numerical_policy',
        'total_model_uncertainty': 'unknown',
    }
    assert model['uncertainty_policy']['total_model_uncertainty'] is None


@pytest.mark.parametrize('w', [.29, .81, F(23, 77), F(47, 53),
                               math.nextafter(.30, -math.inf), math.nextafter(.80, math.inf)])
def test_declared_exploration_range_is_narrower_than_source_nodes(factory, w):
    with pytest.raises(ValueError, match='moisture_domain'):
        factory.make().evaluate(330., w)


@pytest.mark.parametrize('t', [308., 369., math.nextafter(308.15, -math.inf),
                               math.nextafter(368.15, math.inf)])
def test_temperature_range_is_explicit(factory, t):
    with pytest.raises(ValueError, match='temperature_domain'):
        factory.make().evaluate(t, .5)


@pytest.mark.parametrize('value', [True, '0.5', None, float('nan'), float('inf'), Decimal('NaN')])
def test_invalid_coordinates_are_rejected(factory, value):
    provider = factory.make()
    with pytest.raises(ValueError):
        provider.evaluate(330., value)
    with pytest.raises(ValueError):
        provider.evaluate(value, .5)


def test_float_coordinates_mean_their_represented_value(factory):
    provider = factory.make()
    point = provider.evaluate(330., .3)
    assert point.nominal_k_w_m_k == expected(F(.3))
    exact = provider.evaluate(Decimal('330'), Decimal('.3'))
    assert exact.nominal_k_w_m_k == expected(F(3, 10))
    assert exact.nominal_k_w_m_k != point.nominal_k_w_m_k


@pytest.mark.parametrize('target', ['xml', 'facts_path', 'model_path'])
def test_source_file_mutation_stops_all_public_reads(factory, target):
    provider = factory.make()
    path = getattr(factory, target)
    path.write_bytes(path.read_bytes()+b' ')
    for call in (provider.binding, provider.definition, provider.source_points,
                 lambda: provider.source_ids, lambda: provider.model_identity,
                 lambda: provider.evaluate(330., .5)):
        with pytest.raises(ValueError, match='changed'):
            call()


def test_source_hash_checked_before_xml_parsing(factory, monkeypatch):
    factory.xml.write_text('<!DOCTYPE bad [<!ENTITY a "wrong">]><bad>&a;</bad>')
    def forbidden(*args):
        raise AssertionError('unknown XML reached parser')
    monkeypatch.setattr(conductivity.ET, 'fromstring', forbidden)
    with pytest.raises(ValueError, match='changed'):
        factory.make()


@pytest.mark.parametrize('old,new', [('0.056 ± 0.001', '0.566 ± 0.001'),
                                    ('23 ± 6', '32 ± 6'),
                                    ('tbl0010', 'tbl0005'),
                                    ('Thermal conductivity (W/m/K)', 'Thermal diffusivity (m2/s)')])
def test_rehashed_wrong_original_table_cannot_be_admitted(factory, old, new):
    factory.xml.write_text(factory.xml.read_text().replace(old, new))
    factory.repin()
    with pytest.raises(ValueError, match='table|cell|column'):
        factory.make()


def test_fact_labels_alone_cannot_replace_original_cells(factory):
    factory.facts['points'][0]['conductivity_w_m_k_original'] = '0.057 ± 0.001'
    factory.facts['points'][0]['conductivity_w_m_k'] = '0.057'
    factory.repin()
    with pytest.raises(ValueError, match='cell'):
        factory.make()


def test_wrong_dry_basis_derived_fact_is_rejected(factory):
    factory.facts['points'][0]['moisture_dry_basis'] = '23/100'
    factory.repin()
    with pytest.raises(ValueError, match='conversion'):
        factory.make()


def test_absent_file_and_false_confidence_semantics_are_rejected(factory):
    factory.xml.unlink()
    with pytest.raises(ValueError, match='unavailable'):
        factory.make()
    factory.xml.write_text(manufactured_xml().replace('90 %', '95 %'))
    factory.repin()
    with pytest.raises(ValueError, match='confidence'):
        factory.make()


def test_returned_records_do_not_leak_mutable_model_state(factory):
    provider = factory.make()
    definition = provider.definition()
    definition['source_facts']['points'][0]['conductivity_w_m_k'] = '500'
    assert provider.definition()['source_facts']['points'][0]['conductivity_w_m_k'] == '0.056'
    point = provider.evaluate(330., .5)
    record = point.to_record()
    record['provenance']['source_facts']['measurement']['temperature_c'] = 85
    assert point.to_record()['provenance']['source_facts']['measurement']['temperature_c'] is None
    with pytest.raises(FrozenInstanceError):
        point.k_w_m_k = 0.
    with pytest.raises(FrozenInstanceError):
        provider.repository_root = Path('/')
