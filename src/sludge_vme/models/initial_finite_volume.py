"""Initial one-dimensional control volumes and extensive-coordinate algebra.

Arrays use cell as their first axis. These primitives do not evaluate a
constitutive model and are not connected to the full-cycle host yet.
"""
from __future__ import annotations

import numpy as np


def initial_partition(*, cells: int, half_thickness_m: float, area_m2: float,
                      profile: str, exterior_exponent: float) -> dict:
    """Return reference faces/centers/widths (m) and cell volumes (m3).

    The exponent is an explicit numerical input, including for the uniform
    profile. No profile is selected implicitly. Interior distances are the
    sum of adjacent half widths; exterior distance is the last half width.
    """
    if not isinstance(cells, int) or isinstance(cells, bool) or cells <= 0:
        raise ValueError('cells must be a positive integer')
    if not np.isfinite([half_thickness_m, area_m2, exterior_exponent]).all() or min(half_thickness_m, area_m2, exterior_exponent) <= 0:
        raise ValueError('length, area and exponent must be finite and positive')
    coordinate = np.arange(cells + 1, dtype=float) / cells
    if profile == 'uniform':
        faces = half_thickness_m * coordinate
    elif profile == 'exterior_power':
        faces = half_thickness_m * (1 - (1 - coordinate) ** exterior_exponent)
    else:
        raise ValueError('profile must be uniform or exterior_power')
    # Uniform widths retain the original constant L/N representation.
    widths = np.full(cells, half_thickness_m / cells) if profile == 'uniform' else np.diff(faces)
    if np.any(widths <= 0):
        raise ValueError('profile must yield strictly increasing faces')
    centers = (faces[:-1] + faces[1:]) / 2
    return {'faces_m': faces, 'centers_m': centers, 'widths_m': widths,
            'initial_bulk_m3': area_m2 * widths,
            'internal_center_distance_m': np.diff(centers),
            'symmetry_half_width_m': widths[0] / 2,
            'exterior_half_width_m': widths[-1] / 2}


def initial_cell_scales(initial_bulk_m3: np.ndarray, *, dry_density_kg_m3: float,
                        char_molar_mass_kg_mol: float, retention_kg_kg: float,
                        water_molar_mass_kg_mol: float) -> dict:
    """Return per-cell dry kg and chemical/retention mol reference scales.

    Retention is a site-equivalent scale, not additional material inventory.
    The caller retains the scalar retention input for global mechanism choice.
    """
    bulk = np.asarray(initial_bulk_m3)
    if bulk.ndim != 1 or not np.isfinite(bulk).all() or np.any(bulk <= 0):
        raise ValueError('initial bulk must contain positive finite cell volumes')
    values = [dry_density_kg_m3, char_molar_mass_kg_mol, water_molar_mass_kg_mol]
    if not np.isfinite(values).all() or min(values) <= 0 or not np.isfinite(retention_kg_kg) or retention_kg_kg < 0:
        raise ValueError('density/molar masses must be positive; retention nonnegative')
    dry_mass = dry_density_kg_m3 * bulk
    return {'dry_mass_kg': dry_mass,
            'chemical_scale_mol': dry_mass / char_molar_mass_kg_mol,
            'retention_scale_mol': retention_kg_kg * dry_mass / water_molar_mass_kg_mol,
            'total_initial_dry_mass_kg': float(dry_mass.sum())}


def extent_coordinates(extent_mol: np.ndarray, chemical_scale_mol: np.ndarray) -> np.ndarray:
    """Encode given (cells,reactions) mol as reaction-first flat coordinates.

    The same algebra encodes a mol/s rate into coordinate/s. It does not
    reconstruct an independently integrated extent from species inventories.
    """
    extent = np.asarray(extent_mol); scale = np.asarray(chemical_scale_mol)
    if extent.ndim != 2 or scale.ndim != 1 or extent.shape[0] != scale.size:
        raise ValueError('extent must be (cells,reactions), scale must be (cells,)')
    if not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('chemical scales must be finite and positive')
    return (extent / scale[:, None]).T.ravel()


def extent_inventory(flat_coordinates: np.ndarray, chemical_scale_mol: np.ndarray,
                     *, reactions: int) -> np.ndarray:
    """Decode reaction-first coordinates to given (cells,reactions) mol."""
    coordinates = np.asarray(flat_coordinates); scale = np.asarray(chemical_scale_mol)
    if scale.ndim != 1 or coordinates.ndim != 1 or coordinates.size != reactions * scale.size:
        raise ValueError('flat coordinate size must equal reactions times cells')
    if not isinstance(reactions, int) or isinstance(reactions, bool) or reactions <= 0 or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('reaction count and chemical scales must be positive')
    return coordinates.reshape(reactions, scale.size).T * scale[:, None]


def nested_extensive_sum(fine_values: np.ndarray, *, parent_cells: int) -> np.ndarray:
    """Add consecutive children along cell axis; never average extensive data.

    The caller must supply an analytically nested partition. This operation
    accepts independent extents, inventories, kg, J or J/K; it does not infer
    geometry or provide a temperature/chemical-potential interpolation.
    """
    values = np.asarray(fine_values)
    if not isinstance(parent_cells, int) or isinstance(parent_cells, bool) or parent_cells <= 0 or values.ndim == 0 or values.shape[0] % parent_cells:
        raise ValueError('cell axis must be an integer multiple of positive parent count')
    return values.reshape((parent_cells, values.shape[0] // parent_cells, *values.shape[1:])).sum(axis=1)


def shared_face_balance(source_rate: np.ndarray, oriented_face_rate: np.ndarray) -> np.ndarray:
    """Return cell storage rates from extensive sources and signed face rates.

    Face orientation points from the symmetry side toward the exterior.
    Inputs carry consistent mol/s, W or other extensive-rate units. Area and
    distance already belong in the supplied flux; no cell volume is added.
    """
    source = np.asarray(source_rate); faces = np.asarray(oriented_face_rate)
    if source.ndim == 0 or faces.shape != (source.shape[0] + 1, *source.shape[1:]):
        raise ValueError('face rates need cells+1 on the first axis and matching fields')
    return source + faces[:-1] - faces[1:]
