"""D1 effective slab moisture model. No heat equation or intrinsic material claim."""
from dataclasses import dataclass
import math
import numpy as np
from scipy.optimize import brentq

L = .002
TREF = 323.15
R = 8.31446261815324
TAIL_TARGET = 1e-9
MAX_MODES = 512
NUMERICAL_ALLOWANCE = 1e-6
BOUNDS = ((1e-12, 1e-7), (1e-10, 1e-4), (0., 150000.))


def number(x):
    if type(x) not in (int, float):
        raise ValueError('finite numeric input required')
    try:
        value=float(x)
    except OverflowError as exc:
        raise ValueError('finite numeric input required') from exc
    if not math.isfinite(value):
        raise ValueError('finite numeric input required')
    return value


@dataclass(frozen=True)
class Parameters:
    dref: float
    kref: float
    ea: float

    def __post_init__(self):
        for value, (lo, hi) in zip((self.dref, self.kref, self.ea), BOUNDS):
            if not lo <= number(value) <= hi:
                raise ValueError('outside preregistered numerical search box')


def coefficients(p, temperature_c, rh):
    if type(p) is not Parameters:
        raise ValueError('typed parameters required')
    t, h = number(temperature_c), number(rh)
    if not 40 <= t <= 60 or not .3 <= h <= .6:
        raise ValueError('outside source experimental label domain')
    d = p.dref * math.exp(-p.ea / R * (1 / (t + 273.15) - 1 / TREF))
    return d, p.kref * (1 - h) / (1 - .45)


def mean_curve(p, temperature_c, rh, times_s, *, guard=lambda: None):
    """Return MR and explicit truncation diagnostics; no t0 renormalization.

    Root floating arithmetic is tested independently; tail_bound is only the
    mathematical omitted-mode bound, not a full interval-arithmetic certificate.
    """
    d, k = coefficients(p, temperature_c, rh)
    times = np.array([number(t) for t in times_s], dtype=float)
    if times.ndim != 1 or not len(times) or np.any(times < 0):
        raise ValueError('nonempty nonnegative time vector required')
    guard()
    positive = times > 0
    answer = np.ones_like(times)
    if not np.any(positive):
        return answer, {'modes': 0, 'tail_bound': 0., 'log_tail_bound': None, 'tail_underflow': False, 'roots': []}
    fo = d * times[positive] / L**2
    smallest = float(np.min(fo))
    count = next((n for n in range(2, MAX_MODES + 1)
                  if 4 / (math.pi**2 * (n - 1)) * math.exp(-(n * math.pi)**2 * smallest) <= TAIL_TARGET), None)
    if count is None:
        raise ValueError('512-mode cap cannot prove requested positive-time tail')
    bi = k * L / d
    roots = []
    for n in range(count):
        guard()
        # Continuous equivalent avoids evaluating tan at its poles.
        root = brentq(lambda u: u * math.sin(u) - bi * math.cos(u),
                      n * math.pi, (n + .5) * math.pi,
                      xtol=5e-15, rtol=4*np.finfo(float).eps, maxiter=100)
        if not n * math.pi < root < (n + .5) * math.pi:
            raise ValueError('root outside original open eigenvalue interval')
        roots.append(root)
    mu = np.array(roots)
    weights = 4*np.sin(mu)**2 / (mu*(2*mu + np.sin(2*mu)))
    if np.any(weights <= 0):
        raise ValueError('nonpositive modal coefficient')
    answer[positive] = np.sum(weights[:, None] * np.exp(-mu[:, None]**2 * fo), axis=0)
    guard()
    log_tail = math.log(4/(math.pi**2*(count-1))) - (count*math.pi)**2*smallest
    raw_tail = 4/(math.pi**2*(count-1))*math.exp(-(count*math.pi)**2*smallest)
    # A positive-time omitted tail is never mathematically zero. Preserve its
    # log and use the least positive float when the representation underflows.
    underflow = raw_tail == 0.
    represented_tail = math.nextafter(0., math.inf) if underflow else raw_tail
    return answer, {'modes': count, 'tail_bound': represented_tail,
                    'log_tail_bound': log_tail, 'tail_underflow': underflow, 'roots': roots}
