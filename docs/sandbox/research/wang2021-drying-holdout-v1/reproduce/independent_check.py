"""Independent80-digit bisection implementation; posterior numerical check only."""
import numpy as np
from wang_d1 import NUMERICAL_ALLOWANCE


def reference_curve(p,temperature_c,rh,times_s,*,guard=lambda:None):
    import mpmath as mp
    with mp.workdps(80):
        # Interpret the same actual binary64 inputs exactly in high precision.
        d=mp.mpf(p.dref)*mp.exp(-mp.mpf(p.ea)/mp.mpf(8.31446261815324)*(1/(mp.mpf(temperature_c)+mp.mpf(273.15))-1/mp.mpf(323.15)))
        k=mp.mpf(p.kref)*(1-mp.mpf(rh))/(1-mp.mpf(.45))
        length=mp.mpf(.002);bi=k*length/d
        times=[mp.mpf(t) for t in times_s];positive=[t for t in times if t>0]
        if not positive:return [1. for _ in times]
        smallest=d*min(positive)/length**2
        count=next((n for n in range(2,1025) if 4/(mp.pi**2*(n-1))*mp.exp(-(n*mp.pi)**2*smallest)<=mp.mpf('1e-12')),None)
        if count is None:raise ValueError('independent reference tail unresolved')
        roots=[];weights=[]
        for n in range(count):
            guard();lo=n*mp.pi;hi=(n+mp.mpf('.5'))*mp.pi
            for _ in range(110):
                mid=(lo+hi)/2
                f=(-1)**n*(mid*mp.sin(mid)-bi*mp.cos(mid))
                if f>0:hi=mid
                else:lo=mid
            u=(lo+hi)/2
            roots.append(u)
            weights.append(4*mp.sin(u)**2/(u*(2*u+mp.sin(2*u))))
        return [1. if t==0 else float(mp.fsum(a*mp.exp(-u*u*d*t/length**2) for u,a in zip(roots,weights))) for t in times]


def checked_curve(p,t,h,times,predict,*,guard=lambda:None):
    values,info=predict(p,t,h,times,guard=guard)
    reference=reference_curve(p,t,h,times,guard=guard)
    delta=float(np.max(np.abs(values-np.array(reference))))
    if delta>NUMERICAL_ALLOWANCE:
        raise ValueError('independent numerical discrepancy exceeds1e-6MR')
    return values,dict(info,independent_max_abs_delta=delta,independent_method='80-digit110-bisections_tail1e-12; pointwise check not universal machine bound')
