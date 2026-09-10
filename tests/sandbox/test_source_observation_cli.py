"""Real saved N3 observations through the public import/read interface; no EOS."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


FIXTURE = Path(__file__).parent / 'fixtures/source-observation-v1/native-captures.json'


@pytest.fixture(autouse=True)
def forbid_live_physics(monkeypatch):
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    from sludge_sandbox.water_heos import HEOSWaterProperties
    from sludge_sandbox.water_properties import WaterProperties

    def fail(*args, **kwargs):
        pytest.fail('source observation import/read called live physics')

    for cls in (ExactSourceColumn, SourceWetStorage, WaterChemicalPotential,
                HEOSWaterProperties, WaterProperties):
        monkeypatch.setattr(cls, '__init__', fail)
    monkeypatch.setattr(ExactSourceColumn, 'evaluate', fail)
    monkeypatch.setattr(SourceWetStorage, 'evaluate', fail)
    monkeypatch.setattr(WaterProperties, 'state_tp', fail)
    monkeypatch.setattr(HEOSWaterProperties, 'state_tp', fail)


def test_import_then_inspect_preserves_actual_native_values_and_origin(tmp_path, capsys):
    from sludge_sandbox.cli import main

    output = tmp_path / 'observation.json'
    assert main(['source-observation-import', str(FIXTURE), '--capture-index', '1',
                 '--output', str(output)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert main(['source-observation-inspect', str(output)]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected == imported
    original = json.loads(FIXTURE.read_bytes())['captures'][1]
    state = original['packed_input']['fields']
    assert inspected['status'] == 'observation_record_valid'
    assert inspected['record_sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert inspected['provenance']['input_sha256'] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert inspected['provenance']['capture_index'] == '1'
    assert inspected['provenance']['capture_ordinal'] == '17'
    assert inspected['interface_modes'] == original['interface_modes']
    assert inspected['cell_count'] == 3
    assert [row['amounts_mol'] for row in inspected['cells']] == state['amounts_mol']['values']
    assert [row['internal_energy_j'] for row in inspected['cells']] == state['internal_energy_j']['values']
    raw_cells = original['evaluation']['fields']['source_evaluation']['fields']['cells']
    for row, cell in zip(inspected['cells'], raw_cells, strict=True):
        inverse = cell['fields']['inverse']['fields']
        point = inverse['point']['fields']
        mechanical = point['fluid']['fields']['mechanical']['fields']
        assert row['temperature_k'] == mechanical['temperature_k']
        assert row['pressure_pa'] == mechanical['pressure_pa']
        assert row['source_ids'] == list(point['source_ids'])
    assert inspected['material_qualified'] is False
    assert inspected['resume_authorized'] is False
    assert inspected['source_assets_verified'] is False
    assert inspected['full_run_validated'] is False


def test_import_does_not_overwrite_existing_artifact(tmp_path, capsys):
    from sludge_sandbox.cli import main

    output = tmp_path / 'existing.json'
    output.write_bytes(b'original bytes')
    assert main(['source-observation-import', str(FIXTURE), '--capture-index', '0',
                 '--output', str(output)]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
    assert output.read_bytes() == b'original bytes'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['existing.json']


@pytest.mark.parametrize('index', [-1, 2, True])
def test_invalid_capture_index_creates_no_output(tmp_path, index):
    from sludge_sandbox.source_observation_service import import_source_capture

    output = tmp_path / 'missing.json'
    with pytest.raises(ValueError, match='source_capture_index'):
        import_source_capture(FIXTURE, output, capture_index=index)
    assert not output.exists()


@pytest.mark.parametrize('mutation', ['failed_capture', 'wrong_energy', 'wrong_mass', 'wrong_mode', 'wrong_time'])
def test_inconsistent_selected_capture_is_structured_failure(tmp_path, capsys, mutation):
    from sludge_sandbox.cli import main

    document = json.loads(FIXTURE.read_bytes())
    capture = document['captures'][0]
    if mutation == 'failed_capture':
        capture['evaluation'] = None
        capture['failure'] = {'type': 'RuntimeError', 'reason': 'actual saved failure'}
    elif mutation == 'wrong_energy':
        capture['energy_identity'][1][0] = 'f' * 64
    elif mutation == 'wrong_mass':
        document['adapter_provenance']['fixed_dry_mass_kg'][0] = 0.3
    elif mutation == 'wrong_mode':
        capture['interface_modes'][0] = 'depleted_no_nucleation'
    else:
        capture['time']['fields']['seconds']['numerator'] += 1
    source = tmp_path / 'changed.json'
    source.write_text(json.dumps(document))
    output = tmp_path / 'result.json'
    assert main(['source-observation-import', str(source), '--capture-index', '0',
                 '--output', str(output)]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
    assert not output.exists()


def test_duplicate_json_keys_are_not_silently_selected(tmp_path, capsys):
    from sludge_sandbox.cli import main

    source = tmp_path / 'ambiguous.json'
    source.write_text('{"captures":[],"captures":[]}')
    assert main(['source-observation-import', str(source), '--capture-index', '0',
                 '--output', str(tmp_path / 'out.json')]) == 1
    saved = json.loads(capsys.readouterr().out)
    assert saved['status'] == 'failed'
    assert 'duplicate_json_key' in saved['reason']


def test_inspection_cell_filter_uses_original_cell_index(tmp_path):
    from sludge_sandbox.source_observation_service import import_source_capture, inspect_source_observation

    output = tmp_path / 'one.json'
    complete = import_source_capture(FIXTURE, output, capture_index=1)
    selected = inspect_source_observation(output, cell_index=1)
    assert selected['cells'] == [complete['cells'][1]]
    assert selected['cell_count'] == 3
    assert selected['selected_cell_index'] == 1
    with pytest.raises(ValueError, match='source_observation_cell_index'):
        inspect_source_observation(output, cell_index=3)


def test_import_checks_declared_file_budget_before_reading(tmp_path, monkeypatch):
    import sludge_sandbox.source_observation_service as module

    monkeypatch.setattr(module, 'MAX_IMPORT_BYTES', 8)
    with pytest.raises(ValueError, match='source_capture_file_limit'):
        module.import_source_capture(FIXTURE, tmp_path / 'out.json', capture_index=0)
    assert not (tmp_path / 'out.json').exists()


def test_deep_outer_identity_is_structured_failure(tmp_path, capsys):
    from sludge_sandbox.cli import main

    document = json.loads(FIXTURE.read_bytes())
    identity = 'deep'
    for _ in range(600):
        identity = [identity]
    document['captures'][0]['operator_identity'] = identity
    source = tmp_path / 'deep.json'
    source.write_text(json.dumps(document))
    output = tmp_path / 'out.json'
    assert main(['source-observation-import', str(source), '--capture-index', '0',
                 '--output', str(output)]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
    assert not output.exists()


def test_idle_fifo_is_rejected_without_waiting_for_writer(tmp_path):
    source = tmp_path / 'idle.fifo'
    os.mkfifo(source)
    output = tmp_path / 'out.json'
    # An external timeout prevents a blocking-reader regression hanging pytest.
    completed = subprocess.run(
        [sys.executable, '-m', 'sludge_sandbox.cli', 'source-observation-import',
         str(source), '--capture-index', '0', '--output', str(output)],
        capture_output=True, text=True, timeout=5, check=False,
    )
    assert completed.returncode == 1
    saved = json.loads(completed.stdout)
    assert saved['status'] == 'failed'
    assert saved['reason'] == 'source_observation_regular_file_required'
    assert not output.exists()
