from __future__ import annotations

import numpy as np


def nondominated_mask(objectives, feasible) -> np.ndarray:
    values = np.asarray(objectives, dtype=float)
    allowed = np.asarray(feasible, dtype=bool)
    if values.ndim != 2 or allowed.shape != (values.shape[0],):
        raise ValueError("objectives must be 2D and feasible mask match rows")
    allowed &= np.all(np.isfinite(values), axis=1)
    mask = allowed.copy()
    for index in np.flatnonzero(allowed):
        for other in np.flatnonzero(allowed):
            if other == index:
                continue
            if np.all(values[other] <= values[index]) and np.any(values[other] < values[index]):
                mask[index] = False
                break
    return mask
