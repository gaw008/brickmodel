"""Frozen old-host regression; manufactured liquid seam, no native EOS."""
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_transport import setup
from sludge_sandbox import mass_wet_transport as module
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.integration import DomainExit
from sludge_sandbox.water_properties import WaterDomainError


def test_original_whole_observation_identity_and_short_trajectory(monkeypatch):
    pair, states = setup(monkeypatch)
    assert pair._identity == '8747dca55f36484298d63e3a2cffa485f61bf78bade2b57dc5194a736da9b692'
    assert _digest(pair.evaluate(states)) == '7161522281168d26ed72e1453ee9922ad7cd3d3093f557be628df322ed45ea04'
    run = module.integrate_wet_pair(pair, states, duration_s=.001, steps=1)
    assert run.status == 'completed', run.reason
    assert _digest(replace(run, elapsed_seconds=0.)) == 'f27c3bb25d275755cefb990b269784bba9b43778f3c6c28d0bf74c7cfcb65f49'


def point_case(monkeypatch, *, liquid=.2, vapor=1e-8):
    pair, states = setup(monkeypatch)
    st = pair.storages[0]
    s = replace(states[0], liquid_water_mol=liquid, gas_amounts_mol=(.2,.2,vapor))
    return pair, st.evaluate(s,305.)


def phase_args(pair, point):
    return dict(chemical=pair.chemical, inverse_point=point,
                water_vapor_mol=point.fluid.mechanical.gas_inventory_mol['H2O'],
                transfer_coefficient=1e-8, mode='existing_liquid')


def test_shared_calls_and_returned_face_components(monkeypatch):
    pair, states = setup(monkeypatch)
    phase_calls, face_calls = [], []
    phase, face = module.evaluate_wet_phase, module.evaluate_wet_face
    def observe_phase(*args, **kwargs):
        out = phase(*args, **kwargs); phase_calls.append(out); return out
    def observe_face(*args, **kwargs):
        out = face(*args, **kwargs); face_calls.append(out); return out
    monkeypatch.setattr(module,'evaluate_wet_phase',observe_phase)
    monkeypatch.setattr(module,'evaluate_wet_face',observe_face)
    out = pair.evaluate(states)
    assert len(phase_calls)==2 and len(face_calls)==1
    for row, result in zip(out.cells,phase_calls):
        for name in result.__dataclass_fields__:
            assert getattr(row,name)==getattr(result,name)
    for name in face_calls[0].__dataclass_fields__:
        assert getattr(out,name)==getattr(face_calls[0],name)
    assert phase_calls[0].phase_water_mol_s>0>phase_calls[1].phase_water_mol_s


@pytest.mark.parametrize('changes', [
    {'mode':'unknown'}, {'mode':True}, {'water_vapor_mol':True},
    {'water_vapor_mol':-.1}, {'water_vapor_mol':F(1,10)},
    {'transfer_coefficient':float('nan')}, {'transfer_coefficient':-1.},
    {'water_vapor_mol':.1}, {'chemical':object()},
])
def test_invalid_phase_inputs(monkeypatch,changes):
    pair, point = point_case(monkeypatch)
    with pytest.raises(ValueError):
        module.evaluate_wet_phase(**dict(phase_args(pair,point),**changes))


def test_zero_vapor_dry_modes_and_query_failure_categories(monkeypatch):
    pair, wet = point_case(monkeypatch,vapor=0.)
    out = module.evaluate_wet_phase(**phase_args(pair,wet))
    assert out.phase_water_mol_s>0 and out.water_partial_pressure_pa==0
    assert out.chemical_driving_force_j_mol is out.entropy_production_w_k is None
    with pytest.raises(DomainExit,match='dry_interface_requires_exact_zero_liquid'):
        module.evaluate_wet_phase(**dict(phase_args(pair,wet),mode='depleted_no_nucleation'))
    pair, dry = point_case(monkeypatch,liquid=0.,vapor=0.)
    args = dict(phase_args(pair,dry),mode='depleted_no_nucleation')
    assert module.evaluate_wet_phase(**args).phase_water_mol_s==0
    with pytest.raises(DomainExit,match='existing_liquid_interface_requires_positive_inventory'):
        module.evaluate_wet_phase(**phase_args(pair,dry))
    def unknown(*args,**kwargs):raise WaterDomainError('chemical_domain_probe')
    monkeypatch.setattr(module.WaterChemicalPotential,'equilibrium_at_liquid_tp',unknown)
    with pytest.raises(DomainExit,match='dry_interface_condensation_drive_unknown'):
        module.evaluate_wet_phase(**args)
    with pytest.raises(WaterDomainError,match='chemical_domain_probe'):
        module.evaluate_wet_phase(**phase_args(pair,wet))
    def failed(*args,**kwargs):raise RuntimeError('chemical_backend_probe')
    monkeypatch.setattr(module.WaterChemicalPotential,'equilibrium_at_liquid_tp',failed)
    with pytest.raises(RuntimeError,match='chemical_backend_probe'):
        module.evaluate_wet_phase(**args)


def test_dry_supersaturation_and_zero_coefficient_still_check(monkeypatch):
    pair, dry = point_case(monkeypatch,liquid=0.,vapor=.07)
    with pytest.raises(DomainExit,match='dry_interface_condensation_requires_unsupported_nucleation'):
        module.evaluate_wet_phase(**dict(phase_args(pair,dry),mode='depleted_no_nucleation',transfer_coefficient=0.))


def test_source_guard_is_shared_and_not_weakened(monkeypatch):
    pair, _ = setup(monkeypatch)
    module.check_thermal_chemical_sources(pair.storages[0],pair.chemical)
    monkeypatch.setattr(module.WaterChemicalPotential,'gas_constant_j_mol_k',pair.chemical.gas_constant_j_mol_k+1.)
    with pytest.raises(ValueError,match='thermal_chemical_source_mismatch'):
        module.check_thermal_chemical_sources(pair.storages[0],pair.chemical)


def test_face_layout_rejected(monkeypatch):
    pair, states = setup(monkeypatch); gases = pair.evaluate(states).gas_states
    args=dict(face=pair.face,gas_states=gases,gas_ids=pair.storages[0].gas_ids,
              gas_phases=pair.storages[0].fluid_template.gas_phases)
    for changes in ({'gas_states':gases[:1]}, {'gas_ids':('O2','N2')}, {'face':object()}, {'gas_phases':{}}):
        with pytest.raises(ValueError):module.evaluate_wet_face(**dict(args,**changes))


@pytest.mark.parametrize('corruption', ['swap','fake','fake_leaf','mass','R','reference','basis'])
def test_face_caloric_binding_rejected_before_enthalpy_callback(monkeypatch,corruption):
    from types import SimpleNamespace
    from sludge_sandbox.phase_storage import IdealGasPhase
    from sludge_sandbox.thermochemistry import ShomateSegment
    pair, states = setup(monkeypatch)
    gases=pair.evaluate(states).gas_states
    phases=dict(pair.storages[0].fluid_template.gas_phases)
    if corruption=='swap':phases['O2'],phases['N2']=phases['N2'],phases['O2']
    elif corruption=='fake':phases['O2']=SimpleNamespace(_curve=SimpleNamespace(enthalpy_j_mol=lambda t:pytest.fail('fake callback')))
    elif corruption=='fake_leaf':
        fake=SimpleNamespace(**vars(phases['O2']._curve))
        fake.enthalpy_j_mol=lambda t:pytest.fail('fake leaf callback')
        object.__setattr__(phases['O2'].caloric,'segments',(fake,))
    elif corruption=='mass':phases['O2']=replace(phases['O2'],molar_mass_kg_mol=.031)
    elif corruption=='R':
        gas=phases['O2'].caloric
        object.__setattr__(gas,'segments',tuple(replace(s,gas_constant_j_mol_k=s.gas_constant_j_mol_k+1.) for s in gas.segments))
    else:
        original=IdealGasPhase.metadata.fget
        def metadata(self):
            value=original(self)
            return replace(value,**{('energy_reference_id' if corruption=='reference' else 'molar_basis_id'):'wrong'})
        monkeypatch.setattr(IdealGasPhase,'metadata',property(metadata))
    def forbidden(*args,**kwargs):pytest.fail('enthalpy callback before complete face validation')
    monkeypatch.setattr(ShomateSegment,'enthalpy_j_mol',forbidden)
    with pytest.raises(ValueError):
        module.evaluate_wet_face(pair.face,gases,pair.storages[0].gas_ids,phases)
