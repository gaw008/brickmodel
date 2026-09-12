"""Static spherical finite-volume geometry; no radial mechanics or material law.

Cell temperatures represent radial-midpoint unknowns. Interior/surface series
resistance integrates dr/(4*pi*r*r) exactly as an analytic expression, evaluated
in binary64. This is not an interval-certified arithmetic result.
"""
from dataclasses import dataclass
import math


class SphericalGeometryError(ValueError):
    """An explicitly fixed spherical mesh cannot be represented."""


def _positive(value: object, name: str) -> float:
    try:
        valid=type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid=False
    if not valid:
        raise SphericalGeometryError('positive_finite_' + name + '_required')
    return float(value)


@dataclass(frozen=True)
class FixedSphericalShells:
    faces_m: tuple[float, ...]
    geometry_id: str
    source_ids: tuple[str, ...]
    numerical_policy: str = 'fixed_sphere_midpoint_binary64_integrated_resistance_v1'

    def __post_init__(self) -> None:
        if type(self.faces_m) is not tuple or len(self.faces_m) < 2:
            raise SphericalGeometryError('explicit_spherical_faces_required')
        if type(self.faces_m[0]) not in (int, float) or self.faces_m[0] != 0:
            raise SphericalGeometryError('sphere_center_must_be_zero')
        faces = (0.,) + tuple(_positive(r, 'radius') for r in self.faces_m[1:])
        if any(b <= a for a, b in zip(faces, faces[1:])):
            raise SphericalGeometryError('strictly_increasing_radii_required')
        if type(self.geometry_id) is not str or not self.geometry_id.strip() or self.geometry_id != self.geometry_id.strip():
            raise SphericalGeometryError('explicit_geometry_identity_required')
        if (type(self.source_ids) is not tuple or not self.source_ids
                or any(type(s) is not str or not s.strip() or s != s.strip() for s in self.source_ids)
                or len(set(self.source_ids)) != len(self.source_ids)):
            raise SphericalGeometryError('explicit_unique_geometry_sources_required')
        if self.numerical_policy != 'fixed_sphere_midpoint_binary64_integrated_resistance_v1':
            raise SphericalGeometryError('unsupported_spherical_numerical_policy')
        object.__setattr__(self, 'faces_m', faces)
        # Reject overflow, underflow and unresolved centers at construction.
        for name in ('widths_m', 'centers_m', 'volumes_m3'):
            for value in getattr(self, name):
                _positive(value, name)
        for value in self.areas_m2[1:]:
            _positive(value, 'face_area')
        for a, c, b in zip(faces, self.centers_m, faces[1:]):
            if not a < c < b:
                raise SphericalGeometryError('unresolvable_cell_center')
        for face in range(1, self.cells + 1):
            self.face_metric(face)

    @property
    def cells(self) -> int:
        return len(self.faces_m) - 1

    @property
    def widths_m(self) -> tuple[float, ...]:
        return tuple(b - a for a, b in zip(self.faces_m, self.faces_m[1:]))

    @property
    def centers_m(self) -> tuple[float, ...]:
        return tuple(a + (b - a)/2 for a, b in zip(self.faces_m, self.faces_m[1:]))

    @property
    def areas_m2(self) -> tuple[float, ...]:
        return tuple(4 * math.pi * r * r for r in self.faces_m)

    @property
    def volumes_m3(self) -> tuple[float, ...]:
        return tuple((4 * math.pi/3) * (b-a) * (b*b+a*b+a*a)
                     for a, b in zip(self.faces_m, self.faces_m[1:]))

    def face_metric(self, face: int) -> tuple[float, float, float]:
        """Physical area and equivalent left/right distances for a noncentral face.

        ell=Aface*integral(dr/A(r))=rface²*(b-a)/(a*b).
        Thus ell/(Aface*k) is each exact analytic spherical-shell resistance.
        Center noflux is assembled directly, never by evaluating a singular path.
        """
        if type(face) is not int or not 1 <= face <= self.cells:
            raise SphericalGeometryError('noncentral_face_index_required')
        r = self.faces_m[face]
        left = self.centers_m[face-1]
        # Factored expression avoids cancellation in 1/a-1/b.
        dl = r * ((r-left)/left)
        dr = (r * ((self.centers_m[face]-r)/self.centers_m[face])
              if face < self.cells else 0.)
        area = self.areas_m2[face]
        _positive(area, 'face_area')
        _positive(dl, 'left_resistance_distance')
        if face < self.cells:
            _positive(dr, 'right_resistance_distance')
        return area, dl, dr
