"""Behavior after water-transfer method extraction, using legally built hosts.

No constructor bypass or substitute chemical truth is used. Existing source-gated
positive/negative/zero-vapor tests remain authoritative for phase chemistry.
"""
from dataclasses import replace
from fractions import Fraction as F

import numpy as np
import pytest

from sludge_sandbox.integration import DomainExit
from sludge_sandbox.rigid_fluid_heat import RigidFluidHeat
from sludge_sandbox.free_solid_slab import FreeSolidSlab
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer, WaterPhaseTransferError
from test_water_phase_transfer import ingredients, transfer
from test_free_slab_phase_transfer import slab_transfer
from test_joined_water_host import joined, host as joined_host


def test_invalid_interface_stops_before_base_and_assembly(ingredients,monkeypatch):
    wet=transfer(ingredients)
    dry_state=wet.base_model.state_from_temperatures([[0.,.01,1e-5]],[300.])
    dry=wet.with_depleted_cells(dry_state,(0,))
    # A legal numeric state with incompatible mode must fail before any caloric
    # inversion; its deliberately changed inventory is never used as a truth case.
    incompatible=replace(dry_state,amounts_mol=[[1.,.01,1e-5]])
    calls=[]
    def forbidden(*args,**kwargs):
        calls.append('unexpected_evaluation')
        pytest.fail('interface rejection must precede base and transfer assembly')
    monkeypatch.setattr(RigidFluidHeat,'evaluate',forbidden)
    monkeypatch.setattr(WaterPhaseTransfer,'_assemble_transfer',forbidden)
    with pytest.raises(DomainExit,match='no_existing_liquid_interface'):
        wet.evaluate(dry_state,0.)
    with pytest.raises(DomainExit,match='dry_interface_requires_exact_zero_liquid'):
        dry.evaluate(incompatible,0.)
    assert calls==[]
    assert wet.interfaces==('existing_liquid',) and dry.interfaces==('depleted_no_nucleation',)
    assert dry.coefficients_mol_s_pa==wet.coefficients_mol_s_pa
    assert dry.source_ids==wet.source_ids


def _assert_unchanged_context(out):
    base=out.base_evaluation
    for name in ('face_species_mol_s','face_energy_w','cell_power_w','mechanical_rates_per_s'):
        np.testing.assert_array_equal(getattr(out.rates,name),getattr(base.rates,name))
    assert out.rates.cell_power_components_w.keys()==base.rates.cell_power_components_w.keys()
    for key,values in base.rates.cell_power_components_w.items():
        np.testing.assert_array_equal(out.rates.cell_power_components_w[key],values)
    assert set(base.source_ids)<=set(out.source_ids)


def test_active_free_slab_regular_and_autonomous_preserve_actual_context(ingredients,monkeypatch):
    op=slab_transfer(ingredients)
    state=op.base_model.state_from_temperatures([[1.,.01,1e-5,2.],[.5,.008,.001,2.]],
        [300.,301.],normal_stretches=(.95,1.03),tangential_stretch=.99)
    events=[]
    source_probe='manufactured:dynamic-source-forwarding-probe'
    original_check=WaterPhaseTransfer._check_interface_state
    original_assemble=WaterPhaseTransfer._assemble_transfer
    original_evaluate=FreeSolidSlab.evaluate
    original_auto=FreeSolidSlab.evaluate_autonomous
    def check(self,s):
        events.append('check')
        return original_check(self,s)
    def assemble(self,s,b):
        events.append('assemble')
        return original_assemble(self,s,b)
    def evaluate(self,s,t):
        events.append('base')
        result=original_evaluate(self,s,t)
        # Metadata-only routing probe; every actual physics field is unchanged.
        return replace(result,source_ids=result.source_ids+(source_probe,))
    def autonomous(self,s):
        events.append('base_autonomous')
        result=original_auto(self,s)
        return replace(result,source_ids=result.source_ids+(source_probe,))
    monkeypatch.setattr(WaterPhaseTransfer,'_check_interface_state',check)
    monkeypatch.setattr(WaterPhaseTransfer,'_assemble_transfer',assemble)
    monkeypatch.setattr(FreeSolidSlab,'evaluate',evaluate)
    monkeypatch.setattr(FreeSolidSlab,'evaluate_autonomous',autonomous)
    ordinary=op.evaluate(state,0.)
    assert events==['check','base','assemble']
    events.clear()
    autonomous_out=op.evaluate_autonomous(state)
    assert events==['check','base_autonomous','assemble']
    assert ordinary.cell_transfers==autonomous_out.cell_transfers
    for out in (ordinary,autonomous_out):
        _assert_unchanged_context(out)
        assert out.cell_transfers[0].rate_mol_s>0>out.cell_transfers[1].rate_mol_s
        assert np.any(out.rates.mechanical_rates_per_s!=0)
        # A clearly labelled manufactured provenance probe is absent from the
        # static configuration; it is not asserted to be a material source.
        dynamic=set(out.base_evaluation.source_ids)-set(op.source_ids)
        assert source_probe in dynamic and dynamic<=set(out.source_ids)
        for i,phase in enumerate(out.cell_transfers):
            base=out.base_evaluation
            delta=out.rates.reaction_species_mol_s[i]-base.rates.reaction_species_mol_s[i]
            assert F(float(delta[op.liquid_index]))+F(float(delta[op.water_vapor_index]))==0
            assert delta[op.water_vapor_index]==phase.rate_mol_s
            assert np.all(delta[[1,3]]==0)
            current=base.storage_states[i].mechanical
            pressure=F(float(state.amounts_mol[i,op.water_vapor_index]))*F(op.chemical.gas_constant_j_mol_k)*F(current.temperature_k)/F(current.gas_volume_m3)
            assert phase.vapor_partial_pressure_pa==float(pressure)
            assert phase.entropy_production_w_k>=0
    for name in ('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w','mechanical_rates_per_s'):
        np.testing.assert_array_equal(getattr(ordinary.rates,name),getattr(autonomous_out.rates,name))


def test_disabled_legal_free_host_forwards_context_without_querying_chemistry(ingredients,monkeypatch):
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    op=slab_transfer(ingredients,coefficients_mol_s_pa=(0.,0.))
    state=op.base_model.state_from_temperatures([[0.,.01,0.,2.],[0.,.008,0.,2.]],
        [300.,301.],normal_stretches=(.95,1.03),tangential_stretch=.99)
    def forbidden(*args,**kwargs):pytest.fail('disabled coefficient must not query chemistry')
    monkeypatch.setattr(WaterChemicalPotential,'equilibrium_at_liquid_tp',forbidden)
    monkeypatch.setattr(WaterChemicalPotential,'ideal_vapor',forbidden)
    out=op.evaluate_autonomous(state)
    assert all(d.status=='disabled' and d.rate_mol_s==0 for d in out.cell_transfers)
    _assert_unchanged_context(out)
    np.testing.assert_array_equal(out.rates.reaction_species_mol_s,out.base_evaluation.rates.reaction_species_mol_s)


def test_autonomous_entry_rejects_nonfree_host_before_evaluation(ingredients,monkeypatch):
    op=transfer(ingredients,coefficients_mol_s_pa=(0.,))
    state=op.base_model.state_from_temperatures([[0.,.01,0.]],[300.])
    def forbidden(*args,**kwargs):pytest.fail('unsupported autonomous host must be rejected first')
    monkeypatch.setattr(WaterPhaseTransfer,'_check_interface_state',forbidden)
    monkeypatch.setattr(RigidFluidHeat,'evaluate',forbidden)
    with pytest.raises(WaterPhaseTransferError,match='explicit_direct_free_slab_transfer_required'):
        op.evaluate_autonomous(state)


def test_unknown_dry_drive_requires_explicit_metastability_without_long_trajectory(ingredients,joined):
    base=joined_host(ingredients,joined,500.)
    strict=WaterPhaseTransfer(base_model=base,chemical=ingredients[2],coefficients_mol_s_pa=(1e-7,),
        coefficient_set_id='manufactured:dry-behavior',coefficient_version='1',
        coefficient_classification='manufactured_test_fixture',coefficient_source_ids=('manufactured:dry-behavior',),
        allow_manufactured=True,interface_modes=('depleted_no_nucleation',))
    state=base.state_from_temperatures([[2.,.01,0.,0.]],[502.])
    with pytest.raises(DomainExit,match='condensation_drive_unknown'):strict.evaluate(state,0.)
    out=replace(strict,dry_policy='metastable_no_nucleation').evaluate(state,0.)
    assert out.cell_transfers[0].status=='metastable_no_nucleation_condensation_drive_unknown'
    assert out.cell_transfers[0].rate_mol_s==0 and out.cell_transfers[0].hypothetical_equilibrium is None
    np.testing.assert_array_equal(out.rates.cell_power_w,out.base_evaluation.rates.cell_power_w)
    np.testing.assert_array_equal(out.rates.reaction_species_mol_s,out.base_evaluation.rates.reaction_species_mol_s)
