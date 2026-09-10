"""CurrentSlab identity coverage; no material admission or arbitrary array codec.

Golden values were captured from source SHA
c51278bae2c1f4043c804cf198c1180d81f64b147f149c5c86080004ada6a3fd,
prior to adding CurrentSlab support. The frozen source and capture records are
archived under docs/sandbox/research/current-slab-identity-v1/.
The actual moving half-cell regression remains in test_deforming_wet_admission.py.
"""
from dataclasses import dataclass, fields, replace
from fractions import Fraction

import numpy as np
import pytest

from sludge_sandbox.deforming_solid_storage import _canonical, _digest, DeformingStorageError
from sludge_sandbox.geometry import CurrentSlab, ReferenceSlab
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeatError
from sludge_sandbox.water_properties import load_water_properties
from test_rigid_fluid_heat import operator
from test_rigid_storage import DATA


@pytest.fixture(scope='module')
def water():
    return load_water_properties(DATA)


@pytest.fixture
def slab():
    return ReferenceSlab(.02,.014,2).deform([1.,.9],tangential_stretch=.95)


def test_all_seven_fields_bound_and_mutation_changes_digest(slab):
    before=_digest(slab)
    encoded=_canonical(slab)
    assert [row[0] for row in encoded[2]]==[f.name for f in fields(CurrentSlab)]
    for descriptor in fields(CurrentSlab):
        array=getattr(slab,descriptor.name).copy()
        array[0]=np.nextafter(array[0],np.inf)
        assert _digest(replace(slab,**{descriptor.name:array}))!=before
    assert _digest(replace(slab,widths_m=slab.centers_m,centers_m=slab.widths_m))!=before


@pytest.mark.parametrize('name',[f.name for f in fields(CurrentSlab)])
def test_nonfinite_or_bad_arrays_rejected(slab,name):
    original=getattr(slab,name)
    for bad in (original.astype(np.float32),original.reshape(-1,1),original[:-1],original.tolist(),
                np.full(original.shape,np.nan),np.full(original.shape,np.inf),original.astype(object)):
        with pytest.raises(DeformingStorageError):
            _canonical(replace(slab,**{name:bad}))


def test_unknown_arrays_subclasses_and_empty_record_rejected(slab):
    @dataclass
    class Unknown:
        array: object

    @dataclass(frozen=True)
    class OtherSlab(CurrentSlab):
        pass

    for value in (np.array([1.]),Unknown(np.array([1.])),{'array':np.array([1.])},
                  OtherSlab(*(getattr(slab,f.name) for f in fields(CurrentSlab)))):
        with pytest.raises(DeformingStorageError):
            _canonical(value)
    with pytest.raises(DeformingStorageError):
        _canonical(replace(slab,widths_m=np.array([])))


def test_supported_old_graphs_golden_unchanged(water):
    # Literal expectations from the pre-change capture; never recalculate them
    # with the implementation being tested and call that a baseline.
    objects=(operator(water),{'values':(None,True,7,-0.,Fraction(2,3),'x')},water)
    expected=(
        'e295da5ab4d59a0e10b6d5bd28da00c7bc9f935b65d837a8450a493f42b6b9b1',
        '69c8bd28bf68415c794cfcee953f54eb96c1de66e0bc9a8498368855ed6ce242',
        '4e502e981e67a122d7c05d41066a2b9c4703b3ee1fa4393b84d2dc3e7dd81cf9',
    )
    assert tuple(_digest(value) for value in objects)==expected


def test_private_reference_snapshot_not_omitted_and_runtime_change_detected(water):
    from test_deforming_wet_admission import wrapped
    op=wrapped(water)
    op.operator_identity  # Assert that the original object is accepted first.
    motion=op.base_model.point_storages[0].motion
    cached=motion._reference_state
    before_motion=_digest(motion)
    changed=cached.widths_m.copy()
    changed[0]=np.nextafter(changed[0],np.inf)
    object.__setattr__(motion,'_reference_state',replace(cached,widths_m=changed))
    with pytest.raises(ProgrammedSolidFluidHeatError,match='content_changed'):
        op.operator_identity
    assert _digest(motion)!=before_motion


def test_signed_zero_preserved_and_copy_layout_not_physical_identity(slab):
    changed=slab.faces_m.copy()
    changed[0]=-0.
    assert _digest(replace(slab,faces_m=changed))!=_digest(slab)
    copied=replace(slab,**{f.name:getattr(slab,f.name).copy() for f in fields(CurrentSlab)})
    assert _digest(copied)==_digest(slab)
