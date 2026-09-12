"""Passive checks of actual source liquid-face samples used by one terminal.

Saved decoded liquid properties remain original source observations. Replaying
Darcy arithmetic is not a new EOS evaluation or a continuous donor certificate.
"""
from fractions import Fraction as F
import math

from .integration import IntegrationError
from .liquid_transport import LiquidTransportState, liquid_face_exchange
from .phase_storage import LiquidWaterPhase
from .source_net_panel import SourceAffinePanel
from .source_net_prefix import _same
from .source_wet_column import SourceWetColumn, LiquidColumnFaceRate
from .source_inverse_pressure import enclose_source_inverse_pressure


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise IntegrationError(reason)


def _bound_decoded_liquid(saved: LiquidTransportState, source_state, inverse, storage) -> None:
    """Bind saved T/P/inventory, uncertainty, provider and decoded source labels."""
    _require(type(saved) is LiquidTransportState, 'source_terminal_actual_decoded_liquid_required')
    enclose_source_inverse_pressure(storage, source_state, inverse)
    point = inverse.point
    water = storage.water
    mechanical = point.fluid.mechanical
    # These are saved EOS observations, not inferred from a source Cp law.
    # Require their original finite binary64 values; sample bindings retain them.
    names = ('temperature_k', 'pressure_pa', 'inventory_mol', 'saturation',
             'pressure_error_pa', 'molar_volume_m3_mol', 'enthalpy_j_mol')
    _require(all(type(getattr(saved, name)) is float and math.isfinite(getattr(saved, name))
                 for name in names), 'source_terminal_liquid_binary64_properties_required')
    implementation = water.implementation
    expected = LiquidTransportState(temperature_k=point.temperature_k,
        pressure_pa=mechanical.liquid_pressure_pa, inventory_mol=mechanical.liquid_inventory_mol,
        saturation=mechanical.liquid_volume_m3/point.available_pore_volume_m3,
        pressure_error_pa=point.pressure_error_pa, molar_volume_m3_mol=saved.molar_volume_m3_mol,
        enthalpy_j_mol=saved.enthalpy_j_mol, metadata=LiquidWaterPhase(water).metadata,
        provider_id='iapws95_real_fluid_helmholtz' if implementation is None else implementation.provider_id,
        provider_version='1.5.5' if implementation is None else implementation.provider_version,
        source_asset_sha256=tuple(sorted(water.source_asset_sha256.items())))
    _require(_same(saved, expected), 'source_terminal_decoded_liquid_binding_changed')
    lo, hi = map(F, mechanical.pressure_bracket_pa)
    _require(lo <= F(saved.pressure_pa)-F(saved.pressure_error_pa)
             <= F(saved.pressure_pa)+F(saved.pressure_error_pa) <= hi,
             'source_terminal_liquid_pressure_domain_exit')


def check_source_terminal_liquid(panel: SourceAffinePanel, column: SourceWetColumn) -> None:
    """Rebuild original face laws and exclude affine donor reversals over the panel.

    The caller has checked the actual panel/capture bindings and column identity.
    No storage solve or liquid-property evaluation occurs in this function.
    """
    _require(type(panel) is SourceAffinePanel and type(column) is SourceWetColumn,
             'actual_source_terminal_liquid_context_required')
    column._check()
    config = column.liquid_transport
    if config is None:
        return
    samples = (panel.first, panel.interior)
    for sample in samples:
        raw = sample.evaluation.source_evaluation
        _require(type(raw.liquid_states) is tuple and len(raw.liquid_states) == column.cell_count
                 and raw.liquid_pressure_interval_scope == 'fixed_decoded_temperature'
                 and raw.full_inverse_liquid_direction_certified is False,
                 'source_terminal_liquid_scope_or_layout_changed')
        for saved, state, cell, storage in zip(raw.liquid_states, sample.evaluation.source_states,
                                              raw.cells, column.storages):
            _bound_decoded_liquid(saved, state, cell.inverse, storage)
        for face_index, geometry in enumerate(column.faces, 1):
            saved = raw.faces[face_index]
            _require(type(saved) is LiquidColumnFaceRate
                     and type(saved.face_id) is int and saved.face_id == face_index
                     and type(saved.left_cell) is int and saved.left_cell == face_index-1
                     and type(saved.right_cell) is int and saved.right_cell == face_index,
                     'source_terminal_liquid_face_incidence_changed')
            left, right = raw.liquid_states[face_index-1:face_index+1]
            exchange = liquid_face_exchange(left, right,
                left_relation=config.relations[face_index-1], right_relation=config.relations[face_index],
                connection=config.connections[face_index-1], area_m2=geometry.area_m2,
                left_distance_m=geometry.half_widths_m[0], right_distance_m=geometry.half_widths_m[1],
                allow_manufactured=config.allow_manufactured)
            _require(_same(saved.liquid_exchange, exchange)
                     and _same(saved.liquid_mol_s, exchange.molar_flow_mol_s)
                     and _same(saved.liquid_enthalpy_w, exchange.enthalpy_flow_w),
                     'source_terminal_liquid_face_law_changed')
            donor = left if exchange.donor == 'left' else right if exchange.donor == 'right' else None
            projection = (F(exchange.enthalpy_flow_w)-F(exchange.molar_flow_mol_s)*F(donor.enthalpy_j_mol)
                          if donor is not None else F())
            total = math.fsum((saved.conduction_w, *saved.diffusive_enthalpy_w,
                              *saved.advective_enthalpy_w, exchange.enthalpy_flow_w))
            _require(_same(saved.liquid_enthalpy_projection_w, projection)
                     and _same(saved.energy_w, total), 'source_terminal_liquid_energy_projection_changed')
    _check_affine_donors(samples[0].evaluation.source_evaluation.faces[1:-1],
        samples[1].evaluation.source_evaluation.faces[1:-1],
        panel.interior.evaluation.time.elapsed_since(panel.first.evaluation.time),
        panel.upper.elapsed_since(panel.first.evaluation.time))


def _check_affine_donors(first: tuple, interior: tuple, hm: F, duration: F) -> None:
    """Only the sign of saved affine J; caller checks actual observations first."""
    for left, right in zip(first, interior):
        initial, interior = F(left.liquid_mol_s), F(right.liquid_mol_s)
        final = initial+(interior-initial)*duration/hm
        if initial == interior == 0:
            continue
        _require(initial*interior > 0 and initial*final > 0
                 and left.liquid_exchange.donor == right.liquid_exchange.donor,
                 'source_terminal_affine_liquid_donor_change')
