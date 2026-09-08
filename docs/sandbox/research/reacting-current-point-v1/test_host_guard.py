"""Pure constructor check using actual candidate point and exact typed host."""
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
import pytest
from test_dynamic_solid_storage import water,forbid_water_eos
from test_free_solid_slab import host
from test_reacting_current import m as point_module
from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
from sludge_sandbox.integration import IntegrationError


def test_fixed_host_explicitly_refuses_reacting_current_point():
    base=host(water.__wrapped__())
    points=[]
    for p in base.point_storages:
        sk=ManufacturedReactingSkeletonEnergy(reference_model=p.skeleton,composition_offset=1.,
            composition_weights_per_mol=(('fixture_solid',0.),),model_id='guard-reacting',version='1',
            classification='manufactured_test_fixture',allow_manufactured=True)
        points.append(point_module.CurrentSolidStorage(template=p.template,skeleton=sk,error_bounds=p.error_bounds,
            model_id=p.model_id,version=p.version,allow_manufactured=True,solid_inventory_regime='reacting_manufactured'))
    # Overlay just this dependency while loading temporary host; restore registry
    # immediately, never mutate production module/class or filesystem.
    name='sludge_sandbox.current_solid_storage';old=sys.modules[name]
    sys.modules[name]=point_module
    try:
        spec=importlib.util.spec_from_file_location('sludge_sandbox._guard_candidate',Path(__file__).with_name('free_solid_slab.py'))
        candidate=importlib.util.module_from_spec(spec);sys.modules[spec.name]=candidate;spec.loader.exec_module(candidate)
    finally:sys.modules[name]=old
    with pytest.raises(IntegrationError,match='reacting_current_points_not_admitted_by_fixed_free_slab'):
        candidate.FreeSolidSlab(base_model=base.base_model,point_storages=tuple(points),external_pressure_pa=base.external_pressure_pa,
            model_id=base.model_id,version=base.version,source_ids=base.source_ids,allow_manufactured=True)
