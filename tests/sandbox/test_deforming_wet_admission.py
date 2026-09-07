"""No water EOS; actual dry total inverse/current surface admission."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_deforming_solid_heat import host
from test_rigid_storage import water
from test_programmed_solid_fluid_heat import program
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.integration import ConservedState


def wrapped(water):
    base=host(water,isotropic=True)
    transport=replace(base.base_model.transport,conductivities_w_m_k=(1.,),permeability_m2=(1e-15,))
    fixed=replace(base.base_model,transport=transport)
    base=replace(base,base_model=fixed)
    boundary=program(knot_times_s=(0.,.25,.75,1.),gas_temperature_k=(320.,)*4,
        total_pressure_pa=(4e5,)*4,species_order=('fixture',),mole_fractions=((1.,),)*4)
    return ProgrammedSolidFluidHeat(base_model=base,program=boundary,convection_w_m2_k=20.,emissivity=0.,
        stefan_boltzmann_w_m2_k4=5.670374419e-8,coefficient_set_id='manufactured-film',coefficient_version='1',
        coefficient_classification='manufactured',coefficient_source_ids=('manufactured-film',),
        surface_policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=200),allow_manufactured=True)


def test_actual_current_halfcell_surface_single_inverse_and_original_errors(water,monkeypatch):
    op=wrapped(water)
    monkeypatch.setattr(type(water),'state_tp',lambda *a,**k:pytest.fail('water EOS forbidden'))
    state=op.base_model.state_from_temperatures([[0.,.01,2.]],[300.],time_s=.5)
    cls=type(op.base_model.point_storages[0]);old=cls.temperature_from_total_energy;calls=[]
    def counted(self,*a,**k):calls.append(1);return old(self,*a,**k)
    monkeypatch.setattr(cls,'temperature_from_total_energy',counted)
    out=op.evaluate(state,.5)
    assert len(calls)==1
    actual=out.base_evaluation
    area=.014*.95**2;width=.01*.95
    expected=area*20/(width/2+1/20)
    assert out.conductive_into_cell_w==pytest.approx(expected,rel=0,abs=1e-8)
    assert out.storage_states is actual.thermal_evaluation.storage_states
    assert out.storage_inverses is actual.thermal_evaluation.storage_inverses
    assert out.storage_inverses[0].temperature_error_bound_k==actual.total_inverses[0].temperature_error_bound_k
    assert out.rates.face_species_mol_s[-1,1]<0
    # Independent constant Cp fixture enthalpy is Cp*T at the inflowing reservoir.
    assert out.rates.face_energy_w[-1]==pytest.approx(out.rates.face_species_mol_s[-1,1]*30*320-expected,rel=0,abs=1e-8)
    assert set(out.rates.cell_power_components_w)=={'elastic','interface','dissipation','pore','body'}
    assert np.array_equal(out.rates.cell_power_w,actual.rates.cell_power_w)
    assert state.energy_model_identity==op.base_model.energy_model_identity


def test_explicit_type_tag_sources_and_duplicate_boundary_guards(water):
    op=wrapped(water)
    with pytest.raises(ValueError):replace(op,base_model=object())
    with pytest.raises(ValueError):replace(op,allow_manufactured=False)
    with pytest.raises(ValueError):replace(op,coefficient_source_ids=())
    state=op.base_model.state_from_temperatures([[0.,.01,2.]],[300.],time_s=0.)
    with pytest.raises(ValueError):op._check_state(ConservedState(state.amounts_mol,state.internal_energy_j))
    badfixed=replace(op.base_model.base_model,transport=replace(op.base_model.base_model.transport,outer_surface_temperature_k=300.,outer_heat_source_ids=('manufactured-existing',)))
    with pytest.raises(ValueError):replace(op,base_model=replace(op.base_model,base_model=badfixed))


def test_program_motion_knot_union_validates_both_domains(water):
    op=wrapped(water);base=op.base_model;p=base.point_storages[0]
    motion=replace(p.motion,knot_times_s=(0.,.5,1.),normal_stretches_at_knots=((1.,),(.95,),(.9,)),
                   tangential_stretches_at_knots=(1.,.95,.9))
    op=replace(op,base_model=replace(base,point_storages=(replace(p,motion=motion),)))
    assert op.breakpoints_s(0.,1.)==(.25,.5,.75)
    with pytest.raises(ValueError):op.breakpoints_s(-.1,1.)
    short=replace(op.program,knot_times_s=(0.,.25,.75,.9))
    with pytest.raises(ValueError):replace(op,program=short).breakpoints_s(0.,1.)
    shorter_motion=replace(motion,knot_times_s=(0.,.5,.9))
    shorter_base=replace(base,point_storages=(replace(p,motion=shorter_motion),))
    with pytest.raises(ValueError):replace(op,base_model=shorter_base).breakpoints_s(0.,1.)


def water_capable_host(water):
    """Zero-H2O manufactured gas column; not an admitted phase-change material."""
    from sludge_sandbox.phase_storage import IdealGasPhase
    from sludge_sandbox.solid_fluid_heat import InventoryLayout
    base=host(water);point=base.point_storages[0];old=point.template.fluid_template
    caloric=replace(old.gas_phases['fixture'].caloric,species_id='H2O')
    gas=IdealGasPhase(caloric,water.reference.molar_mass_kg_mol,0,('nist-codata-2022',))
    fluid=replace(old,mechanical=replace(old.mechanical,gas_species_ids=('fixture','H2O')),
        gas_phases=dict(old.gas_phases)|{'H2O':gas},envelope=replace(old.envelope,
            gas_u_error_j_mol=dict(old.envelope.gas_u_error_j_mol)|{'H2O':1e-9},
            gas_cv_lower_j_mol_k=dict(old.envelope.gas_cv_lower_j_mol_k)|{'H2O':20.}))
    storage=replace(point.template,fluid_template=fluid)
    transport=replace(base.base_model.transport,storages=(fluid,),gas_species_order=('fixture','H2O'),
        effective_diffusivities_m2_s={'fixture':(0.,),'H2O':(0.,)})
    fixed=replace(base.base_model,storages=(storage,),transport=transport,
        inventory_layout=InventoryLayout(species_order=('liquid','fixture','fixture_solid','H2O'),
            liquid_column_id='liquid',gas_species_order=('fixture','H2O'),solid_species_order=('fixture_solid',)))
    return replace(base,base_model=fixed,point_storages=(replace(point,template=storage),))


def disabled_water_wrapper(water,execution):
    """Explicit constructor-bypassed chemical sentinel, NEVER queried; K=0 only.

    This proves routing/unchanged power, not real chemical model admission.
    """
    from types import SimpleNamespace
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
    chemical=object.__new__(WaterChemicalPotential)
    object.__setattr__(chemical,'water',water)
    object.__setattr__(chemical,'vapor',SimpleNamespace(source_ids=('manufactured-unused-sentinel',)))
    return WaterPhaseTransfer(base_model=execution,chemical=chemical,coefficients_mol_s_pa=(0.,),
        coefficient_set_id='manufactured-disabled',coefficient_version='1',
        coefficient_classification='manufactured_test_fixture',coefficient_source_ids=('manufactured-disabled',),
        allow_manufactured=True)


@pytest.mark.parametrize('programmed',[False,True])
def test_disabled_phase_routes_true_total_context_without_eos(water,monkeypatch,programmed):
    base=water_capable_host(water);execution=base
    if programmed:
        proto=wrapped(water)
        boundary=replace(proto.program,species_order=('fixture','H2O'),mole_fractions=((1.,0.),)*4)
        execution=replace(proto,base_model=base,program=boundary)
    op=disabled_water_wrapper(water,execution)
    monkeypatch.setattr(type(water),'state_tp',lambda *a,**k:pytest.fail('water EOS forbidden'))
    state=base.state_from_temperatures([[0.,.01,2.,0.]],[300.],time_s=.5)
    out=op.evaluate(state,.5)
    assert out.cell_transfers[0].rate_mol_s==0
    assert op.interface_modes is None and op.interfaces==('existing_liquid',)
    assert op._thermal_host is base.base_model
    assert op._deforming_host is base
    assert np.array_equal(out.rates.cell_power_w,out.base_evaluation.rates.cell_power_w)
    assert set(out.rates.cell_power_components_w)=={'elastic','interface','dissipation','pore','body'}
    assert op.breakpoints_s(0.,1.)==execution.breakpoints_s(0.,1.)
    assert state.energy_model_identity==base.energy_model_identity
    # Manufactured H2O caloric is NOT allowed into the active chemical path.
    with pytest.raises(ValueError,match='matching_ideal_water'):
        replace(op,coefficients_mol_s_pa=(1e-6,))
    with pytest.raises(ValueError,match='manufactured'):
        replace(op,allow_manufactured=False)


def test_old_fixed_path_none_matches_actual_old_evaluate(water):
    import ast
    from pathlib import Path
    import sludge_sandbox.programmed_solid_fluid_heat as module
    original=Path(__file__).resolve().parents[2]/'docs/sandbox/research/deforming-wet-admission/baseline/programmed_solid_fluid_heat.py'
    tree=ast.parse(original.read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='ProgrammedSolidFluidHeat')
    method=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='evaluate')
    namespace=dict(vars(module));exec(compile(ast.Module(body=[method],type_ignores=[]),str(original),'exec'),namespace)
    proto=wrapped(water);op=replace(proto,base_model=proto.base_model.base_model)
    state=op.base_model.state_from_temperatures([[0.,.01,2.]],[300.])
    before=namespace['evaluate'](op,state,.5);after=op.evaluate(state,.5)
    for field in ('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w'):
        assert np.array_equal(getattr(before.rates,field),getattr(after.rates,field))
    assert before.rates.cell_power_components_w is after.rates.cell_power_components_w is None
    assert op.breakpoints_s(0.,1.)==(.25,.75)


def test_active_chemical_core_and_dry_policy_match_pre_admission_source():
    """Static regression complements no-EOS tests; does not simulate active water."""
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    import sludge_sandbox.water_phase_transfer as actual_module
    def cls(path):return next(x for x in ast.parse(path.read_text()).body if isinstance(x,ast.ClassDef) and x.name=='WaterPhaseTransfer')
    before=cls(root/'docs/sandbox/research/deforming-wet-admission/baseline/water_phase_transfer.py')
    after=cls(Path(actual_module.__file__))
    def method(c,name):return next(x for x in c.body if isinstance(x,ast.FunctionDef) and x.name==name)
    # evaluate and dry chemistry are wholly unchanged: exact AST, including
    # source direction/zero-vapor/finite chemistry/heat-free component forwarding.
    for name in ('evaluate','_dry_diagnostic','with_depleted_cells'):
        assert ast.dump(method(before,name),include_attributes=False)==ast.dump(method(after,name),include_attributes=False)
    def matching_loop(c):
        constructor=method(c,'__post_init__')
        return next(x for x in constructor.body if isinstance(x,ast.For) and isinstance(x.target,ast.Tuple)
                    and [t.id for t in x.target.elts]==['storage','k','mode'])
    assert ast.dump(matching_loop(before),include_attributes=False)==ast.dump(matching_loop(after),include_attributes=False)


def test_compressed_current_pore_template_is_same_inverse_context(water,monkeypatch):
    base=host(water,isotropic=True);p=base.point_storages[0]
    reference=replace(p.motion.reference,reference_area_m2=.01)
    template=replace(p.template,bulk_volume_m3=1e-4)
    point=replace(p,template=template,motion=replace(p.motion,reference=reference),
        skeleton=replace(p.skeleton,reference=reference))
    transport=replace(base.base_model.transport,storages=(template.fluid_template,),face_area_m2=.01)
    fixed=replace(base.base_model,storages=(template,),transport=transport)
    op=replace(base,base_model=fixed,point_storages=(point,))
    monkeypatch.setattr(type(water),'state_tp',lambda *a,**k:pytest.fail('water EOS forbidden'))
    state=op.state_from_temperatures([[0.,.01,2.]],[300.],time_s=.5)
    cls=type(point);original=cls.temperature_from_total_energy;calls=[]
    def counted(self,*a,**k):calls.append(1);return original(self,*a,**k)
    monkeypatch.setattr(cls,'temperature_from_total_energy',counted)
    out=op.evaluate(state,.5)
    assert len(calls)==1
    current=out.total_inverses[0].state.current_storage
    assert current.bulk_volume_m3 < template.fluid_template.mechanical.available_pore_volume_m3
    exact=F(current.bulk_volume_m3)-sum((F(n)*F(template.solid_phases[k].molar_volume_m3_mol)
        for k,n in point.skeleton.fixed_solid_inventory_mol),F())
    assert exact>0
    assert current.fluid_template.mechanical.available_pore_volume_m3==float(exact)
    assert out.current_host.storages[0] is current
    assert out.current_host.transport.storages[0] is current.fluid_template
    assert out.thermal_evaluation.storage_states[0].mechanical.gas_volume_m3==float(exact)
    assert template.fluid_template.mechanical.available_pore_volume_m3==1e-4
    assert current.solid_phases==template.solid_phases
    assert current.fluid_template.envelope is template.fluid_template.envelope


def test_current_pore_nonpositive_and_uncertain_domains_still_refused(water,monkeypatch):
    from sludge_sandbox.solid_fluid_storage import SolidFluidStorageError
    point=host(water,isotropic=True).point_storages[0]
    monkeypatch.setattr(type(water),'state_tp',lambda *a,**k:pytest.fail('water EOS forbidden'))
    collapsed=replace(point,motion=replace(point.motion,
        normal_stretches_at_knots=((1.,),(.5,)),tangential_stretches_at_knots=(1.,.5)))
    args=dict(liquid_mol=0.,gas_mol={'fixture':.01},solid_mol={'fixture_solid':2.},time_s=1.)
    with pytest.raises(SolidFluidStorageError,match='no_positive_fluid_available_volume'):
        collapsed.forward(300.,**args)
    uncertain=replace(point,error_bounds=replace(point.error_bounds,additional_bulk_volume_error_m3=1e-4))
    with pytest.raises(SolidFluidStorageError,match='available_volume_uncertainty_excludes_positive_domain'):
        uncertain.forward(300.,**args)
