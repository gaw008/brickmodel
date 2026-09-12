"""Dynamic donor conductivity in the actual sorption column (manufactured EOS)."""
from dataclasses import replace
from fractions import Fraction as F
import os
from pathlib import Path

import pytest

from test_arlabosse_sorption_column import setup as sorption_setup
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.septien_conductivity import SeptienConductivity
from sludge_sandbox.source_wet_column import integrate_source_column


def setup(monkeypatch):
    column, states = sorption_setup(monkeypatch)
    directory = Path(os.environ.get('SEPTIEN_SOURCE_DIRECTORY',
        REPOSITORY/'runs/sandbox/source-cache/septien2020'))
    provider = SeptienConductivity(REPOSITORY, directory)
    face = replace(column.faces[0], conductivities_w_m_k=(0., 0.))
    column = replace(column, faces=(face,), thermal_provider=provider,
        transport_classification='mixed_source_exploratory')
    return column, states


def test_dynamic_source_conduction_drives_the_shared_energy_face(monkeypatch):
    column, states = setup(monkeypatch)
    rates = column.evaluate(states)
    witness = rates.faces[1].conductivity_witness
    a, b = rates.cells
    ta, tb = a.inverse.point.temperature_k, b.inverse.point.temperature_k
    ka, kb = (p.k_w_m_k for p in rates.conductivity_points)
    dl, dr = column.faces[0].half_widths_m
    expected = column.face_area_m2/(dl/ka+dr/kb)*(ta-tb)
    assert rates.faces[1].conduction_w == pytest.approx(expected, rel=1e-14)
    assert witness.conduction_w == rates.faces[1].conduction_w
    assert witness.entropy_production_w_k > 0
    assert witness.conductivity_points == rates.conductivity_points
    assert set(column.thermal_provider.source_ids).issubset(rates.source_ids)
    assert not rates.material_qualified


def test_midpoint_conductivity_is_retained_with_its_actual_energy_integral(monkeypatch):
    column, states = setup(monkeypatch)
    initial = column.evaluate(states)
    run = integrate_source_column(column, states, duration_s=1/128, steps=2)
    assert run.status == 'completed', run.reason
    for old, new, ledger, observation in zip(run.states, run.states[1:], run.ledgers, run.observations):
        face = ledger.faces[1]
        witness = face.conductivity_witness
        assert face.conduction_j == ledger.duration_s*F(witness.conduction_w)
        for i, point in enumerate(witness.conductivity_points):
            mid = ledger.midpoint_states[i]
            w = float(F(mid.liquid_water_mol)*F(column.storages[i].wet._mass)/F(column.storages[i].dry_mass_kg))
            assert point.moisture_kg_water_per_kg_dry == w
            assert point.k_w_m_k == column.thermal_provider.evaluate(point.temperature_k, w).k_w_m_k
            assert point.k_w_m_k != observation.conductivity_points[i].k_w_m_k
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j) == (
                ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i])
        assert sum(F(s.internal_energy_j) for s in new)-sum(F(s.internal_energy_j) for s in old) == sum(ledger.roundoff.energy_j)
    assert all(a.k_w_m_k != b.k_w_m_k for a,b in
        zip(initial.conductivity_points,run.observations[-1].conductivity_points))


def test_mixed_source_is_explicit_and_cannot_hide_static_conduction(monkeypatch):
    column, _ = setup(monkeypatch)
    with pytest.raises(ValueError, match='static_conduction_must_be_disabled'):
        replace(column, faces=(replace(column.faces[0],conductivities_w_m_k=(.5,.7)),))
    with pytest.raises(ValueError, match='explicit_transport_classification'):
        replace(column, transport_classification='manufactured_test_fixture')
    with pytest.raises(ValueError):
        replace(column, thermal_provider=object())
    with pytest.raises(ValueError):
        replace(column, thermal_provider=None)


def test_single_cell_cannot_bypass_thermal_domain_or_sources(monkeypatch):
    column, states = setup(monkeypatch)
    single = replace(column, storages=column.storages[:1], inverse_policies=column.inverse_policies[:1],
        transfer_coefficients_mol_s_pa=column.transfer_coefficients_mol_s_pa[:1],
        cell_widths_m=column.cell_widths_m[:1],interface_modes=column.interface_modes[:1],faces=())
    rates = single.evaluate(states[:1])
    assert len(rates.conductivity_points)==1
    assert set(single.thermal_provider.source_ids).issubset(rates.source_ids)
    storage=single.storages[0]
    state=storage.state(.1,states[0].gas_amounts_mol,0.)
    state=replace(state,internal_energy_j=storage.evaluate(state,330.).total_internal_energy_j)
    with pytest.raises(ValueError):
        single.evaluate((state,))
