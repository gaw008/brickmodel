from __future__ import annotations

import numpy as np

from sludge_vme.models.fvm import block_jacobian_sparsity, finite_volume_laplacian


def test_finite_volume_laplacian_preserves_uniform_field_with_symmetry() -> None:
    values = np.ones(21)
    lap = finite_volume_laplacian(values, 0.03 / 21, surface_flux_per_conductivity=0.0)
    assert np.max(np.abs(lap)) == 0.0


def test_sparse_jacobian_pattern_is_bounded_not_dense() -> None:
    pattern = block_jacobian_sparsity(21, reactions=4, gases=4)
    assert pattern.shape == (216, 216)
    assert pattern.nnz < pattern.shape[0] * pattern.shape[1] / 4
