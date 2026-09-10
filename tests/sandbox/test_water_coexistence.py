from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import pytest
from sludge_sandbox.water_coexistence import *


def box(a,b):return Interval(D(a),D(b))
def contains(i,x):assert F(i.lo)<=x<=F(i.hi)


def test_parametric_linear_system_all_temperature_values():
    # F(x,y;t)=(2x+y-t,x+3y-2t), t in [1,2]. C exact inverse /5.
    x=(box('-1','2'),box('0','2'));center=(D('.5'),D('1'))
    c=((D('.6'),D('-.2')),(D('-.2'),D('.4')))
    f=(box('0','1'),box('-.5','1.5')) # actual F(center,t): (2-t,3.5-2t)
    j=((I(2),I(1)),(I(1),I(3)))
    r=krawczyk(x,center,c,f,j)
    assert r.proved and r.contraction_upper==0
    # Correlation is deliberately lost; still encloses full solution curve.
    for t in (F(1),F(3,2),F(2)):
        contains(r.image[0],t/5);contains(r.image[1],3*t/5)


def test_identity_parameter_boundary_not_strict_and_bad_preconditioner():
    x=(box('-1','1'),box('-1','1'));z=(D(0),D(0));j=((I(1),I(0)),(I(0),I(1)))
    c=((D(1),D(0)),(D(0),D(1)))
    r=krawczyk(x,z,c,(box('-1','1'),I(0)),j)
    assert not r.proved and r.strict_margins[0]==(D(0),D(0))
    with pytest.raises(ValueError,match='nonsingular'):krawczyk(x,z,((D(0),D(0)),(D(0),D(0))),(I(0),I(0)),j)
    r=krawczyk(x,z,((D(3),D(0)),(D(0),D(3))),(I(0),I(0)),j)
    assert not r.proved and r.contraction_upper==2


def test_synthetic_helmholtz_formula_and_log_jacobian():
    # alphar=a*delta+b*delta², coefficients temperature-wide a=tau,b=1/10.
    def jet(d,t):return Jet(t*d+I(D('.1'))*d*d,t+I(D('.2'))*d,I(D('.2')))
    with localcontext() as c:
        c.prec=60
        logs=(box('1','1.01'),box('-2','-1.99'))
        r=evaluate_box(box('2','3'),logs,reducing_density=1,reducing_temperature=10,gas_constant=2,jet=jet)
        for temp in (D(2),D('2.5'),D(3)):
            l=D(1).exp();v=D(-2).exp();t=D(10)/temp
            al=t*l+D('.1')*l*l;av=t*v+D('.1')*v*v
            ql=l*(t+D('.2')*l);qv=v*(t+D('.2')*v)
            f=(l*(1+ql)-v*(1+qv),D(3)+al-av+ql-qv)
            for i,val in zip(r.residual,f):assert i.lo<=val<=i.hi
            dl=1+2*t*l+D('.6')*l*l;dv=1+2*t*v+D('.6')*v*v
            for row,actual in zip(r.jacobian,((l*dl,-v*dv),(dl,-dv))):
                for i,val in zip(row,actual):assert i.lo<=val<=i.hi


@pytest.mark.parametrize('temperature,logs',[(box('10','11'),(box('1','2'),box('-2','-1'))),(box('2','3'),(box('-1','1'),box('-2','-1'))),(box('0','3'),(box('1','2'),box('-2','-1')))])
def test_critical_or_nonpositive_domain_refuses(temperature,logs):
    with pytest.raises(ValueError):evaluate_box(temperature,logs,reducing_density=1,reducing_temperature=10,gas_constant=2,jet=lambda d,t:Jet.constant(0))


def test_rounding_norm_does_not_round_long_input_inwards():
    with localcontext() as ctx:
        ctx.prec=8
        x=(box('-1','1'),box('-1','1'));c=((D(1),D(0)),(D(0),D(1)))
        j=((I(D('-0.000000001')),I(0)),(I(0),I(1)))
        r=krawczyk(x,(D(0),D(0)),c,(I(0),I(0)),j)
        assert r.contraction_upper>=D('1.000000001') and not r.proved


def test_pinned_source_wrapper_preserves_unresolved_evidence(tmp_path):
    # Empty residual terms: explicit synthetic ideal model, not real water data.
    terms=[dict(type='ResidualHelmholtzPower',n=[],d=[],t=[],l=[]),dict(type='ResidualHelmholtzGaussian',n=[],d=[],t=[],eta=[],epsilon=[],beta=[],gamma=[]),dict(type='ResidualHelmholtzNonAnalytic',n=[],a=[],b=[],A=[],B=[],C=[],D=[],beta=[])]
    e=dict(BibTeX_EOS='Wagner-JPCRD-2002',STATES={'reducing':{'rhomolar':1,'T':10}},gas_constant=2,alphar=terms)
    p=tmp_path/'synthetic.json';p.write_text(json.dumps([{'EOS':[e]}]));sha=hashlib.sha256(p.read_bytes()).hexdigest()
    args=(p,sha,box('2','3'),(box('1','1.1'),box('-2','-1.9')),(D('1.05'),D('-1.95')),((D(1),D(0)),(D(0),D(1))))
    r=enclose_coexistence(*args)
    assert not r.proved and not r.krawczyk.proved and r.source_sha256==sha
    assert r.domain.temperature==box('2','3') and r.center.temperature==r.domain.temperature
    assert r.pressure is None # no equality of ideal-gas pressure at separated densities
    p.write_text('changed')
    with pytest.raises(ValueError,match='source_bytes_changed'):enclose_coexistence(*args)


@pytest.mark.parametrize('matrix', [((True,D(0)),(D(0),D(1))),[[D(1),D(0)],[D(0),D(1)]]])
def test_strict_matrix_types(matrix):
    with pytest.raises(ValueError):krawczyk((box('-1','1'),box('-1','1')),(D(0),D(0)),matrix,(I(0),I(0)),((I(1),I(0)),(I(0),I(1))))


def test_explicit_weighted_contraction_without_unweighted_contraction():
    # I-CJ = [[0,2],[.1,0]], spectral radius sqrt(.2)<1.
    # X has radii (3,1), so K already lies strictly inside X.
    x=(box('-3','3'),box('-1','1'));center=(D(0),D(0))
    c=((D(1),D(0)),(D(0),D(1)))
    j=((I(1),I(-2)),(I(D('-.1')),I(1)))
    old=krawczyk(x,center,c,(I(0),I(0)),j)
    new=krawczyk(x,center,c,(I(0),I(0)),j,weights=(D(3),D(1)))
    assert not old.proved and old.contraction_upper==2
    assert new.proved and new.image==old.image and new.strict_margins==old.strict_margins
    assert new.unweighted_contraction_upper==2 and new.contraction_upper<1
    assert new.weights==(D(3),D(1)) and new.norm_name=='weighted_infinity'
    assert old.weights is None and old.norm_name=='unweighted_infinity'
    assert new.contraction_upper>=D(2)/D(3)


@pytest.mark.parametrize('weights',[(D(1),D(1)),(D(3),D(1)),(D(100),D('.01'))])
def test_weighting_cannot_hide_spectral_radius_at_least_one(weights):
    # Defect [[0,2],[.5,0]] has eigenvalues +/-1. Every induced norm >=1.
    r=krawczyk((box('-3','3'),box('-1','1')),(D(0),D(0)),((D(1),D(0)),(D(0),D(1))),(I(0),I(0)),((I(1),I(-2)),(I(D('-.5')),I(1))),weights=weights)
    assert not r.proved and r.contraction_upper>=1


@pytest.mark.parametrize('weights',[(D(0),D(1)),(D(-1),D(1)),(1.,1.),[D(1),D(1)],(D('NaN'),D(1))])
def test_invalid_weights_fail_closed(weights):
    with pytest.raises(ValueError,match='positive_decimal_weights'):
        krawczyk((box('-1','1'),box('-1','1')),(D(0),D(0)),((D(1),D(0)),(D(0),D(1))),(I(0),I(0)),((I(1),I(0)),(I(0),I(1))),weights=weights)
