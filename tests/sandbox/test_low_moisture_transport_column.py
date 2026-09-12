"""Low-W D/k in the same actual column and open boundary with a manufactured EOS."""
from dataclasses import replace
from fractions import Fraction as F
import math

import pytest

from test_low_moisture_column import setup as low_setup
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.septien_conductivity import SeptienConductivity
from sludge_sandbox.source_sorption_moisture import MakelaMoistureTransport
from sludge_sandbox.low_moisture_transport import LowMoistureConductivity, LowMoistureTransport
from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn, VaporBoundaryControl
from sludge_sandbox.source_wet_column import integrate_source_column


def setup(monkeypatch):
    base,states=low_setup(monkeypatch)
    thermal=LowMoistureConductivity(SeptienConductivity(REPOSITORY,
        REPOSITORY/'runs/sandbox/source-cache/septien2020'))
    moisture=LowMoistureTransport(MakelaMoistureTransport(REPOSITORY,
        REPOSITORY/'runs/sandbox/source-cache/makela2016/makela2016-accepted.pdf'))
    face=replace(base.faces[0],half_widths_m=(.125,.125),conductivities_w_m_k=(0.,0.),
        diffusivities_m2_s=(0.,)*3,permeability_m2=0.)
    base=replace(base,faces=(face,),cell_widths_m=(.25,.25),thermal_provider=thermal,
        moisture_transport=moisture,transport_classification='mixed_source_exploratory')
    second=replace(states[1],internal_energy_j=base.storages[1].evaluate(states[1],333.).total_internal_energy_j)
    return base,(states[0],second)


def test_zero_face_is_finite_and_each_accepted_exchange_has_actual_context(monkeypatch):
    base,states=setup(monkeypatch)
    first=base.evaluate(states)
    assert first.faces[1].moisture_witness.exchange.molar_flow_mol_s<0
    assert first.faces[1].gas_mol_s==(0.,)*3
    column=ControlledVaporColumn(base,VaporBoundaryControl(0.,1e-9,350.,.001,('virtual:contact',)))
    run=integrate_source_column(column,states,duration_s=1/128,steps=2)
    assert run.status=='completed',run.reason
    assert run.states[-1][0].liquid_water_mol>0
    assert run.ledgers[0].predictor_rates.cells[0].phase.entropy_state=='positive_infinite_boundary_limit'
    assert run.ledgers[0].predictor_rates.closed_rates.faces[1].moisture_witness.exchange.entropy_state=='positive_infinite_boundary_limit'
    for old,new,ledger in zip(run.states,run.states[1:],run.ledgers):
        face=ledger.faces[1]
        witness=face.moisture_witness
        assert witness.source_state_binding_verified
        assert face.moisture_mol==ledger.duration_s*F(witness.exchange.molar_flow_mol_s)
        assert face.moisture_enthalpy_j==ledger.duration_s*F(witness.exchange.carried_energy_w)
        for i,p in enumerate(witness.points):
            state=ledger.midpoint_states[i]
            assert p.moisture_kg_water_per_kg_dry==F(state.liquid_water_mol)*F(base.storages[i].wet._mass)/F(base.storages[i].dry_mass_kg)
            assert witness.inverses[i].target_energy_j==state.internal_energy_j
            assert F(new[i].internal_energy_j)-F(old[i].internal_energy_j)==ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i]
        assert ledger.midpoint_rates.closed_rates.moisture_points==witness.points
        assert ledger.faces[-1].gas_mol[2]>0
        for rate,integral in zip(ledger.predictor_rates.faces,ledger.predictor_faces):
            assert integral.energy_j==ledger.duration_s/2*F(rate.energy_w)


def test_new_transport_semantics_cannot_hide_old_providers_or_duplicate_paths(monkeypatch):
    base,_=setup(monkeypatch)
    for changes in ({'thermal_provider':base.thermal_provider.original},
        {'moisture_transport':base.moisture_transport.original},
        {'faces':(replace(base.faces[0],diffusivities_m2_s=(0.,0.,1e-9)),)},
        {'faces':(replace(base.faces[0],conductivities_w_m_k=(1.,1.)),)}):
        with pytest.raises(ValueError):
            replace(base,**changes)


@pytest.mark.parametrize('nc',[.1,.17])
def test_source_branch_rejects_unresolved_isothermal_moisture_drive(monkeypatch,nc):
    base,initial=setup(monkeypatch)
    storage=base.storages[0]
    states=[]
    for amount in (nc,math.nextafter(nc,math.inf)):
        state=storage.state(amount,initial[0].gas_amounts_mol,0.)
        states.append(replace(state,internal_energy_j=storage.evaluate(state,330.).total_internal_energy_j))
    with pytest.raises(ValueError,match='chemical_drive_resolution'):
        base.evaluate(tuple(states))


def test_new_residual_field_does_not_reinterpret_existing_positional_verification_flag():
    from sludge_sandbox.low_moisture_transport import LowMoistureTransportWitness
    witness=LowMoistureTransportWitness((),None,None,(),(),(),False)
    assert witness.source_state_binding_verified is False
    assert witness.isothermal_fick_drive_residual_j_mol is None
