"""Source-specific paired TG degrees of carbonation, without a forward model.

Inputs are already separated phase masses per the same calcined-CH CaO
reference. This module neither integrates TG peaks nor supplies brick kinetics
or canonical fit observations. Original inputs and their identities survive.
"""
from __future__ import annotations

from copy import deepcopy

from sludge_sandbox.units import convert
from .observations import _known, _number


def map_saeki2026_tg(*, config: dict, record: dict) -> dict:
    """Map one explicitly sourced phase-mass pair using original Eq5/Eq6.

    The root source contract and rounded molar masses are required. The two
    phase values share a declared sample, time, source and CaO reference.
    g/g and kg/kg have equal numerical ratios; their denominator must still
    be the source's calcined-CH CaO reference. No initial-carbonate subtraction,
    initial-remaining-CH normalization, averaging or clipping is performed.

    Semantic admission only checks the supplied declarations, not their truth.
    Signed input values and DoC differences are retained. Measured phase inputs
    produce source-derived results, not direct target-material measurements or
    canonical fit admission. No cycle or optimizer is constructed or called.
    """
    original = deepcopy(record)
    contract = config['source_observation_contracts']['saeki2026_tg']
    sample = record['sample']
    time = record['time']
    denominator = record['denominator']
    separation = record['phase_separation']
    applicability = record['applicability']
    phases = record['phase_masses']
    issues = []
    semantics = {
        'quantity': (record['quantity'], contract['quantity']),
        'denominator.basis': (denominator['basis'], contract['basis']),
        'sample.basis': (sample['basis'], contract['sample_basis']),
        'phase_separation.method': (separation['method'], contract['phase_separation']),
        'applicability.sample_basis': (applicability['sample_basis'], contract['sample_basis']),
    }
    for label, (actual, expected) in semantics.items():
        if actual != expected:
            issues.append(f'{label}: requires {expected}, got {actual}')
    if record['source_kind'] != contract['input_identity_pairs'][record['measurement_kind']]:
        issues.append('source_kind does not match declared measurement identity')
    for label, value in (
        ('source_id', record['source_id']), ('source_locator', record['source_locator']),
        ('sample.id', sample['id']), ('sample.source_locator', sample['source_locator']),
        ('time.id', time['id']), ('time.origin', time['origin']), ('time.source_locator', time['source_locator']),
        ('denominator.id', denominator['id']), ('denominator.source_locator', denominator['source_locator']),
        ('phase_separation.source_locator', separation['source_locator']),
        ('applicability.source', applicability['source']),
    ):
        if not _known(value):
            issues.append(f'{label}: explicit known declaration required')
    for label, group in [('sample', sample), ('time', time), ('denominator', denominator), ('phase_separation', separation)]:
        if group['source_id'] != record['source_id']:
            issues.append(f'{label}.source_id differs from the common input source')
    for phase in contract['phase_order']:
        item = phases[phase]
        if item['unit'] not in contract['mass_ratio_units']:
            issues.append(f'{phase}: requires explicit g/g or kg/kg, without implicit percent conversion')
        for key, expected in [('source_id', record['source_id']), ('sample_id', sample['id']),
                              ('time_id', time['id']), ('denominator_id', denominator['id'])]:
            if item[key] != expected:
                issues.append(f'{phase}.{key} differs from the common declared {key}')
        if not _known(item['source_locator']):
            issues.append(f'{phase}.source_locator: explicit phase-mass derivation required')
    if issues:
        raise ValueError('source TG semantics incompatible: ' + '; '.join(issues))
    constants = {name: deepcopy(config['parameters'][key]) for name, key in contract['molar_mass_parameters'].items()}
    for name, item in constants.items():
        if item['unit'] != contract['molar_mass_unit']:
            raise ValueError(f'{name}: source molar-mass unit must be {contract["molar_mass_unit"]}')
    masses = {name: _number(item['value'], f'{name} source molar mass') for name, item in constants.items()}
    CH = _number(phases['portlandite']['value'], 'M_CH')
    Cc = _number(phases['calcite']['value'], 'M_Cc')
    doc_CH = 1 - masses['CaO'] / masses['CH'] * CH
    doc_Cc = masses['CaO'] / masses['Cc'] * Cc
    return {
        'schema': 'saeki2026_source_TG_DoC_pair_v1',
        'DoC_CH': doc_CH, 'DoC_Cc': doc_Cc, 'DoC_CH_minus_DoC_Cc': doc_CH - doc_Cc, 'unit': '1',
        'time': {'elapsed_s': convert(time['value'], time['unit'], 's'), 'original': deepcopy(time),
                 'meaning': 'Elapsed time relative to supplied source origin; not model process time.'},
        'input_measurement_kind': record['measurement_kind'],
        'derived_identity': 'synthetic' if record['measurement_kind'] == 'synthetic' else 'source-derived',
        'original_input': original, 'source_formula': deepcopy(config['sources'][contract['formula_source_id']]),
        'formula_contract': deepcopy(contract), 'source_molar_masses': constants,
        'definitions': {'DoC_CH': 'Portlandite depletion on source CaO reference, Eq5.',
                        'DoC_Cc': 'Total carbonate contribution on source CaO reference, Eq6; initial carbonate included.',
                        'difference': 'Independent definitions, not forced equal or interpreted as a whole-brick conservation residual.'},
        'admission': {'purpose': 'source_reference_mapping', 'eligible_by_declared_semantics': True,
                      'material_validation': False, 'canonical_fit_observation': False,
                      'applicability': deepcopy(applicability), 'denominator': deepcopy(denominator)},
    }
