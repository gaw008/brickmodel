"""Frozen two-cell manufactured thermoelastic checks; each case runs externally bounded.

This research driver evolves Kelvin temperatures, not the old mol/J state. Its
auxiliary heat/work/entropy integrals use the same actual ODE stages. No fit or
material qualification is performed. Run only after code review and installation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import solve_ivp

from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
from sludge_sandbox.geometry import ReferenceSlab

PREREG_SHA = '12bd994b77f7dc264b3994181696f31140031ccbca8c786ab902ecf632237b35'
M, ALPHA, C, TR, V, G, GB = 1e9, 1e-4, 1e5, 300., 1e-4, 1., 2.
TIMES = np.linspace(0., 10., 101)
PARAMETERS = dict(biaxial_modulus_pa=M, linear_expansion_per_k=ALPHA,
    stress_free_heat_capacity_j_m3_k=C, reference_temperature_k=TR,
    conductivity_w_m_k=1., temperature_bounds_k=(290., 310.),
    strain_bounds=(-.01, .01), outer_temperature_k=300.,
    coefficient_classification='manufactured',
    mechanical_regime='symmetric_free_plane_stress')


def write_new(path: Path, value):
    with path.open('x') as stream:
        json.dump(value, stream, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def independent_fields(temperatures, temperature_rates, external):
    """Direct declared constitutive derivatives and constant face conductances."""
    t = np.asarray(temperatures, dtype=float)
    td = np.asarray(temperature_rates, dtype=float)
    mean, mdot = float(np.mean(t)), float(np.mean(td))
    strain, edot = ALPHA*(mean-TR), ALPHA*mdot
    stress = M*ALPHA*(mean-t)
    heat = np.array([-G*(t[0]-t[1]), G*(t[0]-t[1])])
    qb = GB*(300.-t[1]) if external else 0.
    heat[1] += qb
    power = 2*V*stress*edot
    u = C*(t-TR)+M*(strain+ALPHA*TR)**2-M*ALPHA**2*t**2
    udot = (C-2*t*M*ALPHA**2)*td+2*M*(strain+ALPHA*TR)*edot
    entropy = C*np.log(t/TR)+2*ALPHA*stress
    production = G*(t[0]-t[1])**2/(t[0]*t[1])
    if external:
        production += GB*(300.-t[1])**2/(300.*t[1])
    return dict(heat=heat, power=power, u=u, udot=udot, stress=stress,
                entropy=entropy, production=float(production), qb=float(qb),
                reservoir=-float(qb)/300.)


def analytic_relaxation(times):
    """60-digit positive-root bisection; independent of any candidate heat matrix."""
    rows = []
    with localcontext() as ctx:
        ctx.prec = 60
        d0, b, cap, m0 = map(Decimal, ('2', '10', '100000', '302'))
        k0 = cap-2*b*m0+2*b*b*d0*d0/cap
        for value in times:
            t = Decimal(str(float(value)))
            def residual(d):
                return k0*(d/d0).ln()-(b*b/cap)*(d*d-d0*d0)+Decimal('20000')*t
            if t == 0:
                low = high = d0
            else:
                low, high = Decimal('.000001'), d0
                if not residual(low) < 0 < residual(high):
                    raise ValueError('analytic_root_not_bracketed')
                for _ in range(160):
                    if high-low <= Decimal('1e-12'):
                        break
                    middle = (low+high)/2
                    if residual(middle) > 0:
                        high = middle
                    else:
                        low = middle
                else:
                    raise ValueError('analytic_root_did_not_converge')
            d = (low+high)/2
            mean = m0+(b/cap)*(d*d-d0*d0)
            # |dm/dd| <= 2*b*d0/C; binary64 conversion is separately much smaller.
            error_bound = (high-low)*(1+2*b*d0/cap)/2+Decimal('1e-12')
            if error_bound > Decimal('2e-7'):
                raise ValueError('analytic_root_bound_too_large')
            rows.append(dict(time_s=float(t), temperatures_k=[float(mean+d),float(mean-d)],
                delta_lower=str(low), delta_upper=str(high),
                residual_lower=str(residual(low)), residual_upper=str(residual(high)),
                temperature_error_bound_k=str(error_bound)))
    return rows


def matrix_rhs(temperatures, external, *, omit_coupling=False):
    """Independent full dense thermal matrix. Negative control omits its rank-one term."""
    t = np.asarray(temperatures, dtype=float)
    if t.shape != (2,) or not np.all(np.isfinite(t)) or np.any(t < 290.) or np.any(t > 310.):
        raise ValueError('independent_rhs_temperature_outside_registered_domain')
    eigenstrain = ALPHA*(t-TR)
    common_strain = ALPHA*(float(np.mean(t))-TR)
    if (abs(common_strain) > .01 or np.any(np.abs(eigenstrain) > .01)
            or np.any(np.abs(common_strain-eigenstrain) > .01)):
        raise ValueError('independent_rhs_strain_outside_registered_domain')
    heat = np.array([-G*(t[0]-t[1]), G*(t[0]-t[1])])
    if external:
        heat[1] += GB*(300.-t[1])
    diagonal = C-2*M*ALPHA**2*t
    if not np.all(diagonal > 0.):
        raise ValueError('independent_rhs_nonpositive_fixed_strain_heat_capacity')
    matrix = np.diag(diagonal)
    if not omit_coupling:
        matrix += np.outer(2*M*ALPHA**2*t, np.full(2, .5))
    return np.linalg.solve(matrix, heat/V)


def tracked_reference_rhs(external, *, omit_coupling=False):
    bounds = dict(min_temperature_k=None, max_temperature_k=None,
                  min_fixed_strain_heat_capacity_j_m3_k=None, rhs_calls=0)
    def rhs(time, temperatures):
        rates = matrix_rhs(temperatures, external, omit_coupling=omit_coupling)
        bounds['rhs_calls'] += 1
        low, high = float(np.min(temperatures)), float(np.max(temperatures))
        ce = float(C-2*M*ALPHA**2*high)
        for key,value,operation in [('min_temperature_k',low,min),
                ('max_temperature_k',high,max),
                ('min_fixed_strain_heat_capacity_j_m3_k',ce,min)]:
            bounds[key] = value if bounds[key] is None else operation(bounds[key],value)
        return rates
    return rhs, bounds


def run_candidate(model, initial, policy, directory, name):
    stages = directory/f'{name}-stages.jsonl'
    start = time.monotonic()
    calls = 0
    # State: T[2], integral Q[2], integral P[2], external Q, reservoir S, production S.
    with stages.open('x') as log:
        def rhs(t, y):
            nonlocal calls
            evaluation = model.evaluate(y[:2])
            calls += 1
            log.write(json.dumps(dict(time_s=float(t), evaluation=asdict(evaluation)),
                                 allow_nan=False, separators=(',', ':'))+'\n')
            return np.r_[evaluation.temperature_rates_k_s, evaluation.cell_heat_in_w,
                evaluation.cell_mechanical_power_w, evaluation.external_heat_in_w,
                evaluation.reservoir_entropy_rate_w_k, evaluation.total_entropy_production_w_k]
        result = solve_ivp(rhs, (0., 10.), np.r_[initial, np.zeros(7)],
            method='DOP853', dense_output=True, **policy)
    if not result.success or result.t[-1] != 10.:
        write_new(directory/f'{name}-failure.json', dict(message=result.message,
                  accepted_times_s=result.t.tolist(), accepted_states=result.y.T.tolist()))
        raise RuntimeError('candidate_path_incomplete')
    samples = result.sol(TIMES).T
    report = dict(status='completed', elapsed_s=time.monotonic()-start, policy=policy,
        state_columns=['T0_K','T1_K','heat0_J','heat1_J','work0_J','work1_J',
                       'external_heat_J','reservoir_entropy_J_per_K','production_J_per_K'],
        nfev=result.nfev, logged_rhs=calls, message=result.message,
        accepted_times_s=result.t.tolist(), accepted_states=result.y.T.tolist(),
        times_s=TIMES.tolist(), samples=samples.tolist(),
        observations=[asdict(model.evaluate(row[:2])) for row in samples])
    write_new(directory/f'{name}.json', report)
    return report


def summarize(report, initial, reference, external):
    initial_fields = independent_fields(initial, (0.,0.), external)
    local, global_energy, entropy, coupling_residual = [], [], [], []
    reported_stress, reported_u_error, reported_s_error = [], [], []
    pointwise = []
    for row, observation in zip(report['samples'], report['observations'], strict=True):
        fields = independent_fields(row[:2], observation['temperature_rates_k_s'], external)
        local.append(V*(fields['u']-initial_fields['u'])-row[2:4]-np.array(row[4:6]))
        global_energy.append(V*sum(fields['u']-initial_fields['u'])-row[6])
        entropy.append(V*sum(fields['entropy']-initial_fields['entropy'])+row[7]-row[8])
        coupling_residual.append(V*fields['udot']-fields['heat']-fields['power'])
        reported_stress.append([point['stress_pa'] for point in observation['points']])
        reported_u_error.append([V*(point['internal_energy_j_m3']-u)
                                 for point,u in zip(observation['points'],fields['u'],strict=True)])
        reported_s_error.append([V*(point['entropy_j_m3_k']-s)
                                 for point,s in zip(observation['points'],fields['entropy'],strict=True)])
        pointwise.append(dict(temperatures_k=row[:2], reported_stress_pa=reported_stress[-1],
                             reconstructed_stress_pa=fields['stress'].tolist(),
                             local_energy_residual_j=local[-1].tolist()))
    temperatures = np.asarray(report['samples'])[:,:2]
    reference = np.asarray(reference)
    stress = M*ALPHA*(np.mean(temperatures,axis=1)[:,None]-temperatures)
    ref_stress = M*ALPHA*(np.mean(reference,axis=1)[:,None]-reference)
    temperature_error = float(np.max(np.abs(temperatures-reference)))
    cell_error = float(np.max(np.abs(local)))
    total_error = float(np.max(np.abs(global_energy)))
    return dict(temperature_error_k=temperature_error,
        stress_error_pa=float(np.max(np.abs(np.asarray(reported_stress)-ref_stress))),
        reported_stress_consistency_error_pa=float(np.max(np.abs(np.asarray(reported_stress)-stress))),
        reported_cell_internal_energy_consistency_error_j=float(np.max(np.abs(reported_u_error))),
        reported_cell_entropy_consistency_error_j_k=float(np.max(np.abs(reported_s_error))),
        local_energy_error_j=cell_error, global_energy_error_j=total_error,
        entropy_identity_error_j_k=float(np.max(np.abs(entropy))),
        independently_reconstructed_instantaneous_energy_error_w=float(np.max(np.abs(coupling_residual))),
        gates=dict(temperature=temperature_error/4 <= 1e-6,
                   local_energy=cell_error/80 <= 1e-8, global_energy=total_error/80 <= 1e-8),
        pointwise=pointwise)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=('relaxation','cooling'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preregistration', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.preregistration.read_bytes()).hexdigest() != PREREG_SHA:
        raise ValueError('preregistration_changed')
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    external = args.case == 'cooling'
    initial = [304.,304.] if external else [304.,300.]
    parameters = dict(PARAMETERS, outer_boundary='fixed_temperature' if external else 'adiabatic')
    model = CoolingThermoelasticPlate(reference=ReferenceSlab(.02,.01,2), **parameters)
    write_new(args.output/'INPUTS.json', dict(case=args.case, preregistration_sha256=PREREG_SHA,
        parameters=parameters, reference=dict(half_thickness_m=.02,reference_area_m2=.01,cells=2),
        initial_temperatures_k=initial, material_qualified=False))
    policies = dict(coarse=dict(rtol=1e-9,atol=1e-11,max_step=.05),
                    fine=dict(rtol=1e-11,atol=1e-13,max_step=.025))
    runs = {name:run_candidate(model,initial,policy,args.output,name) for name,policy in policies.items()}
    if external:
        reference_rhs, reference_bounds = tracked_reference_rhs(external)
        reference_run = solve_ivp(reference_rhs, (0.,10.), initial,
            method='DOP853', t_eval=TIMES, **policies['fine'])
        if not reference_run.success or reference_run.t[-1] != 10.:
            raise RuntimeError('dense_reference_incomplete')
        reference = reference_run.y.T.tolist()
        write_new(args.output/'reference.json',dict(temperatures_k=reference,
            times_s=reference_run.t.tolist(), nfev=reference_run.nfev,
            rhs_domain_bounds=reference_bounds, method='independent_dense_rhs'))
    else:
        roots = analytic_relaxation(TIMES)
        reference = [row['temperatures_k'] for row in roots]
        write_new(args.output/'reference.json',dict(method='independent_60_digit_bisection', roots=roots))
    negative_rhs, negative_bounds = tracked_reference_rhs(external, omit_coupling=True)
    negative = solve_ivp(negative_rhs,
        (0.,10.),initial,method='DOP853',t_eval=TIMES,**policies['fine'])
    if not negative.success or negative.t[-1] != 10.:
        raise RuntimeError('negative_control_incomplete')
    negative_error = float(np.max(np.abs(negative.y.T-reference)))
    write_new(args.output/'negative_control.json',dict(method='omit_rank_one_thermal_coupling',
        times_s=negative.t.tolist(),temperatures_k=negative.y.T.tolist(),nfev=negative.nfev,
        rhs_domain_bounds=negative_bounds,
        reference_error_k=negative_error, detected_by_temperature_gate=negative_error/4 > 1e-6))
    metrics = {name:summarize(run,initial,reference,external) for name,run in runs.items()}
    refinement = float(np.max(np.abs(np.asarray(runs['coarse']['samples'])[:,:2]
                         -np.asarray(runs['fine']['samples'])[:,:2])))
    gates = {f'{name}_{gate}':passed for name,row in metrics.items() for gate,passed in row['gates'].items()}
    gates.update(time_refinement=refinement/4 <= 1e-7,
                 negative_control_detected=negative_error/4 > 1e-6)
    write_new(args.output/'RESULT.json',dict(status='completed',elapsed_s=time.monotonic()-start,
        metrics=metrics,refinement_difference_k=refinement,gates=gates,
        numerical_policy_pass=all(gates.values()),material_qualified=False,
        spatial_convergence_demonstrated=False,full_firing_cycle=False))


if __name__ == '__main__':
    main()
