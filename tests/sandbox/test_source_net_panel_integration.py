"""Actual source adapter samples; artificial water seam and transport only.

Euler interior input is explicit, not an accepted physical trajectory. These
checks establish numerical interpolation/mapping, never event admission.
"""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_source_liquid_column import setup as liquid_setup, config
from test_programmed_source_wet_column import setup as furnace_setup
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.integration import ConservedState
from sludge_sandbox.source_net_panel import SavedSourceSample, build_source_panel


HM=F(1,8192)
END=F(1,4096)


def actual_samples(monkeypatch, mode, count):
    if mode=='closed':
        column,initial=liquid_setup(monkeypatch,count=count)
    else:
        column,initial=furnace_setup(monkeypatch,count=count)
        column=replace(column,base=replace(column.base,liquid_transport=config(count)))
    adapter=ExactSourceColumn(column)
    packed=adapter.pack(initial)
    first=adapter.evaluate(packed,T(F()))
    dn,du=first.rates.derivatives(packed)
    # One explicit Euler construction; preserve exact represented operands
    # until the single projection to binary64, and retain its packed state.
    amounts=np.array([[float(F(float(a))+HM*F(float(v))) for a,v in zip(row,rate)]
                      for row,rate in zip(packed.amounts_mol,dn)])
    energy=np.array([float(F(float(a))+HM*F(float(v))) for a,v in zip(packed.internal_energy_j,du)])
    interior_state=ConservedState(amounts,energy,packed.energy_model_identity)
    interior=adapter.evaluate(interior_state,T(HM))
    samples=(SavedSourceSample(packed,first,'original'),SavedSourceSample(interior_state,interior,'euler_interior'))
    kwargs=dict(operator_identity=adapter.operator_identity,energy_identity=adapter.energy_model_identity,
                fixed_dry_mass_kg=tuple(s.dry_mass_kg for s in column.storages))
    return samples,kwargs


def build(samples,kwargs):
    return build_source_panel(*samples,T(END),**kwargs)


def forbid_more_physics(monkeypatch):
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.water_properties import WaterProperties
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    def forbidden(*args,**kwargs):pytest.fail('panel operation requested additional physics')
    for owner,name in ((SourceWetStorage,'invert'),(SourceWetStorage,'evaluate'),
                       (WaterProperties,'state_tp'),(WaterChemicalPotential,'equilibrium_at_liquid_tp'),
                       (ExactSourceColumn,'evaluate')):
        monkeypatch.setattr(owner,name,forbidden)


@pytest.mark.parametrize('mode,count',[('closed',3),('open',1),('open',3)])
def test_actual_N_cell_affine_incidence_and_no_extra_physics(monkeypatch,mode,count):
    samples,kwargs=actual_samples(monkeypatch,mode,count)
    forbid_more_physics(monkeypatch)
    panel=build(samples,kwargs)
    panel.check();minima=panel.minima()
    assert panel.first is samples[0] and panel.interior is samples[1]
    assert len(panel.inventories)==4*count and len(panel.energies)==count and len(minima)==4*count
    assert panel.qualification=='saved_numerical_affine_panel_not_stage_or_event_acceptance'
    for j,sample in enumerate(samples):
        raw=sample.evaluation.source_evaluation
        for i in range(count):
            faces=raw.faces
            phase=F(raw.cells[i].phase.phase_water_mol_s)
            for species in range(4):
                key=(lambda f:F(getattr(f,'liquid_mol_s',0.))) if species==0 else (lambda f:F(f.gas_mol_s[species-1]))
                derivative=key(faces[i])-key(faces[i+1])+(-phase if species==0 else phase if species==3 else F())
                polynomial=panel.inventories[i*4+species]
                assert polynomial.linear+2*polynomial.quadratic*(F() if j==0 else HM)==derivative
            du=F(faces[i].energy_w)-F(faces[i+1].energy_w)
            assert panel.energies[i].linear+2*panel.energies[i].quadratic*(F() if j==0 else HM)==du
        water=sum((p.linear+2*p.quadratic*(F() if j==0 else HM) for p in panel.inventories if p.index in (0,3)),F())
        # Liquid boundaries are closed; vapor exchange may be open.
        assert water==F(raw.faces[0].gas_mol_s[2])-F(raw.faces[-1].gas_mol_s[2])
        assert sum((p.linear+2*p.quadratic*(F() if j==0 else HM) for p in panel.energies),F())==F(raw.faces[0].energy_w)-F(raw.faces[-1].energy_w)
    history=dict((key,(rate,acceleration)) for key,rate,acceleration in panel.shared_rate_history)
    assert len([k for k in history if k[0]=='face_mol'])==(count+1)*4


@pytest.mark.parametrize('corruption',['missing','wrong_time'])
def test_actual_program_boundary_time_is_required(monkeypatch,corruption):
    samples,kwargs=actual_samples(monkeypatch,'open',1)
    evaluation=samples[1].evaluation
    boundary=evaluation.source_evaluation.boundary
    boundary=None if corruption=='missing' else replace(boundary,time=T(HM+F(1,16384)))
    raw=replace(evaluation.source_evaluation,boundary=boundary)
    bad=replace(samples[1],evaluation=replace(evaluation,source_evaluation=raw))
    forbid_more_physics(monkeypatch)
    with pytest.raises(ValueError):build((samples[0],bad),kwargs)


@pytest.mark.parametrize('changes',[
    {'solid_kg_s':(0,)}, {'gas_mol_s':(0.,0.,0.)},
    {'chemical_reference_power_w':False}, {'phase_transfer_included':0},
])
def test_disabled_chemistry_exact_types_cannot_be_substituted(monkeypatch,changes):
    samples,kwargs=actual_samples(monkeypatch,'closed',3)
    e=samples[1].evaluation;raw=e.source_evaluation
    cell=replace(raw.cells[0],chemistry=replace(raw.cells[0].chemistry,**changes))
    modified=replace(raw,cells=(cell,*raw.cells[1:]))
    bad=replace(samples[1],evaluation=replace(e,source_evaluation=modified))
    forbid_more_physics(monkeypatch)
    with pytest.raises(ValueError):build((samples[0],bad),kwargs)


def test_complete_actual_source_record_is_bound(monkeypatch):
    samples,kwargs=actual_samples(monkeypatch,'closed',3)
    panel=build(samples,kwargs)
    forbid_more_physics(monkeypatch)
    # Full raw metadata changes while numerical arrays stay identical.
    object.__setattr__(samples[1].evaluation.source_evaluation,'source_ids',('altered-source-binding',))
    with pytest.raises(ValueError):panel.check()
    with pytest.raises(ValueError):panel.minima()
