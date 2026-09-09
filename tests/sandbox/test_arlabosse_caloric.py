from dataclasses import FrozenInstanceError
from fractions import Fraction as F
from pathlib import Path
import shutil
import pytest
from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric, CaloricError, NODE_ID
from sludge_sandbox.evidence import EvidenceRegistry

REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.fixture
def model():
    return ArlabosseDryCaloric(REPOSITORY/'data/sandbox/research/arlabosse2005/source.json', REPOSITORY)


def test_independent_decimal_endpoints_and_trapezoid(model):
    # Independent printed-decimal arithmetic and exact linear trapezoid rule.
    from decimal import Decimal as D
    low = D('1434') + D('3.29') * D('35')
    high = D('1434') + D('3.29') * D('105')
    assert model.cp(35, unit='degC').value == F(low)
    assert model.cp(F('378.15'), unit='K').value == F(high)
    assert model.delta_h(35,105,unit='degC').value == F((low+high)/2*D(70))
    assert model.delta_h(F('308.15'),F('378.15'),unit='K').value == F('116501')


def test_additivity_reversal_zero_and_trace(model):
    ab=model.delta_h(35,70,unit='degC');bc=model.delta_h(70,105,unit='degC')
    ac=model.delta_h(35,105,unit='degC')
    assert ab.value+bc.value==ac.value==-model.delta_h(105,35,unit='degC').value
    assert model.delta_h(70,70,unit='degC').value==0
    assert ac.unit=='J/kg' and ac.fit_error is None and not ac.material_qualified
    with pytest.raises(FrozenInstanceError):ac.value=F(1)
    trace=EvidenceRegistry.from_dict(model.registry_payload()).trace(NODE_ID)
    assert trace['sources'][0]['id']=='SRC_ARLABOSSE_2005_CONTACT_DRYING'
    assert trace['sources'][0]['metadata_sha256']==ac.source_sha256


@pytest.mark.parametrize('x', [True,False,float('nan'),float('inf'),'35',None,[],F(34999,1000),F(105001,1000)])
def test_invalid_temperature(model,x):
    with pytest.raises(CaloricError):model.cp(x,unit='degC')
    with pytest.raises(CaloricError):model.delta_h(35,x,unit='degC')


@pytest.mark.parametrize('unit',['C','kelvin','J/kg',None,True])
def test_units(model,unit):
    with pytest.raises(CaloricError):model.cp(35,unit=unit)


def test_binding_changes_refused(model,tmp_path):
    source=tmp_path/'source.json';shutil.copyfile(model.source_path,source)
    m=ArlabosseDryCaloric(source,REPOSITORY)
    source.write_bytes(source.read_bytes()+b' ')
    with pytest.raises(CaloricError,match='metadata_changed'):m.cp(35,unit='degC')
    with pytest.raises(CaloricError,match='metadata_changed'):m.registry_payload()


def test_missing_or_altered_assets_refused(model,tmp_path):
    import json
    for asset in json.loads(model.source_path.read_text())['assets']:
        destination=tmp_path/asset['path'];destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(REPOSITORY/asset['path'],destination)
    m=ArlabosseDryCaloric(model.source_path,tmp_path)
    (tmp_path/'.tools/source-cache/arlabosse2005/cp-equation.gif').write_bytes(b'changed')
    with pytest.raises(CaloricError,match='asset_changed'):m.delta_h(35,105,unit='degC')


def test_float_decimal_readout_and_exact_binary_escape(model):
    from decimal import Decimal
    import math
    assert model.cp(308.15,unit='K') == model.cp(Decimal('308.15'),unit='K')
    assert model.cp(378.15,unit='K').input_temperatures_degC == (F(105),)
    assert model.delta_h(308.15,378.15,unit='K').value == F(116501)
    assert model.cp(35.0,unit='degC').value == model.cp(35,unit='degC').value
    for value in (math.nextafter(308.15,-math.inf), F.from_float(308.15), Decimal('308.1499999999999999999')):
        with pytest.raises(CaloricError,match='outside'):model.cp(value,unit='K')
    with pytest.raises(CaloricError,match='outside'):model.cp(math.nextafter(378.15,math.inf),unit='K')
    for value in (Decimal('NaN'),Decimal('Infinity'),Decimal('-Infinity')):
        with pytest.raises(CaloricError):model.cp(value,unit='K')
    assert model.cp(350.0,unit='K').input_policy_id == 'exact_values_float_shortest_decimal_readout_v1'


def test_delta_h_trace_includes_integral_derivation(model):
    result=model.delta_h(35,105,unit='degC')
    assert result.node_id=='ARLABOSSE2005_DRY_SENSIBLE_ENTHALPY_DIFF'
    trace=EvidenceRegistry.from_dict(model.registry_payload()).trace(result.node_id)
    by_id={node['id']:node for node in trace['nodes']}
    derived=by_id[result.node_id]
    assert derived['dependencies']==[NODE_ID] and derived['unit']=='J/kg'
    assert derived['evidence_kind']=='derived_from_evidence'
    assert 'delta_h' in derived['derivation'] and 'formation' in derived['derivation']
    assert NODE_ID in by_id and trace['sources'][0]['id']=='SRC_ARLABOSSE_2005_CONTACT_DRYING'
