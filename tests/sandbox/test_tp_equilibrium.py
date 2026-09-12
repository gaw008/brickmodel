"""Manufactured ideal-mixture/backend tests; no Cantera phases or equilibrium."""
from fractions import Fraction as F
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from sludge_sandbox.tp_equilibrium import TPPool, TPPolicy, solve_tp, _load_pack, _diagnostics

ROOT = Path(__file__).resolve().parents[2]


def analytical():
    pack = _load_pack(ROOT)
    atoms = pack['atoms']
    n = tuple([F(1, 18)]*18+[F(1)])
    b = tuple(sum((n[i]*atoms[i][e] for i in range(19)), F()) for e in range(5))
    pool = TPPool(1000., 100000., b, 'manufactured_equal_mixture', 'manufactured_test_fixture', ('manufactured:analytic',))
    rt = 8000.
    point = {'temperature_k': 1000., 'pressure_pa': 100000., 'amounts_kmol': [float(v/1000) for v in n],
             'gas_constant_j_mol_k': 8., 'standard_g_j_mol': [-rt*math.log(1/18)]*18+[0.],
             'standard_h_j_mol': [0.]*19, 'standard_s_j_mol_k': [0.]*19,
             'standard_cp_j_mol_k': [1.]*19, 'chemical_potentials_j_mol': [0.]*19}
    return pack, pool, point


def test_exact_ideal_equilibrium_passes_and_unmixed_candidate_does_not():
    pack, pool, point = analytical()
    good = _diagnostics(pack, pool, point, point, TPPolicy())
    assert all(good['checks'].values())
    assert abs(good['gap_out_j']) < F('1e-8')
    bad = dict(point, amounts_kmol=list(point['amounts_kmol']))
    # Transfer H2+CO2 -> H2O+CO: atoms conserved, equal-mixture stationarity broken.
    for i, sign in ((0,-1),(3,-1),(1,1),(2,1)):
        bad['amounts_kmol'][i] += sign*1e-5
    wrong = _diagnostics(pack, pool, point, bad, TPPolicy())
    assert not all(wrong['checks'].values())
    assert not wrong['checks']['nominal_gibbs_gap']


def test_requested_and_actual_pool_gaps_retain_projection_identity():
    pack, pool, point = analytical()
    shifted = TPPool(pool.temperature_k, pool.pressure_pa, (pool.element_mol[0]+F('1e-11'), *pool.element_mol[1:]),
                     pool.basis_id, pool.classification, pool.source_ids)
    data = _diagnostics(pack, shifted, point, point, TPPolicy())
    assert data['gap_requested_j']-data['gap_out_j'] == data['requested_pool_gap_correction_j']
    assert data['element_residual_mol'][0] != 0


@pytest.mark.parametrize('field,value', [('temperature_k',799.),('pressure_pa',101325.),
                                        ('element_mol',(F(-1),)*5)])
def test_pool_refuses_invalid_physical_inputs(field,value):
    fields = dict(temperature_k=1000., pressure_pa=100000., element_mol=(F(1),)*5,
                  basis_id='manufactured', classification='manufactured_test_fixture', source_ids=('manufactured:x',))
    fields[field]=value
    with pytest.raises(ValueError): TPPool(**fields)


def test_late_completed_solve_retains_final_snapshot(monkeypatch):
    import sludge_sandbox.tp_equilibrium as module
    pack,pool,point = analytical()
    clock=[0.]
    monkeypatch.setattr(module,'time',SimpleNamespace(monotonic=lambda:clock[0]))
    class Fake:
        identity={'kind':'manufactured'}
        partial={}
        def prepare(self,*a): return point
        def equilibrate(self,*a):
            clock[0]=11.
            return dict(point, marker='actual_manufactured_return')
    result=solve_tp(pool,ROOT,_backend_factory=lambda pack:Fake())
    assert result.status == 'resource_limit'
    assert result.final['marker'] == 'actual_manufactured_return'
    assert result.provider_calls_completed == 3
    assert result.actual_source_properties_checked is False


def test_solver_failure_retains_initial_and_partial_state():
    _,pool,point = analytical()
    class Fake:
        identity={'kind':'manufactured'}
        partial={}
        def prepare(self,*a): return point
        def equilibrate(self,*a):
            self.partial={'state_after_failure':{'raw_amounts':[-1.,2.]}}
            raise RuntimeError('manufactured_native_failure')
    result=solve_tp(pool,ROOT,_backend_factory=lambda pack:Fake())
    assert result.status == 'solve_failed'
    assert result.initial is not None and result.final is None
    assert result.failure['partial']['state_after_failure']['raw_amounts'] == (-1.,2.)
    with pytest.raises(TypeError): result.failure['reason']='changed'


def test_current_pressure_standard_g_is_not_pressure_corrected_twice():
    pack, pool, point = analytical()
    # A supplied current-P standard potential is already complete. This is a
    # manufactured off-domain diagnostic, not an allowed production pressure.
    nonreference = dict(point, pressure_pa=120000., reference_pressure_pa=100000.)
    result = _diagnostics(pack, pool, nonreference, nonreference, TPPolicy())
    assert not result['checks']['pressure']
    assert result['checks']['nominal_gibbs_gap']
    assert abs(result['gibbs_j']) < F('1e-8')


def test_zero_element_subspace_does_not_require_full_chons_rank():
    pack = _load_pack(ROOT)
    pool = TPPool(1000., 100000., (F(),F(2),F(),F(),F()), 'H_only',
                  'manufactured_test_fixture', ('manufactured:one_gas',))
    point = dict(analytical()[2], amounts_kmol=[.001]+[0.]*18,
                 standard_g_j_mol=[0.]*19)
    data = _diagnostics(pack,pool,point,point,TPPolicy())
    assert all(data['checks'].values())
    assert data['resolved_active_species'] == ('H2',)


def test_seed_projection_underflow_and_source_change_are_named_failures(tmp_path):
    pool = TPPool(1000., 100000., (F(),F(1,10**323),F(),F(),F()), 'tiny',
                  'manufactured_test_fixture', ('manufactured:tiny',))
    result = solve_tp(pool,ROOT,_backend_factory=lambda _:pytest.fail('must not load backend'))
    assert result.status == 'construction_failed'
    assert result.reason == 'unrepresentable_seed_inventory'
    import shutil
    folder=tmp_path/'data/sandbox/research/tp-equilibrium-v1'
    shutil.copytree(ROOT/'data/sandbox/research/tp-equilibrium-v1',folder)
    (folder/'derived.json').write_text('{}')
    with pytest.raises(ValueError,match='source_hash_changed:derived.json'): _load_pack(tmp_path)


def test_nasa_join_uses_low_segment_exactly():
    from sludge_sandbox.tp_equilibrium import _nasa_properties
    record={'thermo':{'temperature-ranges':[200.,1000.,6000.],
                      'data':[[2.,0.,0.,0.,0.,0.,0.],[3.,0.,0.,0.,0.,0.,0.]]}}
    assert _nasa_properties(record,1000.,8.)[2] == 16.
    assert _nasa_properties(record,math.nextafter(1000.,math.inf),8.)[2] == 24.


def test_cli_refuses_overwrite_before_importing_solver(tmp_path):
    import importlib.util
    path=ROOT/'examples/sandbox/run_tp_equilibrium.py'
    spec=importlib.util.spec_from_file_location('tp_example',path)
    example=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    output=tmp_path/'saved.json'
    output.write_text('original')
    argv=['--source-root',str(tmp_path),'--output',str(output),'--temperature-k','1000',
          '--carbon-mol','1','--hydrogen-mol','1.6','--oxygen-mol','.6',
          '--nitrogen-mol','.1','--sulfur-mol','.01','--basis-id','virtual']
    assert example.main(argv) == 2
    assert output.read_text() == 'original'


def test_cli_preserves_input_before_construction_failure(tmp_path):
    import importlib.util
    import json
    path=ROOT/'examples/sandbox/run_tp_equilibrium.py'
    spec=importlib.util.spec_from_file_location('tp_example_failure',path)
    example=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    output=tmp_path/'failure.json'
    argv=['--source-root',str(tmp_path),'--output',str(output),'--temperature-k','1000',
          '--carbon-mol','1','--hydrogen-mol','1.6','--oxygen-mol','.6',
          '--nitrogen-mol','.1','--sulfur-mol','.01','--basis-id','virtual']
    assert example.main(argv) == 1
    data=json.loads(output.read_text())
    assert data['result']['status'] == 'construction_failed'
    assert data['request']['element_mol'][1] == {'numerator':8,'denominator':5}
    assert data['result']['provider_calls_attempted'] == 0


def test_snapshot_explicitly_synchronizes_stale_phase_objects():
    from sludge_sandbox.tp_equilibrium import _CanteraBackend
    # Mirror the official Python phase(n): returns an existing object only.
    # These temperature-marker properties are deliberately not NASA material data.
    class Phase:
        def __init__(self, count):
            self.count, self.t, self.p, self.x = count, 800., 101325., None
        @property
        def TP(self): return self.t,self.p
        @TP.setter
        def TP(self,value): self.t,self.p=value
        @property
        def TPX(self): return self.t,self.p,self.x
        @TPX.setter
        def TPX(self,value): self.t,self.p,self.x=value
        def __getattr__(self,name):
            if name.startswith('standard_') or name=='chemical_potentials':
                return [self.t]*self.count
            raise AttributeError(name)
    backend=object.__new__(_CanteraBackend)
    backend.ct=SimpleNamespace(gas_constant=8000.)
    backend.gas,backend.carbon=Phase(18),Phase(1)
    backend.partial,backend.loaded={},{}
    backend.mix=SimpleNamespace(T=1000.,P=100000.,species_moles=[.001]+[0.]*17+[.001],
                                phase=lambda index:(backend.gas,backend.carbon)[index])
    point=backend.snapshot()
    assert point['standard_h_j_mol']==(8000000.,)*19
    assert backend.gas.TP==backend.carbon.TP==(1000.,100000.)
    assert point['amounts_kmol']==(.001,)+(0.,)*17+(.001,)


def test_post_native_readback_failure_keeps_completed_vector_without_retry():
    from sludge_sandbox.tp_equilibrium import _CanteraBackend
    reads=[]
    class Phase:
        def __init__(self,count): self.count=count
        @property
        def standard_enthalpies_RT(self): return [2.]*self.count
        @property
        def standard_entropies_R(self):
            reads.append('entropy')
            raise RuntimeError('manufactured_entropy_read_failure')
    backend=object.__new__(_CanteraBackend)
    backend.ct=SimpleNamespace(gas_constant=8000.)
    backend.gas,backend.carbon=Phase(18),Phase(1)
    backend.partial,backend.loaded={},{}
    backend.mix=SimpleNamespace(T=1000.,P=100000.,species_moles=[.001]+[0.]*17+[.001],
                                equilibrate=lambda *args,**kwargs:None)
    with pytest.raises(RuntimeError,match='manufactured_entropy_read_failure'):
        backend.equilibrate(TPPolicy())
    assert backend.partial['native_equilibrium_returned'] is True
    assert backend.partial['partial_snapshot']['standard_h_j_mol']==(16000.,)*19
    assert 'standard_s_j_mol_k' not in backend.partial['partial_snapshot']
    assert reads==['entropy']


@pytest.mark.parametrize('solver',['vcs','gibbs'])
def test_explicit_native_solver_dispatch_preserves_all_parameters(solver):
    from sludge_sandbox.tp_equilibrium import _CanteraBackend
    calls=[]
    backend=object.__new__(_CanteraBackend)
    backend.partial={}
    backend.mix=SimpleNamespace(equilibrate=lambda *a,**kw:calls.append((a,kw)))
    backend.snapshot=lambda:{'marker':'manufactured_completed_readback'}
    policy=TPPolicy(solver=solver)
    assert backend.equilibrate(policy)=={'marker':'manufactured_completed_readback'}
    assert calls==[(('TP',),{'solver':solver,'rtol':1e-10,'max_steps':1000,
                            'max_iter':100,'estimate_equil':0,'log_level':0})]


def test_vcs_policy_reports_actual_native_rtol_semantics():
    policy=TPPolicy()
    assert policy.solver=='vcs'
    record=policy.definition()
    assert record['policy_id']=='CHONS_TP_NOMINAL_ACCEPTANCE_V2'
    assert record['requested_native_rtol']==1e-10
    effective=record['effective_native_tolerances']
    assert effective['requested_rtol_consumed'] is False
    assert effective['tolmaj']==1e-8 and effective['tolmin']==1e-6
    assert effective['tolmaj2']==1e-10 and effective['tolmin2']==1e-8
    old=TPPolicy(solver='gibbs').definition()['effective_native_tolerances']
    assert old['requested_rtol_consumed'] is True
    with pytest.raises(ValueError): TPPolicy(solver='auto')


@pytest.mark.parametrize('specified',[None,'gibbs'])
def test_cli_vcs_solver_selection_is_saved_and_passed(tmp_path,monkeypatch,specified):
    import importlib.util
    import json
    from dataclasses import dataclass
    import sludge_sandbox.tp_equilibrium as module
    @dataclass
    class Response:
        status:str='construction_failed'
        reason:str='manufactured_no_native'
    calls=[]
    def solve(pool,root,**kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr(module,'solve_tp',solve)
    spec=importlib.util.spec_from_file_location('tp_solver_example',ROOT/'examples/sandbox/run_tp_equilibrium.py')
    example=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    output=tmp_path/'policy.json'
    argv=['--source-root',str(tmp_path),'--output',str(output),'--temperature-k','1000',
          '--carbon-mol','1','--hydrogen-mol','1.6','--oxygen-mol','.6',
          '--nitrogen-mol','.1','--sulfur-mol','.01','--basis-id','virtual']
    if specified is not None: argv+=['--solver',specified]
    assert example.main(argv)==1
    expected=specified or 'vcs'
    assert json.loads(output.read_text())['request']['solver']==expected
    assert calls[0]['policy'].solver==expected
