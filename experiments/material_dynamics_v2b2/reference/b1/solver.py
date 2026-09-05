"""Cell-centred finite volume + SSPRK2. No clipping and no legacy imports."""
from dataclasses import dataclass
import math
import time

from model import Config


@dataclass
class State:
    u: list[float]
    v: list[float]
    f: list[float]
    generated: float = 0.0
    net_u: float = 0.0
    net_v: float = 0.0
    u_res: float | None = None
    v_res: float | None = None


@dataclass
class Record:
    tau: float
    state: State


@dataclass
class Result:
    config: Config
    records: list[Record]
    steps: int
    dt_max: float


def conductance(bi, dx):
    """Film and half-cell diffusion resistances in series."""
    return 0.0 if bi == 0 else 1.0 / (1.0 / bi + dx / 2)


def boundary_flux(state, cfg, g):
    if cfg.boundary_mode == "sealed":
        return 0.0, 0.0
    ue, ve = (state.u_res, state.v_res) if cfg.boundary_mode == "finite" else (1.0, 0.0)
    return g * (state.u[-1] - ue), g * (state.v[-1] - ve)


def surface_oxygen(state, cfg):
    """Reconstruct the physical surface, not the last cell centre."""
    ju, _ = boundary_flux(state, cfg, conductance(cfg.Bi, 1/cfg.n_cells))
    return state.u[-1] - ju / (2*cfg.n_cells)


def _check(state):
    values = state.u + state.v + state.f
    if state.u_res is not None:
        values += [state.u_res, state.v_res]
    if not all(math.isfinite(x) and x >= 0 for x in values):
        raise ArithmeticError("nonfinite or negative inventory; no clipping applied")
    if max(state.f) > 1.0:
        raise ArithmeticError("solid inventory increased beyond initial value")
    if not all(math.isfinite(x) for x in (state.generated, state.net_u, state.net_v)):
        raise ArithmeticError("nonfinite integrated flux")


def _euler(state, cfg, h, g):
    n = cfg.n_cells
    ju, jv = boundary_flux(state, cfg, g)
    u, v, f = state.u, state.v, state.f
    new_u, new_v, new_f = [], [], []
    produced = 0.0
    for i in range(n):
        # One flux per shared face; core face is exactly no-flux.
        ul = (u[i-1]-u[i])*n*n if i else 0.0
        vl = (v[i-1]-v[i])*n*n if i else 0.0
        ur = (u[i+1]-u[i])*n*n if i < n-1 else -ju*n
        vr = (v[i+1]-v[i])*n*n if i < n-1 else -jv*n
        reaction = h * cfg.Gamma * cfg.K * f[i] * u[i]
        new_u.append(u[i] + h*(ul+ur) - reaction)
        new_v.append(v[i] + h*(vl+vr) + reaction)
        new_f.append(f[i] - reaction/cfg.Gamma)
        produced += reaction/n
    out = State(new_u, new_v, new_f, state.generated+produced,
                state.net_u+h*ju, state.net_v+h*jv)
    if cfg.boundary_mode == "finite":
        out.u_res = state.u_res + h*ju/cfg.reservoir_ratio
        out.v_res = state.v_res + h*jv/cfg.reservoir_ratio
    _check(out)
    return out


def _average(a, b):
    avg = lambda x, y: [(s+t)/2 for s, t in zip(x, y)]
    state = State(avg(a.u, b.u), avg(a.v, b.v), avg(a.f, b.f),
                  (a.generated+b.generated)/2, (a.net_u+b.net_u)/2,
                  (a.net_v+b.net_v)/2)
    if a.u_res is not None:
        state.u_res = (a.u_res+b.u_res)/2
        state.v_res = (a.v_res+b.v_res)/2
    _check(state)
    return state


def simulate(cfg, *, dt_scale=1.0, sample_dt=0.1, deadline=None):
    return _simulate(cfg, dt_scale=dt_scale, sample_dt=sample_dt, deadline=deadline)


def simulate_diffusion_test(cfg, *, boundary="robin", dt_scale=1.0, deadline=None):
    """Test-only initial u=0,v=1; Dirichlet is NOT a configuration mode."""
    if cfg.K != 0 or cfg.boundary_mode != "infinite" or boundary not in ("robin", "dirichlet_limit"):
        raise ValueError("diffusion reference requires no reaction and infinite exterior")
    return _simulate(cfg, dt_scale=dt_scale, sample_dt=.1, deadline=deadline,
                     diffusion_test_boundary=boundary)


def _simulate(cfg, *, dt_scale, sample_dt, deadline, diffusion_test_boundary=None):
    """Frozen initial state. dt_scale only tightens the internal CFL step.

    SSPRK2 is a convex average of two positivity-preserving Euler steps.
    Shared reaction and boundary transfers conserve linear C/O inventories.
    """
    if not math.isfinite(dt_scale) or not 0 < dt_scale <= 1:
        raise ValueError("dt_scale must lie in (0,1]")
    if not math.isfinite(sample_dt) or sample_dt <= 0:
        raise ValueError("positive finite sample interval required")
    cfg = Config.from_dict(cfg.to_dict())
    n = cfg.n_cells
    g = 0.0 if cfg.boundary_mode == "sealed" else conductance(cfg.Bi, 1/n)
    if diffusion_test_boundary == "dirichlet_limit":
        g = 2.0*n
    # u<=1, f<=1 is an invariant region for this equimolar initial domain.
    reservoir_loss = 0.0
    if cfg.boundary_mode == "finite":
        assert cfg.reservoir_ratio is not None
        reservoir_loss = g/cfg.reservoir_ratio
    loss = max(2*n*n + g*n + cfg.Gamma*cfg.K, cfg.K, reservoir_loss)
    if not math.isfinite(loss):
        raise ArithmeticError("unrepresentable rate coefficient")
    dt_max = .8 * dt_scale / loss
    if dt_max == 0 or cfg.tau_end/dt_max > 1_000_000 or cfg.tau_end/sample_dt > 5000:
        raise TimeoutError("bounded step/output budget exceeded")
    if deadline is None:
        deadline = time.monotonic() + 180
    state = State([1.0]*n, [0.0]*n, [1.0]*n)
    if diffusion_test_boundary is not None:
        state = State([0.0]*n, [1.0]*n, [1.0]*n)
    if cfg.boundary_mode == "finite":
        state.u_res, state.v_res = 1.0, 0.0
    records = [Record(0.0, state)]
    tau, steps = 0.0, 0
    for sample in range(1, math.ceil(cfg.tau_end/sample_dt)+1):
        target = min(sample*sample_dt, cfg.tau_end)
        while tau < target:
            if steps % 128 == 0 and time.monotonic() > deadline:
                raise TimeoutError("wall-time budget exceeded")
            h = min(dt_max, target-tau)
            if tau+h == tau:
                raise ArithmeticError("time step cannot advance floating point time")
            intermediate = _euler(state, cfg, h, g)
            state = _average(state, _euler(intermediate, cfg, h, g))
            tau = min(target, tau+h)
            steps += 1
        records.append(Record(tau, state))
    return Result(cfg, records, steps, dt_max)
