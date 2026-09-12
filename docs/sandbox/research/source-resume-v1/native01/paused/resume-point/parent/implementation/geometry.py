"""Compatible one-dimensional slab kinematics, independent of a shrinkage constitutive law.

All cells share a tangential stretch and a common face area. Normal stretches may
vary by cell; using separate J**(2/3) face areas in that case is incompatible.
"""

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray


class GeometryError(ValueError):
    """Geometry or phase volumes leave the explicitly supported open-pore domain."""


def _positive(value: float, field: str) -> None:
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise GeometryError(f"{field} must be a positive finite number")


def _array(values, cells: int, field: str, *, strictly_positive: bool = False) -> NDArray[np.float64]:
    try:
        # Inspect before NumPy can silently turn a mixed [True, 1] list into integers.
        if any(isinstance(v, (bool, np.bool_)) for v in np.asarray(values, dtype=object).flat):
            raise GeometryError(f"{field} cannot contain booleans")
        raw = np.asarray(values)
        if raw.dtype.kind not in "ifu":
            raise GeometryError(f"{field} requires numeric values")
        a = np.array(raw, dtype=float, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise GeometryError(f"Invalid {field}") from exc
    if a.shape != (cells,) or not np.all(np.isfinite(a)):
        raise GeometryError(f"{field} must have one finite value per cell")
    if np.any(a <= 0 if strictly_positive else a < 0):
        raise GeometryError(f"{field} outside positive volume domain")
    a.flags.writeable = False
    return a


@dataclass(frozen=True)
class CurrentSlab:
    widths_m: NDArray[np.float64]
    faces_m: NDArray[np.float64]
    centers_m: NDArray[np.float64]
    face_areas_m2: NDArray[np.float64]
    reference_volumes_m3: NDArray[np.float64]
    volumes_m3: NDArray[np.float64]
    volume_ratios: NDArray[np.float64]


@dataclass(frozen=True)
class ReferenceSlab:
    half_thickness_m: float
    reference_area_m2: float
    cells: int

    def __post_init__(self):
        _positive(self.half_thickness_m, "half_thickness_m")
        _positive(self.reference_area_m2, "reference_area_m2")
        if type(self.cells) is not int or self.cells < 1:
            raise GeometryError("cells must be a positive integer")

    def deform(self, normal_stretches, *, tangential_stretch: float) -> CurrentSlab:
        _positive(tangential_stretch, "tangential_stretch")
        normal = _array(normal_stretches, self.cells, "normal_stretches", strictly_positive=True)
        dx0 = self.half_thickness_m / self.cells
        with np.errstate(over="raise", invalid="raise"):
            try:
                widths = normal * dx0
                area = self.reference_area_m2 * tangential_stretch**2
                ratios = normal * tangential_stretch**2
                volumes = widths * area
                faces = np.concatenate(([0.0], np.cumsum(widths)))
                arrays = (widths, faces, (faces[:-1] + faces[1:]) / 2,
                          np.full(self.cells + 1, area),
                          np.full(self.cells, dx0 * self.reference_area_m2), volumes, ratios)
            except (OverflowError, FloatingPointError) as exc:
                raise GeometryError("Geometry exceeds finite numeric range") from exc
        if any(not np.all(np.isfinite(a)) for a in arrays) or np.any(volumes <= 0):
            raise GeometryError("Invalid deformed volume")
        for a in arrays:
            a.flags.writeable = False
        return CurrentSlab(*arrays)


@dataclass(frozen=True)
class PoreGeometry:
    total_pore_volume_ref: NDArray[np.float64]
    open_pore_volume_ref: NDArray[np.float64]
    gas_volume_ref: NDArray[np.float64]
    open_porosity: NDArray[np.float64]
    liquid_saturation: NDArray[np.float64]


def pore_geometry(current: CurrentSlab, *, solid_volume_ref, liquid_volume_ref,
                  closed_pore_volume_ref) -> PoreGeometry:
    """Volumes are m3 phase / m3 initial bulk; no phase volume is inferred or clipped."""
    if not isinstance(current, CurrentSlab) or np.ndim(current.volume_ratios) != 1:
        raise GeometryError("A one-dimensional CurrentSlab is required")
    cells = len(current.volume_ratios)
    if cells == 0:
        raise GeometryError("At least one cell is required")
    ratios = _array(current.volume_ratios, cells, "volume_ratios", strictly_positive=True)
    solid = _array(solid_volume_ref, cells, "solid_volume_ref")
    liquid = _array(liquid_volume_ref, cells, "liquid_volume_ref")
    closed = _array(closed_pore_volume_ref, cells, "closed_pore_volume_ref")
    total = ratios - solid
    opened = total - closed
    gas = opened - liquid
    if np.any(total < 0) or np.any(opened <= 0) or np.any(gas <= 0):
        raise GeometryError("Open gas volume exhausted; a supported phase/topology transition is required")
    arrays = (total, opened, gas, opened / ratios, liquid / opened)
    for a in arrays:
        a.flags.writeable = False
    return PoreGeometry(*arrays)
