"""Explicit complete inventory layout for solid/fluid transport."""
import pytest
from sludge_sandbox.solid_fluid_heat import InventoryLayout,SolidFluidHeatError


def test_arbitrary_column_order_is_explicit():
    layout=InventoryLayout(species_order=('quartz','H2O','liquid','N2'),liquid_column_id='liquid',
        gas_species_order=('N2','H2O'),solid_species_order=('quartz',))
    assert layout.liquid_index==2
    assert layout.gas_inventory([3,2,1,4])=={'N2':4.,'H2O':2.}
    assert layout.solid_inventory([3,2,1,4])=={'quartz':3.}

@pytest.mark.parametrize('order',[('liquid','N2'),('liquid','N2','solid','unknown'),('liquid','N2','solid','solid')])
def test_incomplete_or_duplicate_layout_rejected(order):
    with pytest.raises(SolidFluidHeatError):
        InventoryLayout(species_order=order,liquid_column_id='liquid',gas_species_order=('N2',),solid_species_order=('solid',))

from dataclasses import replace
import numpy as np
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat,SolidFluidHeatEvaluation
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.integration import IntegrationPolicy,integrate
from test_water_phase_transfer import transfer,DATA
from test_incompressible_solid import phase,caloric

@pytest.fixture(scope='module')
def ingredients():return load_water_properties(DATA),IdealWaterVapor(DATA),WaterChemicalPotential(DATA)

def solid_host(ingredients,*,cells=1,cp=50.,heat=.1):
    from sludge_sandbox.solid_fluid_storage import SolidFluidStorage
    template=transfer(ingredients).base_model
    if cells==2:
        template=replace(template,storages=template.storages*2,cell_widths_m=(.01,)*2,
            conductivities_w_m_k=(heat,)*2,effective_diffusivities_m2_s={'fixture':(1e-6,)*2,'H2O':(1e-6,)*2},
            permeability_m2=(0.,)*2,relative_permeability=(1.,)*2,viscosity_pa_s=(1e-5,)*2,
            temperature_brackets_k=((295.,310.),)*2)
    solid=phase(caloric=caloric(coefficients=(cp,0.,0.,0.,0.,-100.,0.,-100.)),molar_volume_m3_mol=1e-6,declared_v_error_m3_mol=1e-18)
    storages=tuple(SolidFluidStorage(fluid_template=s,solid_phases={'fixture_solid':solid},
        bulk_volume_m3=.0001,bulk_volume_error_m3=1e-18,
        geometry_id='manufactured:bulk',geometry_version='1',geometry_classification='manufactured_test_fixture',
        geometry_source_ids=('manufactured:bulk',),allow_manufactured=True) for s in template.storages)
    layout=InventoryLayout(species_order=('fixture_solid','H2O','H2O_liquid','fixture'),
        liquid_column_id='H2O_liquid',gas_species_order=('fixture','H2O'),solid_species_order=('fixture_solid',))
    return SolidFluidHeat(storages=storages,inventory_layout=layout,transport=template)


def test_real_two_cell_face_preserves_immobile_columns_and_energy(ingredients):
    host=solid_host(ingredients,cells=2)
    initial=host.state_from_temperatures([[2.,1e-5,0.,.01],[3.,4e-5,0.,.02]],[300.,301.])
    result=host.evaluate(initial,0)
    assert type(result) is SolidFluidHeatEvaluation
    assert np.all(result.rates.face_species_mol_s[:,[0,2]]==0)
    assert result.rates.face_species_mol_s[1,3]!=0
    assert result.rates.face_energy_w[1]!=0
    assert result.storage_inverses[0].state is result.storage_states[0]
    run=integrate(initial,host,start_s=0,end_s=.001,policy=IntegrationPolicy(
        initial_step_s=.001,maximum_step_s=.001,minimum_step_s=1e-10,relative_tolerance=1e-7,
        amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
        amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=10,maximum_rejections=10,maximum_wall_seconds=90))
    assert run.status=='completed',run.reason
    for state in run.states:
        assert np.array_equal(state.amounts_mol[:,[0,2]],initial.amounts_mol[:,[0,2]])
        assert state.amounts_mol.sum(axis=0)==pytest.approx(initial.amounts_mol.sum(axis=0),rel=0,abs=1e-12)
        assert sum(state.internal_energy_j)==pytest.approx(sum(initial.internal_energy_j),rel=0,abs=1e-7)


def test_template_identity_and_bulk_geometry_gate(ingredients):
    host=solid_host(ingredients)
    with pytest.raises(SolidFluidHeatError,match='template_identity'):
        replace(host,transport=replace(host.transport,storages=(replace(host.transport.storages[0]),)))
    with pytest.raises(SolidFluidHeatError,match='bulk_geometry'):
        replace(host,transport=replace(host.transport,face_area_m2=.02))


def test_solid_domain_exit_is_preserved(ingredients):
    from sludge_sandbox.integration import DomainExit
    host=solid_host(ingredients)
    solid=host.storages[0].solid_phases['fixture_solid']
    solid=replace(solid,caloric=replace(solid.caloric,temperature_range_k=(301.,500.)))
    host=replace(host,storages=(replace(host.storages[0],solid_phases={'fixture_solid':solid}),))
    with pytest.raises(DomainExit,match='solid_temperature_out_of_domain'):
        host.state_from_temperatures([[2.,1e-5,0.,.01]],[300.])

@pytest.mark.parametrize('liquid',[[],None,' liquid '])
def test_invalid_liquid_label_has_configuration_error(liquid):
    with pytest.raises(SolidFluidHeatError):
        InventoryLayout(species_order=('liquid','gas','solid'),liquid_column_id=liquid,
            gas_species_order=('gas',),solid_species_order=('solid',))
