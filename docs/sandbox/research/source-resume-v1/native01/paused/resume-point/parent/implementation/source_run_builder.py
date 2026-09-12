"""Assemble the real HEOS/source-Cp N3 model from explicit, verified inputs.

The available volume and transport remain manufactured numerical assumptions.
Construction performs the providers' real reference anchors; initial total U
and every time-dependent evaluation belong to the observing run service.
"""
from dataclasses import dataclass
from fractions import Fraction
import json
import math

from .arlabosse_caloric import ArlabosseDryCaloric
from .depletion_integration import DepletionPolicy
from .depletion_roundoff import DepletionRoundoffPolicy
from .exact_record import pack
from .exact_source_column import ExactSourceColumn
from .ideal_water_vapor import IdealWaterVapor
from .integration import IntegrationPolicy
from .liquid_transport import LiquidConnection, SaturationMobilityTable
from .mass_wet_storage import WaterElementConvention, WetMixedState
from .mass_wet_transport import WetFace
from .phase_storage import IdealGasPhase, InversePolicy
from .rigid_storage import DeclaredNumericalEnvelope, RigidStorage
from .rigid_water_gas import PressurePolicy, RigidWaterGas
from .source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
from .source_run_config import (SourceRunAssets, SourceRunConfig, SourceRunConfigError,
                                exact_config_fraction, required_source_assets, source_heos_manifest)
from .solid_fluid_heat import LiquidTransportConfig
from .source_wet_column import SourceWetColumn
from .source_wet_storage import ManufacturedFixedFluidVolume, SourceWetStorage
from .thermochemistry import load_thermochemistry
from .water_chemical_potential import WaterChemicalPotential
from .water_properties import load_water_properties

GAS_IDS = ('O2', 'N2', 'H2O')


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SourceRunConfigError(reason)


def _snapshot(value: object) -> bytes:
    return json.dumps(pack(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


@dataclass(frozen=True)
class BuiltSourceRun:
    """Live constructor result; zero-energy placeholders are not an evolved state."""
    config: SourceRunConfig
    assets: SourceRunAssets
    storages: tuple[SourceWetStorage, ...]
    chemical: WaterChemicalPotential
    column: SourceWetColumn
    adapter: ExactSourceColumn
    unset_energy_states: tuple[WetMixedState, ...]
    initial_temperatures_k: tuple[float, ...]
    original_binding: bytes

    def _binding(self) -> bytes:
        states = tuple((state.solid_mass_kg, state.liquid_water_mol,
                        state.gas_amounts_mol, state.internal_energy_j,
                        state.energy_model_identity) for state in self.unset_energy_states)
        return _snapshot((self.config.sha256, self.assets.sha256, self.assets.config_sha256,
                          tuple(storage.model_identity for storage in self.storages),
                          self.column.model_identity, self.adapter.operator_identity,
                          states, self.initial_temperatures_k))

    def check(self) -> None:
        """Recheck source content and constructor associations without solving U/T/P."""
        _require(type(self.config) is SourceRunConfig and type(self.assets) is SourceRunAssets,
                 'source_run_build_input_types')
        self.config.check()
        self.assets.check()
        _require(self.assets.config_sha256 == self.config.sha256 and
                 self.assets.files == required_source_assets(self.config.values['profile']) and
                 type(self.storages) is tuple and len(self.storages) == 3 and
                 all(type(storage) is SourceWetStorage for storage in self.storages),
                 'source_run_build_storage_types')
        _require(type(self.column) is SourceWetColumn and type(self.adapter) is ExactSourceColumn and
                 self.adapter.column is self.column and self.column.chemical is self.chemical and
                 all(a is b for a, b in zip(self.storages, self.column.storages)) and
                 len({id(storage) for storage in self.storages}) == 3 and
                 len({id(storage.volume) for storage in self.storages}) == 3,
                 'source_run_build_live_associations')
        self.column._check_states(self.unset_energy_states)
        _require(type(self.original_binding) is bytes and self._binding() == self.original_binding,
                 'source_run_build_content_changed')


def _fluid(config: SourceRunConfig, assets: SourceRunAssets) -> RigidStorage:
    values = config.values
    root = assets.root
    water_directory = root / 'data/sandbox/water'
    selection = {'backend': 'heos', 'backend_manifest':
                 water_directory / source_heos_manifest(config)}
    water = load_water_properties(water_directory, **selection)
    vapor = IdealWaterVapor(water_directory, **selection)
    thermochemistry = load_thermochemistry(root / 'data/sandbox/thermochemistry/nist_gases_v1.json')
    rows = json.loads((root / 'data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json').read_bytes())
    facts = {row['species_id']: row for row in rows}
    phases = {key: IdealGasPhase(thermochemistry.species(key), facts[key]['nominal_molar_mass_kg_mol'],
                                0, (facts[key]['source_id'], facts[key]['cache_sha256']))
              for key in GAS_IDS[:2]}
    phases['H2O'] = IdealGasPhase(vapor, vapor.molar_mass_kg_mol)
    storage = values['storage']
    mechanical = RigidWaterGas(water, GAS_IDS, storage['fluid_volume_m3'], storage['pressure_domain_pa'],
                               storage['pressure_closure'], PressurePolicy(**values['pressure_policy']))
    return RigidStorage(mechanical, phases, DeclaredNumericalEnvelope(**values['envelope']))


def _liquid(config: SourceRunConfig) -> LiquidTransportConfig:
    values = config.values['liquid_transport']
    fields = {key: value for key, value in values.items() if not key.startswith('connection_')}
    table = SaturationMobilityTable(**fields, classification='manufactured_test_fixture',
        relation_kind='tabulated_saturation_relation',
        source_asset_sha256=(('source_run_config_v1', config.sha256),))
    connections = tuple(LiquidConnection(status=status, connection_id=identity,
        version=values['version'], classification='manufactured_test_fixture',
        source_ids=values['connection_source_ids'])
        for status, identity in zip(values['connection_statuses'], values['connection_ids']))
    return LiquidTransportConfig(relations=(table,) * 3, connections=connections, allow_manufactured=True)


def build_source_run(config: SourceRunConfig, assets: SourceRunAssets) -> BuiltSourceRun:
    """Build actual HEOS/Arlabosse/NIST objects; do not initialize energy or run RHS."""
    _require(type(config) is SourceRunConfig and type(assets) is SourceRunAssets,
             'source_run_explicit_config_and_assets')
    config.check()
    assets.check()
    _require(assets.config_sha256 == config.sha256 and
             assets.files == required_source_assets(config.values['profile']), 'source_run_asset_config_binding')
    values, root = config.values, assets.root
    storage = values['storage']
    fluid = _fluid(config, assets)
    caloric = ArlabosseMassCaloric(ArlabosseDryCaloric(
        root / 'data/sandbox/research/arlabosse2005/source.json', root),
        exact_config_fraction(storage['caloric_reference_temperature_k']))
    disabled = ReactionDisabled((caloric.component_id,), GAS_IDS, storage['chemistry_rationale'])
    convention = WaterElementConvention.load(root / 'data/sandbox/research/water-element-convention-v1/facts.json')
    storages = tuple(SourceWetStorage(caloric, storage['dry_mass_kg'], fluid,
        ManufacturedFixedFluidVolume(storage['fluid_volume_m3'], storage['fluid_volume_error_m3'],
                                     storage['geometry_rationale']),
        storage['temperature_domain_k'], disabled, convention) for _ in range(3))
    water_directory = root / 'data/sandbox/water'
    chemical = WaterChemicalPotential(water_directory, backend='heos',
        backend_manifest=water_directory / source_heos_manifest(config))
    grid = values['grid']
    widths = grid['cell_widths_m']
    faces = tuple(WetFace(grid['face_area_m2'], (widths[i] / 2, widths[i + 1] / 2),
        grid['conductivities_w_m_k'][i], grid['diffusivities_m2_s'][i],
        grid['gas_permeability_m2'][i], grid['gas_viscosity_pa_s'][i], grid['source_ids'])
        for i in range(2))
    column = SourceWetColumn(storages, tuple(InversePolicy(**values['inverse_policy']) for _ in range(3)),
        chemical, values['transfer_coefficients_mol_s_pa'], faces, widths, grid['face_area_m2'],
        values['initial']['interface_modes'], grid['source_ids'], liquid_transport=_liquid(config))
    adapter = ExactSourceColumn(column)
    initial = values['initial']
    states = tuple(model.state(liquid, gases, 0.) for model, liquid, gases in
                   zip(storages, initial['liquid_water_mol'], initial['gas_amounts_mol']))
    result = BuiltSourceRun(config, assets, storages, chemical, column, adapter, states,
                            initial['temperature_k'], b'')
    object.__setattr__(result, 'original_binding', result._binding())
    result.check()
    return result


@dataclass(frozen=True)
class SourceRunControls:
    """Original numerical policies with actual source M and probe-derived step size."""
    integration_policy: IntegrationPolicy
    event_policy: DepletionPolicy
    horizon: Fraction
    config_sha256: str
    original_binding: bytes

    def check(self) -> None:
        _require(type(self.integration_policy) is IntegrationPolicy and
                 type(self.event_policy) is DepletionPolicy and
                 type(self.event_policy.roundoff_policy) is DepletionRoundoffPolicy and
                 type(self.horizon) is Fraction and self.horizon > 0 and
                 type(self.config_sha256) is str and type(self.original_binding) is bytes,
                 'source_run_controls_types')
        _require(_snapshot((self.integration_policy, self.event_policy, self.horizon,
                             self.config_sha256)) == self.original_binding,
                 'source_run_controls_content_changed')


def build_source_controls(config: SourceRunConfig, built: BuiltSourceRun, *,
                          horizon: Fraction) -> SourceRunControls:
    """Use the actual net-loss horizon and the providers' exact binary64 water M.

    Initial and maximum reference-step durations retain the historical float(H)
    conversion. The original exact H remains separately available to the trial.
    """
    _require(type(config) is SourceRunConfig and type(built) is BuiltSourceRun and
             type(horizon) is Fraction and horizon > 0, 'source_run_controls_inputs')
    config.check()
    built.check()
    _require(config.sha256 == built.config.sha256, 'source_run_controls_config_binding')
    mass = built.chemical.reference.molar_mass_kg_mol
    _require(type(mass) is float and math.isfinite(mass) and mass > 0 and
             all(type(storage.water.reference.molar_mass_kg_mol) is float and
                 storage.water.reference.molar_mass_kg_mol.hex() == mass.hex()
                 for storage in built.storages), 'source_run_water_molar_mass_binding')
    try:
        step = float(horizon)
    except OverflowError as exc:
        raise SourceRunConfigError('source_run_horizon_unrepresentable') from exc
    integration = IntegrationPolicy(initial_step_s=step, maximum_step_s=step,
                                    **config.values['integration_policy'])
    rounding = DepletionRoundoffPolicy(**config.values['roundoff_policy'], molar_mass_kg_mol=mass)
    event = DepletionPolicy(**config.values['event_policy'], roundoff_policy=rounding)
    binding = _snapshot((integration, event, horizon, config.sha256))
    result = SourceRunControls(integration, event, horizon, config.sha256, binding)
    result.check()
    return result
