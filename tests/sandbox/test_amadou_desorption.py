from dataclasses import FrozenInstanceError
from decimal import Decimal as D, Context, localcontext
from fractions import Fraction as F
from pathlib import Path
import json
import shutil

import pytest

from sludge_sandbox.amadou_desorption import AmadouDesorption, DesorptionError, SOURCE_SHA256
from sludge_sandbox.evidence import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def model():
    return AmadouDesorption(ROOT / 'data/sandbox/research/amadou2006-desorption/source.json', ROOT)


@pytest.mark.parametrize('temperature,k,n', [(30, '0.112', '0.416'), (50, '0.0938', '0.484')])
def test_independent_reference_monotone_and_inverse(model, temperature, k, n):
    previous = D(0)
    for i in range(10, 81):
        a = F(i, 100)
        result = model.moisture(a, temperature, unit='1', temperature_unit='degC')
        with localcontext(Context(prec=110)):
            ad = D(i) / 100
            reference = D(k) * (D(n) * (ad.ln() - (1-ad).ln())).exp()
            assert abs(result.value - reference) < D('1e-78')
        assert result.value > previous
        previous = result.value
        inverted = model.activity(result.value, temperature, unit='1', temperature_unit='degC')
        with localcontext(Context(prec=110)):
            assert abs(inverted.value - D(i)/100) < D('1e-78')
        assert inverted.value >= D('.1') and inverted.value <= D('.8')
        assert result.uncertainty is None and result.material_qualified is False
        assert result.source_sha256 == SOURCE_SHA256
        assert result.basis == 'kg water / kg dry solid' and result.unit == '1'
    with pytest.raises(FrozenInstanceError):
        result.value = D(0)


def test_endpoint_no_epsilon_admission_and_private_decimal_context(model):
    for t in (30, 50):
        for a in (D('.1'), D('.8')):
            v = model.moisture(a, t, unit='1', temperature_unit='degC')
            assert model.activity(v.value, t, unit='1', temperature_unit='degC').value == a
            outside = F(v.value) + (F(-1, 10**100) if a == D('.1') else F(1, 10**100))
            with pytest.raises(DesorptionError, match='outside'):
                model.activity(outside, t, unit='1', temperature_unit='degC')
        for a in (F(1, 10)-F(1, 10**100), F(4, 5)+F(1, 10**100)):
            with pytest.raises(DesorptionError, match='outside'):
                model.moisture(a, t, unit='1', temperature_unit='degC')
    original = model.moisture(.4, 30, unit='1', temperature_unit='degC')
    with localcontext(Context(prec=3)):
        assert model.moisture(.4, 30, unit='1', temperature_unit='degC') == original


@pytest.mark.parametrize('bad', [True, False, None, '0.4', [], float('nan'), float('inf'), D('NaN'), D('-Infinity')])
def test_non_numeric_rejected(model, bad):
    for method in (model.moisture, model.activity):
        with pytest.raises(DesorptionError):
            method(bad, 30, unit='1', temperature_unit='degC')
        with pytest.raises(DesorptionError):
            method(.4, bad, unit='1', temperature_unit='degC')


@pytest.mark.parametrize('bad', [0, 1, -.1, .81, .09, 40, 80])
def test_activity_domain(model, bad):
    with pytest.raises(DesorptionError):
        model.moisture(bad, 30, unit='1', temperature_unit='degC')


@pytest.mark.parametrize('bad', [29, 31, 40, 49, 51, F(30)+F(1, 10**100)])
def test_exact_temperatures_only(model, bad):
    with pytest.raises(DesorptionError):
        model.moisture(.4, bad, unit='1', temperature_unit='degC')


def test_kelvin_decimal_semantics_and_no_percent(model):
    assert model.moisture(.4, 303.15, unit='1', temperature_unit='K') == model.moisture(D('.4'), 30, unit='1', temperature_unit='degC')
    assert model.moisture(.4, D('323.15'), unit='1', temperature_unit='K').temperature_degC == 50
    with pytest.raises(DesorptionError):
        model.moisture(.4, F.from_float(303.15), unit='1', temperature_unit='K')
    for unit in (None, True, '%', 'wt%', 'kg/kg', 'K'):
        for method in (model.moisture, model.activity):
            with pytest.raises(DesorptionError):
                method(.4, 30, unit=unit, temperature_unit='degC')
    for unit in ('C', None, True, 'celsius'):
        with pytest.raises(DesorptionError):
            model.moisture(.4, 30, unit='1', temperature_unit=unit)


def test_registry_trace_per_row_and_interpretations(model):
    registry = EvidenceRegistry.from_dict(model.registry_payload())
    for t in (30, 50):
        result = model.moisture(.4, t, unit='1', temperature_unit='degC')
        inverse = model.activity(result.value, t, unit='1', temperature_unit='degC')
        trace = registry.trace(inverse.node_id)
        assert len(trace['nodes']) == 3
        assert trace['nodes'][0]['id'].endswith(f'{t}_PARAMETERS')
        assert trace['nodes'][1]['id'] == result.node_id
        assert trace['nodes'][2]['id'] == inverse.node_id
        assert trace['sources'][0]['metadata_sha256'] == SOURCE_SHA256
        assert 'inconsistency' in trace['sources'][0]['activity_label_interpretation']
        assert 'nomenclature' in trace['sources'][0]['basis_locator']


def test_source_change_and_pdf_change_refused(model, tmp_path):
    source = tmp_path/'source.json'
    shutil.copyfile(model.source_path, source)
    bound = AmadouDesorption(source, ROOT)
    source.write_bytes(source.read_bytes()+b' ')
    for call in (lambda: bound.moisture(.4, 30, unit='1', temperature_unit='degC'), bound.registry_payload):
        with pytest.raises(DesorptionError, match='metadata_changed'):
            call()
    for asset in json.loads(model.source_path.read_text())['assets']:
        dest = tmp_path/asset['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/asset['path'], dest)
    bound = AmadouDesorption(model.source_path, tmp_path)
    dest.write_bytes(b'altered pdf')
    with pytest.raises(DesorptionError, match='asset_changed'):
        bound.activity(.1, 30, unit='1', temperature_unit='degC')
    dest.unlink()
    with pytest.raises(DesorptionError, match='asset_unavailable'):
        bound.registry_payload()
