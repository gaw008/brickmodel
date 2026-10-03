"""Offline inventories and signed ledgers for the declared saved endpoint chain.

This producer adds output only. The unchanged strict checkpoint loader and
unchanged complete storage expression remain authoritative. It never integrates
a trajectory or substitutes the new declared initial reference for saved states.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from .full_cycle import write_json
from .full_cycle_checkpoint import load_native_checkpoint, _source_text


def relative_residual(residual, scale, *, unit, source, threshold):
    """A zero actual denominator has no relative verdict, even at zero residual."""
    defined = scale != 0
    relative = abs(residual)/abs(scale) if defined else None
    return {'signed_residual':float(residual), 'unit':unit,
            'denominator':float(scale), 'denominator_source':source,
            'absolute_relative_residual':float(relative) if defined else None,
            'denominator_status':'defined' if defined else 'undefined_zero_budget',
            'passed':bool(relative < threshold) if defined and threshold is not None else (None if defined else False),
            'threshold':threshold}


def endpoint_inventory(model, stage, time_s, y, *, provenance, contract):
    """One native decode and one complete potential value, with no gradients."""
    state = model.native_potential_state(y)
    values = model.potential_values(state)
    n, g = model.n, model.g
    slots = contract['native_cumulative_slots']
    condensed = state['condensed_mol']
    gas = state['gas_mol']
    inventory = np.r_[condensed.sum(axis=0), gas.sum(axis=0)]
    extents = y[model.extent_offset:model.last].reshape(model.nr,n).T*model.cell_chemical_scale[:,None]
    return {'stage':stage, 'time_s':float(time_s), 'provenance':provenance,
            'native_y':y, 'temperature_k':state['temperature_k'],
            'condensed_inventory_mol':{name:condensed[:,i] for i,name in enumerate(model.ns)},
            'gas_inventory_mol':{name:gas[:,i] for i,name in enumerate(model.ng)},
            'inventory_total_mol':{name:float(inventory[i]) for i,name in enumerate(model.names)},
            'complete_mass_kg':float(inventory@model.mw),
            'element_inventory_mol_atoms':{name:float((inventory@model.atom)[i]) for i,name in enumerate(model.elements)},
            'bulk_m3':state['bulk_m3'], 'native_pore_m3':state['native_pore_m3'],
            'native_surface_energy_j':state['native_surface_energy_j'],
            'minimum_condensed_inventory_mol':float(condensed.min()),
            'minimum_gas_inventory_mol':float(gas.min()),
            'strict_nonnegative_inventories':bool(condensed.min() >= 0 and gas.min() >= 0),
            'complete_storage':values,
            'reaction_extent_mol':{r['id']:float(extents[:,i].sum()) for i,r in enumerate(model.reactions)},
            'boundary_in_mol':{name:float(y[model.last+i]*model.nscale) for i,name in enumerate(model.ng)},
            'boundary_out_mol':{name:float(y[model.last+g+i]*model.nscale) for i,name in enumerate(model.ng)},
            'heat_j':float(y[slots['heat_field']*n:(slots['heat_field']+1)*n].sum()*model.escale),
            'carried_energy_j':float(y[slots['carried_field']*n:(slots['carried_field']+1)*n].sum()*model.escale),
            'exterior_pressure_work_j':float(y[-slots['work_from_end']]*model.escale),
            'entropy_production_j_k':float(y[-slots['production_from_end']]*model.escale/model.Tr),
            'entropy_exchange_j_k':float(y[-slots['exchange_from_end']]*model.escale/model.Tr)}


def interval_ledger(model, points, reference, contract, *, name, evidence_basis):
    """The original rules evaluated on supplied endpoint samples, not a path maximum."""
    start, end = points[0], points[-1]
    threshold = model.config['parameters'][contract['balance_threshold_parameter']]['value']
    s_threshold = model.config['parameters'][contract['entropy_threshold_parameter']]['value']
    inflow = np.array([end['boundary_in_mol'][s]-start['boundary_in_mol'][s] for s in model.ng])
    outflow = np.array([end['boundary_out_mol'][s]-start['boundary_out_mol'][s] for s in model.ng])
    net_in = inflow-outflow
    mass_residual = end['complete_mass_kg']-start['complete_mass_kg']-net_in@model.mw[len(model.ns):]
    mass = relative_residual(mass_residual, reference['complete_mass_kg'],unit='kg',
        source=contract['normalization']['mass'],threshold=threshold)
    incoming_elements = inflow@model.atom[len(model.ns):]
    net_elements = net_in@model.atom[len(model.ns):]
    elements = {}
    for i,element in enumerate(model.elements):
        residual = end['element_inventory_mol_atoms'][element]-start['element_inventory_mol_atoms'][element]-net_elements[i]
        scale = max(reference['element_inventory_mol_atoms'][element],incoming_elements[i])
        elements[element] = relative_residual(residual,scale,unit='mol_atoms',
            source=contract['normalization']['elements'],threshold=threshold)
        elements[element]['initial_reference_mol_atoms'] = reference['element_inventory_mol_atoms'][element]
        elements[element]['signed_boundary_in_mol_atoms'] = float(incoming_elements[i])
    energy_ranges = {key:float(np.ptp([row[key] for row in points]))
                     for key in ['heat_j','carried_energy_j','exterior_pressure_work_j']}
    energy_scale = max(sum(energy_ranges.values()),model.escale)
    delta_heat = end['heat_j']-start['heat_j']
    delta_carried = end['carried_energy_j']-start['carried_energy_j']
    delta_work = end['exterior_pressure_work_j']-start['exterior_pressure_work_j']
    delta_u = end['complete_storage']['global']['native_reduction_U_j']-start['complete_storage']['global']['native_reduction_U_j']
    energy = relative_residual(delta_u-delta_heat-delta_carried-delta_work,energy_scale,
        unit='J',source=contract['normalization']['energy'],threshold=threshold)
    energy.update(stored_U_change_j=float(delta_u),heat_change_j=delta_heat,
        carried_energy_change_j=delta_carried,exterior_pressure_work_change_j=delta_work,
        endpoint_sample_cumulative_ranges_j=energy_ranges,
        original_initial_thermal_capacity_scale_j=float(model.escale))
    delta_s = end['complete_storage']['global']['native_reduction_S_j_k']-start['complete_storage']['global']['native_reduction_S_j_k']
    delta_prod = end['entropy_production_j_k']-start['entropy_production_j_k']
    delta_exchange = end['entropy_exchange_j_k']-start['entropy_exchange_j_k']
    canonical_s_residual = (delta_s-delta_prod)-delta_exchange
    entropy = relative_residual(canonical_s_residual,model.escale/model.Tr,
        unit='J/K',source=contract['normalization']['entropy'],threshold=s_threshold)
    production_offset = contract['native_cumulative_slots']['production_from_end']
    original_order = delta_s-float((end['native_y'][-production_offset:]-start['native_y'][-production_offset:]).sum()*model.escale/model.Tr)
    entropy.update(stored_S_change_j_k=float(delta_s),production_change_j_k=delta_prod,
        exchange_change_j_k=delta_exchange,original_slot_sum_order_residual_j_k=original_order,
        separate_minus_original_order_residual_j_k=float(canonical_s_residual-original_order))
    reaction_changes = {r['id']:end['reaction_extent_mol'][r['id']]-start['reaction_extent_mol'][r['id']]
                        for r in model.reactions}
    gas_ledgers = {}
    for i,species in enumerate(model.ng):
        n0=start['inventory_total_mol'][species]; n1=end['inventory_total_mol'][species]
        sources={r['id']:reaction_changes[r['id']]*r['stoichiometry'].get(species,0)
                 for r in model.reactions}
        residual = n1-n0-sum(sources.values())-inflow[i]+outflow[i]
        budget = max(abs(n0),abs(n1),sum(abs(value) for value in sources.values()),abs(inflow[i])+abs(outflow[i]))
        gas_ledgers[species] = {'start_inventory_mol':n0,'end_inventory_mol':n1,
            'signed_inventory_change_mol':n1-n0,'signed_reaction_sources_mol':sources,
            'signed_reaction_net_source_mol':sum(sources.values()),
            'signed_boundary_in_mol':float(inflow[i]),'signed_boundary_out_mol':float(outflow[i]),
            'budget_normalization':relative_residual(residual,budget,unit='mol',
                source=contract['normalization']['gas_budget'],threshold=threshold),
            'initial_reference_normalization':relative_residual(residual,reference['inventory_total_mol'][species],
                unit='mol',source=contract['normalization']['gas_initial_reference'],threshold=None)}
    pressure_check = delta_work+model.P*(sum(end['bulk_m3'])-sum(start['bulk_m3']))
    return {'name':name,'start_time_s':start['time_s'],'end_time_s':end['time_s'],
            'evidence_basis':evidence_basis,'mass':mass,'elements':elements,'complete_energy':energy,
            'entropy':entropy,'gas_species':gas_ledgers,'signed_reaction_extent_changes_mol':reaction_changes,
            'pressure_work_integration_signed_residual_j':float(pressure_check),
            'pressure_work_diagnostic_criterion':'criterion_not_applicable',
            'endpoint_balance_passed':mass['passed'] and all(v['passed'] for v in elements.values())
                and energy['passed'] and entropy['passed']
                and all(v['budget_normalization']['passed'] for v in gas_ledgers.values()),
            'scope':'Supplied endpoint samples only. No interval maximum or continuous entropy/source/material admission.',
            'whole_model_complete':False}


def export_endpoint_ledgers(parameters: Path, out: Path):
    """Read declared inputs, then use their unchanged strict loader exactly once."""
    root=json.loads(parameters.read_text())
    contract=root['endpoint_ledger_export']
    project_root=Path(__file__).resolve().parents[3]
    paths=[project_root/name for name in contract['inputs']]
    bundles=[json.loads(path.read_text()) for path in paths]
    final_bundle=bundles[-1]
    for bundle in bundles:
        if bundle['config']['parameters'] != final_bundle['config']['parameters'] or bundle['context'] != final_bundle['context']:
            raise ValueError('Saved endpoint physical case or original reference context differs')
    if root['parameters'] != final_bundle['config']['parameters']:
        raise ValueError('Current root physical parameter records differ from the declared saved case')
    for bundle in bundles[:-1]:
        if _source_text(bundle['config']) != bundle['source_version']['source_text']:
            raise ValueError('Saved endpoint inherited production source differs from current source')
    model, _, _, loaded = load_native_checkpoint(paths[-1],stage=None)
    endpoints={e['stage']:e for bundle in bundles for e in bundle['endpoints']}
    ordered=[endpoints[name] for name in loaded['config']['stages']]
    for bundle in bundles[1:]:
        origin=bundle['resume_origin']
        if origin['native_y'] != endpoints[origin['stage']]['native_y']:
            raise ValueError('Saved continuation origin differs from the preceding actual endpoint')
    # initial_state creates a new y; it does not assign any model reference.
    # All nine evaluations use the original context already restored by the loader.
    initial_y=model.initial_state()
    points=[endpoint_inventory(model,contract['initial_reference_label'],model.times[0],initial_y,
        provenance=contract['initial_reference_basis'],contract=contract)]
    points += [endpoint_inventory(model,e['stage'],e['time_s'],np.asarray(e['native_y'],dtype=float),
        provenance={'kind':'actual_saved_solver_endpoint','native_y_basis':e['native_y_basis']},contract=contract) for e in ordered]
    intervals=[interval_ledger(model,points[i:i+2],points[0],contract,name=name,
        evidence_basis=contract['first_interval_basis'] if i==0 else contract['saved_interval_basis'])
        for i,name in enumerate(loaded['config']['stages'])]
    whole=interval_ledger(model,points,points[0],contract,name=contract['whole_cycle_label'],
        evidence_basis=contract['whole_cycle_basis'])
    actual_calls={'saved_checkpoint_load':1,'make_cycle':1,'native_initial_state':1,
                  'native_potential_state':len(points),'complete_potential_values':model.potential_value_calls,
                  'native_RHS_counter':model.rhs_calls,'native_Jacobian_counter':model.jacobian_calls,
                  'ODE':0,'rates':0,'state_dynamics':0,'instantaneous_projection':0,
                  'potential_gradient_directions':0,'trajectory_summary':0,'predict':0,'fit':0,'UQ':0}
    payload={'schema':contract['schema'],'created_utc':datetime.now(timezone.utc).isoformat(),
        'units':contract['units'],'source_identity':{
            'inherited_source_paths':[bundle['config']['native_checkpoint']['source_paths'] for bundle in bundles],
            'inherited_identity_basis':'Existing per-bundle complete ordinary source comparison; final strict loader unchanged.',
            'independent_output_producer_path':contract['producer_source_path'],
            'independent_output_producer_text':(project_root/contract['producer_source_path']).read_text()},
        'inputs':[{'path':str(path),'full_bytes':path.stat().st_size} for path in paths],
        'initial_reference_basis':contract['initial_reference_basis'],
        'points':points,'intervals':intervals,'whole_cycle':whole,
        'completed_production_calls':actual_calls,'existing_potential_helper_counters':dict(model.potential_helper_calls),
        'uninstrumented_internal_calls':contract['source_only_forecast'],
        'normalization':contract['normalization'],'scope_limits':contract['scope_limits'],
        'criterion':'endpoint_ledger_criterion_only','whole_model_complete':False}
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/'case-parameters.json',{'saved_physical_case':loaded['config'],'endpoint_ledger_contract':contract})
    write_json(out/contract['output_filename'],payload)
    return {'output':str(out/contract['output_filename']),'completed_production_calls':actual_calls,
            'whole_model_complete':False,'criterion':'endpoint_ledger_criterion_only'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(export_endpoint_ledgers(args.parameters,args.out),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
