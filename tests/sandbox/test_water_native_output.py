from decimal import Decimal as D
from fractions import Fraction as F
from sludge_sandbox.water_native_output import *


def run(**kw):
    # p=2*rho root at10, observed rho10.0000000001; scales=1.
    rho=10.0000000001;n=.02;mass=.02
    q=(300.,20.,rho*mass,mass,mass,n,n*mass/(rho*mass),1e-10)
    opts=dict(pressure=lambda t,r:(2*r,I(2)),binding=lambda:('synthetic',))
    opts.update(kw)
    return analyze(q,Interval(D(9),D(11)),**opts)


def test_exact_linear_root_discrepancy_and_rounding():
    r=run();assert r['status']=='passed_observed_query',r['reason']
    q=r['query'];actual=abs(F(q[3])/F(q[2])-F(1,10))
    assert actual<=F(r['metrics']['native_volume_error_bound'])
    assert r['attempted']==r['completed']==4 and len(r['accepted_leaves'])==1


def test_original_declaration_not_enlarged():
    r=run();q=(*r['query'][:-1],1e-30)
    x=analyze(q,r['density_box'],pressure=lambda t,r:(2*r,I(2)),binding=lambda:('synthetic',))
    assert x['status']=='failed' and 'original_volume_declaration_exceeded' in x['reason']
    assert x['metrics']['original_declaration']==I(1e-30)


def test_strict_faces_and_budget_and_source_failure():
    r=run(pressure=lambda t,r:(I(20),I(2)))
    assert r['status']=='failed' and 'strict_root_faces' in r['reason']
    r=run(pressure=lambda t,r:(2*r,Interval(D(-1),D(3))),maximum_boxes=4)
    assert r['status']=='failed' and r['attempted']==4 and r['pending']
    source=['old']
    def bad(t,r):source[0]='new';return 2*r,I(2)
    r=run(pressure=bad,binding=lambda:tuple(source))
    assert r['status']=='failed' and r['completed']==1 and r['source_before']==('old',)


def test_wrong_host_rounding_refused():
    r=run();q=list(r['query']);q[6]*=1.0000001
    r=analyze(tuple(q),r['density_box'],pressure=lambda t,r:(2*r,I(2)),binding=lambda:('synthetic',))
    assert r['status']=='failed' and 'saved_host_volume_rounding_mismatch' in r['reason']
