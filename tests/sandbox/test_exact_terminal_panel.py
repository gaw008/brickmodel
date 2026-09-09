from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState,Rates,IntegrationPolicy,IntegrationError
from sludge_sandbox.exact_event_clock import ExactEventTime as T

import sludge_sandbox.exact_terminal_panel as m


def policy():
    return IntegrationPolicy(initial_step_s=.1,maximum_step_s=1.,minimum_step_s=1e-12,relative_tolerance=1e-7,
        amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-10,amount_scale_mol=1.,energy_scale_j=1.,
        maximum_steps=20,maximum_rejections=20,maximum_wall_seconds=10.,stretch_absolute_tolerance=1e-12,stretch_scale=1.)


def data():
    s=ConservedState([[10.,2.],[8.,3.]],[10.,20.],mechanical_stretches=[1.,2.,3.])
    a=Rates([[1.,0.],[.5,0.],[0.,0.]],[2.,1.,0.],[[-1.,1.],[-.5,.5]],[3.,4.],{'body':[2.,3.],'external_traction':[1.,1.]},mechanical_rates_per_s=[.1,.2,.3])
    b=Rates([[2.,0.],[1.,0.],[0.,0.]],[4.,2.,0.],[[-2.,2.],[-1.,1.]],[6.,8.],{'body':[4.,6.],'external_traction':[2.,2.]},mechanical_rates_per_s=[.2,.4,.6])
    return s,a,b


def call(s,a,b,origin=F()):
    return m.build_exact_affine_panel(s,a,b,start=T(origin),midpoint=T(origin+F(1,4)),end=T(origin+F(1,2)),policy=policy(),liquid_index=0,selected_cell=0,wet_cells=(0,1),source_binding=('caller-reviewed-samples',))


def test_hand_integrals_all_fields_translation_and_immutable():
    s,a,b=data();p=call(s,a,b);translated=call(s,a,b,F(10**12))
    # b=2a at hmid=.25 => integral at .5 is exactly a for represented a,b.
    for key,rkey in [('face_species_mol','face_species_mol_s'),('face_energy_j','face_energy_w'),('reaction_species_mol','reaction_species_mol_s'),('cell_work_j','cell_power_w')]:
        np.testing.assert_array_equal(getattr(p.ledger,key),getattr(a,rkey))
        np.testing.assert_array_equal(getattr(p.ledger,key),getattr(translated.ledger,key))
    np.testing.assert_array_equal(p.raw_state.amounts_mol,[[9.5,3.],[8.,3.5]])
    np.testing.assert_array_equal(p.raw_state.internal_energy_j,[14.,25.])
    np.testing.assert_array_equal(p.raw_state.mechanical_stretches,[1.1,2.2,3.3])
    for key in a.cell_power_components_w:
        np.testing.assert_array_equal(p.ledger.cell_work_components_j[key],a.cell_power_components_w[key])
        assert p.ledger.component_quadrature_roundoff_j[key]==(F(),F())
    assert p.ledger.stretch_quadrature_roundoff==(F(),F(),F())
    with pytest.raises(ValueError):p.raw_state.amounts_mol[0,0]=0


@pytest.mark.parametrize('mechanical',[False,True])
def test_positive_endpoint_does_not_hide_negative_interior(mechanical):
    s,a,b=data()
    # n(t)=.1-2t+4t²: both endpoints .1, interior -.15.
    if mechanical:
        s=replace(s,mechanical_stretches=[.1,2.,3.]);a=replace(a,mechanical_rates_per_s=[-2.,0.,0.]);b=replace(b,mechanical_rates_per_s=[0.,0.,0.])
    else:
        s=replace(s,amounts_mol=[[10.,.1],[8.,3.]])
        a=replace(a,reaction_species_mol_s=[[-1.,-2.],[-.5,.5]])
        b=replace(b,reaction_species_mol_s=[[-2.,0.],[-1.,1.]])
    with pytest.raises(IntegrationError,match='polynomial'):call(s,a,b)


def test_competing_liquid_zero_refused_selected_zero_allowed():
    s=ConservedState([[1.],[1.]],[0.,0.])
    r=Rates(np.zeros((3,1)),np.zeros(3),[[-2.],[-2.]],np.zeros(2))
    with pytest.raises(IntegrationError,match='polynomial'):call(s,r,r)
    r=replace(r,reaction_species_mol_s=[[-2.],[-1.]])
    out=m.build_exact_affine_panel(s,r,r,start=T(F()),midpoint=T(F(1,4)),end=T(F(1,2)),policy=policy(),liquid_index=0,selected_cell=0,wet_cells=(0,1),source_binding=('labels-not-proof',))
    assert out.raw_state.amounts_mol[0,0]==0


def test_shapes_schema_and_time_refusal():
    s,a,b=data()
    with pytest.raises(IntegrationError,match='schema'):call(s,a,replace(b,cell_power_components_w=None))
    with pytest.raises(IntegrationError,match='shape'):call(s,a,replace(b,mechanical_rates_per_s=[1.,2.]))
    with pytest.raises(IntegrationError,match='times'):
        m.build_exact_affine_panel(s,a,b,start=T(F()),midpoint=T(F(1)),end=T(F(1,2)),policy=policy(),liquid_index=0,selected_cell=0,wet_cells=(0,1),source_binding=('x',))
