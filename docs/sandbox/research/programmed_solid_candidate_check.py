"""Run actual programmed solid/fluid heat against a separate Decimal oracle."""
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests/sandbox'))
from test_solid_fluid_heat import solid_host
from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.integration import IntegrationPolicy, integrate
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.water_properties import load_water_properties
from programmed_solid_analytic_reference import reference


def main():
    data=ROOT/'data/sandbox/water'
    base=solid_host((load_water_properties(data),IdealWaterVapor(data),WaterChemicalPotential(data)))
    base=replace(base,transport=replace(base.transport,conductivities_w_m_k=(10.,),
        inverse_policy=InversePolicy(1e-6,1e-6,100)))
    program=BoundaryProgram(identity=ProgramIdentity(program_id='manufactured:ramp-reference',version='1',
        classification='virtual_design_choice',source_ids=('manufactured:ramp-reference',)),
        knot_times_s=(0.,10.,20.,40.),gas_temperature_k=(300.,305.,305.,295.),
        radiation_temperature_k=(300.,)*4,total_pressure_pa=(3e5,)*4,
        species_order=base.gas_species_order,mole_fractions=((1.,0.),)*4)
    model=ProgrammedSolidFluidHeat(base_model=base,program=program,convection_w_m2_k=100000.,emissivity=0.,
        stefan_boltzmann_w_m2_k4=5.670374419e-8,coefficient_set_id='manufactured:film',coefficient_version='1',
        coefficient_classification='manufactured',coefficient_source_ids=('manufactured:film',),allow_manufactured=True,
        surface_policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=200))
    initial=base.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    runs=[]
    for dt in (.5,.25,.125):
        surface_limits=[]
        surface_residuals=[]
        def operator(state,time_s):
            evaluation=model.evaluate(state,time_s)
            surface_limits.append(evaluation.surface_balance_limit_w)
            surface_residuals.append(abs(evaluation.surface_balance_residual_w))
            return evaluation.rates
        result=integrate(initial,operator,start_s=0,end_s=40,breakpoints_s=model.breakpoints_s(0,40),
            policy=IntegrationPolicy(initial_step_s=dt,maximum_step_s=dt,minimum_step_s=1e-10,
                relative_tolerance=1e-3,amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1.,
                amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=2000,maximum_rejections=20,
                maximum_wall_seconds=120))
        traces=[]
        for time,state in zip(result.times_s,result.states):
            inv=base.decode_inverse(state)[0]
            truth=reference(time)
            traces.append(dict(time_s=time,temperature_k=inv.state.mechanical.temperature_k,
                reference_temperature_k=float(truth['temperature_k']),temperature_bound_k=inv.temperature_error_bound_k,
                energy_change_j=float(state.internal_energy_j[0]-initial.internal_energy_j[0]),
                reference_energy_change_j=float(truth['net_heat_j'])))
        ledger=[float(step.face_energy_j[-1]) for step in result.steps]
        step_errors=[float(b.internal_energy_j[0]-a.internal_energy_j[0]+q)
            for a,b,q in zip(result.states,result.states[1:],ledger)]
        prefix_errors=[row['energy_change_j']+math.fsum(ledger[:i]) for i,row in enumerate(traces)]
        maxerror=max(abs(row['temperature_k']-row['reference_temperature_k']) for row in traces)
        steps=np.diff(result.times_s)
        # Floating endpoint differences near knots are allowed only at representation scale.
        uniform=all(abs(float(step)-dt)<=1e-10 for step in steps)
        inventory_equal=all(np.array_equal(state.amounts_mol,initial.amounts_mol) for state in result.states)
        nodes=all(t in result.times_s for t in (0.,10.,20.,40.))
        phase_temperatures={t:row['temperature_k'] for t,row in zip(result.times_s,traces) if t in (0.,10.,20.,40.)}
        shape=(nodes and phase_temperatures[0.]<phase_temperatures[10.]<phase_temperatures[20.]
            and phase_temperatures[40.]<phase_temperatures[0.])
        surface_bound=40*max(surface_limits)/float(reference(0)['capacity_j_k'])
        runs.append(dict(max_surface_limit_w=max(surface_limits),max_surface_residual_w=max(surface_residuals),
            accumulated_surface_temperature_bound_k=surface_bound,dt_s=dt,status=result.status,reason=result.reason,elapsed_seconds=result.elapsed_seconds,
            evaluations=result.evaluations,rejected_trials=result.rejected_trials,uniform_steps=uniform,
            inventory_equal=inventory_equal,nodes_exact=nodes,ramp_hold_cooling=shape,
            max_temperature_error_k=maxerror,max_inverse_bound_k=max(row['temperature_bound_k'] for row in traces),
            max_step_energy_error_j=max(map(abs,step_errors),default=0.),
            max_prefix_energy_error_j=max(map(abs,prefix_errors)),traces=traces,face_energy_j=ledger))
    ratios=[a['max_temperature_error_k']/b['max_temperature_error_k'] if b['max_temperature_error_k']>0 else None
        for a,b in zip(runs,runs[1:])]
    passed=(all(r['status']=='completed' and r['uniform_steps'] and r['inventory_equal']
        and r['nodes_exact'] and r['ramp_hold_cooling'] and r['rejected_trials']==0
        and r['max_step_energy_error_j']<=1e-7 and r['max_prefix_energy_error_j']<=1e-6 for r in runs)
        and runs[-1]['max_temperature_error_k']<=1e-3 and all(r is not None and r>=2.8 for r in ratios)
        and all(max(r['max_inverse_bound_k'],r['accumulated_surface_temperature_bound_k'])
            <.1*r['max_temperature_error_k'] for r in runs))
    paths=[Path(__file__),Path(__file__).with_name('programmed_solid_analytic_reference.py'),
           ROOT/'src/sludge_sandbox/programmed_solid_fluid_heat.py',ROOT/'src/sludge_sandbox/solid_fluid_heat.py',
           ROOT/'src/sludge_sandbox/solid_fluid_storage.py',ROOT/'src/sludge_sandbox/integration.py',
           ROOT/'tests/sandbox/test_solid_fluid_heat.py',ROOT/'tests/sandbox/test_water_phase_transfer.py',
           ROOT/'tests/sandbox/test_rigid_storage.py',ROOT/'tests/sandbox/test_incompressible_solid.py']
    output=dict(classification='manufactured_test_fixture',passed=passed,refinement_ratios=ratios,runs=runs,
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    Path(__file__).with_suffix('.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(passed=passed,ratios=ratios,runs=[{k:v for k,v in r.items() if k not in ('traces','face_energy_j')} for r in runs]),indent=2))
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
