"""Propose an exactly nested initial-material partition from saved amounts.

Standard library only; imports the existing saved-data comparison primitive.
No model construction, rate evaluation, integration or acceptance decision.
Every numerical selection input is required explicitly by the caller.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

from reference_volume_compare import ConservativeMap, ReferencePartition, compare_profile


def saved_sample(record: dict, time_s: float) -> tuple[int, dict]:
    """Select exactly one stored time; never interpolate or search for a score."""
    rows = [(i, row) for i, row in enumerate(record["saved_numerical_samples"])
            if row["time_s"] == time_s]
    if len(rows) != 1:
        raise ValueError(f"expected one saved sample at {time_s} s, found {len(rows)}")
    return rows[0]


def saved_amount(sample: dict, field: str) -> tuple[list[float], str]:
    """Read the extensive fields actually stored by the P44/P46 producers."""
    scalar_profiles = {
        "calcite_inventory_mol": "mol",
        "lime_inventory_mol": "mol",
        "portlandite_inventory_mol": "mol",
        "calcium_inventory_residual_mol": "mol",
        "residual_carbon_kg": "kg",
    }
    if field in scalar_profiles:
        return sample[field], scalar_profiles[field]
    parts = field.split(".")
    if len(parts) == 2 and parts[0] in ("reaction_extent_mol", "gas_inventory_mol"):
        return sample[parts[0]][parts[1]], "mol"
    raise ValueError("field must be a saved inventory, independent reaction extent, "
                     "calcium inventory residual or residual carbon amount")


def mapping_record(mapping: ConservativeMap, source_name: str, target_name: str) -> dict:
    return {
        "source_partition": source_name,
        "target_partition": target_name,
        "target_rows": [
            {"target_cell_index": i,
             "source_cell_indices": [j for j, _ in row],
             "extensive_weights": [w for _, w in row]}
            for i, row in enumerate(mapping.weights)
        ],
        "diagnostics": mapping.diagnostics(),
    }


def source_record(record: dict, partition: ReferencePartition, sample_index: int) -> dict:
    initial = record["actual_initial_state"]
    return {
        "id": record["id"],
        "schema": record["schema"],
        "identity": record["identity"],
        "recorded_utc": record["recorded_utc"],
        "selected_saved_sample_index": sample_index,
        "selected_saved_time_s": record["saved_numerical_samples"][sample_index]["time_s"],
        "active_profile_mode": record.get("active_profile_mode"),
        "actual_calcium_coordinate_mode": record.get("actual_calcium_coordinate_mode"),
        "frozen_job": record["frozen_job"],
        "initial_reference_faces_m": initial["initial_reference_faces_m"],
        "initial_reference_centers_m": initial["initial_reference_centers_m"],
        "initial_reference_bulk_m3": initial["initial_reference_bulk_m3"],
        "geometry_diagnostics": partition.geometry_diagnostics(),
    }


def propose(coarse: dict, fine: dict, *, area_m2: float, time_s: float,
            field: str, split_count: int) -> dict:
    """Split the largest saved local differences, once, on original coarse cells.

    split_count counts coarse cells, not new faces. Each selected coarse cell
    receives all of its already saved internal fine faces. Rank by absolute
    extensive fine-minus-coarse difference, with lower coarse index first for
    exact ties. No reranking after a split or guessed coarse-to-child profile.
    """
    cp = ReferencePartition.from_saved(coarse, area_m2)
    fp = ReferencePartition.from_saved(fine, area_m2)
    fine_to_coarse = ConservativeMap(fp, cp)
    coarse_index, coarse_sample = saved_sample(coarse, time_s)
    fine_index, fine_sample = saved_sample(fine, time_s)
    coarse_amount, unit = saved_amount(coarse_sample, field)
    fine_amount, _ = saved_amount(fine_sample, field)
    comparison = compare_profile(coarse_amount, fine_amount, fine_to_coarse)

    ranking = []
    for i, (delta, row) in enumerate(zip(comparison["signed_fine_minus_coarse"],
                                        fine_to_coarse.weights)):
        children = [j for j, _ in row]
        inside = list(range(children[0] + 1, children[-1] + 1))
        ranking.append({
            "coarse_cell_index": i,
            "initial_reference_interval_m": [cp.faces_m[i], cp.faces_m[i + 1]],
            "coarse_amount": coarse_amount[i],
            "fine_conservative_mapped_amount": comparison["fine_conservative_mapped"][i],
            "signed_fine_minus_coarse_amount": delta,
            "absolute_local_difference_amount": abs(delta),
            "saved_fine_child_cell_indices": children,
            "available_internal_fine_face_indices": inside,
            "splittable": bool(inside),
        })
    ranking.sort(key=lambda row: (-row["absolute_local_difference_amount"],
                                  row["coarse_cell_index"]))
    eligible = [row for row in ranking if row["splittable"]]
    if split_count < 1 or split_count > len(eligible):
        raise ValueError(f"split_count must be between 1 and {len(eligible)} splittable coarse cells")
    selected = eligible[:split_count]
    selected_cells = {row["coarse_cell_index"] for row in selected}
    for rank, row in enumerate(ranking, start=1):
        row["absolute_difference_rank"] = rank
        row["selected"] = row["coarse_cell_index"] in selected_cells

    faces = [cp.faces_m[0]]
    inserted = []
    for i, children in enumerate(fine_to_coarse.weights):
        if i in selected_cells:
            for face_index in range(children[0][0] + 1, children[-1][0] + 1):
                faces.append(fp.faces_m[face_index])
                inserted.append({"proposal_face_index": len(faces) - 1,
                                 "fine_face_index": face_index,
                                 "coarse_parent_cell_index": i,
                                 "initial_reference_position_m": fp.faces_m[face_index]})
        faces.append(cp.faces_m[i + 1])

    # Exact face aggregation also supplies the proposed reference volumes.
    face_indices = [fp.faces_m.index(face) for face in faces]
    volumes = tuple(math.fsum(fp.bulk_m3[a:b])
                    for a, b in zip(face_indices, face_indices[1:]))
    pp = ReferencePartition(tuple(faces), volumes, area_m2)
    fine_to_proposal = ConservativeMap(fp, pp)
    proposal_to_coarse = ConservativeMap(pp, cp)
    proposed_amount = fine_to_proposal.apply(fine_amount)
    back_to_coarse = proposal_to_coarse.apply(proposed_amount)
    parent_by_proposal_cell = [0] * pp.cells
    for parent, row in enumerate(proposal_to_coarse.weights):
        for child, _ in row:
            parent_by_proposal_cell[child] = parent

    return {
        "schema": "saved_nested_reference_partition_proposal_v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "basis": "Saved initial material coordinates; exact fine-cell aggregation on the same reference intervals",
        "inputs": {"time_s": time_s, "field": field, "amount_unit": unit,
                   "area_m2": area_m2, "split_count_coarse_cells": split_count,
                   "coordinate_unit": "m", "reference_volume_unit": "m3"},
        "sources": {"coarse": source_record(coarse, cp, coarse_index),
                    "fine": source_record(fine, fp, fine_index)},
        "selection": {
            "score": "absolute saved extensive fine-conservative-mapped minus coarse amount; not density or relative error",
            "ordering": "descending score, then ascending zero-based original coarse cell index",
            "unsplittable_cells": "remain in ranking; skipped because no saved internal fine face exists",
            "split_rule": "insert every saved internal fine face in each selected original coarse cell",
            "split_count_meaning": "number of original coarse cells; inserted face count can differ",
            "zero_difference_rule": "explicit split count still applies; exact ties use coarse index",
            "selected_coarse_cell_indices_in_rank_order": [row["coarse_cell_index"] for row in selected],
            "ranking": ranking,
        },
        "original_same_reference_interval_comparison": comparison,
        "proposed_initial_partition": {
            "cells": pp.cells,
            "initial_reference_faces_m": pp.faces_m,
            "initial_reference_centers_m": [(a + b) / 2 for a, b in zip(pp.faces_m, pp.faces_m[1:])],
            "initial_reference_widths_m": [b - a for a, b in zip(pp.faces_m, pp.faces_m[1:])],
            "initial_reference_bulk_m3": pp.bulk_m3,
            "area_m2": area_m2,
            "volume_basis": "sum of saved fine reference bulk volumes; raw area-width/coarse roundoff remains recorded",
            "original_coarse_parent_cell_by_proposal_cell": parent_by_proposal_cell,
            "saved_fine_face_index_by_proposal_face": face_indices,
            "inserted_face_sources": inserted,
            "geometry_diagnostics": pp.geometry_diagnostics(),
        },
        "conservative_maps": {
            "fine_to_coarse": mapping_record(fine_to_coarse, "saved_fine", "saved_coarse"),
            "fine_to_proposal": mapping_record(fine_to_proposal, "saved_fine", "proposal"),
            "proposal_to_coarse": mapping_record(proposal_to_coarse, "proposal", "saved_coarse"),
        },
        "saved_fine_amount_on_proposal": {
            "field": field, "unit": unit, "amount_by_cell": proposed_amount,
            "signed_fine_total_minus_proposed_total_roundoff": math.fsum(fine_amount) - math.fsum(proposed_amount),
            "signed_via_proposal_minus_direct_fine_to_coarse_roundoff_by_cell":
                [a - b for a, b in zip(back_to_coarse, comparison["fine_conservative_mapped"])],
            "scope": "rebinning saved fine data, not a newly simulated proposal solution or a coarse-to-child reconstruction",
        },
        "spatial_resolution_qualified": False,
        "new_model_instances_constitutive_RHS_Jac_ODE_fit_UQ_calls": 0,
        "limits": [
            "Proposal only; no threshold, convergence order or new simulation qualification",
            "The selected field and time are caller inputs; no time/parameter search or post-split error prediction",
            "Centers are geometric midpoints in initial reference coordinates; no current-space overlap",
            "Coarse child amounts are unknown; no prolongation, interpolation, face snapping, clipping or invented subgrid state",
            "Matching saved domains does not establish identical physics; source identities and modes must be read by the caller",
            "Original failures, physical boundaries and measured-data status are unchanged",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coarse", type=Path, required=True, help="saved coarse case JSON")
    parser.add_argument("--fine", type=Path, required=True, help="saved exactly nested fine case JSON")
    parser.add_argument("--parameters", type=Path, required=True, help="root-format physical parameter JSON, preferably the saved run snapshot")
    parser.add_argument("--area-parameter", required=True, help="explicit root parameter key with unit m2")
    parser.add_argument("--time-s", type=float, required=True, help="one exactly saved time in seconds")
    parser.add_argument("--field", required=True, help="saved extensive field, e.g. reaction_extent_mol.direct_carbonation")
    parser.add_argument("--split-count", type=int, required=True, help="number of original coarse cells to split")
    parser.add_argument("--output", type=Path, required=True, help="proposal JSON path; parent directory must exist")
    args = parser.parse_args()
    started = time.monotonic()
    parameter_path = args.parameters.resolve()
    area_record = json.loads(parameter_path.read_text())["parameters"][args.area_parameter]
    if area_record["unit"] != "m2":
        raise ValueError("area parameter must be expressed in m2; no implicit unit conversion")
    coarse_path, fine_path = args.coarse.resolve(), args.fine.resolve()
    result = propose(json.loads(coarse_path.read_text()), json.loads(fine_path.read_text()),
                     area_m2=area_record["value"], time_s=args.time_s,
                     field=args.field, split_count=args.split_count)
    result["sources"]["coarse"]["path"] = str(coarse_path)
    result["sources"]["fine"]["path"] = str(fine_path)
    result["sources"]["area_parameter"] = {"path": str(parameter_path),
                                           "key": args.area_parameter, "record": area_record}
    result["elapsed_saved_data_conversion_s"] = time.monotonic() - started
    output_path = args.output.resolve()
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output_path),
                      "selected_coarse_cell_indices": result["selection"]["selected_coarse_cell_indices_in_rank_order"],
                      "proposal_cells": result["proposed_initial_partition"]["cells"],
                      "inserted_faces": len(result["proposed_initial_partition"]["inserted_face_sources"]),
                      "elapsed_saved_data_conversion_s": result["elapsed_saved_data_conversion_s"],
                      "output_bytes": output_path.stat().st_size,
                      "spatial_resolution_qualified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
