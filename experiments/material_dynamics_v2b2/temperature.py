"""Prescribed temperature: fixed concentration reference, no energy/EOS model."""
from dataclasses import dataclass
from functools import lru_cache
import math


@lru_cache(maxsize=64)
def data(scenario):
    return scenario.to_dict()


@dataclass(frozen=True, slots=True)
class Coefficients:
    T_K: float
    K: float
    d: float
    a_D: float
    b: float


def evaluate(scenario,tau):
    d=data(scenario); knots=d['temperature']['knots']
    if not math.isfinite(tau) or not 0 <= tau <= d['numerics']['tau_end']: raise ValueError('temperature_extrapolation')
    for a,b in zip(knots,knots[1:]):
        if a['tau'] <= tau <= b['tau']:
            T=a['T_K']+(b['T_K']-a['T_K'])*(tau-a['tau'])/(b['tau']-a['tau'])
            break
    else:
        raise ValueError('temperature_interval')
    reaction=d['reaction']; tr=d['transport']; ell=d['geometry']['length_ratio']
    K=reaction['K_ref']*math.exp(reaction['theta']*(1-600/T))
    diff=tr['d_ref']*(T/600)**tr['m']
    return Coefficients(T,K,diff,diff/ell**2,tr['Bi_ref']/ell)
