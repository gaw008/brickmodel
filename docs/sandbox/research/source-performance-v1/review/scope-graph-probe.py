"""N3 structural-class walk only. No provider initialization or property calls."""
import hashlib
import json
from pathlib import Path
import sys

import iapws
import pytest
sys.path.insert(0, '/Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox')
from test_heos_rhs_scope import class_graph, shell
import sludge_sandbox._heos_rhs_scope as scope
from sludge_sandbox.source_run_config import load_source_run_config
from sludge_sandbox.source_run_builder import _liquid
from sludge_sandbox.source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume
from sludge_sandbox.mass_wet_transport import WetFace
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.water_properties import WaterSourceError

repo = Path('/Users/wanggaoying/Desktop/brickmodel-github')
out = Path(__file__).parent
checks = []
with pytest.MonkeyPatch.context() as patch:
    adapter = class_graph(patch)
    column=adapter.column
    original=column.storages[0]
    storages=[]
    for _ in range(3):
        values=dict(vars(original))
        values['volume']=shell(ManufacturedFixedFluidVolume)
        storages.append(shell(SourceWetStorage, **values))
    object.__setattr__(column, 'storages', tuple(storages))
    config=load_source_run_config((repo/'data/sandbox/cases/source-nonstationary-heos-rhs-v3.json').read_bytes())
    values=config.values;grid=values['grid'];widths=grid['cell_widths_m']
    faces=tuple(WetFace(grid['face_area_m2'], (widths[i]/2,widths[i+1]/2),
        grid['conductivities_w_m_k'][i],grid['diffusivities_m2_s'][i],
        grid['gas_permeability_m2'][i],grid['gas_viscosity_pa_s'][i],grid['source_ids']) for i in range(2))
    object.__setattr__(column,'faces',faces)
    object.__setattr__(column,'liquid_transport',_liquid(config))
    object.__setattr__(column,'inverse_policies',tuple(InversePolicy(**values['inverse_policy']) for _ in range(3)))
    object.__setattr__(column,'interface_modes',('existing_liquid','depleted_no_nucleation','existing_liquid'))
    # Replace the test's module stand-in with the actual imported IAPWS type.
    # object.__new__ invokes no IAPWS initialization or EOS, so this is still only a class/field probe.
    graph=scope._closed_graph(adapter)
    patch.setitem(sys.modules,'iapws',iapws)
    for water in graph.waters:
        object.__setattr__(water._ideal,'_backend',iapws)
        object.__setattr__(water._ideal,'_model',object.__new__(iapws.IAPWS95))
    graph=scope._closed_graph(adapter)
    assert len(graph.waters)==len(graph.kernels)==4
    assert len({id(s) for s in storages})==len({id(s.volume) for s in storages})==3
    checks.append('actual IAPWS class, three distinct source-storage/volume shells, all four water paths')
    assert all(any(item is face for item in graph.objects) for face in faces)
    assert any(item is column.liquid_transport for item in graph.objects)
    assert all(any(item is relation for item in graph.objects) for relation in column.liquid_transport.relations)
    assert all(any(item is connection for item in graph.objects) for connection in column.liquid_transport.connections)
    checks.append('actual configured N3 face/policy/liquid relation and connection objects covered')
    relation=column.liquid_transport.relations[0]
    object.__setattr__(relation,'evaluate',lambda *a: (_ for _ in ()).throw(AssertionError('must never call')))
    try:
        scope._closed_graph(adapter)
    except WaterSourceError as exc:
        assert 'instance_override:SaturationMobilityTable' in str(exc)
        checks.append('nested liquid callback override rejected before invocation')
    else:
        raise AssertionError('nested override admitted')

result=dict(status='passed',checks=checks,scope='structural class and configured passive control objects; not live graph numerical validation',
    provider_initializations=0,eos_calls=0,scope_sha256=hashlib.sha256(Path(scope.__file__).read_bytes()).hexdigest())
(out/'SCOPE_GRAPH_PROBE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
