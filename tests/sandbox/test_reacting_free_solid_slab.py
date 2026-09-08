"""Manufactured chemistry in a genuinely free, current two-cell slab."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_dynamic_solid_storage import water,forbid_water_eos
from test_free_solid_slab import host
from test_reacting_deforming_solid_heat import reacting_host as prescribed_material
from sludge_sandbox.current_solid_storage import CurrentSolidStorage
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat


def reacting_host(water,*,order=1.,weights=10.,equal_volume=False):
    base=host(water)
    material=prescribed_material(water,constant=True,order=order,weights=weights,equal_volume=equal_volume)
    original=material.point_storages[0]
    points=tuple(CurrentSolidStorage(template=original.template,
        skeleton=replace(original.skeleton,reference_model=replace(original.skeleton.reference_model,
            reference=p.skeleton.reference,cell_index=i,viscosity_pa_s=1e6)),
        error_bounds=p.error_bounds,model_id=f'reacting-point-{i}',version='1',allow_manufactured=True,
        solid_inventory_regime='reacting_manufactured') for i,p in enumerate(base.point_storages))
    storages=tuple(p.template for p in points)
    transport=replace(base.base_model.transport,storages=tuple(s.fluid_template for s in storages))
    reactions=replace(material.base_model.solid_reactions,storages=storages)
    thermal=SolidFluidHeat(storages=storages,inventory_layout=material.inventory_layout,
        transport=transport,solid_reactions=reactions)
    return replace(base,base_model=thermal,point_storages=points,external_pressure_pa=101325.,
        solid_inventory_regime='reacting_manufactured',
        mechanical_regime='reduced_common_tangent_quasistatic_reacting_manufactured')


def initial(op):
    return op.state_from_temperatures([[0.,.01,0.,2.],[0.,.008,0.,2.]],[300.,301.],
        normal_stretches=(1.,1.),tangential_stretch=1.)


def test_current_reaction_volume_and_original_inverse_with_free_power(water,monkeypatch):
    op=reacting_host(water,order=2.)
    state=op.state_from_temperatures([[.2,.01,0.,1.8],[.1,.008,0.,1.9]],[300.,301.],
        normal_stretches=(.95,1.1),tangential_stretch=.99)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',lambda *a:pytest.fail('duplicate inverse'))
    out=op.evaluate(state,0.)
    assert out.free.zero_balance_enclosed
    assert out.qualification.startswith('manufactured_reacting') and not op.material_qualified
    for i,amount in enumerate((1.8,1.9)):
        storage=out.current_host.storages[i]
        assert out.current_host.solid_reactions.storages[i] is storage
        assert storage is out.total_inverses[i].state.current_storage
        assert out.total_inverses[i].thermal_inverse is out.storage_inverses[i]
        expected=F(.1)*F(amount)**2/F(float(out.geometry.volumes_m3[i]))
        actual=out.thermal_evaluation.reaction_cells[i].network_rates.extent_mol_s[0]
        assert abs(F(actual)-expected)<abs(expected)*F(1e-12)
        assert abs(F(actual)-F(.1)*F(amount)**2/F(.00014))>abs(expected)*F(.01)
        assert F(float(out.rates.reaction_species_mol_s[i,0]))+F(float(out.rates.reaction_species_mol_s[i,3]))==0
        assert out.rates.cell_power_w[i]==float(F(out.free.external_powers_w[i])+F(out.free.constraint_powers_w[i]))
    assert set(out.rates.cell_power_components_w)=={'external_traction','mechanical_constraint','body'}
    assert np.all(out.rates.cell_power_components_w['body']==0.)
    assert set(out.current_host.source_ids)<=set(out.source_ids)


def test_changed_composition_enters_total_energy_and_current_pore(water):
    op=reacting_host(water);start=initial(op)
    changed=replace(start,amounts_mol=[[.2,.01,0.,1.8],[.1,.008,0.,1.9]])
    out=op.evaluate(changed,0.)
    for i,(nb,gas,temp) in enumerate(((.2,.01,300.),(.1,.008,301.))):
        closed=out.storage_states[i]
        # uB-uA=-4 J/mol, recoverable interface derivative=3 J/mol.
        r=op.storages[i].fluid_template.mechanical.gas_constant_j_mol_k
        expected=temp+nb/(10+gas*(30-r))
        assert abs(closed.mechanical.temperature_k-expected)<1e-6
        assert abs(closed.solid_volume_m3-((2-nb)*2e-5+nb*1e-5))<1e-18
        assert abs(out.free.states[i].interface_energy_j-.3*(1+10*nb))<1e-13
    assert not np.array_equal(out.rates.mechanical_rates_per_s,op.evaluate(start,0.).rates.mechanical_rates_per_s)


def test_explicit_regime_source_binding_and_invalid_inventory(water):
    op=reacting_host(water);state=initial(op)
    with pytest.raises(ValueError,match='fixed_free_slab'):
        replace(op,solid_inventory_regime='fixed_solid')
    with pytest.raises(ValueError,match='regimes'):
        replace(op,mechanical_regime='reduced_common_tangent_quasistatic_fixed_solid')
    with pytest.raises(ValueError,match='regime'):
        replace(host(water),solid_inventory_regime='reacting_manufactured')
    with pytest.raises(ValueError):
        op.evaluate(replace(state,amounts_mol=[[0.,.01,0.,0.],[0.,.008,0.,2.]]),0.)
    with pytest.raises(ValueError,match='binding'):
        op.evaluate(replace(state,energy_model_identity=('wrong',)),0.)
    object.__setattr__(op.base_model.solid_reactions,'binding_id','changed')
    with pytest.raises(ValueError,match='runtime_base'):
        op.evaluate(state,0.)


def test_reacting_mode_without_network_has_no_inventory_or_extra_heat_source(water):
    op=reacting_host(water)
    op=replace(op,base_model=replace(op.base_model,solid_reactions=None))
    state=initial(op);out=op.evaluate(state,0.)
    assert np.all(out.rates.reaction_species_mol_s==0.)
    assert np.all(out.rates.cell_power_components_w['body']==0.)
    assert out.free.zero_balance_enclosed


def test_declared_kinetic_temperature_domain_is_enforced(water):
    from sludge_sandbox.integration import DomainExit
    op=reacting_host(water)
    state=op.state_from_temperatures([[0.,.01,0.,2.],[0.,.008,0.,2.]],[299.,301.],
        normal_stretches=(1.,1.),tangential_stretch=1.)
    with pytest.raises(DomainExit,match='temperature_out_of_kinetic_domain'):
        op.evaluate(state,0.)
