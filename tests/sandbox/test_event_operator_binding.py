"""Source-backed construction test; no trajectory/state inversion is requested."""
from dataclasses import replace
import pytest
from test_water_phase_transfer import ingredients, transfer
from sludge_sandbox.integration import ConservedState
import sludge_sandbox.event_record as m

@pytest.mark.parametrize('change',[
 {'coefficients_mol_s_pa':(2e-7,)},
 {'coefficient_set_id':'changed'},
 {'coefficient_version':'2'},
 {'dry_policy':'metastable_no_nucleation'},
])
def test_source_ids_do_not_mask_changed_operator_content(ingredients,change):
 original=transfer(ingredients);changed=replace(original,**change)
 state=ConservedState([[1.,.01,.001]],[600.])
 assert original.source_ids==changed.source_ids
 assert m.binding(original,state)!=m.binding(changed,state)
