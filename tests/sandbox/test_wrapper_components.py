"""Explicit manufactured wiring instrumentation, not EOS/material validation.

Constructors are deliberately not invoked here; actual evaluate methods run on
controlled collaborators. Production type/source admission is not changed.
"""
from types import SimpleNamespace as NS
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState,Rates
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat


def instance(cls,**fields):
    obj=object.__new__(cls)
    for k,v in fields.items():object.__setattr__(obj,k,v)
    return obj


@pytest.mark.parametrize('parts',[None,{'body':[3.]}])
def test_water_real_evaluate_keeps_power_while_adding_phase_inventory(parts):
    r=Rates([[0,0],[0,0]],[0,0],[[0,0]],[3],parts)
    closed=NS(mechanical=NS(temperature_k=300.,gas_volume_m3=1.,liquid_pressure_pa=1e5))
    b=NS(rates=r,storage_states=(closed,))
    base=NS(_check_state=lambda s:None,evaluate=lambda s,t:b,species_order=('liquid','H2O'),source_ids=())
    chemical=NS(source_ids=(),gas_constant_j_mol_k=8.,equilibrium_at_liquid_tp=lambda t,p:
                NS(equilibrium_partial_pressure_pa=1.))
    op=instance(WaterPhaseTransfer,base_model=base,chemical=chemical,
        coefficients_mol_s_pa=(.1,),interface_modes=('existing_liquid',),dry_policy='strict',
        coefficient_set_id='manufactured-wiring',coefficient_version='1',
        coefficient_classification='manufactured_test_fixture',coefficient_source_ids=())
    out=op.evaluate(ConservedState([[1,0]],[1]),0.)
    assert out.base_evaluation is b
    assert np.array_equal(out.rates.reaction_species_mol_s,[[-.1,.1]])
    assert out.rates.cell_power_w[0]==3
    assert (out.rates.cell_power_components_w is None)==(parts is None)
    if parts:assert out.rates.cell_power_components_w['body'][0]==3


@pytest.mark.parametrize('parts',[None,{'body':[3.]}])
def test_program_real_evaluate_keeps_power_and_distinct_face_enthalpy(monkeypatch,parts):
    r=Rates([[0,0],[0,0]],[0,0],[[0,0]],[3],parts)
    b=NS(rates=r,gas_states=(NS(temperature_k=300.),))
    template=NS(gas_phases={'H2O':NS(metadata=NS(molar_mass_kg_mol=.018))},
                mechanical=NS(gas_constant_j_mol_k=8.))
    transport=NS(_face=lambda *args:NS(net_mol_s={'H2O':.25}),_enthalpy=lambda exchange:7.)
    base=NS(evaluate=lambda s,t:b,storages=(NS(fluid_template=template),),transport=transport,
            gas_species_order=('H2O',),species_order=('liquid','H2O'))
    boundary=NS(total_pressure_pa=1e5,gas_temperature_k=400.,mole_fractions={'H2O':1.})
    op=instance(ProgrammedSolidFluidHeat,base_model=base,program=NS(at=lambda t:boundary))
    monkeypatch.setattr(ProgrammedSolidFluidHeat,'_surface',lambda *args:(350.,None,2.,0.,0.,0,'fixture'))
    out=op.evaluate(ConservedState([[1,0]],[1]),0.)
    assert out.base_evaluation is b
    assert out.rates.face_species_mol_s[-1,1]==.25
    assert out.rates.face_energy_w[-1]==5
    assert out.rates.cell_power_w[0]==3
    assert (out.rates.cell_power_components_w is None)==(parts is None)
    if parts:assert out.rates.cell_power_components_w['body'][0]==3
