"""C host modes only; no localized event or numerical writeback is claimed."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_transport import setup,totals
from sludge_sandbox.mass_wet_transport import WetPair,integrate_wet_pair
from sludge_sandbox.integration import DomainExit
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential


def dry_states(pair,states):
    result=[]
    for i,(st,state) in enumerate(zip(pair.storages,states)):
        new=st.state(state.solid_mass_kg,0.,(state.gas_amounts_mol[0],state.gas_amounts_mol[1],1e-8),0.)
        result.append(replace(new,internal_energy_j=st.evaluate(new,305.+5*i).total_internal_energy_j))
    return tuple(result)


def test_strict_mode_conversion_and_no_inventory_mutation(monkeypatch):
    pair,states=setup(monkeypatch)
    with pytest.raises(ValueError,match='exact_zero'):pair.with_depleted_cells(states,(0,))
    zeros=dry_states(pair,states)
    new=pair.with_depleted_cells(zeros,(1,0))
    assert pair.interfaces==('existing_liquid',)*2 and new.interfaces==('depleted_no_nucleation',)*2
    assert new._identity!=pair._identity and new.storages==pair.storages
    assert all(s.liquid_water_mol==0 for s in zeros)
    for bad in ((),(True,),(0,0),(2,),[0]):
        with pytest.raises(ValueError):pair.with_depleted_cells(zeros,bad)
    with pytest.raises(ValueError,match='already_depleted'):new.with_depleted_cells(zeros,(0,))
    with pytest.raises(DomainExit,match='exact_zero'):new.evaluate(states)
    for modes in ((True,'existing_liquid'),('dry','existing_liquid'),['existing_liquid']*2):
        with pytest.raises(ValueError):replace(pair,interface_modes=modes)


def test_actual_zero_liquid_dry_rhs_and_two_cell_dynamics(monkeypatch):
    pair,states=setup(monkeypatch);zeros=dry_states(pair,states);dry=pair.with_depleted_cells(zeros,(0,1))
    calls=[0];original=WaterChemicalPotential.equilibrium_at_liquid_tp
    def observed(self,*a,**k):calls[0]+=1;return original(self,*a,**k)
    monkeypatch.setattr(WaterChemicalPotential,'equilibrium_at_liquid_tp',observed)
    obs=dry.evaluate(zeros)
    assert calls[0]==2 # Hypothetical chemical diagnosis only; inventory remains zero.
    for c in obs.cells:
        p=c.inverse.point
        assert p.fluid.mechanical.liquid_inventory_mol==0 and p.gas_volume_m3==p.available_pore_volume_m3
        assert c.phase_water_mol_s==0 and c.extent_kg_s>0
    assert obs.face_energy_w!=0
    initial=totals(dry,zeros)
    run=integrate_wet_pair(dry,zeros,duration_s=.001,steps=2)
    assert run.status=='completed',run.reason
    for row,l in zip(run.states[1:],run.ledgers):
        assert all(s.liquid_water_mol==0 for s in row) and l.phase_water_mol==(0.,0.)
        e,m,w,u=totals(dry,row)
        assert max(abs(a-b) for a,b in zip(e,initial[0]))<F(2e-15)
        assert abs(m-initial[1])<F(2e-15) and abs(w-initial[2])<F(2e-15) and abs(u-initial[3])<F(2e-10)
    assert run.states[-1][0].solid_mass_kg!=zeros[0].solid_mass_kg


def test_mixed_wet_dry_and_strict_recondensation_exit(monkeypatch):
    pair,states=setup(monkeypatch);zeros=dry_states(pair,states)
    mixed=(zeros[0],states[1]);host=pair.with_depleted_cells(mixed,(0,))
    obs=host.evaluate(mixed)
    assert obs.cells[0].phase_water_mol_s==0 and obs.cells[1].phase_water_mol_s<0
    assert host.interfaces==('depleted_no_nucleation','existing_liquid')
    # A dry cell with a supersaturated gas is out of this strict no-nucleation
    # domain, not an automatically regenerated liquid interface.
    st=host.storages[0];wetgas=replace(zeros[0],gas_amounts_mol=(.2,.2,.1))
    wetgas=replace(wetgas,internal_energy_j=st.evaluate(wetgas,305.).total_internal_energy_j)
    run=integrate_wet_pair(host,(wetgas,states[1]),duration_s=.001,steps=2)
    assert run.status=='domain_exit' and run.reason=='dry_interface_condensation_requires_unsupported_nucleation'
    assert len(run.states)==1 and not run.ledgers and run.evaluations_attempted==1 and run.evaluations_completed==0


def test_dry_unknown_equilibrium_and_mode_source_drift(monkeypatch):
    from sludge_sandbox.water_properties import WaterDomainError
    pair,states=setup(monkeypatch);zeros=dry_states(pair,states);dry=pair.with_depleted_cells(zeros,(0,1))
    def unavailable(*args,**kwargs):raise WaterDomainError('outside_liquid_domain')
    monkeypatch.setattr(WaterChemicalPotential,'equilibrium_at_liquid_tp',unavailable)
    with pytest.raises(DomainExit,match='condensation_drive_unknown'):dry.evaluate(zeros)
    object.__setattr__(dry,'interface_modes',('existing_liquid','depleted_no_nucleation'))
    with pytest.raises(ValueError,match='source_changed'):dry.evaluate(zeros)
