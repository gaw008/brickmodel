"""Dry analytic Darcy/enthalpy face check; no tested face helper in oracle."""
from dataclasses import replace
from fractions import Fraction as F
import math
import numpy as np
import pytest
from test_dynamic_solid_storage import water, forbid_water_eos
from test_free_solid_slab import host
from test_rigid_storage import R


def oracle(amounts, temperatures, normals, tangent):
    n = tuple(map(F, normals)); t = F(tangent)
    widths = [F(.01)*v for v in n]
    dl, dr = [v/2 for v in widths]
    area = F(.014)*t*t
    pores = [F(.00014)*v*t*t-2*F(2e-5) for v in n]
    pressures = [F(a)*F(R)*F(T)/v for a,T,v in zip(amounts,temperatures,pores)]
    weight = dr/(dl+dr)
    pf = weight*pressures[0]+(1-weight)*pressures[1]
    tf = weight*F(temperatures[0])+(1-weight)*F(temperatures[1])
    # Serial mobilities and face EOS density, NOT upstream concentration.
    mobility = (dl+dr)/(dl/(F(1e-15)/F(1e-5))+dr/(F(3e-15)/F(2e-5)))
    velocity = mobility*(pressures[0]-pressures[1])/(dl+dr)
    flux = area*pf/(F(R)*tf)*velocity
    donor = 0 if velocity>0 else 1
    heat = flux*30*F(temperatures[donor])
    return pressures,flux,heat,area*F(amounts[donor])/pores[donor]*velocity


@pytest.mark.parametrize('amounts',[(.014,.006),(.006,.014)])
def test_current_geometry_darcy_face_and_donor_enthalpy(water,amounts):
    old=host(water)
    transport=replace(old.base_model.transport,permeability_m2=(1e-15,3e-15),
        viscosity_pa_s=(1e-5,2e-5),relative_permeability=(1.,1.),
        conductivities_w_m_k=(0.,0.),effective_diffusivities_m2_s={'fixture':(0.,0.)})
    op=replace(old,base_model=replace(old.base_model,transport=transport))
    normals=(.8,1.2);t=.9
    state=op.state_from_temperatures([[0.,amounts[0],2.],[0.,amounts[1],2.]],
        [299.,304.],normal_stretches=normals,tangential_stretch=t)
    # Independently decode T from total E and explicit fixed caloric/potential.
    temperatures=[]
    for i,n in enumerate(normals):
        ln,lt=math.log(n),math.log(t);theta=ln+2*lt
        recover=.00014*(500*theta*theta+400*((ln-theta/3)**2+2*(lt-theta/3)**2))+.0015*t*t
        temperatures.append((float(state.internal_energy_j[i])-recover+200004.)/(10+amounts[i]*(30-R)))
    pressures,flux,energy,wrong_density=oracle(amounts,temperatures,normals,t)
    out=op.evaluate(state,0.)
    actual=F(float(out.rates.face_species_mol_s[1,1]))
    carried=F(float(out.rates.face_energy_w[1]))
    assert abs(actual-flux)<abs(flux)*F(1e-8)
    assert abs(carried-energy)<abs(energy)*F(1e-8)
    assert actual*flux>0 and carried*flux>0
    for p,decoded in zip(pressures,out.storage_states):
        assert abs(float(p)-decoded.mechanical.pressure_pa)<1e-4
    # Negative controls must be distinguishable from the correct convention.
    _,reference_flux,reference_energy,_=oracle(amounts,temperatures,(1.,1.),1.)
    assert abs(reference_flux-flux)>abs(flux)*F(.01)
    assert abs(reference_energy-energy)>abs(energy)*F(.01)
    assert abs(wrong_density-flux)>abs(flux)*F(.01)
    assert np.all(out.rates.face_species_mol_s[[0,2]]==0.)
    assert np.all(out.rates.face_species_mol_s[:,[0,2]]==0.)
    assert out.rates.face_energy_w[0]==out.rates.face_energy_w[-1]==0.
    dn,du=out.rates.derivatives(state)
    assert F(float(dn[0,1]))==-actual and F(float(dn[1,1]))==actual
    for i,sign in enumerate((-1,1)):
        assert abs(F(float(du[i]))-F(float(out.rates.cell_power_w[i]))-sign*carried)<F(1e-12)
