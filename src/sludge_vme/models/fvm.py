from __future__ import annotations

import numpy as np
from scipy.sparse import lil_matrix


def finite_volume_laplacian(values: np.ndarray, dx: float, surface_flux_per_conductivity: float = 0.0) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2 or dx <= 0.0:
        raise ValueError("finite-volume field must be one-dimensional with at least two cells and dx > 0")
    result = np.zeros_like(values)
    result[0] = (values[1] - values[0]) / dx**2
    result[1:-1] = (values[:-2] - 2.0 * values[1:-1] + values[2:]) / dx**2
    result[-1] = (values[-2] - values[-1]) / dx**2 + surface_flux_per_conductivity / dx
    return result


def current_pore_molar_concentration(
    reference_molar_inventory: np.ndarray,
    open_porosity: np.ndarray,
    volume_ratio: np.ndarray,
) -> np.ndarray:
    """Convert molar inventory per reference bulk volume to current-pore molarity."""
    inventory = np.asarray(reference_molar_inventory, dtype=float)
    porosity = np.asarray(open_porosity, dtype=float)
    jacobian = np.asarray(volume_ratio, dtype=float)
    if inventory.ndim != 1 or porosity.shape != inventory.shape or jacobian.shape != inventory.shape:
        raise ValueError("inventory, porosity and volume ratio must be one-dimensional arrays of equal shape")
    if not np.all(np.isfinite(inventory)) or not np.all(np.isfinite(porosity)) or not np.all(np.isfinite(jacobian)):
        raise ValueError("current-pore transport inputs must be finite")
    if np.any(porosity <= 0.0) or np.any(jacobian <= 0.0):
        raise ValueError("open porosity and volume ratio must be strictly positive")
    return inventory / (porosity * jacobian)


def conservative_molar_fick_rate(
    reference_molar_inventory: np.ndarray,
    open_porosity: np.ndarray,
    volume_ratio: np.ndarray,
    *,
    diffusivity_m2_s: float,
    dx_reference_m: float,
    surface_transfer_m_s: float,
) -> tuple[np.ndarray, float]:
    """Return molar-storage rate and outward molar flux on reference geometry.

    ``reference_molar_inventory`` is in ``mol/m3_reference_bulk`` and the
    current concentration is ``N_ref / (phi_open * J)`` in
    ``mol/m3_current_pore``. Isotropic
    deformation gives the reference-area Fick mobility ``D * J**(1/3)`` and
    transforms the current surface area by ``J**(2/3)``.  Summing the returned
    molar cell rates times ``dx_reference_m`` exactly cancels the returned
    ``mol/m2_reference/s`` outflow. Species mass storage is recovered only by
    multiplying both outputs by that species' ``kg/mol`` molar mass.
    """
    if diffusivity_m2_s <= 0.0 or dx_reference_m <= 0.0 or surface_transfer_m_s < 0.0:
        raise ValueError("diffusivity and dx must be positive; surface transfer must be nonnegative")
    concentration = current_pore_molar_concentration(reference_molar_inventory, open_porosity, volume_ratio)
    if concentration.size < 2:
        raise ValueError("Fick finite-volume transport requires at least two cells")
    stretch = np.asarray(volume_ratio, dtype=float) ** (1.0 / 3.0)
    face_stretch = 0.5 * (stretch[:-1] + stretch[1:])
    internal_flux = -diffusivity_m2_s * face_stretch * np.diff(concentration) / dx_reference_m
    surface_outflow = surface_transfer_m_s * float(concentration[-1]) * stretch[-1] ** 2
    rate = np.empty_like(concentration)
    rate[0] = -internal_flux[0] / dx_reference_m
    rate[1:-1] = (internal_flux[:-1] - internal_flux[1:]) / dx_reference_m
    rate[-1] = (internal_flux[-1] - surface_outflow) / dx_reference_m
    return rate, float(surface_outflow)


def block_jacobian_sparsity(cells: int, reactions: int, gases: int):
    size = cells * (2 + reactions + gases) + gases + 2
    pattern = lil_matrix((size, size), dtype=int)
    fields = 2 + reactions + gases
    for field in range(fields):
        start = field * cells
        for cell in range(cells):
            row = start + cell
            for local_field in range(fields):
                pattern[row, local_field * cells + cell] = 1
            if cell > 0:
                pattern[row, start + cell - 1] = 1
            if cell + 1 < cells:
                pattern[row, start + cell + 1] = 1
    released_start = fields * cells
    pattern[released_start:, :] = 1
    for row in range(size):
        pattern[row, row] = 1
    return pattern.tocsr()
