"""Bounded independent references and prescribed 3-case refinement checks."""
from dataclasses import replace
import math

from diagnostics import summarize, timeseries_rows
from solver import simulate, simulate_diffusion_test

# Numerical acceptance gates, distinct from chemistry diagnostic thresholds and
# the invariant 1e-6 conservation audit. No artifact can change these constants.
SPACE_GATES = dict(carbon_mean=0.005, carbon_max=0.01, u_core=0.015, event_tau=0.05)
TIME_GATES = dict(carbon_mean=0.0001, carbon_max=0.0001, u_core=0.0001, event_tau=0.005)


def normalization_check():
    # Exponents in (length, time, amount); porosity and concentration ratio are 0.
    add = lambda a,b: tuple(x+y for x,y in zip(a,b))
    sub = lambda a,b: tuple(x-y for x,y in zip(a,b))
    zero, length, area, volume = (0,0,0), (1,0,0), (2,0,0), (3,0,0)
    diffusion, concentration, speed, rate = (2,-1,0), (-3,0,1), (1,-1,0), (0,-1,0)
    tau_d = sub(add(length, length), diffusion)
    groups = dict(tau_D=tau_d, Gamma=sub(concentration, concentration),
                  K=add(rate,tau_d), Bi=sub(add(speed,length), diffusion),
                  rho=sub(volume,add(area,length)),
                  diffusion_pde_coefficient=add(sub(diffusion,add(length,length)),tau_d))
    passed = groups["tau_D"] == (0,1,0) and all(v == zero for k,v in groups.items() if k != "tau_D")
    # Atom counts for C, O2, CO2 and signed stoichiometric vector (-1,-1,+1).
    carbon = -1*1 - 1*0 + 1*1
    oxygen = -1*0 - 1*2 + 1*2
    mass = -12-32+44
    passed = passed and (carbon, oxygen, mass) == (0,0,0)
    return dict(status="passed" if passed else "failed", dimension_exponents=groups,
                tau_D_formula="epsilon_o*L^2/D_eff", gas_basis="pore_volume",
                diffusion_basis="total_area", stoichiometric_residuals=dict(C=carbon,O=oxygen,mass=mass),
                note="algebra_and_units_only_no_physical_time_conversion_or_energy_audit")


def diffusion_reference(n, tau, boundary, bi=1.0):
    """Fourier eigenfunctions integrated over each FV cell, not point values."""
    values = [1.0]*n
    for m in range(80):
        if boundary == "dirichlet_limit":
            lam = (m+.5)*math.pi
            coefficient = 2*(-1)**m/lam
        else:
            # Neumann at 0, Robin at 1 => lambda*tan(lambda)=Bi.
            low, high = m*math.pi, (m+.5)*math.pi
            for _ in range(60):
                mid = (low+high)/2
                if mid*math.tan(mid) < bi:
                    low = mid
                else:
                    high = mid
            lam = (low+high)/2
            coefficient = (math.sin(lam)/lam)/(.5+math.sin(2*lam)/(4*lam))
        decay = math.exp(-lam*lam*tau)
        for i in range(n):
            avg_cos = n*(math.sin(lam*(i+1)/n)-math.sin(lam*i/n))/lam
            values[i] -= coefficient*avg_cos*decay
    return values


def closed_reference(gamma, k, tau):
    if gamma == 1:
        return 1/(1+k*tau)
    difference = gamma-1
    oxygen = difference/(gamma*math.exp(k*difference*tau)-1)
    return (oxygen+difference)/gamma


def comparison(coarse, fine):
    a, b = timeseries_rows(coarse), timeseries_rows(fine)
    if [r["tau"] for r in a] != [r["tau"] for r in b]:
        raise ValueError("refinement samples must align")
    fields = ("carbon_mean", "carbon_max", "u_core")
    answer = dict(max_trajectory_difference={key: max(abs(x[key]-y[key]) for x,y in zip(a,b)) for key in fields},
                  horizon_difference={key: abs(a[-1][key]-b[-1][key]) for key in fields}, events={})
    sa, sb = summarize(coarse), summarize(fine)
    for key in ("t_burn95", "t_burn99", "t_local_burn95", "t_local_burn99"):
        if sa[key] is None and sb[key] is None:
            event = dict(status="not_comparable_not_reached", delta=None)
        elif sa[key] is None or sb[key] is None:
            event = dict(status="event_presence_mismatch", delta=None)
        else:
            event = dict(status="compared", delta=abs(sa[key]-sb[key]))
        answer["events"][key] = event
    return answer


def refinement_pass(comparisons, gates):
    coarse, fine = comparisons
    for key in ("carbon_mean", "carbon_max", "u_core"):
        first, second = coarse["max_trajectory_difference"][key], fine["max_trajectory_difference"][key]
        if second > gates[key] or (first > 1e-10 and second >= .7*first):
            return False
    for event in fine["events"].values():
        if event["status"] == "event_presence_mismatch":
            return False
        if event["delta"] is not None and event["delta"] > gates["event_tau"]:
            return False
    return True


def run_description(result, dt_scale):
    s = summarize(result)
    return dict(n_cells=result.config.n_cells, dt_scale=dt_scale, dt_max=result.dt_max,
                steps=result.steps, final_carbon_mean=s["final"]["carbon_mean"],
                final_carbon_max=s["final"]["carbon_max"], final_u_core=s["final"]["u_core"],
                t_burn95=s["t_burn95"], t_burn99=s["t_burn99"],
                t_local_burn95=s["t_local_burn95"], t_local_burn99=s["t_local_burn99"],
                event_status95=s["t_burn95_status"], event_status99=s["t_burn99_status"])


def verify_numerics(baseline, *, deadline=None):
    convergence = {}
    for sid in ("base", "reaction_fast", "finite_small"):
        mid = baseline[sid]
        if mid.config.n_cells != 15 or mid.config.tau_end != 20:
            raise ValueError("refinement baseline must be frozen 15-cell horizon-20 case")
        spatial = [simulate(replace(mid.config, n_cells=7), deadline=deadline), mid,
                   simulate(replace(mid.config, n_cells=31), deadline=deadline)]
        temporal = [mid, simulate(mid.config, dt_scale=.5, deadline=deadline),
                    simulate(mid.config, dt_scale=.25, deadline=deadline)]
        sc = [comparison(a,b) for a,b in zip(spatial, spatial[1:])]
        tc = [comparison(a,b) for a,b in zip(temporal, temporal[1:])]
        convergence[sid] = dict(space_runs=[run_description(r,1) for r in spatial],
                                time_runs=[run_description(r,s) for r,s in zip(temporal,(1,.5,.25))],
                                space_comparisons=sc, time_comparisons=tc,
                                passed=refinement_pass(sc,SPACE_GATES) and refinement_pass(tc,TIME_GATES))
    base = baseline["base"].config
    diffusion = {}
    for boundary in ("robin", "dirichlet_limit"):
        errors = []
        for n in (7,15,31):
            cfg = replace(base, K=0, n_cells=n, tau_end=.2)
            state = simulate_diffusion_test(cfg, boundary=boundary, deadline=deadline).records[-1].state
            expected = diffusion_reference(n,.2,boundary)
            error = max(abs(a-b) for a,b in zip(state.u,expected))
            errors.append(dict(n_cells=n, tau=.2, max_cell_average_error=error))
        diffusion[boundary] = errors
    closed = []
    for gamma in (.25,1,2):
        cfg = replace(base, Gamma=gamma, boundary_mode="sealed", reservoir_ratio=None)
        result = simulate(cfg, deadline=deadline)
        error = max(abs(sum(r.state.f)/cfg.n_cells-closed_reference(gamma,cfg.K,r.tau)) for r in result.records)
        closed.append(dict(Gamma=gamma, max_carbon_error=error, final_carbon_mean=sum(result.records[-1].state.f)/cfg.n_cells))
    norm = normalization_check()
    diffusion_pass = all(v[-1]["max_cell_average_error"] < 3e-4 and
                         v[2]["max_cell_average_error"] < v[1]["max_cell_average_error"]/3 and
                         v[1]["max_cell_average_error"] < v[0]["max_cell_average_error"]/3
                         for v in diffusion.values())
    closed_pass = all(row["max_carbon_error"] < 2e-6 for row in closed)
    passed = all(c["passed"] for c in convergence.values()) and diffusion_pass and closed_pass and norm["status"] == "passed"
    return dict(status="passed" if passed else "failed", normalization=norm,
                convergence=convergence, diffusion=diffusion, diffusion_passed=diffusion_pass,
                closed_reaction=dict(status="passed" if closed_pass else "failed", cases=closed),
                gates=dict(space=SPACE_GATES,time=TIME_GATES,refinement_ratio_max=.7,
                           ratio_roundoff_floor=1e-10, diffusion_cell_error=3e-4, closed_carbon_error=2e-6),
                limitations=["numerical_convergence_not_material_calibration", "null_events_are_not_zero_errors",
                             "core_is_first_cell_average", "event_interpolation_uses_exported_0.1_tau_samples"])
