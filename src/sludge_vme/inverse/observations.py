"""Pure-data preparation for the existing full-cycle observation/fit interface.

Reference conversions retain their original rows. Admission checks declared
provenance and configuration compatibility, not truth or material validation.
No model, optimizer, field integration or parameter estimation runs here.
"""
from __future__ import annotations

from copy import deepcopy
import math

from sludge_sandbox.units import convert
from ..units import degc_to_k, water_per_dry_mass

UNITS = {'tg':'1', 'dsc':'W/kg', 'dilatometry':'1', 'kiln':'K',
         'absorption':'kg/kg', 'strength':'Pa', 'defects':'1',
         'liquid_water':'kg/kg', 'surface_temperature':'K'}
PRODUCTS = ('absorption', 'strength', 'defects')


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{label}: finite numeric value required')
    return value


def _known(value):
    return isinstance(value, str) and value.strip().lower() not in ('', 'unknown', 'pending', 'template')


def configured_conditions(config: dict) -> dict:
    """Declared model conditions, NOT measured protocol or compatibility evidence."""
    return {'stages':list(config['stages']), 'parameters':{
        key:{field:deepcopy(config['parameters'][key][field]) for field in ('value', 'unit')}
        for key in config['observation_contract']['condition_parameter_keys']}}


def _time_end(config):
    p = config['parameters']
    return p['process.'+config['stages'][-1]+'.end']['value']*p['process.time_scale']['value']


def _canonical_rows(config, rows):
    if not rows:
        raise ValueError('observations must not be empty')
    for row in rows:
        kind = row['kind']
        if kind not in UNITS or row['unit'] != UNITS[kind]:
            raise ValueError(f'unknown kind or noncanonical unit: {kind}')
        _number(row['value'], 'value')
        if _number(row['scale'], 'scale') <= 0:
            raise ValueError('scale must be positive')
        if kind in PRODUCTS and config['stages'][-1] != config['observation_contract']['semantics'][kind]['terminal_stage']:
            raise ValueError('product observation requires the configured final cooling stage')
        if kind not in PRODUCTS:
            t = _number(row['time_s'], 'time_s')
            if not 0 <= t <= _time_end(config):
                raise ValueError('observation time outside the configured process')


def _fit_parameters(config, dataset):
    keys = dataset['fit_parameters']
    if not keys or len(keys) != len(set(keys)):
        raise ValueError('fit_parameters must be nonempty and unique')
    for key in keys:
        if key not in config['parameters']:
            raise ValueError(f'unknown fit parameter: {key}')
        if config['parameters'][key]['range'][1] <= config['parameters'][key]['range'][0]:
            raise ValueError(f'fit parameter requires a nonzero range: {key}')


def _ratio_basis(row):
    basis = row['basis']
    value = _number(row['value'], 'water value')
    if row['unit'] not in ('kg/kg', '1'):
        raise ValueError('water input requires kg/kg or dimensionless ratio; no implicit percent conversion')
    if basis == 'initial_dry_mass':
        if row['unit'] != 'kg/kg':
            raise ValueError('initial-dry water requires kg/kg')
        return value, 'water / initial dry mass: unchanged'
    if basis in ('current_dry_mass', 'wet_mass', 'dry_reference_mass'):
        factor_key = 'dry_reference_over_initial_dry' if basis == 'dry_reference_mass' else 'current_dry_over_initial_dry'
        factor = row.get(factor_key)
        if not isinstance(factor, dict) or not _known(factor.get('source')):
            raise ValueError('current dry / initial dry mass requires an explicit sourced factor')
        if factor['source_id'] != row['source_id']:
            raise ValueError('dry-mass factor source_id differs from the observation source')
        ratio = _number(factor['value'], 'current_dry_over_initial_dry')
        if factor['unit'] != '1' or ratio <= 0:
            raise ValueError('current dry / initial dry mass must be positive and dimensionless')
        dry = water_per_dry_mass(value) if basis == 'wet_mass' else value
        return dry*ratio, ('w/(1-w)' if basis == 'wet_mass' else 'd')+' * '+factor_key
    if basis == 'moisture_ratio':
        denominator = row.get('mr_denominator')
        if not isinstance(denominator, dict) or not _known(denominator.get('source')):
            raise ValueError('MR requires explicit same-source initial water and formula; root water is not a substitute')
        if denominator['formula'] != 'water_over_initial_water' or denominator['unit'] != 'kg/kg_initial_dry':
            raise ValueError('only explicit water/initial_water MR with an initial-dry denominator is supported')
        if denominator['source_id'] != row['source_id']:
            raise ValueError('MR denominator source_id differs from the observation source')
        initial = _number(denominator['value'], 'MR initial denominator')
        if initial <= 0:
            raise ValueError('MR initial denominator must be positive')
        return value*initial, 'MR * sourced initial water/initial dry mass'
    raise ValueError(f'unsupported or unknown water denominator: {basis}')


def _reference_row(config, original):
    # A prepared dataset may be passed to fit. Re-read its preserved source row
    # so converted units/bases cannot erase the original admission restrictions.
    if 'mapping' in original:
        original = original['mapping']['original']
    row = deepcopy(original)
    kind = row['kind']
    if kind not in UNITS:
        raise ValueError(f'unsupported observation kind: {kind}')
    semantics = config['observation_contract']['semantics'][kind]
    for key in ('quantity', 'location'):
        if row[key] != semantics[key]:
            raise ValueError(f'{kind}: {key} must be {semantics[key]}, got {row[key]}')
    if not _known(row['source_id']) or not _known(row['source_locator']):
        raise ValueError('observation source_id and source_locator are required')
    notes = []
    value = _number(row['value'], 'value')
    if kind == 'liquid_water':
        value, conversion = _ratio_basis(row)
    else:
        if row['basis'] != semantics['basis']:
            raise ValueError(f'{kind}: denominator/basis must be {semantics["basis"]}')
        if row['unit'] == UNITS[kind]:
            conversion = 'canonical unit unchanged'
        elif kind in ('surface_temperature', 'kiln') and row['unit'] == 'degC':
            value = degc_to_k(value)
            conversion = 'degC to K; value offset only'
        elif kind == 'strength' and row['unit'] == 'MPa':
            value = convert(value, 'MPa', 'Pa')
            conversion = 'MPa to Pa'
        else:
            raise ValueError(f'unsupported unit conversion for {kind}')
    # scale is deliberately supplied in target units; it is not a measured sigma.
    if row['scale_unit'] != UNITS[kind] or not _known(row['scale_source']):
        raise ValueError('scale requires canonical target unit and an explicit source; no uncertainty propagation')
    if _number(row['scale'], 'scale') <= 0:
        raise ValueError('scale must be positive')
    if row['acquisition'] != semantics['acquisition']:
        notes.append(f'acquisition {row["acquisition"]!r} is not model {semantics["acquisition"]!r}')
    if row['segment'] not in semantics['segments']:
        notes.append(f'segment {row["segment"]!r} is not admitted for {kind}')
    if kind in PRODUCTS and config['stages'][-1] != semantics['terminal_stage']:
        notes.append('product observation requires the configured final cooling stage')
    if kind == 'liquid_water' and row['basis'] in ('current_dry_mass', 'wet_mass', 'dry_reference_mass', 'moisture_ratio'):
        factor_key = {'moisture_ratio':'mr_denominator', 'dry_reference_mass':'dry_reference_over_initial_dry'}.get(row['basis'], 'current_dry_over_initial_dry')
        factor = row[factor_key]
        if factor['status'] not in ('measured', 'literature', 'assumed', 'synthetic'):
            raise ValueError('explicit denominator/factor status required')
        if factor['status'] != 'measured':
            notes.append('denominator/factor is not target-measured; converted data remain reference')
    if kind not in PRODUCTS:
        t = row['time']
        elapsed = convert(t['value'], t['unit'], 's')
        if not _known(t['origin']) or t['offset_to_process_start_s'] is None or not _known(t['source']):
            row['time_s'] = None
            notes.append('time origin/offset/source unknown')
        else:
            offset = _number(t['offset_to_process_start_s'], 'time offset')
            if t['origin'] == 'process_start' and offset != 0:
                raise ValueError('process_start time origin requires zero offset')
            row['time_s'] = elapsed+offset
            if not 0 <= row['time_s'] <= _time_end(config):
                notes.append('observation time outside the configured process')
            if row['segment'] == 'main_drying':
                p = config['parameters']
                dry_end = p['process.drying.end']['value']*p['process.time_scale']['value']
                if not 0 <= row['time_s'] <= dry_end:
                    notes.append('main_drying observation outside the configured drying window')
    _number(value, 'converted value')
    row.update(value=value, unit=UNITS[kind], basis=semantics['basis'])
    row['mapping'] = {'original':deepcopy(original), 'conversion':conversion,
                      'scale_meaning':'Residual normalization in target units; not inferred measurement uncertainty.',
                      'calibration_issues':notes}
    return row


def prepare_dataset(config: dict, dataset: dict, *, for_calibration: bool = False) -> dict:
    """Normalize reference data or validate calibration before optimizer/forward.

    Legacy canonical synthetic data remain supported. Measured calibration needs
    a declared target, raw experimental provenance and matching fixed conditions.
    Unknown target metadata do not prevent running the forward base model.
    """
    result = deepcopy(dataset)
    kind = result['measurement_kind']
    if not _known(result['source']):
        raise ValueError('dataset source is required')
    if kind == 'synthetic':
        _canonical_rows(config, result['observations'])
        result['admission'] = {'purpose':'synthetic', 'material_validation':False,
                               'note':'Same-model software input; no measured identity is assigned.'}
    elif kind in ('measured', 'reference'):
        contract = config['observation_contract']
        if result['source_kind'] not in ('raw_experiment', 'paper_table', 'digitized_curve'):
            raise ValueError('source_kind must identify raw experiment, paper table or digitized curve')
        result['observations'] = [_reference_row(config, row) for row in result['observations']]
        if not result['observations']:
            raise ValueError('observations must not be empty')
        issues = []
        if result.get('data_role') == 'regression-only':
            issues.append('regression-only structural inputs cannot become measured calibration data')
        if kind != 'measured' or result['source_kind'] != 'raw_experiment':
            issues.append('target calibration requires measured raw_experiment data; external literature remains reference')
        for group in ('material', 'conditions'):
            for key, expected in contract['target'][group].items():
                actual = result[group].get(key)
                if not _known(expected) or not _known(actual) or actual != expected:
                    issues.append(f'{group}.{key}: target/input unknown or mismatched')
        for source in ('identity_source', 'compatibility_source'):
            if not _known(contract['target'][source]) or not _known(result.get(source)):
                issues.append(f'{source}: explicit target and input evidence required')
        declared = result['conditions']['configuration']
        if declared != configured_conditions(config):
            issues.append('geometry/initial/recipe/boundary configuration differs or is unknown')
        for index, row in enumerate(result['observations']):
            original = row['mapping']['original']
            if row['kind'] == 'liquid_water':
                factor_key = {'moisture_ratio':'mr_denominator', 'dry_reference_mass':'dry_reference_over_initial_dry',
                              'wet_mass':'current_dry_over_initial_dry', 'current_dry_mass':'current_dry_over_initial_dry'}.get(original['basis'])
                if factor_key and original[factor_key]['status'] == 'measured':
                    if original[factor_key].get('material') != result['material']:
                        issues.append(f'row {index}: measured denominator/factor material/recipe/batch unknown or mismatched')
            issues.extend(f'row {index}: {issue}' for issue in row['mapping']['calibration_issues'])
        result['admission'] = {'purpose':'target_calibration' if for_calibration else 'reference_mapping',
                               'eligible_by_declared_metadata':not issues,
                               'issues':issues, 'material_validation':False,
                               'provenance':{key:deepcopy(result[key]) for key in (
                                   'source_kind','material','conditions','identity_source','compatibility_source')},
                               'target_declaration':deepcopy(contract['target']),
                               'model_conditions':configured_conditions(config)}
        if for_calibration:
            if issues:
                raise ValueError('observation admission failed: '+'; '.join(issues))
            _canonical_rows(config, result['observations'])
    else:
        raise ValueError('template/unknown identity cannot be calibrated; choose explicit synthetic, reference or measured')
    if for_calibration:
        _fit_parameters(config, result)
        if kind == 'measured':
            fixed = set(config['observation_contract']['condition_parameter_keys'])
            if fixed.intersection(result['fit_parameters']):
                raise ValueError('declared fixed geometry/initial/recipe/boundary conditions cannot also be fitted')
    return result
