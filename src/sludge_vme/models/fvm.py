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
