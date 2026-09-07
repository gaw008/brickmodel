"""Manufactured kinematic cases; no assertion about a real brick's shrinkage law."""

import numpy as np
import pytest

from sludge_sandbox.geometry import GeometryError, ReferenceSlab, pore_geometry


def test_nonuniform_shrinkage_uses_one_shared_face_area_and_consistent_volumes():
    slab = ReferenceSlab(half_thickness_m=0.02, reference_area_m2=0.04, cells=3)
    current = slab.deform([0.8, 0.9, 1.0], tangential_stretch=0.95)
    assert current.face_areas_m2.tolist() == pytest.approx([0.04 * 0.95**2] * 4)
    assert current.widths_m.tolist() == pytest.approx(np.array([0.8, 0.9, 1.0]) * 0.02 / 3)
    assert current.volume_ratios.tolist() == pytest.approx(np.array([0.8, 0.9, 1.0]) * 0.95**2)
    assert sum(current.volumes_m3) == pytest.approx(current.faces_m[-1] * current.face_areas_m2[-1])


def test_uniform_isotropic_limit_and_liquid_occupies_gas_pore_volume():
    current = ReferenceSlab(0.01, 1.0, 2).deform([0.9, 0.9], tangential_stretch=0.9)
    pores = pore_geometry(current, solid_volume_ref=[0.4, 0.4],
                          liquid_volume_ref=[0.1, 0.0], closed_pore_volume_ref=[0.02, 0.02])
    assert pores.open_pore_volume_ref.tolist() == pytest.approx([0.9**3 - 0.42] * 2)
    assert pores.gas_volume_ref[1] - pores.gas_volume_ref[0] == pytest.approx(0.1)
    assert pores.open_porosity.tolist() == pytest.approx(pores.open_pore_volume_ref / 0.9**3)


@pytest.mark.parametrize("arguments", [(0, 1, 2), (1, -1, 2), (1, 1, True), (1, 1, 1.5)])
def test_invalid_reference_domain_rejected(arguments):
    with pytest.raises(GeometryError):
        ReferenceSlab(*arguments)


@pytest.mark.parametrize("stretches", [[1], [1, 0], [1, float("nan")], [True, 1]])
def test_invalid_deformation_rejected(stretches):
    with pytest.raises(GeometryError):
        ReferenceSlab(1, 1, 2).deform(stretches, tangential_stretch=1)


@pytest.mark.parametrize("solid,water,closed", [(1.1, 0, 0), (0.5, 0.6, 0), (0.5, 0, 0.6), (0.5, -0.1, 0)])
def test_invalid_or_closed_gas_domain_fails_without_clamping(solid, water, closed):
    current = ReferenceSlab(1, 1, 1).deform([1], tangential_stretch=1)
    with pytest.raises(GeometryError):
        pore_geometry(current, solid_volume_ref=[solid], liquid_volume_ref=[water],
                      closed_pore_volume_ref=[closed])


def test_mutated_current_volume_ratio_is_checked_before_pore_arithmetic():
    current = ReferenceSlab(1, 1, 1).deform([1], tangential_stretch=1)
    current.volume_ratios.setflags(write=True)
    current.volume_ratios[0] = float("nan")
    with pytest.raises(GeometryError):
        pore_geometry(current, solid_volume_ref=[0.5], liquid_volume_ref=[0.1],
                      closed_pore_volume_ref=[0])
