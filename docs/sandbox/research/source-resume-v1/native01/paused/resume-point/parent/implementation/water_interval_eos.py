"""Research interval evaluation of pinned HEOS Water Helmholtz coefficients.

No phase selection, flash, U inversion, material admission or native error bound.
All binary64 coefficients are interpreted as exact real numbers. Decimal exp/ln
are enclosed using adjacent values around their correctly rounded results.
"""
from dataclasses import dataclass
from decimal import Decimal as D, localcontext, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class Interval:
    lo: D
    hi: D

    def __post_init__(self):
        if not self.lo.is_finite() or not self.hi.is_finite() or self.lo > self.hi:
            raise ValueError('finite_ordered_interval_required')

    @classmethod
    def point(cls, x):
        if isinstance(x, cls):
            return x
        if type(x) not in (int, float, D):
            raise TypeError('explicit_exact_numeric')
        v = D(x)
        return cls(v, v)

    def __add__(self, other):
        other = self.point(other)
        with localcontext() as ctx:
            ctx.rounding = ROUND_FLOOR
            lo = self.lo + other.lo
            ctx.rounding = ROUND_CEILING
            hi = self.hi + other.hi
        return Interval(lo, hi)

    __radd__ = __add__

    def __neg__(self):
        return Interval(self.hi.copy_negate(), self.lo.copy_negate())

    def __sub__(self, other):
        return self + -self.point(other)

    def __rsub__(self, other):
        return self.point(other) + -self

    def __mul__(self, other):
        other = self.point(other)
        corners = [(a, b) for a in (self.lo, self.hi) for b in (other.lo, other.hi)]
        with localcontext() as ctx:
            ctx.rounding = ROUND_FLOOR
            lo = min(a*b for a, b in corners)
            ctx.rounding = ROUND_CEILING
            hi = max(a*b for a, b in corners)
        return Interval(lo, hi)

    __rmul__ = __mul__

    def reciprocal(self):
        if self.lo <= 0 <= self.hi:
            raise ValueError('division_interval_contains_zero')
        with localcontext() as ctx:
            ctx.rounding = ROUND_FLOOR
            lo = D(1)/self.hi
            ctx.rounding = ROUND_CEILING
            hi = D(1)/self.lo
        return Interval(lo, hi)

    def __truediv__(self, other):
        return self * self.point(other).reciprocal()

    def __rtruediv__(self, other):
        return self.point(other) * self.reciprocal()

    def exp(self):
        return Interval(max(D(0), self.lo.exp().next_minus()), self.hi.exp().next_plus())

    def ln(self):
        if self.lo <= 0:
            raise ValueError('log_interval_not_positive')
        return Interval(self.lo.ln().next_minus(), self.hi.ln().next_plus())

    def __pow__(self, power):
        if type(power) is int:
            if power < 0:
                return (self**(-power)).reciprocal()
            result = self.point(1)
            for _ in range(power):
                result = result * self
            return result
        return (self.ln()*self.point(power)).exp()


I = Interval.point


@dataclass(frozen=True)
class Jet:
    value: Interval
    first: Interval
    second: Interval

    @classmethod
    def constant(cls, x):
        return x if isinstance(x, cls) else cls(I(x), I(0), I(0))

    def __add__(self, other):
        b = self.constant(other)
        return Jet(self.value+b.value, self.first+b.first, self.second+b.second)

    __radd__ = __add__

    def __neg__(self):
        return Jet(-self.value, -self.first, -self.second)

    def __sub__(self, other):
        return self + -self.constant(other)

    def __rsub__(self, other):
        return self.constant(other) + -self

    def __mul__(self, other):
        b = self.constant(other)
        return Jet(self.value*b.value, self.first*b.value+self.value*b.first,
                   self.second*b.value+2*self.first*b.first+self.value*b.second)

    __rmul__ = __mul__

    def exp(self):
        e = self.value.exp()
        return Jet(e, e*self.first, e*(self.first*self.first+self.second))

    def __pow__(self, power):
        if type(power) is int and power >= 0:
            out = self.constant(1)
            for _ in range(power):
                out = out*self
            return out
        q = I(power)
        v = (self.value.ln()*q).exp()
        a = q*v/self.value
        b = q*(q-1)*v/(self.value*self.value)
        return Jet(v, a*self.first, b*self.first*self.first+a*self.second)


def residual(delta, tau, terms):
    d = Jet(delta, I(1), I(0))
    t = Jet.constant(tau)
    result = Jet.constant(0)
    if [x['type'] for x in terms] != ['ResidualHelmholtzPower',
            'ResidualHelmholtzGaussian', 'ResidualHelmholtzNonAnalytic']:
        raise ValueError('unsupported_residual_layout')
    p, g, c = terms
    for n, di, ti, li in zip(p['n'], p['d'], p['t'], p['l'], strict=True):
        term = n*d**di*t**ti
        result = result + (term if li == 0 else term*(-(d**li)).exp())
    for n, di, ti, eta, epsilon, beta, gamma in zip(g['n'], g['d'], g['t'],
            g['eta'], g['epsilon'], g['beta'], g['gamma'], strict=True):
        result = result + n*d**di*t**ti*(-eta*(d-epsilon)**2-beta*(t-gamma)**2).exp()
    for n, a, b, A, B, C, DD, beta in zip(c['n'], c['a'], c['b'], c['A'],
            c['B'], c['C'], c['D'], c['beta'], strict=True):
        x = (d-1)**2
        theta = 1-t+A*x**(I(1)/(2*I(beta)))
        big_delta = theta**2+B*x**a
        psi = (-C*x-DD*(t-1)**2).exp()
        result = result + n*big_delta**b*d*psi
    return result


def pressure_interval(source, expected_sha256, temperature, molar_density, *, precision=60):
    """Enclose mathematical p and dp/d(rhomolar) on an explicit rectangle.

    Positive dp/drho is only a local branch check. This routine does not establish
    global stable-liquid selection, chemical coexistence or a flash enclosure.
    """
    raw = Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('source_bytes_changed')
    if type(precision) is not int or precision < 40:
        raise ValueError('explicit_precision_at_least_40')
    e = json.loads(raw)[0]['EOS'][0]
    if e['BibTeX_EOS'] != 'Wagner-JPCRD-2002':
        raise ValueError('unsupported_eos')
    if temperature.lo <= 0 or molar_density.lo <= 0:
        raise ValueError('positive_T_rho_required')
    with localcontext() as ctx:
        ctx.prec = precision
        delta = molar_density/I(e['STATES']['reducing']['rhomolar'])
        tau = I(e['STATES']['reducing']['T'])/temperature
        ar = residual(delta, tau, e['alphar'])
        rt = I(e['gas_constant'])*temperature
        p = molar_density*rt*(1+delta*ar.first)
        derivative = rt*(1+2*delta*ar.first+delta*delta*ar.second)
        return p, derivative
