"""Run one root-declared saved-face short production transient, offline.

Uses the existing model.integrate and its native summaries. No extra RHS,
Jacobian, constitutive scan, independent model, or repeated forward.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    snapshot = json.loads(args.parameters.read_text())
    contract = snapshot['public_reference_cases']['saved_reference_transient']
    sys.path.insert(0, str(project / contract['frozen_source_root']))
    import numpy as np
    from sludge_vme.models.full_cycle import read_parameters, make_cycle
    from sludge_vme.models.instantaneous_diagnostics import plain
    root = read_parameters(args.parameters)
    case_path = project / contract['case_output']
    case = read_parameters(case_path)
    calls = {}; summary_depth = 0; phase = 'construction'; actual_events = []; strict = []; native_heat = {}
    cpu = resource.getrusage(resource.RUSAGE_SELF); start = time.monotonic(); model = None
    def save_counts():
        output = {'recorded_utc':datetime.now(timezone.utc).isoformat(),'entries_by_phase':calls,'actual_events':actual_events,
                  'core_RHS_calls':None if model is None else model.rhs_calls,
                  'scope':'Normal observed entries; inheritance entries are not additional instances. Solver Jacobian RHS are included.'}
        (project / contract['calls_output']).write_text(json.dumps(output,indent=2)+'\n')
    selected_names = {'make_cycle','ThermoelasticFullCycle.__init__','FiniteGasFullCycle.__init__','FullCycle.__init__',
        'ThermoelasticFullCycle.integrate','FiniteGasFullCycle.integrate','ThermoelasticFullCycle.rhs','FiniteGasFullCycle.rhs',
        'ThermoelasticFullCycle.jacobian','FiniteGasFullCycle.jacobian','FiniteGasFullCycle.rates',
        'ThermoelasticFullCycle.summarize','FiniteGasFullCycle.summarize','direct_carbonation_sources',
        'FiniteGasFullCycle.transport','FiniteGasFullCycle.water_transport','ThermoelasticFullCycle.mechanical_rates',
        'ThermoelasticFullCycle.porous_mechanical_rates','initial_partition_from_faces','configured_sampler',
        'FullCycle.heat_transfer_from_conductivity','solve_ivp'}
    def observer(frame,event,value):
        nonlocal summary_depth
        name = frame.f_code.co_qualname
        namespace = frame.f_globals.get('__name__', '')
        if name not in selected_names and not namespace.startswith('sludge_vme.'):
            return
        effective_phase = 'summary' if summary_depth else phase
        if event == 'call':
            calls.setdefault(effective_phase,{})[name] = calls.setdefault(effective_phase,{}).get(name,0)+1
            if name.endswith('.summarize'):
                summary_depth += 1
            if name in ['make_cycle','FiniteGasFullCycle.integrate','solve_ivp']:
                actual_events.append({'entry':name,'utc':datetime.now(timezone.utc).isoformat()});save_counts()
        if event == 'return':
            if name == 'FullCycle.heat_transfer_from_conductivity' and summary_depth:
                native_heat.update({'internal_into_left_cell_W':plain(frame.f_locals['internal']),
                                    'external_into_brick_W':float(frame.f_locals['qext'])})
            if name == 'FiniteGasFullCycle.rates' and summary_depth:
                local = frame.f_locals
                strict.append({'time_s':float(local['t']),'minimum_condensed_mol':float(local['ns'].min()),
                    'minimum_gas_mol':float(value['gas'].min()),
                    'native_faces':{'gas_internal_mol_s':plain(value['gas_flux'][:-1]),
                        'gas_boundary_outward_mol_s':plain(value['gas_flux'][-1]),
                        'gas_energy_internal_W':plain(value['energy_flux'][:-1]),
                        'gas_energy_boundary_outward_W':float(value['energy_flux'][-1]),
                        'water_internal_mol_s':plain(value['water_flux']),
                        'water_energy_internal_W':plain(value['water_energy_flux']),
                        'heat':deepcopy(native_heat),
                        'orientation':'Gas/water toward exterior; native internal heat is gain into leftcell, externalheat into brick. Original same-call values; no extra operator.'},
                    'reaction_entropy_W_K_by_cell_channel':plain(-value['rate']*local['dg']/local['T'][:,None]),
                    'gas_face_entropy_W_K':plain(local['face_entropy']),
                    'water_face_entropy_W_K':plain(value['water_entropy']),
                    'thermal_entropy_W_K':float(local['thermal_entropy']),
                    'mechanical_entropy_W_K':float(local['mechanical_entropy']),
                    'entropy_storage_rate_W_K':float(local['sdot']),
                    'entropy_production_W_K':float(value['production']),
                    'entropy_exchange_W_K':float(value['exchange']),
                    'raw_entropy_rate_identity_residual_W_K':float(value['entropy_identity_residual']),
                    'scope':'Raw saved summary instant; no second constitutive call, no continuous-domain claim'})
            if name.endswith('.summarize'):
                summary_depth -= 1
    sys.setprofile(observer)
    try:
        model = make_cycle(case)
        phase = 'integration'
        report, fields = model.integrate()
    except BaseException as error:
        save_counts()
        (project / contract['result_output']).with_name('failure.json').write_text(json.dumps({'recorded_utc':datetime.now(timezone.utc).isoformat(),
            'exception_type':type(error).__name__,'exception':str(error),'calls':calls,'scope':'Soleattempt consumed; no retry',
            'whole_project_complete':False},indent=2)+'\n')
        raise
    finally:
        sys.setprofile(None)
        save_counts()
    rows = [{key:row[key] for key in contract['saved_row_keys']} for row in fields['rows']]
    native = {key:report[key] for key in contract['summary_report_keys']}
    result = {'schema':'P51_single_actual_saved13cell_short_production_transient_v1','recorded_utc':datetime.now(timezone.utc).isoformat(),
        'identity':contract['identity'],'report':native,'saved_numerical_samples':rows,'strict_saved_instant_observations':strict,
        'geometry':plain(model.initial_partition),'scales':{'b0_m3':plain(model.b0),'md_kg':plain(model.md),
            'chemical_mol':plain(model.cell_chemical_scale),'extent_scale_mol':plain(model.extent_scale),
            'calcium_pool_mol':plain(model.calcium_pool),'energy_scale_J':model.escale,'temperature_reference_K':model.Tr},
        'actual_entries_by_phase':calls,'actual_RHS_including_solver_Jacobian':model.rhs_calls,
        'actual_Jacobian_entries':sum(items.get('ThermoelasticFullCycle.jacobian',items.get('FiniteGasFullCycle.jacobian',0)) for items in calls.values()),
        'actual_make_cycle_instances':sum(items.get('make_cycle',0) for items in calls.values()),
        'physical_ODE_forwards':sum(items.get('solve_ivp',0) for items in calls.values()),
        'CPU_s_including_constructor':(lambda current:current.ru_utime+current.ru_stime-cpu.ru_utime-cpu.ru_stime)(resource.getrusage(resource.RUSAGE_SELF)),
        'elapsed_constructor_integration_summary_report_s':time.monotonic()-start,
        'completed_declared_end':rows[-1]['time_s']==model.times[-1],
        'initial_state_or_physics_overwritten':False,'raw_full_state_fields_saved':False,
        'extra_independent_operators_fit_UQ_or_retry':0,
        'time_grid_8stage_Csampling_comparison_inverse_modelCLI_qualified':False,'whole_project_complete':False,
        'retained_P50_initial_inventory_eligibility':contract['retained_P50']}
    result = plain(result)
    target = project / contract['result_output']
    target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({'result':str(target),'bytes':target.stat().st_size,'RHS':model.rhs_calls,'njev':report['solver']['njev'],
        'constructor_instances':result['actual_make_cycle_instances'],'completed_end':result['completed_declared_end']}),flush=True)


if __name__ == '__main__':
    main()
