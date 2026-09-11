"""Closed, bounded configuration for an explicitly virtual three-cell source run.

Reading and asset validation are passive. Source assets are pinned independently
of scenario values. Binary64 numbers and exact rational clocks are not coerced.
No material, geometry, transport or full-cycle qualification is granted here.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType

from .source_record_io import read_record_bytes
from .heos_runtime_registry import RHS_MANIFEST_ASSET, WORKFLOW_MANIFEST_ASSET

CONFIG_BYTE_LIMIT = 65536
SCHEMA = 'source_run_config_v1'
PROFILE = 'source_multicell_wet_to_dry_heos_v1'
RHS_PROFILE = 'source_multicell_wet_to_dry_heos_rhs_v2'
WORKFLOW_PROFILE = 'source_multicell_wet_to_dry_heos_workflow_v3'

_SHAPE = {'schema': 'str',
 'profile': 'str',
 'classification': 'str',
 'storage': {'dry_mass_kg': 'float',
             'fluid_volume_m3': 'float',
             'fluid_volume_error_m3': 'float',
             'temperature_domain_k': ['float', 'float'],
             'pressure_domain_pa': ['float', 'float'],
             'caloric_reference_temperature_k': {'numerator': 'int', 'denominator': 'int'},
             'pressure_closure': 'str',
             'geometry_rationale': 'str',
             'chemistry_rationale': 'str'},
 'envelope': {'temperature_range_k': ['float', 'float'],
              'pressure_range_pa': ['float', 'float'],
              'liquid_u_error_j_mol': 'float',
              'liquid_v_error_m3_mol': 'float',
              'liquid_abs_du_dp_bound_j_mol_pa': 'float',
              'gas_u_error_j_mol': {'O2': 'float', 'N2': 'float', 'H2O': 'float'},
              'gas_cv_lower_j_mol_k': {'O2': 'float', 'N2': 'float', 'H2O': 'float'},
              'method': 'str',
              'source_ids': ['str']},
 'grid': {'cell_widths_m': ['float', 'float', 'float'],
          'face_area_m2': 'float',
          'conductivities_w_m_k': [['float', 'float'], ['float', 'float']],
          'diffusivities_m2_s': [['float', 'float', 'float'], ['float', 'float', 'float']],
          'gas_permeability_m2': ['float', 'float'],
          'gas_viscosity_pa_s': ['float', 'float'],
          'source_ids': ['str']},
 'liquid_transport': {'saturation_knots': ['float', 'float', 'float'],
                      'permeability_m2': ['float', 'float', 'float'],
                      'relative_permeability': ['float', 'float', 'float'],
                      'viscosity_pa_s': ['float', 'float', 'float'],
                      'temperature_range_k': ['float', 'float'],
                      'pressure_range_pa': ['float', 'float'],
                      'model_id': 'str',
                      'version': 'str',
                      'source_ids': ['str'],
                      'connection_statuses': ['str', 'str'],
                      'connection_ids': ['str', 'str'],
                      'connection_source_ids': ['str']},
 'initial': {'liquid_water_mol': ['float', 'float', 'float'],
             'gas_amounts_mol': [['float', 'float', 'float'],
                                 ['float', 'float', 'float'],
                                 ['float', 'float', 'float']],
             'temperature_k': ['float', 'float', 'float'],
             'interface_modes': ['str', 'str', 'str']},
 'transfer_coefficients_mol_s_pa': ['float', 'float', 'float'],
 'pressure_policy': {'volume_tolerance_m3': 'float',
                     'pressure_tolerance_pa': 'float',
                     'maximum_iterations': 'int',
                     'strategy': 'NoneType'},
 'inverse_policy': {'energy_tolerance_j': 'float',
                    'temperature_tolerance_k': 'float',
                    'maximum_iterations': 'int'},
 'integration_policy': {'minimum_step_s': 'float',
                        'relative_tolerance': 'float',
                        'amount_absolute_tolerance_mol': 'float',
                        'energy_absolute_tolerance_j': 'float',
                        'amount_scale_mol': 'float',
                        'energy_scale_j': 'float',
                        'maximum_steps': 'int',
                        'maximum_rejections': 'int',
                        'maximum_wall_seconds': 'float',
                        'stretch_absolute_tolerance': 'NoneType',
                        'stretch_scale': 'NoneType'},
 'event_policy': {'time_absolute_s': 'float',
                  'amount_absolute_mol': 'float',
                  'energy_absolute_j': 'float',
                  'temperature_absolute_k': 'float',
                  'pressure_absolute_pa': 'float',
                  'terminal_window_s': 'float',
                  'maximum_refinements': 'int',
                  'common_time_horizon_s': 'float',
                  'safe_inventory_fraction': 'float',
                  'nested_approach': 'NoneType',
                  'terminal_method': 'str',
                  'pressure_comparison': 'NoneType',
                  'ordered_event_policy': 'NoneType'},
 'roundoff_policy': {'correction_absolute_mol': 'float',
                     'correction_fraction_evaporated': 'float',
                     'storage_absolute_mol': 'float',
                     'cumulative_storage_absolute_mol': 'float',
                     'element_absolute_mol': 'float',
                     'cumulative_element_absolute_mol': 'float',
                     'mass_absolute_kg': 'float',
                     'cumulative_mass_absolute_kg': 'float',
                     'cumulative_correction_absolute_mol': 'float'},
 'study': {'selected_cell_index': 'int',
           'start_seconds': {'numerator': 'int', 'denominator': 'int'},
           'horizon_multiplier': {'numerator': 'int', 'denominator': 'int'},
           'shared_dry_cell_index': 'int',
           'shared_wet_cell_indices': ['int', 'int']},
 'resources': {'callback_cap': 'int',
               'dry_path_callback_cap': 'int',
               'total_callback_cap': 'int',
               'wet_pressure_request_cap': 'int',
               'outer_seconds': 'float'}}

REQUIRED_ASSETS = (('.tools/source-cache/arlabosse2005/article.html',
  115329,
  '7dc682647cc70503820e6738b806b052ddccc9f1bc14650178e8813c7e203816'),
 ('.tools/source-cache/arlabosse2005/cp-equation.gif',
  1221,
  '3b406de01f7ac8bbf27c06c3245345a0966aee1d6fcd90e4f00541a06064cf85'),
 ('.tools/source-cache/arlabosse2005/nomenclature.gif',
  9743,
  '24c38177563d883c17f343b152746a849db485a25eace21fe6d2efad5021f759'),
 ('.tools/source-cache/arlabosse2005/table1.gif',
  6086,
  '8db1e49fcd6f3afc1a279bdf7c061d04ce93956c6d1b39f853248c84b138be8e'),
 ('data/sandbox/research/arlabosse2005/source.json',
  4033,
  '2f9caf23689092e548b2b3d7abf7c54d58d177569a7850b47c69df15e74295d6'),
 ('data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json',
  1503,
  '85f34b18308cb355f979f111467e6ad9d9dc1e9c08c5d0678cceddaa2376ba62'),
 ('data/sandbox/research/water-element-convention-v1/facts.json',
  2013,
  'a9b5bec83df94504346a5f93f3008a0029653f24bfc085babeb65bbdbb919838'),
 ('data/sandbox/research/water-element-convention-v1/source-excerpt.txt',
  77,
  '510543e4d5b343463126ed87957ba9f5b24d1bb4c0978fc51199c3acb2b769bc'),
 ('data/sandbox/thermochemistry/nist_gases_v1.json',
  5521,
  'b3ed8274b56fd773a01340308651c301f133dbd097cf4abcc0baed05e5ef7e53'),
 ('data/sandbox/water/IAPWS95-2018.pdf',
  380240,
  '512879217b94f4d0741c88cab743d41098268914d538d73e680a736cb1c3aad7'),
 ('data/sandbox/water/heos-8.0.0-approved-manifest.json',
  4532,
  '5f9e39bf1d3376b931caaf8fbda478b482cafe4c8b57a490860ac6ed080bf6db'),
 ('data/sandbox/water/iapws-1.5.5-LICENSE',
  35120,
  'fe3eea6c599e23a00c08c5f5cb2320c30adc8f8687db5fcec9b79a662c53ff6b'),
 ('data/sandbox/water/iapws-1.5.5-iapws95.py',
  106695,
  '89edb7c0e3b77533319d253819cdb4c1da50775d2e7b324249574607d6790520'),
 ('data/sandbox/water/iapws-1.5.5-py3-none-any.whl',
  117421,
  '97810dca5155cce1e2ec964dd254fc9e4858fbb1c9967da6c4f817adaf3a818e'),
 ('data/sandbox/water/source_facts.json',
  1763,
  '53af498b3974d180d273d7b17a6619d49d9a7d90bbacdd6e0304651f33bd79d6'),
 ('runs/sandbox/source-cache/nist-thermochemistry-20260907/N2-web-extract.json',
  10941,
  'b18746e5bcf3e7ce0008986332784771ce1d17e60103e5181b2569e2d395a2de'),
 ('runs/sandbox/source-cache/nist-thermochemistry-20260907/O2-web-extract.json',
  10944,
  'ac8fb628c03e4c17aff32b64bfd2e5292c336eb42ff847cacfd3e0c3742ecaf2'))


class SourceRunConfigError(ValueError):
    """A configuration or its required source bundle is not admissible."""


def required_source_assets(profile):
    """Select a complete pinned bundle; historical manifests remain unchanged."""
    if profile == PROFILE:
        return REQUIRED_ASSETS
    if profile in (RHS_PROFILE, WORKFLOW_PROFILE):
        manifest = RHS_MANIFEST_ASSET if profile == RHS_PROFILE else WORKFLOW_MANIFEST_ASSET
        return tuple(manifest if row[0].endswith('/heos-8.0.0-approved-manifest.json')
                     else row for row in REQUIRED_ASSETS)
    raise SourceRunConfigError('source_run_config_profile')


def source_heos_manifest(config):
    return required_source_assets(config.values['profile'])[10][0].rsplit('/', 1)[-1]


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SourceRunConfigError(reason)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _freeze(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if type(value) is MappingProxyType:
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    _require(type(value) in (str, float, int, type(None)), 'source_run_config_value_type')
    return value


def _pairs(items: list) -> dict:
    result = {}
    for key, value in items:
        _require(key not in result, 'source_run_config_duplicate_key')
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise SourceRunConfigError('source_run_config_nonfinite:' + value)


def _integer(value: str) -> int:
    _require(len(value) <= 100, 'source_run_config_integer_limit')
    return int(value)


def _shape(value: object, expected: object, path: str) -> None:
    if type(expected) is dict:
        _require(type(value) is dict and value.keys() == expected.keys(),
                 'source_run_config_fields:' + path)
        for key, child in expected.items():
            _shape(value[key], child, path + '/' + key)
    elif type(expected) is list:
        _require(type(value) is list and len(value) == len(expected),
                 'source_run_config_layout:' + path)
        for index, child in enumerate(expected):
            _shape(value[index], child, path + '/' + str(index))
    else:
        _require(type(value).__name__ == expected, 'source_run_config_type:' + path)
        if type(value) is float:
            _require(math.isfinite(value), 'source_run_config_nonfinite:' + path)
        if type(value) is str:
            _require(bool(value.strip()) and value == value.strip(), 'source_run_config_label:' + path)


def exact_config_fraction(value: Mapping[str, int]) -> Fraction:
    """Decode the explicit exact-rational spelling used by this configuration."""
    _require(isinstance(value, Mapping) and set(value) == {'numerator', 'denominator'},
             'source_run_config_fraction_fields')
    n, d = value['numerator'], value['denominator']
    _require(type(n) is int and type(d) is int and d > 0 and
             max(n.bit_length(), d.bit_length()) <= 332, 'source_run_config_fraction_value')
    result = Fraction(n, d)
    _require((result.numerator, result.denominator) == (n, d), 'source_run_config_fraction_canonical')
    return result


def _positive(values: object, *, zero: bool = False) -> None:
    if isinstance(values, Mapping):
        values = values.values()
    _require(all(value >= 0 if zero else value > 0 for value in values),
             'source_run_config_numeric_domain')


def _range(values: list) -> None:
    _require(0 < values[0] < values[1], 'source_run_config_range')


def _validate(values: dict) -> None:
    _require(type(values) is dict and set(values) == set(_SHAPE) | {'assets'},
             'source_run_config_fields:root')
    _shape({key: values[key] for key in _SHAPE}, _SHAPE, '')
    expected = [{'path': p, 'bytes': n, 'sha256': h}
                for p, n, h in required_source_assets(values['profile'])]
    _require(type(values['assets']) is list and _canonical(values['assets']) == _canonical(expected),
             'source_run_config_pinned_assets')
    _require(values['schema'] == SCHEMA and values['profile'] in (PROFILE, RHS_PROFILE, WORKFLOW_PROFILE) and
             values['classification'] == 'manufactured_test_fixture', 'source_run_config_profile')
    s, e, grid, liquid, initial = (values[name] for name in
                                  ('storage', 'envelope', 'grid', 'liquid_transport', 'initial'))
    for row in (s['temperature_domain_k'], s['pressure_domain_pa'],
                e['temperature_range_k'], e['pressure_range_pa'],
                liquid['temperature_range_k'], liquid['pressure_range_pa']):
        _range(row)
    reference = exact_config_fraction(s['caloric_reference_temperature_k'])
    _require(Fraction(6163, 20) <= reference <= Fraction(7563, 20),
             'source_run_caloric_reference_domain')
    _require(Fraction(6163, 20) <= s['temperature_domain_k'][0] and
             s['temperature_domain_k'][1] <= Fraction(7563, 20), 'source_run_caloric_domain')
    _positive((s['dry_mass_kg'], s['fluid_volume_m3'], grid['face_area_m2']))
    _require(0 <= s['fluid_volume_error_m3'] < s['fluid_volume_m3'], 'source_run_volume_error')
    _require(s['pressure_closure'] == 'planar_interface_no_capillary_pressure', 'source_run_pressure_closure')
    for outer, inner in ((e['temperature_range_k'], s['temperature_domain_k']),
                         (e['pressure_range_pa'], s['pressure_domain_pa'])):
        _require(outer[0] <= inner[0] < inner[1] <= outer[1], 'source_run_envelope_domain')
    _positive((e['liquid_u_error_j_mol'], e['liquid_v_error_m3_mol'],
               e['liquid_abs_du_dp_bound_j_mol_pa']), zero=True)
    _positive(e['gas_u_error_j_mol'], zero=True)
    _positive(e['gas_cv_lower_j_mol_k'])
    _positive(grid['cell_widths_m'])
    _require(all(Fraction(s['fluid_volume_m3']) + Fraction(s['fluid_volume_error_m3']) <=
                 Fraction(grid['face_area_m2']) * Fraction(width) for width in grid['cell_widths_m']),
             'source_run_cell_capacity')
    for rows in (grid['conductivities_w_m_k'], grid['diffusivities_m2_s']):
        for row in rows:
            _positive(row, zero=True)
    _positive(grid['gas_permeability_m2'], zero=True)
    _positive(grid['gas_viscosity_pa_s'])
    _positive(values['transfer_coefficients_mol_s_pa'], zero=True)
    _positive(initial['liquid_water_mol'])
    for row in initial['gas_amounts_mol']:
        _positive(row, zero=True)
        _require(math.fsum(row) > 0, 'source_run_initial_gas_inventory')
    _require(all(s['temperature_domain_k'][0] <= t <= s['temperature_domain_k'][1]
                 for t in initial['temperature_k']), 'source_run_initial_temperature_domain')
    _require(initial['interface_modes'] == ['existing_liquid'] * 3, 'source_run_initial_wet_modes')
    _validate_policies(values)
    from .liquid_transport import SaturationMobilityTable, LiquidConnection
    table = {key: tuple(value) if type(value) is list else value for key, value in liquid.items()
             if not key.startswith('connection_')}
    SaturationMobilityTable(**table, classification='manufactured_test_fixture',
                           relation_kind='tabulated_saturation_relation',
                           source_asset_sha256=(('source_run_config_v1',
                               hashlib.sha256(_canonical(values)).hexdigest()),))
    for status, identity in zip(liquid['connection_statuses'], liquid['connection_ids']):
        LiquidConnection(status=status, connection_id=identity, version=liquid['version'],
                         classification='manufactured_test_fixture',
                         source_ids=tuple(liquid['connection_source_ids']))


def _validate_policies(values: dict) -> None:
    from .phase_storage import InversePolicy
    from .rigid_water_gas import PressurePolicy
    from .integration import IntegrationPolicy
    InversePolicy(**values['inverse_policy'])
    PressurePolicy(**values['pressure_policy'])
    policy = values['integration_policy']
    IntegrationPolicy(initial_step_s=policy['minimum_step_s'],
                      maximum_step_s=policy['minimum_step_s'], **policy)
    event = values['event_policy']
    _positive(tuple(event[key] for key in ('time_absolute_s', 'amount_absolute_mol',
              'energy_absolute_j', 'temperature_absolute_k', 'pressure_absolute_pa',
              'terminal_window_s', 'common_time_horizon_s')))
    _require(0 < event['safe_inventory_fraction'] < .5 and 2 <= event['maximum_refinements'] <= 32,
             'source_run_event_limits')
    _require(event['terminal_method'] == 'affine_midpoint', 'source_run_terminal_method')
    _positive(values['roundoff_policy'])
    _require(values['roundoff_policy']['correction_fraction_evaporated'] <= 1e-8,
             'source_run_roundoff_fraction')
    study = values['study']
    _require(study['selected_cell_index'] == study['shared_dry_cell_index'] == 1 and
             study['shared_wet_cell_indices'] == [0, 2], 'source_run_supported_selected_cell')
    exact_config_fraction(study['start_seconds'])
    _require(exact_config_fraction(study['horizon_multiplier']) > 1, 'source_run_horizon_multiplier')
    limits = values['resources']
    for name, cap in (('callback_cap', 16), ('dry_path_callback_cap', 24),
                      ('total_callback_cap', 97), ('wet_pressure_request_cap', 16), ('outer_seconds', 510.)):
        _require(0 < limits[name] <= cap, 'source_run_resource_limit:' + name)
    _require(policy['maximum_steps'] <= 4 and policy['maximum_rejections'] <= 4 and
             policy['maximum_wall_seconds'] <= 180., 'source_run_integration_resource_limit')


@dataclass(frozen=True)
class SourceRunConfig:
    """Validated immutable inputs; this identity is for a new virtual experiment."""
    canonical_bytes: bytes
    sha256: str
    values: Mapping[str, object]

    def check(self) -> None:
        _require(type(self.canonical_bytes) is bytes and type(self.sha256) is str and
                 type(self.values) is MappingProxyType, 'source_run_config_record_type')
        rebuilt = load_source_run_config(self.canonical_bytes)
        _require(rebuilt.sha256 == self.sha256 and _canonical(_thaw(self.values)) == self.canonical_bytes,
                 'source_run_config_binding')


def load_source_run_config(raw: bytes) -> SourceRunConfig:
    """Read a closed JSON configuration without loading a physical backend."""
    _require(type(raw) is bytes and 0 < len(raw) <= CONFIG_BYTE_LIMIT, 'source_run_config_byte_limit')
    try:
        values = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite, parse_int=_integer)
        _validate(values)
        canonical = _canonical(values)
    except SourceRunConfigError:
        raise
    except (ValueError, TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        raise SourceRunConfigError('source_run_config_invalid:' + str(exc)) from exc
    return SourceRunConfig(canonical, hashlib.sha256(canonical).hexdigest(), _freeze(values))


@dataclass(frozen=True)
class SourceRunAssets:
    """Verified external bundle; no source cache is silently downloaded or replaced."""
    root: Path
    files: tuple[tuple[str, int, str], ...]
    sha256: str
    config_sha256: str

    def check(self) -> None:
        _require(type(self.root) is type(Path()) and self.root == self.root.resolve() and
                 type(self.files) is tuple and self.files in
                 (REQUIRED_ASSETS, required_source_assets(RHS_PROFILE), required_source_assets(WORKFLOW_PROFILE)) and
                 all(type(row) is tuple and len(row) == 3 and type(row[0]) is str and
                     type(row[1]) is int and type(row[2]) is str for row in self.files) and
                 type(self.config_sha256) is str and len(self.config_sha256) == 64,
                 'source_run_assets_binding')
        _require(self.sha256 == hashlib.sha256(_canonical(self.files)).hexdigest(),
                 'source_run_assets_manifest_binding')
        for relative, size, digest in self.files:
            path = (self.root / relative).resolve()
            _require(path.is_relative_to(self.root), 'source_run_asset_outside_root')
            try:
                raw = read_record_bytes(path, size, size_reason='source_run_asset_size',
                                        regular_reason='source_run_asset_not_regular')
            except OSError as exc:
                raise SourceRunConfigError('source_run_asset_unavailable:' + relative) from exc
            _require(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest,
                     'source_run_asset_hash:' + relative)


def validate_source_run_assets(config: SourceRunConfig, *, assets_root: Path) -> SourceRunAssets:
    """Verify every required asset in a supplied local bundle, without any EOS call."""
    _require(type(config) is SourceRunConfig, 'source_run_config_required')
    config.check()
    root = Path(assets_root).resolve()
    files = required_source_assets(config.values['profile'])
    result = SourceRunAssets(root, files,
                             hashlib.sha256(_canonical(files)).hexdigest(), config.sha256)
    result.check()
    return result
