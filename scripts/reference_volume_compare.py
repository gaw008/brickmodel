"""Saved-data conservative comparison on reference material intervals.

Standard library only. No model imports, state construction or rate evaluation.
Only extensive quantities (mol, kg, J, ...) may be passed to the mapper.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class ReferencePartition:
    faces_m: tuple[float, ...]
    bulk_m3: tuple[float, ...]
    area_m2: float

    @classmethod
    def from_saved(cls, record: dict, area_m2: float) -> "ReferencePartition":
        initial = record["actual_initial_state"]
        return cls(initial["initial_reference_faces_m"],
                   initial["initial_reference_bulk_m3"], area_m2)

    @property
    def cells(self) -> int:
        return len(self.bulk_m3)

    def geometry_diagnostics(self) -> dict:
        residuals = [v - self.area_m2 * (b - a) for a, b, v in
                     zip(self.faces_m, self.faces_m[1:], self.bulk_m3)]
        mean_volume = math.fsum(self.bulk_m3) / self.cells
        return {
            "cells": self.cells,
            "reference_faces_m": self.faces_m,
            "saved_reference_bulk_m3": self.bulk_m3,
            "area_m2": self.area_m2,
            "signed_cell_volume_minus_area_width_m3": residuals,
            "signed_total_volume_minus_area_domain_m3": math.fsum(self.bulk_m3) - self.area_m2 * (self.faces_m[-1] - self.faces_m[0]),
            "uniform_b0_over_saved_reference_volume": [mean_volume / v for v in self.bulk_m3],
            "roundoff_check_scope": "Raw stored geometry residuals only; no geometry tolerance or scientific acceptance decision",
        }


class ConservativeMap:
    """Sum saved child-cell amounts onto exactly nested initial material faces.

    Every target face must occur in the saved source faces. No interpolation,
    face snapping, partial coverage or within-cell reconstruction is performed.
    """

    def __init__(self, source: ReferencePartition, target: ReferencePartition):
        if source.area_m2 != target.area_m2:
            raise ValueError("reference areas differ")
        if (source.faces_m[0], source.faces_m[-1]) != (target.faces_m[0], target.faces_m[-1]):
            raise ValueError("reference domains differ")
        self.source, self.target = source, target
        self.weights = tuple(tuple((j, 1.0) for j in range(source.faces_m.index(a), source.faces_m.index(b)))
                             for a, b in zip(target.faces_m, target.faces_m[1:]))
        self.exact_aggregation = True

    def apply(self, amounts: Sequence[float]) -> list[float]:
        if len(amounts) != self.source.cells:
            raise ValueError("extensive field length does not match source cells")
        return [math.fsum(amounts[j] for j, _ in row) for row in self.weights]

    def diagnostics(self) -> dict:
        coverage = [math.fsum(w for row in self.weights for j, w in row if j == i)
                    for i in range(self.source.cells)]
        volumes = self.apply(self.source.bulk_m3)
        return {
            "mode": "exact_saved_child_aggregation" if self.exact_aggregation else "piecewise_constant_reference_volume_reconstruction",
            "source_cells": self.source.cells, "target_cells": self.target.cells,
            "source_cell_coverage_fractions": coverage,
            "signed_mapped_minus_target_reference_volume_m3": [a - b for a, b in zip(volumes, self.target.bulk_m3)],
            "partial_source_cell_assumption": None if self.exact_aggregation else "constant extensive density within each source reference cell; no continuous-solution qualification",
        }


def safe_ratio(numerator: float, denominator: float):
    return numerator / denominator if denominator != 0 else None


def compare_profile(coarse: Sequence[float], fine: Sequence[float], mapping: ConservativeMap) -> dict:
    """Signed differences and cumulative amounts; no acceptance decision."""
    left = tuple(coarse)
    if len(left) != mapping.target.cells:
        raise ValueError("coarse field length does not match target cells")
    right = mapping.apply(fine)
    delta = [b - a for a, b in zip(left, right)]
    prefix = [0.0] + [math.fsum(delta[:i]) for i in range(1, len(delta) + 1)]
    signed_total = math.fsum(delta)
    absolute_total = math.fsum(abs(v) for v in delta)
    return {
        "coarse_raw": left, "fine_conservative_mapped": right,
        "signed_fine_minus_coarse": delta,
        "signed_global_difference": signed_total,
        "sum_absolute_local_difference": absolute_total,
        "global_absolute_over_local_absolute": safe_ratio(abs(signed_total), absolute_total),
        "relative_global_to_abs_coarse_total": safe_ratio(abs(signed_total), abs(math.fsum(left))),
        "relative_local_L1_to_coarse_L1": safe_ratio(absolute_total, math.fsum(abs(v) for v in left)),
        "signed_cumulative_difference_at_target_faces": prefix,
        "maximum_absolute_cumulative_difference": max(abs(v) for v in prefix),
        "coarse_amount_per_reference_bulk": [v / volume for v, volume in zip(left, mapping.target.bulk_m3)],
        "fine_mapped_amount_per_same_reference_bulk": [v / volume for v, volume in zip(right, mapping.target.bulk_m3)],
        "signed_fine_total_minus_mapped_total_roundoff": math.fsum(fine) - math.fsum(right),
        "outer_interval_signed_difference": delta[-1],
        "outer_interval_fraction_of_signed_global_difference": safe_ratio(delta[-1], signed_total),
        "outer_interval_fraction_of_local_absolute_difference": safe_ratio(abs(delta[-1]), absolute_total),
        "zero_denominator_policy": "undefined ratios are null; no floor or acceptance threshold",
    }


def co2_endpoint_diagnostic(record: dict) -> dict:
    """Expose supply mismatch without inserting the existing residual to zero it."""
    row = record["report"]["gas_species_ledger"]["whole_cycle"]["species"]["CO2"]
    extent = record["report"]["summary"]["reaction_totals_mol"]["direct_carbonation"]
    other = math.fsum(v for k, v in row["reaction_sources_mol"].items() if k != "direct_carbonation")
    supply = math.fsum([row["initial_inventory_mol"], -row["final_inventory_mol"],
                        row["boundary_in_mol"], -row["boundary_out_mol"], other])
    mismatch = extent - supply
    return {
        "independent_saved_extent_mol": extent,
        "initial_CO2_mol": row["initial_inventory_mol"], "final_CO2_mol": row["final_inventory_mol"],
        "boundary_in_CO2_mol": row["boundary_in_mol"], "boundary_out_CO2_mol": row["boundary_out_mol"],
        "other_signed_CO2_sources_mol": other,
        "residual_free_endpoint_supply_mol": supply,
        "extent_minus_residual_free_supply_mol": mismatch,
        "original_signed_CO2_residual_mol": row["residual_mol"],
        "signed_mismatch_minus_original_residual_roundoff_mol": mismatch - row["residual_mol"],
        "scope": "Endpoint cross-read of saved independent state slots. The mismatch is the original budget residual, not a second independent conservation test or reconstructed extent. No molecular/Darcy decomposition.",
    }


def compare_saved(coarse: dict, fine: dict, area_m2: float) -> dict:
    cp = ReferencePartition.from_saved(coarse, area_m2)
    fp = ReferencePartition.from_saved(fine, area_m2)
    mapping = ConservativeMap(fp, cp)
    cr, fr = coarse["saved_numerical_samples"], fine["saved_numerical_samples"]
    times = tuple(r["time_s"] for r in cr)
    if not times or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("saved times must be nonempty and strictly increasing")
    if times != tuple(r["time_s"] for r in fr):
        raise ValueError("saved times differ; implicit time interpolation forbidden")
    samples = []
    for left, right in zip(cr, fr):
        direct = compare_profile(left["reaction_extent_mol"]["direct_carbonation"],
                                 right["reaction_extent_mol"]["direct_carbonation"], mapping)
        gas = compare_profile(left["gas_inventory_mol"]["CO2"], right["gas_inventory_mol"]["CO2"], mapping)
        cb = [v * (1 - sh) for v, sh in zip(cp.bulk_m3, left["thickness_shrinkage"])]
        fb = [v * (1 - sh) for v, sh in zip(fp.bulk_m3, right["thickness_shrinkage"])]
        if len(left["thickness_shrinkage"]) != cp.cells or len(right["thickness_shrinkage"]) != fp.cells:
            raise ValueError("saved shrinkage length does not match partition")
        samples.append({"time_s": left["time_s"], "direct_extent_mol": direct, "CO2_inventory_mol": gas,
                        "current_bulk_m3": {"coarse": cb, "fine_mapped": mapping.apply(fb)},
                        "original_peak_temperature_contrast_K": {"coarse": left["temperature_difference_k"], "fine": right["temperature_difference_k"]}})
    endpoints = {"coarse": co2_endpoint_diagnostic(coarse), "fine": co2_endpoint_diagnostic(fine)}
    account_delta = {key: value - endpoints["coarse"][key]
                     for key, value in endpoints["fine"].items() if isinstance(value, (int, float))}
    return {
        "coarse_case": coarse["id"], "fine_case": fine["id"],
        "geometry": {"coarse": cp.geometry_diagnostics(), "fine": fp.geometry_diagnostics()},
        "mapping": mapping.diagnostics(), "saved_samples": samples,
        "initial_saved_direct_rate_mol_s": compare_profile(cr[0]["direct_carbonation_rate_mol_s"], fr[0]["direct_carbonation_rate_mol_s"], mapping),
        "endpoint_CO2": endpoints,
        "signed_fine_minus_coarse_CO2_endpoint_account": account_delta,
        "basis": "Same initial material intervals, reference-volume density and exact saved-face aggregation. Current volumes come from each saved cell V0*(1-shrinkage); this is not current-space overlap. Intensives and temperature are not conservatively summed.",
        "spatial_resolution_qualified": False, "scientific_model_bug_confirmed": False,
    }
