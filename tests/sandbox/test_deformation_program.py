"""Kinematic identities and explicit numerical domain failures."""
import math
from dataclasses import replace
import numpy as np
import pytest
from sludge_sandbox.geometry import ReferenceSlab

from sludge_sandbox.deformation_program import PrescribedSlabMotion as Motion
from sludge_sandbox.deformation_program import DeformationProgramError as Error


def program():
    return Motion(reference=ReferenceSlab(.02,.04,2),knot_times_s=(0.,2.,4.),
        normal_stretches_at_knots=((1.,1.),(.8,1.2),(1.,.9)),
        tangential_stretches_at_knots=(1.,.9,1.1),motion_id='manufactured:motion-fixture',version='1',
        classification='manufactured_test_fixture',source_ids=('manufactured:explicit-kinematics',),
        source_asset_sha256=())


def test_independent_midpoint_and_full_product_volume_derivative():
    motion=program();snapshot=motion.sample(1.)
    # q=.5: stretch=(a+b)/2, derivative=1.5*(b-a)/duration.
    normal=np.array([.9,1.1]);normal_rate=np.array([-.15,.15]);tangent=.95;tangent_rate=-.075
    area=.04*tangent**2;area_rate=2*.04*tangent*tangent_rate
    widths=.01*normal;width_rates=.01*normal_rate
    expected_volume_rate=area*width_rates+area_rate*widths
    assert snapshot.current.widths_m==pytest.approx(widths,rel=0,abs=1e-16)
    assert snapshot.current.face_areas_m2==pytest.approx([area]*3,rel=0,abs=1e-16)
    assert snapshot.volume_rates_m3_s==pytest.approx(expected_volume_rate,rel=0,abs=1e-17)
    assert snapshot.face_velocities_m_s==pytest.approx([0.,-.0015,0.],rel=0,abs=1e-17)
    assert snapshot.face_area_rate_m2_s==pytest.approx(area_rate,rel=0,abs=1e-16)
    # Normal-face motion alone omits a real tangential contribution.
    assert abs(snapshot.volume_rates_m3_s[0]-area*width_rates[0])>1e-5


def test_independent_finite_difference_volume_and_face_motion():
    m=program();h=1e-5
    for t in (.3,1.3,2.7,3.8):
        a,b=m.sample(t-h),m.sample(t+h);center=m.sample(t)
        dv=(b.current.volumes_m3-a.current.volumes_m3)/(2*h)
        dx=(b.current.faces_m-a.current.faces_m)/(2*h)
        assert dv==pytest.approx(center.volume_rates_m3_s,rel=1e-7,abs=1e-12)
        assert dx==pytest.approx(center.face_velocities_m_s,rel=1e-7,abs=1e-12)
        identity=center.current.volumes_m3*(center.normal_rates_per_s/center.normal_stretches+2*center.tangential_rate_per_s/center.tangential_stretch)
        assert identity==pytest.approx(center.volume_rates_m3_s,rel=1e-13,abs=1e-18)


def test_c1_nodes_exact_zero_rates_and_repeatable_nonincremental_sampling():
    m=program()
    for t in (0.,2.,4.):
        s=m.sample(t)
        assert np.all(s.volume_rates_m3_s==0) and np.all(s.face_velocities_m_s==0)
        assert s.face_area_rate_m2_s==0
    first=m.sample(.25);m.sample(3.9);again=m.sample(.25)
    assert np.array_equal(first.current.volumes_m3,again.current.volumes_m3)
    assert m.breakpoints_s(0.,4.)==(2.,)
    assert m.breakpoints_s(.5,1.5)==()


def test_snapshot_arrays_and_input_data_are_immutable():
    m=program();s=m.sample(1.)
    for value in (*vars(s.current).values(),s.normal_stretches,s.normal_rates_per_s,s.width_rates_m_s,s.face_velocities_m_s,s.volume_rates_m3_s):
        with pytest.raises(ValueError):value.setflags(write=True)
    with pytest.raises(Exception):s.time_s=2.
    assert s.motion_identity==m.identity and s.source_ids==m.source_ids
    assert m.identity!=replace(m,version='2').identity


def test_reference_shape_binding_rejects_same_volume_different_shape():
    m=program()
    alignment=m.validate_reference_geometry(cell_count=2,face_area_m2=.04,cell_widths_m=(.01,.01),gas_volumes_m3=(.0004,.0004))
    assert alignment.exact_match
    with pytest.raises(Error,match='reference_area'):
        m.validate_reference_geometry(cell_count=2,face_area_m2=.08,cell_widths_m=(.005,.005),gas_volumes_m3=(.0004,.0004))
    near=m.validate_reference_geometry(cell_count=2,face_area_m2=math.nextafter(.04,math.inf),cell_widths_m=(.01,.01),gas_volumes_m3=(.0004,.0004))
    assert not near.exact_match and near.area_residual_m2!=0 and near.tolerance_ulps==2


@pytest.mark.parametrize('change',[{'knot_times_s':(0.,0.,4.)},{'normal_stretches_at_knots':((1.,1.),(0.,1.),(1.,1.))},
    {'tangential_stretches_at_knots':(1.,True,1.)},{'normal_stretches_at_knots':((1.,),(1.,),(1.,))},
    {'motion_id':''},{'source_ids':()},{'source_asset_sha256':(('x','bad'),)}])
def test_invalid_explicit_program_contract(change):
    with pytest.raises(Error):replace(program(),**change)


@pytest.mark.parametrize('time',[-.1,4.1,float('nan'),float('inf'),True])
def test_time_domain(time):
    with pytest.raises(Error):program().sample(time)


def test_overflow_underflow_and_face_coalescence_are_not_clipped():
    with pytest.raises(Error):replace(program(),reference=ReferenceSlab(1e-320,1e-320,2))
    with pytest.raises(Error):replace(program(),tangential_stretches_at_knots=(1e308,)*3).sample(1.)
    with pytest.raises(Error,match='face'):
        replace(program(),normal_stretches_at_knots=((1e16,1.),)*3).sample(1.)


def test_scalar_array_and_unresolvable_time_interval_have_explicit_errors():
    with pytest.raises(Error):replace(program(),knot_times_s=np.array(1.))
    with pytest.raises(Error):replace(program(),normal_stretches_at_knots=np.array(1.))
    with pytest.raises(Error):replace(program(),knot_times_s=(0.,math.nextafter(0.,1.),1.))


@pytest.mark.parametrize('change',[{'cell_count':1},{'cell_widths_m':(.02,.01)},{'gas_volumes_m3':(.0008,.0004)}, {'cell_count':True}])
def test_each_reference_geometry_component_is_bound(change):
    values=dict(cell_count=2,face_area_m2=.04,cell_widths_m=(.01,.01),gas_volumes_m3=(.0004,.0004))
    values.update(change)
    with pytest.raises(Error):program().validate_reference_geometry(**values)


def test_constructor_detaches_caller_arrays_and_source_identity():
    normal=np.array([[1.,1.],[.8,1.2],[1.,.9]])
    m=replace(program(),normal_stretches_at_knots=normal)
    before=m.identity;normal[1,0]=.2
    assert m.identity==before
    assert m.sample(1.).normal_stretches[0]==pytest.approx(.9,rel=0,abs=1e-15)


def test_nonzero_numeric_underflow_cannot_enter_time_domain():
    from fractions import Fraction
    tiny = Fraction(1, 10**400)
    with pytest.raises(Error): program().sample(-tiny)
    with pytest.raises(Error): program().breakpoints_s(-tiny, 1.)


@pytest.mark.parametrize('count', [16, 32, 64])
def test_regular_multicell_coordinate_rounding_is_resolved(count):
    motion = replace(program(), reference=ReferenceSlab(.02, .04, count),
                     normal_stretches_at_knots=((1.,)*count,)*3)
    state = motion.sample(1.)
    assert len(state.current.widths_m) == count
    assert np.all(np.diff(state.current.faces_m) > 0)


def test_unrepresentable_knot_geometry_rejected_at_construction():
    with pytest.raises(Error):
        replace(program(), tangential_stretches_at_knots=(1., 1e308, 1.))
