"""Pure point and injected-solver tests: no registered trajectory is integrated."""
import importlib.util
import json
from decimal import Decimal, localcontext
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate._ivp.bdf import BdfDenseOutput


HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load('run_spatial')
s = load('supervise')


def independent_rhs(t):
    """Direct dense thermomechanics, not the implementation's fields/Jacobian."""
    n = len(t)
    h, volume = .02/n, .01*.02/n
    g = .01/h
    faces = np.r_[0., g*(t[:-1]-t[1:]), 0.]
    heat = faces[:-1]-faces[1:]
    ce = 100000.-20.*t
    a = np.diag(ce)+np.outer(20.*t, np.ones(n)/n)
    rates = np.linalg.solve(a, heat/volume)
    work = 2*volume*10*(np.mean(t)-t)*np.mean(rates)
    entropy = sum(g*(t[:-1]-t[1:])**2/(t[:-1]*t[1:]))
    return np.r_[rates, heat, work, entropy]


@pytest.mark.parametrize('cells', [16,32,64])
def test_initial_exact_cell_average_and_energy_projection(cells):
    t = d.initial_temperatures(cells)
    boundaries = np.arange(cells+1)*np.pi/cells
    direct = 302.+2*cells/np.pi*np.diff(np.sin(boundaries))
    np.testing.assert_allclose(t, direct, atol=2e-13, rtol=0)
    assert abs(np.mean(t)-302.) < 1e-12
    system = d.SpatialSystem(cells)
    report = d.initial_report(system, t)
    assert report['mean_rate_k_s'] < 0
    assert abs(report['discrete_initial_u_j']-report['formula_discrete_initial_u_j']) < 3e-11
    assert report['initial_projection_difference_j'] > 0
    if cells > 16:
        restriction = t.reshape(-1,2).mean(axis=1)
        assert np.max(np.abs(restriction-d.initial_temperatures(cells//2)))/4 <= d.ROUND_T


def test_machin_reference_against_independent_literal_pi():
    report = d.continuous_initial_reference()
    with localcontext() as ctx:
        ctx.prec = 65
        pi = Decimal('3.1415926535897932384626433832795028841971693993751058209749445923')
        assert abs(Decimal(report['pi'])-pi) < Decimal('1e-60')
        rate = -Decimal(80)*(pi/Decimal('.02'))**2/(Decimal(100000)*(
            Decimal(93960)+(Decimal(93960)**2-Decimal(40)**2).sqrt()))
        assert abs(rate-Decimal(report['rate_k_s'])) < Decimal('1e-60')
        assert Decimal(report['rate_bounds_k_s'][0]) < Decimal(report['rate_k_s']) < Decimal(report['rate_bounds_k_s'][1])
    errors = [d.initial_report(d.SpatialSystem(n), d.initial_temperatures(n))['mean_rate_error_k_s']
              for n in (16,32,64)]
    for left, right in zip(errors[:-1], errors[1:]):
        assert 1.8 <= np.log2(left/right) <= 2.2


@pytest.mark.parametrize('cells', [16,32,64])
@pytest.mark.parametrize('uniform', [False,True])
def test_full_analytic_jacobian_directions_and_half_difference(cells, uniform):
    system = d.SpatialSystem(cells)
    t = np.full(cells,302.) if uniform else d.initial_temperatures(cells)
    jac = system.jacobian(t)
    assert jac.format == 'csc'
    assert jac.shape == (3*cells+1,3*cells+1)
    assert jac[:,cells:].nnz == 0
    for mode in (0,1,2,cells-1):
        direction = np.cos(mode*np.pi*(np.arange(cells)+.5)/cells)
        exact = jac[:,:cells]@direction
        for step in (.002,.001):
            difference = (independent_rhs(t+step*direction)-independent_rhs(t-step*direction))/(2*step)
            np.testing.assert_allclose(exact, difference, rtol=3e-6, atol=3e-9)


def test_stage_independent_ledger_and_candidate_actual_stress():
    system = d.SpatialSystem(16)
    y = np.r_[d.initial_temperatures(16), np.zeros(33)]
    audit = d.StageAudit()
    ev, fields = audit.observe(system, 0., y, 'rhs')
    reference = independent_rhs(y[:16])
    np.testing.assert_allclose(np.r_[ev.temperature_rates_k_s,ev.cell_heat_in_w,
                                   ev.cell_mechanical_power_w,ev.total_entropy_production_w_k],
                               reference, rtol=1e-8, atol=2e-12)
    assert audit.calls['rhs'] == 1
    assert abs(audit.residuals['total_mechanical_power_w']['value']) < 1e-16
    assert fields['production'] > 0
    assert min(fields['stress']) < 0 < max(fields['stress'])


@pytest.mark.parametrize('index,amount,gate', [(16,2e-6,'local_energy'),(32,2e-6,'local_energy'),(-1,1e-8,'entropy')])
def test_integral_gates_detect_wrong_heat_work_or_entropy(index, amount, gate):
    system = d.SpatialSystem(16)
    t = np.full(16,302.)
    fields = system.fields(t, np.zeros(16))
    y = np.r_[t,np.zeros(33)]
    y[index] = amount
    row = d.ledger_row(system, 1., y, fields, fields)
    assert not row['gates'][gate]


def make_dense(t0, t1, y, *, order=1):
    return BdfDenseOutput(t0, t1, t1-t0, order, np.vstack([y]+[np.zeros_like(y)]*order))


def test_interval_envelope_covers_scipy_polynomial_every_sample():
    y = np.r_[np.full(16,302.),np.zeros(33)]
    dense = make_dense(.1,.2,y,order=5)
    for j in range(1,6):
        dense.D[j,:16] = .03*(-1)**j*np.arange(1,17)/16
    bounds = d.dense_envelope(dense,16,49,.1,.2)
    low, high = np.asarray(bounds['temperature_bounds_k'])
    evaluated = dense(np.linspace(.1,.2,501))[:16]
    assert bounds['within_domain']
    assert np.all(evaluated >= low[:,None])
    assert np.all(evaluated <= high[:,None])


def test_dense_middle_overshoot_is_detected_despite_valid_endpoints():
    y = np.r_[np.full(16,302.),np.zeros(33)]
    dense = make_dense(0.,1.,y,order=2)
    dense.D[2,:16] = -80.  # 302 + 40*t*(1-t), peak 312 K.
    assert np.max(dense(0.)[:16]) == 302.
    assert np.max(dense(1.)[:16]) == 302.
    assert np.max(dense(.5)[:16]) == 312.
    assert not d.dense_envelope(dense,16,49,0.,1.)['within_domain']


def test_dense_domain_margin_and_malformed_structure_rejected():
    y = np.r_[np.full(16,302.),np.zeros(33)]
    dense = make_dense(0.,1.,y)
    dense.denom[0] = 0.
    with pytest.raises(d.StudyError,match='denominator'):
        d.dense_envelope(dense,16,49,0.,1.)
    dense = make_dense(0.,1.,y)
    dense.D[1,0] = np.nan
    with pytest.raises(d.StudyError,match='coefficients'):
        d.dense_envelope(dense,16,49,0.,1.)


class ConstantFakeBDF:
    """Explicit fake, exercises accepted-step bookkeeping without integrating."""
    def __init__(self, fun, t0, y0, bound, *, jac, **policy):
        self.t, self.y, self.status = t0, y0.copy(), 'running'
        self.nfev, self.njev, self.nlu = 1, 1, 1
        self.index, self.t_old = 0, None
        self.policy = policy
        fun(t0,y0)
        jac(t0,y0)

    def step(self):
        self.t_old = self.t
        self.t = (.07,.31,10.)[self.index]
        self.index += 1
        if self.index == 3:
            self.status = 'finished'

    def dense_output(self):
        return make_dense(self.t_old,self.t,self.y)


def test_fake_accepted_steps_samples_schema_and_counters(tmp_path):
    system = d.SpatialSystem(16)
    report = d.run_policy(system,np.full(16,302.),'coarse',tmp_path/'case',lambda:None,
                          solver_factory=ConstantFakeBDF)
    assert report['status'] == 'completed'
    assert report['real_time_integration'] is False
    assert report['accepted_count'] == 4
    assert report['times_s'] == d.TIMES.tolist()
    assert np.asarray(report['samples']).shape == (101,49)
    assert np.asarray(report['reported_stress_pa']).shape == (101,16)
    assert all(report['gates'].values())
    assert report['nfev'] == report['njev'] == report['nlu'] == 1
    assert report['stage_audit']['calls'] == dict(rhs=1,jacobian=1,accepted=4,sample=101)
    assert report['dense_segments'] == 3
    assert report['worst_dense_segment']['within_domain']
    lines = [json.loads(x) for x in (tmp_path/'case'/'accepted.jsonl').read_text().splitlines()]
    assert [x['time_s'] for x in lines] == [0.,.07,.31,10.]
    assert all(len(x['state']) == 49 for x in lines)
    assert (tmp_path/'case'/'policy.json').exists()


def test_fake_failure_preserves_confirmed_accepted_prefix(tmp_path):
    class Failing(ConstantFakeBDF):
        def step(self):
            if self.index == 1:
                raise RuntimeError('injected_step_failure')
            return super().step()
    report = d.run_policy(d.SpatialSystem(16),np.full(16,302.),'fine',tmp_path/'case',lambda:None,
                          solver_factory=Failing)
    assert report['status'] == 'failed'
    assert report['failure']['message'] == 'injected_step_failure'
    assert report['accepted_count'] == 2
    assert report['reached_time_s'] == .07
    assert not report['gates']['completed_interval']
    assert s.confirmed_prefix(tmp_path/'case'/'accepted.jsonl')['last']['time_s'] == .07


def test_fake_dense_failure_is_saved_and_not_accepted(tmp_path):
    class Overshoot(ConstantFakeBDF):
        def dense_output(self):
            dense = make_dense(self.t_old,self.t,self.y,order=2)
            dense.D[2,:16] = -80.
            return dense
    report = d.run_policy(d.SpatialSystem(16),np.full(16,302.),'coarse',tmp_path/'case',lambda:None,
                          solver_factory=Overshoot)
    assert report['failure']['message'] == 'unresolved_dense_domain'
    assert report['accepted_count'] == 1
    assert not report['worst_dense_segment']['within_domain']


def test_guard_failure_and_nonfinite_input_keep_errors(tmp_path):
    def guard():
        raise TimeoutError('injected_deadline')
    report = d.run_policy(d.SpatialSystem(16),np.full(16,302.),'coarse',tmp_path/'guard',guard,
                          solver_factory=ConstantFakeBDF)
    assert report['failure']['type'] == 'TimeoutError'
    assert report['nfev'] is None
    audit = d.StageAudit()
    y = np.r_[np.full(16,302.),np.zeros(33)]
    y[0] = np.nan
    with pytest.raises(d.StudyError):
        audit.observe(d.SpatialSystem(16),0.,y,'rhs')
    assert audit.calls['rhs'] == 1
    assert audit.last_call['state'][0] == 'nan'
    json.dumps(audit.report(),allow_nan=False)


@pytest.mark.parametrize('value',[True,8,128,16.,None])
def test_unregistered_grid_rejected(value):
    with pytest.raises(d.StudyError):
        d.SpatialSystem(value)


def test_protocol_and_installed_runtime_identity_without_integration(tmp_path):
    identity = d.runtime_identity(HERE/'NEXT.md')
    assert identity['bdf']['sha256'] == d.BDF_SHA
    wrong = tmp_path/'NEXT.md'
    wrong.write_text('wrong protocol')
    with pytest.raises(d.StudyError,match='protocol_identity'):
        d.runtime_identity(wrong)


def test_prefix_parser_does_not_repair_truncated_tail(tmp_path):
    path = tmp_path/'accepted.jsonl'
    content = json.dumps(dict(time_s=0.,state=[302.]))+'\n'+json.dumps(dict(time_s=.1,state=[302.]))
    path.write_text(content)
    report = s.confirmed_prefix(path)
    assert report['count'] == 1
    assert report['trailing_error'] == 'unterminated_final_record'
    assert path.read_text() == content


def test_prefix_requires_initial_time_and_expected_state_shape(tmp_path):
    path = tmp_path/'accepted.jsonl'
    path.write_text(json.dumps(dict(time_s=.1,state=[302.]*49))+'\n')
    assert s.confirmed_prefix(path,49)['count'] == 0
    path.write_text(json.dumps(dict(time_s=0.,state=[302.]))+'\n')
    assert s.confirmed_prefix(path,49)['count'] == 0


def fake_policy_writer(*, fail_fine=False, fine_shift=0.):
    """Only writes prescribed records; never instantiates a solver."""
    def run(system, initial, name, directory, guard, **kwargs):
        directory.mkdir()
        status = 'failed' if name == 'fine' and fail_fine else 'completed'
        y = np.r_[initial+(fine_shift if name == 'fine' else 0.),np.zeros(2*system.n+1)]
        report = dict(status=status,samples=[y.tolist()]*101)
        d.write_new(directory/'policy.json',report)
        return report
    return run


def test_grid_keeps_completed_coarse_before_failed_fine(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'run_policy',fake_policy_writer(fail_fine=True))
    result = d.run_grid(16,tmp_path/'grid',d.time.monotonic()+10,HERE/'NEXT.md',
                        solver_factory=ConstantFakeBDF)
    assert result['status'] == 'failed'
    assert result['completed_policies'] == ['coarse']
    assert result['failure']['message'] == 'policy_failed:fine'
    assert json.loads((tmp_path/'grid'/'coarse'/'policy.json').read_text())['status'] == 'completed'
    assert json.loads((tmp_path/'grid'/'fine'/'policy.json').read_text())['status'] == 'failed'


def test_grid_time_comparison_rejects_prescribed_excess_difference(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'run_policy',fake_policy_writer(fine_shift=1e-6))
    result = d.run_grid(16,tmp_path/'grid',d.time.monotonic()+10,HERE/'NEXT.md',
                        solver_factory=ConstantFakeBDF)
    assert result['status'] == 'failed'
    assert result['completed_policies'] == ['coarse','fine']
    assert not result['time_comparison']['passed']
    assert result['scientific_validated'] is False
    assert result['real_time_integration'] is False


def test_supervisor_shared_timeout_and_partial_preservation(tmp_path):
    ticks = iter([100.,100.5,130.,130.01])
    def child(command, **kwargs):
        assert kwargs['timeout'] == 29.5
        assert command[1] == '-I'
        assert command[command.index('--deadline-monotonic')+1] == '130.0'
        coarse = tmp_path/'run'/'worker'/'coarse'
        coarse.mkdir(parents=True)
        (coarse/'accepted.jsonl').write_text(json.dumps(dict(time_s=0.,state=[302.]*49))+'\n')
        raise subprocess.TimeoutExpired(command,kwargs['timeout'])
    report = s.supervise('/fake/python',16,tmp_path/'run',run_child=child,clock=lambda:next(ticks))
    assert report['timed_out'] and report['child_reaped']
    assert not report['passed']
    assert report['accepted_prefixes']['coarse']['count'] == 1
    assert report['accepted_prefixes']['fine']['count'] == 0


def test_supervisor_completed_child_and_output_collision(tmp_path):
    ticks = iter([100.,100.5,120.,120.01])
    def child(command, **kwargs):
        assert kwargs['timeout'] == 29.5
        worker = tmp_path/'run'/'worker'
        worker.mkdir()
        (worker/'result.json').write_text(json.dumps(dict(status='completed',real_time_integration=True)))
        return SimpleNamespace(returncode=0)
    report = s.supervise('/fake/python',16,tmp_path/'run',run_child=child,clock=lambda:next(ticks))
    assert report['passed'] and report['inputs_unchanged']
    with pytest.raises(FileExistsError):
        s.supervise('/fake/python',16,tmp_path/'run',run_child=child)


@pytest.mark.parametrize('fault',['posthash','prefix_oserror','prefix_unicode','worker_list'])
def test_supervisor_evidence_error_preserves_terminal_record(tmp_path,monkeypatch,fault):
    ticks = iter([100.,100.5,120.,120.01])
    if fault == 'posthash':
        original_hashes = s.hashes
        calls = []
        def hashing(paths):
            calls.append(1)
            if len(calls) == 2:
                raise FileNotFoundError('injected_missing_posthash_source')
            return original_hashes(paths)
        monkeypatch.setattr(s,'hashes',hashing)
    if fault.startswith('prefix_'):
        original_prefix = s.confirmed_prefix
        def reading(path,state_size=None):
            if path.parent.name == 'fine':
                if fault == 'prefix_oserror':
                    raise OSError('injected_prefix_io_error')
                raise UnicodeDecodeError('utf-8',b'\xff',0,1,'injected invalid byte')
            return original_prefix(path,state_size)
        monkeypatch.setattr(s,'confirmed_prefix',reading)
    returncode = 7 if fault == 'posthash' else 0
    def child(command,**kwargs):
        worker = tmp_path/'run'/'worker'
        coarse = worker/'coarse'
        coarse.mkdir(parents=True)
        (coarse/'accepted.jsonl').write_text(json.dumps(dict(time_s=0.,state=[302.]*49))+'\n')
        result = [] if fault == 'worker_list' else dict(status='completed',real_time_integration=True)
        (worker/'result.json').write_text(json.dumps(result))
        return SimpleNamespace(returncode=returncode)
    report = s.supervise('/fake/python',16,tmp_path/'run',run_child=child,clock=lambda:next(ticks))
    assert report['returncode'] == returncode
    assert report['child_reaped'] is True
    assert report['accepted_prefixes']['coarse']['count'] == 1
    assert report['accepted_prefixes']['coarse']['last']['time_s'] == 0.
    assert report['evidence_errors']
    assert report['passed'] is False
    assert json.loads((tmp_path/'run'/'EXECUTION.json').read_text()) == report
