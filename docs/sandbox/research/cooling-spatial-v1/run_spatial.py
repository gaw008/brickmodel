"""One frozen manufactured spatial grid, with two BDF accuracy policies.

The command is a research entry point, not a material model or a parameter scan.
Only its supervisor supplies the shared wall-clock deadline. Tests may inject a
fake accepted-step solver; the command always uses the inspected SciPy BDF.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import scipy
from scipy.integrate import BDF
from scipy.sparse import csc_matrix, vstack, hstack

import sludge_sandbox.cooling_thermoelastic_plate as plate_module
import sludge_sandbox.exchanges as exchange_module
import sludge_sandbox.geometry as geometry_module


PROTOCOL_SHA = 'dfa6363b6e83d0a2de8495153ce81c7a814ee55901d54a43f84f790baa7872fb'
BDF_SHA = '92014c6ddb85e0757ae2b951dfd783a4b5b92a9829a5cdf3f26b41c8390fe4b7'
CORE_SHA = {
    'plate': '33851857946f16b560529ad8a9d3ab1bc4fec6c1a18ae63bb9897d77a03746d7',
    'geometry': '384d35d67ed7aa043991d69e795169bafddb8e1466c1d1f0b072521c10a72312',
    'exchanges': '09f148ff097ac6467e38905b36da6de1e6093209b8ff598ff8fcf2befde4d983',
}
M, ALPHA, C, K_COND, TR, L, AREA = 1e9, 1e-4, 1e5, 1., 300., .02, .01
B = M * ALPHA**2
T_SCALE, E_SCALE, S_SCALE = 4., 80., 80./300.
ROUND_T = 128. * 2.**-53 * 310. / T_SCALE
TIMES = np.arange(101, dtype=float) / 10.
POLICIES = {
    'coarse': dict(rtol=1e-9, atol=1e-11, max_step=.05),
    'fine': dict(rtol=1e-11, atol=1e-13, max_step=.025),
}


class StudyError(ValueError):
    pass


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def fingerprint(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def runtime_identity(protocol):
    identity = dict(protocol=fingerprint(protocol), driver=fingerprint(__file__),
                    python=sys.version, executable=sys.executable,
                    scipy_version=scipy.__version__, numpy_version=np.__version__,
                    bdf=fingerprint(inspect.getsourcefile(BDF)))
    identity['core'] = {name: fingerprint(module.__file__) for name, module in
                        [('plate', plate_module), ('geometry', geometry_module),
                         ('exchanges', exchange_module)]}
    if identity['protocol']['sha256'] != PROTOCOL_SHA:
        raise StudyError('protocol_identity_mismatch')
    if identity['bdf']['sha256'] != BDF_SHA or scipy.__version__ != '1.18.1':
        raise StudyError('unreviewed_bdf_dense_output_implementation')
    if any(identity['core'][name]['sha256'] != sha for name, sha in CORE_SHA.items()):
        raise StudyError('frozen_core_identity_mismatch')
    return identity


def deadline_guard(deadline):
    if not math.isfinite(deadline):
        raise StudyError('nonfinite_deadline')
    def guard():
        if time.monotonic() >= deadline:
            raise TimeoutError('shared_grid_deadline_exceeded')
    return guard


def cell_count(cells):
    if type(cells) is not int or cells not in (16, 32, 64):
        raise StudyError('registered_grid_required')
    return cells


def initial_temperatures(cells):
    n = cell_count(cells)
    x = math.pi / (2*n)
    return 302. + 2*(math.sin(x)/x)*np.cos(math.pi*(np.arange(n)+.5)/n)


def continuous_initial_reference():
    """Machin pi, alternating-series tails, then the rationalized mean rate."""
    with localcontext() as ctx:
        ctx.prec = 80
        def arctan_inverse(integer):
            x = Decimal(1)/integer
            power, total, sign, count = x, Decimal(0), 1, 0
            while True:
                term = power/(2*count+1)
                total += sign*term
                count += 1
                power *= x*x
                sign = -sign
                next_term = power/(2*count+1)
                if next_term < Decimal('1e-85'):
                    return total, next_term, count
        a5, tail5, n5 = arctan_inverse(5)
        a239, tail239, n239 = arctan_inverse(239)
        pi = 16*a5-4*a239
        # 1e-70 exceeds 80-digit arithmetic accumulation in these <1000
        # bounded operations, in addition to the rigorous alternating tails.
        pi_margin = 16*tail5+4*tail239+Decimal('1e-70')
        b, cap, a, mean, length = map(Decimal, ('10', '100000', '2', '302', '.02'))
        d0, d1 = cap-2*b*mean, 2*b*a
        root = (d0*d0-d1*d1).sqrt()
        def rate(p):
            return -2*b*(p/length)**2*a*a/(cap*(d0+root))
        value = rate(pi)
        # This margin is >15 decimal digits above the internal arithmetic
        # scale and leaves more than 50 resolved decimal places for this rate.
        low = rate(pi+pi_margin)-Decimal('1e-65')
        high = rate(pi-pi_margin)+Decimal('1e-65')
        return dict(method='Decimal Machin pi; rationalized continuous mean rate',
                    precision=ctx.prec, pi=str(pi), pi_abs_error_bound=str(pi_margin),
                    arctan_terms=[n5, n239], rate_k_s=str(value),
                    rate_bounds_k_s=[str(low), str(high)],
                    formula='-2*b*k*(pi/L)^2*a^2/(C*(d0+sqrt(d0^2-(2*b*a)^2)))',
                    inputs=dict(b='10', C='100000', k='1', L='.02', a='2', mean='302'))


def finite_array(values, shape, name):
    try:
        values = np.asarray(values, dtype=float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise StudyError(f'invalid_{name}') from exc
    if values.shape != shape or not np.all(np.isfinite(values)):
        raise StudyError(f'invalid_{name}')
    return values


class SpatialSystem:
    def __init__(self, cells):
        self.n = cell_count(cells)
        self.h, self.v = L/self.n, AREA*L/self.n
        self.g = K_COND*AREA/self.h
        self.w = np.full(self.n, 1/self.n)
        self.K = np.diag(np.full(self.n, -2.))
        self.K[0, 0] = self.K[-1, -1] = -1.
        self.K += np.diag(np.ones(self.n-1), 1)+np.diag(np.ones(self.n-1), -1)
        self.K *= K_COND/self.h**2
        self.model = plate_module.CoolingThermoelasticPlate(
            reference=geometry_module.ReferenceSlab(L, AREA, self.n),
            biaxial_modulus_pa=M, linear_expansion_per_k=ALPHA,
            stress_free_heat_capacity_j_m3_k=C, reference_temperature_k=TR,
            conductivity_w_m_k=K_COND, temperature_bounds_k=(290., 310.),
            strain_bounds=(-.01, .01), outer_temperature_k=300.,
            outer_boundary='adiabatic', coefficient_classification='manufactured',
            mechanical_regime='symmetric_free_plane_stress')

    def temperatures(self, values):
        t = finite_array(values, (self.n,), 'temperature_state')
        if np.min(t) < 290. or np.max(t) > 310.:
            raise StudyError('temperature_outside_registered_domain')
        # Convex mean and this temperature domain imply |e|,|eigen|<=.001
        # and |mismatch|<=.002. Retain explicit independent checks as well.
        mean = math.fsum(t)/self.n
        if (np.any(C-2*B*t <= 0.) or abs(ALPHA*(mean-TR)) > .01
                or np.any(np.abs(ALPHA*(t-TR)) > .01)
                or np.any(np.abs(ALPHA*(mean-t)) > .01)):
            raise StudyError('independent_thermoelastic_domain_failure')
        return t

    def fields(self, temperatures, rates):
        """O(N) equations independent of candidate constitutive/face helpers."""
        t = self.temperatures(temperatures)
        r = finite_array(rates, (self.n,), 'temperature_rate')
        mean, mdot = math.fsum(t)/self.n, math.fsum(r)/self.n
        flux = self.g*(t[:-1]-t[1:])
        heat = np.diff(np.r_[0., -flux, 0.])
        q, ce = heat/self.v, C-2*B*t
        stress = M*ALPHA*(mean-t)
        strain, edot = ALPHA*(mean-TR), ALPHA*mdot
        mismatch = strain-ALPHA*(t-TR)
        entropy = C*np.log1p((t-TR)/TR)+2*ALPHA*stress
        psi = C*((t-TR)-t*np.log1p((t-TR)/TR))+M*mismatch*mismatch
        # Full Legendre form; not thermal energy plus elastic free energy.
        u = C*(t-TR)+M*(strain+ALPHA*TR)**2-B*t*t
        power = 2*self.v*stress*edot
        udot = ce*r+2*M*(strain+ALPHA*TR)*edot
        sdot = ce/t*r+2*M*ALPHA*edot
        production_faces = self.g*(t[:-1]-t[1:])**2/(t[:-1]*t[1:])
        variance = math.fsum((t-mean)**2)/self.n
        return dict(t=t, r=r, mean=mean, mdot=mdot, heat=heat, q=q, ce=ce,
                    flux=flux, stress=stress, strain=strain, edot=edot,
                    mismatch=mismatch, u=u, psi=psi, entropy=entropy, power=power,
                    udot=udot, sdot=sdot, production_faces=production_faces,
                    production=math.fsum(production_faces), variance=variance,
                    total_u=self.v*math.fsum(u), total_s=self.v*math.fsum(entropy),
                    total_psi=self.v*math.fsum(psi),
                    variance_u=AREA*L*(C*(mean-TR)-B*variance))

    def jacobian(self, temperatures):
        t = self.temperatures(temperatures)
        fields = self.fields(t, np.zeros(self.n))
        a = np.diag(fields['ce'])+np.outer(2*B*t, self.w)
        rates = np.linalg.solve(a, fields['q'])
        mdot = math.fsum(rates)/self.n
        jac = np.linalg.solve(a, self.K-2*B*np.diag(mdot-rates))
        mean = math.fsum(t)/self.n
        dp = 2*self.v*B*(mdot*(np.ones((self.n, 1))*self.w-np.eye(self.n))
                        + np.outer(mean-t, self.w@jac))
        ds = np.zeros(self.n)
        common = self.g*(t[:-1]-t[1:])*(t[:-1]+t[1:])
        ds[:-1] += common/(t[:-1]**2*t[1:])
        ds[1:] -= common/(t[:-1]*t[1:]**2)
        left = vstack([csc_matrix(jac), csc_matrix(self.v*self.K),
                       csc_matrix(dp), csc_matrix(ds[None, :])], format='csc')
        result = hstack([left, csc_matrix((3*self.n+1, 2*self.n+1))], format='csc')
        if not np.all(np.isfinite(result.data)):
            raise StudyError('nonfinite_analytic_jacobian')
        return result


class StageAudit:
    def __init__(self):
        self.calls = dict(rhs=0, jacobian=0, accepted=0, sample=0)
        self.extremes, self.residuals = {}, {}
        self.last_call = None

    def begin(self, when, y, kind):
        self.calls[kind] += 1
        raw = np.asarray(y).tolist()
        # Failed nonfinite inputs remain legible without invalid JSON NaN.
        safe = [float(x) if isinstance(x, (float,int,np.floating,np.integer)) and math.isfinite(x)
                else repr(x) for x in raw] if isinstance(raw, list) else repr(raw)
        self.last_call = dict(time_s=float(when), kind=kind, state=safe)

    def observe(self, system, when, y, kind):
        self.begin(when, y, kind)
        y = finite_array(y, (3*system.n+1,), 'augmented_state')
        t = system.temperatures(y[:system.n])
        ev = system.model.evaluate(t)
        f = system.fields(t, ev.temperature_rates_k_s)
        context = dict(time_s=float(when), kind=kind, temperatures_k=t.tolist(),
                       rates_k_s=f['r'].tolist())
        values = dict(temperature_k=t, ce_j_m3_k=f['ce'],
                      strain_margin=.01-np.abs(np.r_[f['strain'], ALPHA*(t-TR), f['mismatch']]))
        for name, array in values.items():
            for side, op in [('min', np.argmin), ('max', np.argmax)]:
                index = int(op(array))
                value = float(array[index])
                key = f'{side}_{name}'
                old = self.extremes.get(key)
                if old is None or (value < old['value'] if side == 'min' else value > old['value']):
                    self.extremes[key] = dict(value=value, index=index, **context)
        residuals = dict(
            thermal_equation_w_m3=f['ce']*f['r']+2*B*t*f['mdot']-f['q'],
            strain_rate_per_s=np.array([ev.in_plane_strain_rate_per_s-f['edot']]),
            local_first_law_w=system.v*f['udot']-f['heat']-f['power'],
            entropy_equation_w_m3=t*f['sdot']-f['q'],
            total_mechanical_power_w=np.array([math.fsum(f['power'])]),
            candidate_heat_w=np.asarray(ev.cell_heat_in_w)-f['heat'],
            candidate_power_w=np.asarray(ev.cell_mechanical_power_w)-f['power'],
            candidate_u_j_m3=np.array([p.internal_energy_j_m3 for p in ev.points])-f['u'],
            candidate_stress_pa=np.array([p.stress_pa for p in ev.points])-f['stress'],
            candidate_s_j_m3_k=np.array([p.entropy_j_m3_k for p in ev.points])-f['entropy'],
            candidate_udot_j_m3_s=np.asarray(ev.cell_u_rates_j_m3_s)-f['udot'],
            candidate_sdot_j_m3_k_s=np.asarray(ev.cell_s_rates_j_m3_k_s)-f['sdot'],
            candidate_entropy_production_w_k=np.array([ev.total_entropy_production_w_k-f['production']]))
        for name, values in residuals.items():
            if not np.all(np.isfinite(values)):
                raise StudyError(f'nonfinite_stage_residual:{name}')
            index = int(np.argmax(np.abs(values)))
            value = float(values[index])
            if name not in self.residuals or abs(value) > abs(self.residuals[name]['value']):
                self.residuals[name] = dict(value=value, index=index, **context)
        if np.any(f['production_faces'] < 0.) or not math.isfinite(f['production']):
            raise StudyError('invalid_face_entropy_production')
        return ev, f

    def report(self):
        return dict(calls=self.calls, extrema=self.extremes, residuals=self.residuals,
                    last_call=self.last_call,
                    residual_policy='independent raw maxima; integral/domain gates are separate')


def ledger_row(system, when, y, f, initial):
    n, v = system.n, system.v
    local = v*(f['u']-initial['u'])-y[n:2*n]-y[2*n:3*n]
    global_residual = f['total_u']-initial['total_u']
    entropy_residual = f['total_s']-initial['total_s']-y[-1]
    ledger = dict(local_residual_j=local.tolist(), global_residual_j=global_residual,
                  entropy_residual_j_k=entropy_residual,
                  heat_sum_j=math.fsum(y[n:2*n]), work_sum_j=math.fsum(y[2*n:3*n]),
                  u_variance_identity_residual_j=f['total_u']-f['variance_u'],
                  external_heat_j=0., reservoir_entropy_j_k=0.)
    gates = dict(local_energy=bool(max(abs(local))/E_SCALE <= 1e-8),
                 global_energy=bool(abs(global_residual)/E_SCALE <= 1e-8),
                 entropy=bool(abs(entropy_residual)/S_SCALE <= 1e-8))
    return dict(time_s=float(when), state=y.tolist(), ledger=ledger, gates=gates,
                fields=dict(mean_temperature_k=f['mean'], variance_k2=f['variance'],
                            common_strain=f['strain'], common_strain_rate_s=f['edot'],
                            total_u_j=f['total_u'], total_psi_j=f['total_psi'],
                            total_entropy_j_k=f['total_s'], production_w_k=f['production'],
                            min_stress_pa=float(min(f['stress'])), max_stress_pa=float(max(f['stress'])),
                            total_mechanical_power_w=math.fsum(f['power'])))


def dense_envelope(dense, n, state_size, left, right):
    """Outward interval evaluation of the inspected BdfDenseOutput polynomial."""
    if (type(dense.order) not in (int, np.int64, np.int32) or not 1 <= dense.order <= 5
            or dense.t_old != left or dense.t != right or not left < right):
        raise StudyError('unsupported_dense_segment')
    shifts = finite_array(dense.t_shift, (dense.order,), 'dense_shift')
    denom = finite_array(dense.denom, (dense.order,), 'dense_denominator')
    coefficients = finite_array(dense.D, (dense.order+1, state_size), 'dense_coefficients')[:, :n]
    if np.any(denom <= 0.):
        raise StudyError('nonpositive_dense_denominator')
    down = lambda x: np.nextafter(x, -np.inf)
    up = lambda x: np.nextafter(x, np.inf)
    def multiply(a, b):
        products = np.array([a[0]*b[0], a[0]*b[1], a[1]*b[0], a[1]*b[1]])
        return down(np.min(products, axis=0)), up(np.max(products, axis=0))
    lower, upper = coefficients[0].copy(), coefficients[0].copy()
    prefix = (1., 1.)
    magnitude = np.abs(coefficients[0]).copy()
    for j, (shift, denominator) in enumerate(zip(shifts, denom)):
        factor = (down(down(left-shift)/denominator), up(up(right-shift)/denominator))
        prefix = multiply(prefix, factor)
        term = multiply(prefix, (coefficients[j+1], coefficients[j+1]))
        lower, upper = down(lower+term[0]), up(upper+term[1])
        magnitude = up(magnitude+np.maximum(np.abs(term[0]), np.abs(term[1])))
    # Include the binary64 dot/cumulative-product evaluation in SciPy, not
    # merely the real polynomial defined by its stored coefficients.
    margin = up(64*2.**-53*magnitude)
    lower, upper = down(lower-margin), up(upper+margin)
    if not np.all(np.isfinite(np.r_[lower, upper])):
        raise StudyError('nonfinite_dense_enclosure')
    evidence = dict(left_s=float(left), right_s=float(right), order=int(dense.order),
                    temperature_bounds_k=[lower.tolist(), upper.tolist()],
                    t_shift=shifts.tolist(), denom=denom.tolist(),
                    D_temperatures=coefficients.tolist(),
                    method='outward nextafter interval factors + 64u floating evaluation margin')
    evidence['within_domain'] = bool(np.all(lower >= 290.) and np.all(upper <= 310.))
    return evidence


def initial_report(system, temperature):
    ev = system.model.evaluate(temperature)
    fields = system.fields(temperature, ev.temperature_rates_k_s)
    reference = continuous_initial_reference()
    mean_rate = math.fsum(ev.temperature_rates_k_s)/system.n
    if not mean_rate < 0.:
        raise StudyError('initial_coupled_mean_rate_not_negative')
    error = abs(mean_rate-float(reference['rate_k_s']))
    x = math.pi/(2*system.n)
    exact_discrete_u = 40.-.004*(math.sin(x)/x)**2
    return dict(temperatures_k=temperature.tolist(), mean_rate_k_s=mean_rate,
                rates_k_s=list(ev.temperature_rates_k_s), reference=reference,
                mean_rate_error_k_s=error, normalized_mean_rate_error=error/.4,
                normalized_rate_roundoff=128*2.**-53*max(1., max(abs(fields['r'])))/.4,
                discrete_initial_u_j=fields['total_u'],
                formula_discrete_initial_u_j=exact_discrete_u, continuous_initial_u_j=39.996,
                initial_projection_difference_j=exact_discrete_u-39.996,
                initialization='exact cell averages: 302+2*sinc(pi/(2N))*cos(pi*(i+.5)/N)')


def run_policy(system, initial_t, policy_name, directory, guard, *, solver_factory=BDF,
               initial_metadata=None):
    """No repeated integrations; one real accepted-step BDF object per call."""
    policy = POLICIES[policy_name]
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    started = time.monotonic()
    n = system.n
    initial_t = system.temperatures(initial_t)
    y0 = np.r_[initial_t, np.zeros(2*n+1)]
    initial = system.fields(initial_t, np.zeros(n))
    audit, samples, dense_worst = StageAudit(), [], None
    accepted_count, segment_count, next_sample = 0, 0, 1
    solver = None
    failure = None
    gate_failures = []
    maxima = dict(local_energy_normalized=0., global_energy_normalized=0., entropy_normalized=0.)
    def observe_row(when, y, kind):
        guard()
        ev, fields = audit.observe(system, when, y, kind)
        row = ledger_row(system, when, np.asarray(y), fields, initial)
        row['reported_stress_pa'] = [point.stress_pa for point in ev.points]
        for name, value in [('local_energy_normalized', max(abs(np.asarray(row['ledger']['local_residual_j'])))/E_SCALE),
                            ('global_energy_normalized', abs(row['ledger']['global_residual_j'])/E_SCALE),
                            ('entropy_normalized', abs(row['ledger']['entropy_residual_j_k'])/S_SCALE)]:
            maxima[name] = max(maxima[name], value)
        for name, passed in row['gates'].items():
            if not passed and name not in gate_failures:
                gate_failures.append(name)
        return row
    def rhs(when, y):
        guard()
        ev, _ = audit.observe(system, when, y, 'rhs')
        return np.r_[ev.temperature_rates_k_s, ev.cell_heat_in_w,
                     ev.cell_mechanical_power_w, ev.total_entropy_production_w_k]
    def jac(when, y):
        guard()
        audit.begin(when, y, 'jacobian')
        y = finite_array(y, (3*n+1,), 'jacobian_state')
        return system.jacobian(y[:n])
    with (directory/'accepted.jsonl').open('x') as accepted:
        try:
            first = observe_row(0., y0, 'accepted')
            accepted.write(json.dumps(first, allow_nan=False, separators=(',', ':'))+'\n')
            accepted.flush()
            accepted_count += 1
            samples.append(observe_row(0., y0, 'sample'))
            guard()
            solver = solver_factory(rhs, 0., y0.copy(), 10., jac=jac,
                                    atol=np.full(3*n+1, policy['atol']),
                                    rtol=policy['rtol'], max_step=policy['max_step'])
            while solver.status == 'running':
                guard()
                previous = float(solver.t)
                message = solver.step()
                if solver.status == 'failed':
                    raise StudyError(f'bdf_failed:{message}')
                if not previous < solver.t <= 10.:
                    raise StudyError('invalid_accepted_time_progress')
                guard()
                dense = solver.dense_output()
                enclosure = dense_envelope(dense, n, 3*n+1, previous, float(solver.t))
                segment_count += 1
                bounds = np.asarray(enclosure['temperature_bounds_k'])
                margin = min(float(np.min(bounds[0])-290.), float(310.-np.max(bounds[1])))
                if dense_worst is None or margin < dense_worst['domain_margin_k']:
                    dense_worst = dict(domain_margin_k=margin, **enclosure)
                if not enclosure['within_domain']:
                    raise StudyError('unresolved_dense_domain')
                row = observe_row(solver.t, solver.y, 'accepted')
                row['preceding_dense_bounds_k'] = [float(np.min(bounds[0])), float(np.max(bounds[1]))]
                accepted.write(json.dumps(row, allow_nan=False, separators=(',', ':'))+'\n')
                accepted.flush()
                accepted_count += 1
                while next_sample < len(TIMES) and TIMES[next_sample] <= solver.t:
                    when = float(TIMES[next_sample])
                    if when < previous:
                        raise StudyError('missed_requested_time')
                    samples.append(observe_row(when, dense(when), 'sample'))
                    next_sample += 1
            if solver.status != 'finished' or solver.t != 10. or len(samples) != 101:
                raise StudyError('incomplete_physical_interval')
            guard()
        except Exception as exc:
            failure = dict(type=type(exc).__name__, message=str(exc),
                           last_call=audit.last_call,
                           solver_time_s=None if solver is None else float(solver.t))
    completed_interval = bool(solver is not None and solver.status == 'finished'
                              and solver.t == 10. and len(samples) == 101 and failure is None)
    mean_info = None if initial_metadata is None else dict(
        observed_k_s=initial_metadata['mean_rate_k_s'], reference=initial_metadata['reference'],
        temperature_rates_k_s=initial_metadata['rates_k_s'],
        error_k_s=initial_metadata['mean_rate_error_k_s'],
        normalized_error=initial_metadata['normalized_mean_rate_error'], rate_scale_k_s=.4,
        normalized_roundoff=initial_metadata['normalized_rate_roundoff'])
    report = dict(status='failed' if failure or gate_failures else 'completed',
                  cells=n, policy_name=policy_name, policy=dict(method='BDF', **policy),
                  initial_temperatures_k=initial_t.tolist(), initial_mean_rate=mean_info,
                  atol_vector=[policy['atol']]*(3*n+1),
                  state_layout=dict(T=[0,n,'K'], H=[n,2*n,'J'], W=[2*n,3*n,'J'], Z=[3*n,3*n+1,'J/K']),
                  scales=dict(temperature_k=T_SCALE, energy_j=E_SCALE, entropy_j_k=S_SCALE),
                  accepted_file='accepted.jsonl', accepted_count=accepted_count,
                  times_s=[row['time_s'] for row in samples],
                  samples=[row['state'] for row in samples],
                  reported_stress_pa=[row['reported_stress_pa'] for row in samples],
                  observations=[{key:value for key,value in row.items()
                                 if key not in ('state','reported_stress_pa')} for row in samples],
                  stage_audit=audit.report(), metrics=maxima,
                  gates=dict(completed_interval=completed_interval,
                             all_dense_segments_in_domain=completed_interval and dense_worst is not None,
                             local_energy='local_energy' not in gate_failures,
                             global_energy='global_energy' not in gate_failures,
                             entropy='entropy' not in gate_failures),
                  dense_segments=segment_count, worst_dense_segment=dense_worst,
                  failure=failure, gate_failures=gate_failures,
                  elapsed_s=time.monotonic()-started,
                  nfev=None if solver is None else int(solver.nfev),
                  njev=None if solver is None else int(solver.njev),
                  nlu=None if solver is None else int(solver.nlu),
                  solver_status=None if solver is None else solver.status,
                  reached_time_s=None if solver is None else float(solver.t),
                  material_qualified=False, source_material_qualified=False,
                  qualification='manufactured_constant_coefficient_symmetric_free_plane_stress',
                  ledger_scope='reference_half_slab')
    report['real_time_integration'] = solver_factory is BDF
    write_new(directory/'policy.json', report)
    return report


def run_grid(cells, directory, deadline, protocol, *, solver_factory=BDF):
    """Public worker operation; cross-grid comparisons are deliberately external."""
    started = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    completed, results = [], {}
    summary = dict(cells=cells, status='failed', material_qualified=False,
                   source_material_qualified=False, completed_policies=completed,
                   scientific_validated=False, real_time_integration=solver_factory is BDF,
                   cross_grid_validation='not_performed_by_single_grid_worker')
    try:
        guard = deadline_guard(deadline)
        guard()
        identity = runtime_identity(protocol)
        system = SpatialSystem(cells)
        initial_t = initial_temperatures(cells)
        init = initial_report(system, initial_t)
        write_new(directory/'INPUT.json', dict(identity=identity, initial=init,
                  parameters=dict(M=M, alpha=ALPHA, C=C, k=K_COND, Tr=TR, L=L, A=AREA,
                                  temperature_bounds_k=[290.,310.], strain_bounds=[-.01,.01],
                                  coefficient_classification='manufactured', boundary='adiabatic'),
                  policies=POLICIES, times_s=TIMES.tolist(), deadline_monotonic=deadline))
        for name in POLICIES:
            guard()
            result = run_policy(system, initial_t, name, directory/name, guard,
                                solver_factory=solver_factory, initial_metadata=init)
            results[name] = result
            summary[name] = dict(path=f'{name}/policy.json', status=result['status'])
            if result['status'] != 'completed':
                raise StudyError(f'policy_failed:{name}')
            completed.append(name)
        guard()
        coarse = np.asarray(results['coarse']['samples'])[:, :cells]
        fine = np.asarray(results['fine']['samples'])[:, :cells]
        difference = (coarse-fine)/T_SCALE
        e_inf = float(np.max(np.abs(difference)))
        e_two = math.sqrt(math.fsum((difference*difference).ravel())/difference.size)
        summary['time_comparison'] = dict(infinity_normalized=e_inf, two_normalized=e_two,
                                          max_limit=1e-7, passed=e_inf <= 1e-7)
        if e_inf > 1e-7:
            raise StudyError('single_grid_time_refinement_failed')
        guard()
        summary['status'] = 'completed'
    except Exception as exc:
        summary['failure'] = dict(type=type(exc).__name__, message=str(exc))
    summary['elapsed_s'] = time.monotonic()-started
    write_new(directory/'result.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, choices=(16,32,64), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deadline-monotonic', type=float, required=True)
    parser.add_argument('--protocol', type=Path, default=Path(__file__).with_name('NEXT.md'))
    args = parser.parse_args()
    result = run_grid(args.cells, args.output, args.deadline_monotonic, args.protocol)
    return 0 if result['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
