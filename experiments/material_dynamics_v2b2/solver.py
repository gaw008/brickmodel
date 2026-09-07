"""Conservative cell-average FV + nonautonomous SSPRK2, without clipping.

Each Euler stage has a shared face transfer and a shared reaction extent.
The second stage uses t+h; convex averaging preserves all linear inventories.
"""
from dataclasses import dataclass
import math
from temperature import data, evaluate


# Numerical quadrature budget, not a material parameter or audit tolerance.
# Reserve a factor of ten below B2-AUDIT-1's fixed 1e-6 minimum scale.
EXPOSURE_ABS_BUDGET = 1e-7


def exposure_step_limits(s):
    """Bound cumulative trapezoidal H error without changing RK ledger weights.

    On a linear temperature segment, A = theta*T_ref and slope = dT/dtau:
      K'' = K*slope**2*A/T**3*(A/T - 2).
    Its absolute maximum occurs at a segment end or A/T = 3 +/- sqrt(3).
    Each step's trapezoid error is <= max|K''|*h**3/12. Allocating the
    absolute budget by ramp duration bounds their sum at every output time.
    Holds have constant K and no quadrature truncation error.
    """
    d = data(s)
    segments = list(zip(d['temperature']['knots'], d['temperature']['knots'][1:]))
    ramp_duration = sum(b['tau'] - a['tau'] for a, b in segments if a['T_K'] != b['T_K'])
    activation = d['reaction']['theta'] * d['temperature']['T_ref_K']
    kref = d['reaction']['K_ref']
    limits = []
    for left, right in segments:
        limit = math.inf
        if activation and kref and left['T_K'] != right['T_K']:
            low, high = sorted((left['T_K'], right['T_K']))
            slope = (right['T_K'] - left['T_K']) / (right['tau'] - left['tau'])
            candidates = [low, high]
            for x in (3 - math.sqrt(3), 3 + math.sqrt(3)):
                critical = activation / x
                if low <= critical <= high:
                    candidates.append(critical)
            curvature = max(
                abs(kref * math.exp(d['reaction']['theta'] - activation / temperature)
                    * slope**2 * activation / temperature**3 * (activation / temperature - 2))
                for temperature in candidates
            )
            if curvature:
                limit = math.sqrt(12 * EXPOSURE_ABS_BUDGET / (ramp_duration * curvature))
        limits.append((right['tau'], limit))
    return limits


@dataclass(slots=True)
class State:
    u: list
    v: list
    f: list
    u_res: float | None = None
    v_res: float | None = None
    generated: float = 0.0
    net_u: float = 0.0
    net_v: float = 0.0
    H: float = 0.0
    S_D: float = 0.0
    S_B: float = 0.0


@dataclass
class RunResult:
    scenario: object
    records: list
    steps: int
    rejected_steps: int
    min_step: float
    max_step: float
    knot_times: list
    execution_status: str = 'integrated'
    test_only_dirichlet: bool = False


def initial_state(s):
    d=data(s); n=d['numerics']['n_cells']; finite=d['boundary']['mode']=='finite'
    return State([1.0]*n,[0.0]*n,[1.0]*n,1.0 if finite else None,0.0 if finite else None)


def conductance(a,b,dx):
    return 0.0 if b==0 else 1/(1/b+dx/(2*a))


def check(state):
    for values in (state.u,state.v,state.f):
        for x in values:
            if not math.isfinite(x) or x<0: raise ArithmeticError('inventory_negative_or_nonfinite')
    if max(state.f)>1: raise ArithmeticError('carbon_increase')
    for x in (state.u_res,state.v_res):
        if x is not None and (not math.isfinite(x) or x<0): raise ArithmeticError('reservoir_invalid')
    for x in (state.generated,state.net_u,state.net_v,state.H,state.S_D,state.S_B):
        if not math.isfinite(x): raise ArithmeticError('ledger_nonfinite')


def euler(s,state,c,h,g):
    d=data(s); n=len(state.u); gamma=d['reaction']['Gamma']; mode=d['boundary']['mode']
    ue,ve=(state.u_res,state.v_res) if mode=='finite' else (1.,0.)
    ju=g*(state.u[-1]-ue); jv=g*(state.v[-1]-ve)
    u,v,f=state.u,state.v,state.f; un=[]; vn=[]; fn=[]; produced=0.; a=c.a_D*n*n
    for i in range(n):
        ul=a*(u[i-1]-u[i]) if i else 0.; vl=a*(v[i-1]-v[i]) if i else 0.
        ur=a*(u[i+1]-u[i]) if i<n-1 else -ju*n
        vr=a*(v[i+1]-v[i]) if i<n-1 else -jv*n
        extent=h*gamma*c.K*f[i]*u[i]
        un.append(u[i]+h*(ul+ur)-extent); vn.append(v[i]+h*(vl+vr)+extent); fn.append(f[i]-extent/gamma)
        produced+=extent/n
    out=State(un,vn,fn,generated=state.generated+produced,net_u=state.net_u+h*ju,net_v=state.net_v+h*jv,
              H=state.H+h*c.K,S_D=state.S_D+h*c.a_D,S_B=state.S_B+h*c.b)
    if mode=='finite':
        rho=d['boundary']['reservoir_ratio']
        out.u_res=state.u_res+h*ju/rho; out.v_res=state.v_res+h*jv/rho
    check(out)
    return out


def average(a,b):
    out=State([(x+y)/2 for x,y in zip(a.u,b.u)],[(x+y)/2 for x,y in zip(a.v,b.v)],[(x+y)/2 for x,y in zip(a.f,b.f)])
    for k in ('u_res','v_res','generated','net_u','net_v','H','S_D','S_B'):
        x,y=getattr(a,k),getattr(b,k)
        setattr(out,k,None if x is None else (x+y)/2)
    check(out)
    return out


def loss(s,state,c,g):
    d=data(s); n=len(state.u)
    # Exact FV diagonal (including a boundary half-cell resistance).
    transport=max(2*c.a_D*n*n,c.a_D*n*n+g*n)
    oxygen=transport+d['reaction']['Gamma']*c.K*max(state.f)
    carbon=c.K*max(state.u)
    reservoir=g/d['boundary']['reservoir_ratio'] if state.u_res is not None else 0.
    return max(oxygen,carbon,reservoir)


def step(s,state,t,h,*,dirichlet=False):
    n=len(state.u); c0=evaluate(s,t); c1=evaluate(s,t+h)
    g0=2*c0.a_D*n if dirichlet else conductance(c0.a_D,c0.b,1/n)
    g1=2*c1.a_D*n if dirichlet else conductance(c1.a_D,c1.b,1/n)
    scale=data(s)['numerics']['dt_scale']
    if h*max(loss(s,state,c0,g0),loss(s,state,c1,g1))>.8*scale*(1+1e-12): raise ArithmeticError('stage_cfl')
    intermediate=euler(s,state,c0,h,g0)
    if h*loss(s,intermediate,c1,g1)>.8*scale*(1+1e-12): raise ArithmeticError('stage_cfl')
    return average(state,euler(s,intermediate,c1,h,g1))


def integrate(s,budget,*,test_only_dirichlet=False):
    d=data(s); num=d['numerics']; n=num['n_cells']; end=num['tau_end']; scale=num['dt_scale']
    budget.check(); state=initial_state(s)
    if test_only_dirichlet:
        if d['reaction']['K_ref']!=0 or d['boundary']['mode']!='infinite': raise ValueError('test_fixture')
        state.u=[0.]*n; state.v=[1.]*n
    records=[(0.,state)]; t=0.; steps=0; rejected=0; small=float('inf'); large=0.; knots_seen=[0.]
    knots=[k['tau'] for k in d['temperature']['knots']]
    exposure_limits = exposure_step_limits(s)
    for sample in range(1,math.ceil(end/.1)+1):
        target=min(sample*.1,end)
        while t<target:
            if (steps+rejected)%128==0: budget.check()
            if steps+rejected>=1_000_000: raise RuntimeError('step_resource_limit')
            knot=next(k for k in knots if k>t)
            stop=min(target,knot)
            c0=evaluate(s,t); c1=evaluate(s,stop)
            g0=2*c0.a_D*n if test_only_dirichlet else conductance(c0.a_D,c0.b,1/n)
            g1=2*c1.a_D*n if test_only_dirichlet else conductance(c1.a_D,c1.b,1/n)
            maxloss=max(loss(s,state,c0,g0),loss(s,state,c1,g1))
            exposure_limit = next(limit for end_time, limit in exposure_limits if end_time > t)
            h=min(num['max_dtau']*scale,.8*scale/maxloss,exposure_limit*scale,stop-t)
            for attempt in range(32):
                if t+h==t: raise ArithmeticError('time_stagnation')
                try: nxt=step(s,state,t,h,dirichlet=test_only_dirichlet)
                except ArithmeticError:
                    rejected+=1; h/=2; budget.check()
                    continue
                break
            else: raise ArithmeticError('positive_step_not_found')
            state=nxt; t=min(stop,t+h); steps+=1; small=min(small,h); large=max(large,h)
            if t==knot and (not knots_seen or knots_seen[-1]!=t): knots_seen.append(t)
        records.append((target,state))
    budget.check()
    return RunResult(s,records,steps,rejected,small,large,knots_seen,test_only_dirichlet=test_only_dirichlet)
