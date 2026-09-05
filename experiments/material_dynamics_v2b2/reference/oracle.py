"""Independent mathematical oracle. Imports ONLY math, no B2 implementation.

Uniform sealed: du/df=Gamma, so u=1-Gamma+Gamma*f.
Integrating df/dH=-f*(1-Gamma+Gamma*f) gives the closed form below.
Diffusion: dS=a_D dt transforms the PDE into the unit heat equation;
the cosine eigenfunctions are integrated over each FV cell, not point sampled.
"""
import math


def temperature(knots,t):
    if not knots[0]['tau']<=t<=knots[-1]['tau']: raise ValueError('oracle_extrapolation')
    for left,right in zip(knots,knots[1:]):
        if left['tau']<=t<=right['tau']:
            fraction=(t-left['tau'])/(right['tau']-left['tau'])
            return left['T_K']*(1-fraction)+right['T_K']*fraction
    raise ValueError('oracle_knots')


def exposure(knots,t,kref,theta):
    if t==0: return 0.,[{'subintervals':64,'estimate':0.,'change':0.}]
    previous=None; trace=[]
    for count in (64,128,256,512,1024,2048,4096):
        total=0.
        for left,right in zip(knots,knots[1:]):
            a=left['tau']; b=min(right['tau'],t)
            if b<=a: continue
            dx=(b-a)/count
            def rate(x):
                T=left['T_K']+(right['T_K']-left['T_K'])*(x-left['tau'])/(right['tau']-left['tau'])
                return kref*math.exp(theta*(1-600/T))
            value=rate(a)+rate(b)
            for i in range(1,count): value+=(4 if i%2 else 2)*rate(a+i*dx)
            total+=value*dx/3
        change=None if previous is None else abs(total-previous)
        trace.append({'subintervals':count,'estimate':total,'change':change})
        if change is not None and change<=1e-9: return total,trace
        previous=total
    raise ArithmeticError('reference_not_converged')


def sealed_state(gamma,H):
    a=1-gamma
    f=1/(1+H) if a==0 else a/(a+math.expm1(a*H))
    u=1-gamma+gamma*f
    return u,1-u,f


def diffusion_time(knots,t,dref=1,m=1,ell=1):
    total=0.
    for a,b in zip(knots,knots[1:]):
        end=min(t,b['tau'])
        if end<=a['tau']: continue
        T_end=a['T_K']+(b['T_K']-a['T_K'])*(end-a['tau'])/(b['tau']-a['tau'])
        total+=(end-a['tau'])*dref*(1 if m==0 else (a['T_K']+T_end)/1200)/ell**2
    return total


def diffusion_cell(n,i,S,terms):
    left=i/n; right=(i+1)/n; deficit=0.
    for j in range(terms):
        lam=(j+.5)*math.pi
        average_cos=(math.sin(lam*right)-math.sin(lam*left))*n/lam
        deficit+=2*(-1)**j/lam*average_cos*math.exp(-lam*lam*S)
    return 1-deficit
