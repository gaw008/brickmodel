"""Projection restoration only; existing source-bound numerical fixture, no EOS."""
from dataclasses import replace
import json
import numpy as np
import pytest
from test_exact_record import make
from test_dynamic_solid_storage import forbid_water_eos
from sludge_sandbox.exact_record import read_exact_run,pack,EvidenceNode,encode_exact_run
from sludge_sandbox.exact_depletion_integration import ExactDepletionResult,ExactPacketFrame
from sludge_sandbox.exact_integration import ExactStepLedger
import sludge_sandbox.exact_projection_restore as m


def restored(monkeypatch,cancelled=False):
    raw,view,original=make(monkeypatch,cancelled)
    projection=m.restore_exact_projection(raw,original_operator=view,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})
    return raw,view,original,projection


def test_full_projection_roundtrip_and_committed_ledger_alias(monkeypatch):
    raw,view,original,projection=restored(monkeypatch)
    run=projection.result
    assert type(run) is ExactDepletionResult and projection.resume_authorized is False
    assert projection.rebound_committed_ledgers==2
    assert pack(run)==pack(original)
    checked=read_exact_run(raw)
    assert encode_exact_run(run,original_operator=view,start=checked.start,end=checked.end,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})==raw
    for packet in run.packets:
        for frame in packet:
            assert type(frame) is ExactPacketFrame
            ledger=frame.terminal.terminal_panel.ledger
            assert type(ledger) is ExactStepLedger and any(ledger is x for x in run.steps)
            assert type(frame.terminal.observations[0]) is EvidenceNode
            assert frame.terminal.observations[0].kind=='TerminalObservation'
            assert frame.terminal.observations[0].evaluation.kind=='Observation'
    assert len(run.refinements)==len(original.refinements) and len(run.terminal_attempts)==len(original.terminal_attempts)


def test_cancelled_projection_retains_only_actual_prefix(monkeypatch):
    raw,_,original,projection=restored(monkeypatch,True)
    assert projection.result.status=='cancelled' and projection.result.steps
    assert pack(projection.result)==pack(original)
    assert not projection.resume_authorized


@pytest.mark.parametrize('attack',['duplicate_frame','missing_step','changed_panel'])
def test_alias_association_attacks(monkeypatch,attack):
    _,_,_,projection=restored(monkeypatch);run=projection.result
    if attack=='duplicate_frame':
        bad=replace(run,packets=(run.packets[0]+(run.packets[0][0],),)+run.packets[1:])
    elif attack=='missing_step':bad=replace(run,steps=run.steps[:-1])
    else:
        frame=run.packets[0][0];panel=frame.terminal.terminal_panel
        values=np.array(panel.ledger.cell_work_j);values[0]+=1.
        ledger=replace(panel.ledger,cell_work_j=values)
        frame=replace(frame,terminal=replace(frame.terminal,terminal_panel=replace(panel,ledger=ledger)))
        bad=replace(run,packets=((frame,)+run.packets[0][1:],)+run.packets[1:])
    with pytest.raises(m.ProjectionRestoreError):m._canonicalize_committed_ledgers(bad)


def test_fresh_bytes_and_external_source_required(monkeypatch):
    raw,view,_,projection=restored(monkeypatch)
    with pytest.raises(m.ProjectionRestoreError):m.restore_exact_projection(projection,original_operator=view,case_sha256='a'*64,runtime_identity={})
    object.__setattr__(view.operator,'coefficient_version','changed')
    with pytest.raises(m.ProjectionRestoreError):m.restore_exact_projection(raw,original_operator=view,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})


@pytest.mark.parametrize('attack',['wrong_cell','wrong_clock'])
def test_correction_association_not_lost_when_rebinding(monkeypatch,attack):
    from fractions import Fraction as F
    from sludge_sandbox.exact_affine_depletion import ExactDepletionWritebackRecord
    _,_,_,projection=restored(monkeypatch);run=projection.result;frame=run.packets[0][0]
    order=frame.terminal.root_order
    selected=next(c.evidence for c in order.candidates if c.cell_index==order.selected_cell)
    if attack=='wrong_clock':
        evidence=next(c.evidence for c in order.candidates if c.cell_index!=order.selected_cell)
        cell=order.selected_cell
    else:evidence=selected;cell=1-order.selected_cell
    # Explicit association attack, not a claim that the exact-zero fixture needed
    # this fabricated correction. The restore helper must never hide its identity.
    correction=ExactDepletionWritebackRecord(cell,0,1,0.,0.,0.,F(),F(),F(),F(),F(),F(),0.,F(),clock_evidence=evidence)
    frame=replace(frame,terminal=replace(frame.terminal,correction=correction))
    bad=replace(run,packets=((frame,)+run.packets[0][1:],)+run.packets[1:])
    with pytest.raises(m.ProjectionRestoreError,match='correction_selected'):m._canonicalize_committed_ledgers(bad)
