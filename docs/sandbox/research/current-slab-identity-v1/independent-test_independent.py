from dataclasses import fields,replace,dataclass
from pathlib import Path
import struct,sys,importlib.util,json,hashlib
import numpy as np
import pytest
from sludge_sandbox.geometry import ReferenceSlab
p=Path('/private/tmp/brick-current-slab-identity-candidate/deforming_solid_storage.py');spec=importlib.util.spec_from_file_location('sludge_sandbox._independent_current_identity',p);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
@pytest.fixture
def slab():return ReferenceSlab(.012,.02,3).deform([1.,.8,1.2],tangential_stretch=.9)
def test_exact_complete_binary64_record(slab):
    actual=module._canonical(slab)
    expected=['sludge_sandbox.geometry','CurrentSlab',[]]
    for f in fields(slab):
        a=getattr(slab,f.name)
        independent=[v[0].hex() for v in struct.iter_unpack('=d',a.tobytes())]
        expected[2].append([f.name,['numpy_float64_1d',[a.size],independent]])
    assert actual==expected
    assert module._digest(slab)==hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_tiny_signs_and_stride_readout(slab):
    a=slab.volume_ratios.copy();a[:]=[np.nextafter(0.,1.),-0.,np.finfo(float).max]
    changed=replace(slab,volume_ratios=a)
    text=module._canonical(changed)[2][-1][1][-1]
    assert text==['0x0.0000000000001p-1022','-0x0.0p+0','0x1.fffffffffffffp+1023']
    values=np.zeros(6);values[::2]=slab.volume_ratios
    assert module._digest(replace(slab,volume_ratios=values[::2]))==module._digest(slab)
def test_additional_array_types_and_hidden_arbitrary_array_refused(slab):
    class Sub(np.ndarray):pass
    a=slab.widths_m
    for bad in [a.astype(complex),a.astype(bool),a.astype(np.int64),a.astype('>f8'),a.view(Sub)]:
        with pytest.raises(module.DeformingStorageError):module._canonical(replace(slab,widths_m=bad))
    @dataclass
    class Envelope:
        valid:object
        _cache:object
    with pytest.raises(module.DeformingStorageError):module._canonical(Envelope(slab,np.zeros(3)))
def test_inserting_zero_length_and_cross_shape_face_refused(slab):
    for name in [f.name for f in fields(slab)]:
        with pytest.raises(module.DeformingStorageError):module._canonical(replace(slab,**{name:np.array([],dtype=float)}))
    with pytest.raises(module.DeformingStorageError):module._canonical(replace(slab,faces_m=slab.widths_m))
