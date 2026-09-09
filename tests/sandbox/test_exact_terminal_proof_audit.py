"""Pure numerical chain; instrumented host samples are not an EOS oracle."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace as NS
import json
import pytest
from test_exact_depletion_integration import setup
from test_dynamic_solid_storage import water,forbid_water_eos
from test_free_solid_slab import host,initial
from sludge_sandbox.exact_record import encode_exact_run,read_exact_run
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_depletion_integration import integrate_exact_depletion
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
import sludge_sandbox.exact_terminal_proof_audit as m


def fixture(monkeypatch,gap=.008):
    s,v,p,e,calls=setup(monkeypatch,gap=gap)
    # Existing numerical-chain fixture has partial typed provider shells.
    # These two instrumented host seams are NOT claimed as geometry/RHS proof.
    monkeypatch.setattr(WaterPhaseTransfer,'__post_init__',lambda self:None)
    monkeypatch.setattr(m,'observation_binding',lambda v,o,s:m.numeric(o.rates))
    monkeypatch.setattr(m,'geometry_binding',lambda v,s,o:())
    start,end=T(F()),T(F(3,100))
    run=integrate_exact_depletion(s,v,start=start,end=end,integration_policy=p,event_policy=e)
    assert run.status=='completed',run.reason
    raw=encode_exact_run(run,original_operator=v,start=start,end=end,case_sha256='a'*64,runtime_identity={})
    kw=dict(original_operator=v,original_initial=s,start=start,end=end,integration_policy=p,event_policy=e,case_sha256='a'*64,runtime_identity={})
    return raw,kw


def test_all_candidate_exclusion_and_full_panels(monkeypatch):
    raw,kw=fixture(monkeypatch)
    report=m.audit_committed_terminal_proofs(raw,**kw)
    assert report.committed_terminals==2 and report.candidates_checked>=2 and report.exclusions_checked>0
    assert 'six_gate_refinement_comparisons' in report.remaining_gates
    assert 'cumulative_resources' in report.remaining_gates


@pytest.mark.parametrize('kind',['candidate_rate','exclusion_minimum','predictor_energy','midpoint_rate','source_binding','input_totals'])
def test_independent_saved_evidence_tamper(monkeypatch,kind):
    raw,kw=fixture(monkeypatch);d=json.loads(raw)
    a=d['result']['fields']['packets']['sequence'][0]['sequence'][0]['fields']['terminal']['fields']
    if kind=='candidate_rate':
        arr=a['root_order']['fields']['candidates']['sequence'][0]['fields']['evidence']['fields']['samples']['fields']['liquid_rates_start_mol_s']['sequence']
        arr[0]={'float_hex':(.001).hex()}
    elif kind=='exclusion_minimum':
        a['root_order']['fields']['exclusions']['sequence'][0]['fields']['minimum_mol']={'fraction':[1,1]}
    elif kind=='predictor_energy':
        a['predictor_panel']['fields']['raw_state']['fields']['internal_energy_j']['array']['values'][0]={'float_hex':(100.).hex()}
    elif kind=='midpoint_rate':
        a['observations']['sequence'][1]['fields']['evaluation']['fields']['rates']['fields']['face_energy_w']['array']['values'][0]={'float_hex':(.001).hex()}
    elif kind=='source_binding':
        a['root_order']['fields']['candidates']['sequence'][0]['fields']['evidence']['fields']['samples']['fields']['source_ids']={'sequence':['invented']}
    elif kind=='input_totals':a['input_totals']['fields']['numerical_phase_correction_mol']={'fraction':[1,1000]}
    with pytest.raises(m.TerminalProofAuditError):m.audit_committed_terminal_proofs(json.dumps(d).encode(),**kw)


def test_external_original_policy_mismatch(monkeypatch):
    raw,kw=fixture(monkeypatch)
    kw['integration_policy']=replace(kw['integration_policy'],energy_absolute_tolerance_j=1.)
    with pytest.raises(m.TerminalProofAuditError,match='original_integration_policy'):m.audit_committed_terminal_proofs(raw,**kw)


def test_actual_dry_point_geometry_preparation_without_water_calls(water):
    op=host(water);s=initial(op)
    # No chemical/native host construction here: this tests the geometry helper
    # against real CurrentSolidStorage and skeletons, including source guards.
    class Transfer:
        base_model=op
        def _check_interface_state(self,state):pass
    view=NS(operator=Transfer(),operator_identity=('test-direct-geometry',))
    observation=NS(temperatures_k=(300.,301.),pressures_pa=(100000.,100000.))
    rows=m.geometry_binding(view,s,observation)
    assert len(rows)==2
    reference=op.point_storages[0].skeleton.reference
    for i,row in enumerate(rows):
        expected=F(reference.reference_area_m2)*F(reference.half_thickness_m)/2*F(float(s.mechanical_stretches[i]))*F(float(s.mechanical_stretches[-1]))**2
        assert abs(F(row[1])-expected)<=F(row[4])
    bad=replace(s,mechanical_stretches=(.1,1.,1.))
    with pytest.raises(ValueError):m.geometry_binding(view,bad,observation)


def test_observation_contract_binds_actual_coefficients_sources_and_state(monkeypatch):
    # Exercise the unpatched observation helper separately from the instrumented
    # integration fixture. This is source/shape association, not an EOS RHS oracle.
    actual=m.observation_binding
    raw,kw=fixture(monkeypatch)
    record=read_exact_run(raw);a=record.result.packets[0][0].terminal
    node=a.observations[0].evaluation;state=m.numeric(a.initial_state)
    op=NS(interfaces=node.interface_modes,coefficient_set_id=node.coefficient_set_id,
        coefficient_version=node.coefficient_version,coefficient_classification=node.coefficient_classification,
        dry_policy=node.dry_policy,source_ids=node.source_ids,
        coefficients_mol_s_pa=tuple(c.coefficient_mol_s_pa for c in node.cell_transfers))
    assert actual(NS(operator=op),node,state).reaction_species_mol_s.shape==state.amounts_mol.shape
    op.coefficient_version='changed'
    with pytest.raises(m.TerminalProofAuditError,match='coefficient_version'):actual(NS(operator=op),node,state)
    op.coefficient_version=node.coefficient_version;op.source_ids=('unrecorded-source',)
    with pytest.raises(m.TerminalProofAuditError,match='actual_source'):actual(NS(operator=op),node,state)
    op.source_ids=node.source_ids;op.coefficients_mol_s_pa=(9.,9.)
    with pytest.raises(m.TerminalProofAuditError,match='actual_phase_coefficients'):actual(NS(operator=op),node,state)
