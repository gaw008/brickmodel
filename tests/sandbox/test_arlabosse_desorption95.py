from decimal import Decimal, Inexact, localcontext
from fractions import Fraction as F
import json
import math
from pathlib import Path
import shutil

import pytest

from sludge_sandbox.arlabosse_desorption95 import (
    ArlabosseDesorption95, DesorptionError, MU_NODE_ID,
)
from sludge_sandbox.evidence import EvidenceRegistry

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data/sandbox/research/arlabosse95/source.json'


@pytest.fixture
def model():
    return ArlabosseDesorption95(SOURCE, ROOT)


def independent_log_bounds(x):
    # Exact atanh series with a geometric tail bound, independent of Decimal.ln.
    z = (x - 1) / (x + 1)
    n = 160
    value = 2 * sum((z ** (2*k + 1) / (2*k + 1) for k in range(n)), F(0))
    error = 2 * abs(z) ** (2*n + 1) / ((2*n + 1) * (1 - z*z))
    return value - error, value + error


def test_original_raster_nodes_and_heat_basis(model):
    point = model.at_moisture(F(3, 20), temperature=95, unit='degC')
    assert point.activity.value == F(1941, 3743)
    assert point.activity.digitization_bounds == (F(212, 415), F(219, 416))
    assert point.total_desorption_heat.value == F(166780000, 63)
    assert point.total_desorption_heat.digitization_bounds == (F(54760000, 21), F(56440000, 21))
    assert point.total_desorption_heat.unit == 'J/kg removed water'
    assert point.total_desorption_heat.experimental_uncertainty is None
    assert point.temperature_K == F(7363, 20)
    assert not point.material_qualified and not point.full_firing_cycle


@pytest.mark.parametrize('w', [F(1,10), F(3,5), F(1,2)])
def test_occluded_heat_is_unknown_without_losing_activity(model, w):
    point = model.at_moisture(w, temperature=368.15, unit='K')
    assert point.activity.value is not None
    assert point.total_desorption_heat.value is None
    assert point.total_desorption_heat.digitization_bounds is None
    assert point.total_desorption_heat.unknown_reasons
    assert point.chemical_potential_shift.value < 0


@pytest.mark.parametrize('w', [F(1,10), F(3,20), F(1,5), F(3,10), F(2,5), F(1,2), F(3,5), F(7,10), F(4,5)])
def test_chemical_shift_independent_series_and_read_bounds(model, w):
    point = model.at_moisture(w, temperature=95, unit='degC')
    shift = point.chemical_potential_shift
    rt = F('1.380649e-23') * F('6.02214076e23') * F('368.15')
    lo, hi = independent_log_bounds(point.activity.value)
    assert shift.numerical_bounds[0] <= rt * lo <= rt * hi <= shift.numerical_bounds[1]
    assert shift.numerical_bounds[0] <= shift.value <= shift.numerical_bounds[1]
    assert shift.numerical_bounds[1] - shift.numerical_bounds[0] < F('1e-43')
    a, b = point.activity.digitization_bounds
    alo, _ = independent_log_bounds(a)
    _, bhi = independent_log_bounds(b)
    assert shift.digitization_bounds[0] <= rt * alo
    assert rt * bhi <= shift.digitization_bounds[1] < 0
    assert shift.unit == 'J/mol water'
    assert shift.experimental_uncertainty is None


@pytest.mark.parametrize('w', [0, 1, F(9,50), F(41,100), -1, True, '0.15', None, float('nan'), float('inf'), Decimal('NaN'), F.from_float(.15)])
def test_no_interpolation_extrapolation_or_implicit_input_conversion(model, w):
    with pytest.raises(DesorptionError):
        model.at_moisture(w, temperature=95, unit='degC')


@pytest.mark.parametrize('temperature,unit', [(94.999,'degC'),(96,'degC'),(95,'K'),(368.15,'C'),(True,'degC'),('95','degC'),(math.nextafter(368.15, math.inf),'K')])
def test_temperature_is_exactly_source_isotherm(model, temperature, unit):
    with pytest.raises(DesorptionError):
        model.at_moisture(.15, temperature=temperature, unit=unit)


def test_trace_and_json_record_include_only_actual_dependencies(model):
    point = model.at_moisture(.15, temperature=Decimal('368.15'), unit='K')
    record = point.to_record()
    assert record['activity']['value']['numerator'] == '1941'
    assert json.loads(json.dumps(record)) == record
    trace = EvidenceRegistry.from_dict(model.registry_payload()).trace(MU_NODE_ID)
    ids = {s['id'] for s in trace['sources']}
    assert ids == {'SRC_ARLABOSSE_2005_CONTACT_DRYING', 'nist-codata-2022', 'HACK_2011_ACTIVITY'}
    assert all('CP_EQ2' not in n['id'] for n in trace['nodes'])
    assert not record['continuous_domain_admitted']


def test_decimal_global_context_cannot_change_result(model):
    expected = model.at_moisture(.15, temperature=95, unit='degC')
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.traps[Inexact] = True
        assert model.at_moisture(.15, temperature=95, unit='degC') == expected


def test_decimal_default_context_cannot_change_result(model, monkeypatch):
    from decimal import DefaultContext, ROUND_UP, Rounded
    expected = model.at_moisture(.15, temperature=95, unit='degC')
    monkeypatch.setattr(DefaultContext, 'rounding', ROUND_UP)
    monkeypatch.setattr(DefaultContext, 'Emin', -1)
    monkeypatch.setattr(DefaultContext, 'Emax', 1)
    monkeypatch.setattr(DefaultContext, 'clamp', 1)
    monkeypatch.setitem(DefaultContext.traps, Inexact, True)
    monkeypatch.setitem(DefaultContext.traps, Rounded, True)
    assert model.at_moisture(.15, temperature=95, unit='degC') == expected


def test_source_mutation_after_construction_refused(model, tmp_path):
    source = tmp_path / 'source.json'
    shutil.copyfile(SOURCE, source)
    copied = ArlabosseDesorption95(source, ROOT)
    source.write_bytes(source.read_bytes() + b' ')
    with pytest.raises(DesorptionError, match='metadata_changed'):
        copied.at_moisture(.15, temperature=95, unit='degC')


def test_missing_and_changed_original_assets_refused(tmp_path):
    metadata = json.loads(SOURCE.read_bytes())
    with pytest.raises(DesorptionError, match='unavailable'):
        ArlabosseDesorption95(SOURCE, tmp_path)
    for asset in metadata['assets']:
        destination = tmp_path / asset['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / asset['path'], destination)
    copied = ArlabosseDesorption95(SOURCE, tmp_path)
    (tmp_path / metadata['assets'][0]['path']).write_bytes(b'changed')
    with pytest.raises(DesorptionError, match='asset_changed'):
        copied.registry_payload()


@pytest.mark.parametrize('moisture,temperature,expected', [('3/20', '95', 0), ('0.15', '96', 1), ('1/0', '95', 1)])
def test_cli_exact_query_and_controlled_errors(capsys, moisture, temperature, expected):
    from sludge_sandbox.cli import main
    code = main(['arlabosse95', '--source', str(SOURCE), '--assets-root', str(ROOT),
                 '--moisture', moisture, '--temperature', temperature, '--unit', 'degC', '--trace'])
    result = json.loads(capsys.readouterr().out)
    assert code == expected
    if expected == 0:
        assert result['point']['activity']['value']['numerator'] == '1941'
        assert result['trace']['nodes']
    else:
        assert result['status'] == 'failed'
        assert result['error_type'] == 'DesorptionError'
