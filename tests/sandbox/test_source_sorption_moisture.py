"""Actual storage/phase adapters with manufactured fluid callbacks, not EOS validation."""
from dataclasses import replace
from fractions import Fraction as F
import os
from pathlib import Path

import pytest

from test_sorption_conductivity_column import setup as thermal_setup
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.source_sorption_moisture import MakelaMoistureTransport, condensed_water_point
from sludge_sandbox.source_wet_column import integrate_source_column


def setup(monkeypatch):
    column, states = thermal_setup(monkeypatch)
    path = Path(os.environ.get('MAKELA_SOURCE_PDF',
        REPOSITORY/'runs/sandbox/source-cache/makela2016/makela2016-accepted.pdf'))
    transport = MakelaMoistureTransport(REPOSITORY, path)
    face = replace(column.faces[0], half_widths_m=(.125, .125),
                   diffusivities_m2_s=(0.,)*3, permeability_m2=0.)
    return replace(column, faces=(face,), cell_widths_m=(.25, .25),
                   moisture_transport=transport), states


def test_actual_full_chemical_potential_and_partial_enthalpy(monkeypatch):
    column, states = setup(monkeypatch)
    rates = column.evaluate(states)
    for point, cell, state in zip(rates.moisture_points, rates.cells, states):
        pure = cell.phase.equilibrium.pure_equilibrium.liquid
        source = cell.inverse.point
        assert point.chemical_potential_j_mol == F(pure.chemical_potential_j_mol)+F(source.excess_chemical_potential_j_mol)
        assert point.partial_molar_enthalpy_j_mol == F(pure.enthalpy_j_mol)+F(source.excess_partial_water_enthalpy_j_mol)
        assert point.moisture_kg_water_per_kg_dry == F(source.moisture_kg_water_per_kg_dry)
        assert point.chemical_potential_j_mol != F(source.excess_chemical_potential_j_mol)
        assert point.partial_molar_enthalpy_j_mol != F(pure.enthalpy_j_mol)
    face = rates.faces[1]
    assert face.moisture_witness.exchange.molar_flow_mol_s != 0
    assert face.gas_mol_s == (0.,)*3
    assert face.moisture_witness.source_state_binding_verified
    assert not face.moisture_witness.material_qualified


def test_actual_midpoint_water_energy_and_witness(monkeypatch):
    column, states = setup(monkeypatch)
    run = integrate_source_column(column, states, duration_s=1/128, steps=2)
    assert run.status == 'completed', run.reason
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        face = ledger.faces[1]
        exchange = face.moisture_witness.exchange
        assert face.moisture_mol == ledger.duration_s*F(exchange.molar_flow_mol_s)
        assert face.moisture_enthalpy_j == ledger.duration_s*F(exchange.carried_energy_w)
        assert face.energy_j == face.conduction_j+face.moisture_enthalpy_j+face.energy_decomposition_roundoff_j
        for i, point in enumerate(face.moisture_witness.points):
            mid = ledger.midpoint_states[i]
            w = float(F(mid.liquid_water_mol)*F(column.storages[i].wet._mass)/F(column.storages[i].dry_mass_kg))
            assert point.moisture_kg_water_per_kg_dry == F(w)
            incoming = -face.moisture_mol if i == 0 else face.moisture_mol
            assert F(new[i].liquid_water_mol)-F(old[i].liquid_water_mol) == incoming-ledger.phase_water_mol[i]+ledger.roundoff.liquid_mol[i]
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i]
            for k in range(3):
                assert F(new[i].gas_amounts_mol[k])-F(old[i].gas_amounts_mol[k]) == (ledger.phase_water_mol[i] if k == 2 else 0)+ledger.roundoff.gas_mol[i][k]
        water = lambda row: sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in row), F())
        assert water(new)-water(old) == sum(ledger.roundoff.liquid_mol)+sum(r[2] for r in ledger.roundoff.gas_mol)


def test_total_loss_diffusivity_cannot_double_count_gas_or_darcy(monkeypatch):
    column, _ = setup(monkeypatch)
    for change in ({'diffusivities_m2_s': (0., 0., 1e-9)}, {'permeability_m2': 1e-13}):
        with pytest.raises(ValueError, match='moisture_requires_disabled_gas_transport'):
            replace(column, faces=(replace(column.faces[0], **change),))
    with pytest.raises(ValueError, match='moisture_requires_source_conductivity'):
        replace(column, thermal_provider=None)
    with pytest.raises(ValueError, match='uniform_dry_density'):
        replace(column, cell_widths_m=(.25, .3125),
                faces=(replace(column.faces[0],half_widths_m=(.125,.15625)),))


def test_adapter_refuses_unrelated_inventory_and_modified_excess(monkeypatch):
    column, states = setup(monkeypatch)
    rates = column.evaluate(states)
    cell = rates.cells[0]
    with pytest.raises(ValueError, match='moisture_inverse_state'):
        condensed_water_point(column.storages[0], column.chemical, states[1], cell.inverse, cell.phase)
    bad = replace(cell.inverse, point=replace(cell.inverse.point,
        excess_chemical_potential_j_mol=cell.inverse.point.excess_chemical_potential_j_mol+1))
    with pytest.raises(ValueError, match='excess_model_mismatch'):
        condensed_water_point(column.storages[0], column.chemical, states[0], bad, cell.phase)


def test_same_W_factor_uses_explicit_source_limit(monkeypatch):
    column, states = setup(monkeypatch)
    rates = column.evaluate(states)
    left = rates.moisture_points[0]
    right = replace(left, temperature_k=F(333))
    factor = column.moisture_transport.factor(column.storages[0], left, right)
    assert factor.gamma_j_mol > 0
    assert factor.temperature_k == (left.temperature_k+right.temperature_k)/2
    assert factor.method == 'declared_same_W_limit'
    assert factor.moisture_interval == (left.moisture_kg_water_per_kg_dry,)*2


def test_single_cell_still_binds_moisture_source_and_domain(monkeypatch):
    column, states = setup(monkeypatch)
    single = replace(column, storages=column.storages[:1], inverse_policies=column.inverse_policies[:1],
        transfer_coefficients_mol_s_pa=column.transfer_coefficients_mol_s_pa[:1],
        cell_widths_m=column.cell_widths_m[:1], interface_modes=column.interface_modes[:1], faces=())
    rates = single.evaluate(states[:1])
    assert len(rates.moisture_points) == 1
    assert set(single.moisture_transport.source_ids).issubset(rates.source_ids)


def test_exchange_cannot_certify_declared_or_modified_points(monkeypatch):
    column, states = setup(monkeypatch)
    rates = column.evaluate(states)
    config = column.moisture_transport
    kwargs = dict(area_m2=column.face_area_m2,widths_m=column.cell_widths_m,
                  geometry_sources=column.coefficient_source_ids)
    with pytest.raises(ValueError,match='actual_runtime_context_required'):
        config.exchange(column.storages,rates.moisture_points,**kwargs)
    kwargs.update(chemical=column.chemical,states=states,
        inverses=tuple(c.inverse for c in rates.cells),phases=tuple(c.phase for c in rates.cells))
    for altered in (tuple(replace(p,chemical_potential_j_mol=p.chemical_potential_j_mol+1000)
                           for p in rates.moisture_points),
                    tuple(replace(p,energy_reference_id='unrelated') for p in rates.moisture_points)):
        with pytest.raises(ValueError,match='do_not_match_actual_runtime'):
            config.exchange(column.storages,altered,**kwargs)
