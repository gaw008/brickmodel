"""Fresh exact-continuation admission; no partial audit token acceptance."""
from dataclasses import dataclass
from collections.abc import Mapping
import hashlib
from sludge_sandbox.integration import IntegrationError
from sludge_sandbox.exact_record import read_exact_run,pack
from sludge_sandbox.exact_record_audit import audit_exact_run
from sludge_sandbox.exact_terminal_proof_audit import audit_committed_terminal_proofs
from sludge_sandbox.exact_record_comparison_audit import audit_exact_comparisons
from sludge_sandbox.exact_resource_audit import audit_exact_resources
from sludge_sandbox.exact_projection_restore import restore_exact_projection
from sludge_sandbox.run_service import runtime_identity as current_runtime

class ExactContinuationError(IntegrationError):pass

def require(ok,reason):
    if not ok:raise ExactContinuationError(reason)

@dataclass(frozen=True)
class ExactContinuationRequest:
    parent_bytes:bytes
    expected_parent_sha256:str
    case_sha256:str
    runtime_identity:Mapping


def admit(request,operator,initial,start,end,p,ep):
    require(type(request) is ExactContinuationRequest,'explicit_continuation_request')
    require(type(request.parent_bytes) is bytes and type(request.expected_parent_sha256) is str,'authoritative_parent_bytes_hash')
    digest=hashlib.sha256(request.parent_bytes).hexdigest()
    require(digest==request.expected_parent_sha256,'authoritative_parent_hash_mismatch')
    require(pack(current_runtime())==pack(request.runtime_identity),'execution_runtime_mismatch')
    checked=read_exact_run(request.parent_bytes)
    common=dict(original_initial=initial,start=start,end=end,integration_policy=p,event_policy=ep,
        case_sha256=request.case_sha256,runtime_identity=request.runtime_identity)
    prefix=audit_exact_run(checked,operator,**common)
    terminal=audit_committed_terminal_proofs(request.parent_bytes,original_operator=operator,**common)
    comparisons=audit_exact_comparisons(checked,operator,**common)
    resources=audit_exact_resources(checked,original_policy=p)
    require(all(report.record_sha256==checked.sha256 for report in (prefix,terminal,comparisons,resources)),'audit_record_mismatch')
    require(checked.result.status in ('cancelled','resource_limit'),'parent_status_not_continuable')
    require(bool(checked.ledgers) and start<checked.times[-1]<end,'accepted_interior_checkpoint_required')
    exhausted=resources.remaining_panels<=0 or resources.remaining_rejections<=0 or resources.remaining_wall_seconds<=0
    if checked.result.status=='resource_limit':require(exhausted,'nonexhausted_resource_parent_not_continuable')
    restored=restore_exact_projection(request.parent_bytes,original_operator=operator,case_sha256=request.case_sha256,runtime_identity=request.runtime_identity)
    require(restored.record_sha256==checked.sha256,'restored_record_mismatch')
    # Recheck after all read-audits; no saved approval can bypass this live guard.
    require(pack(current_runtime())==pack(request.runtime_identity),'execution_runtime_changed_during_admission')
    operator.operator_identity
    return restored.result,resources
