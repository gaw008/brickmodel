"""Fixed-source rate reproduction and an isothermal finite-inventory heat ledger.

The hold is an explicit conditional calorimeter calculation, not a reconstructed
experimental time series. No experimental point or thermal coefficient is fitted.
"""
import argparse
from decimal import Decimal, localcontext
import itertools
import json
import math
from pathlib import Path

from scipy.integrate import quad
from scipy.optimize import linprog

from calcite_affinity_setup import build
from sludge_sandbox.recorded_calcite_steam_plateau import RecordedCalciteSteamPlateau


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    s = json.loads(args.parameters.read_text())
    source = json.loads((root/s['source_file']).read_text())
    thermal_settings = json.loads((root/s['thermal_parameters']).read_text())
    reaction, _, facts = build(root,thermal_settings)
    parameters = s['numerical_review']; budgets = parameters['budgets']
    options = {'epsabs':parameters['quad_epsabs'],'epsrel':parameters['quad_epsrel'],
               'limit':parameters['quad_limit']}
    rate_factor = s['site_density_mol_m2']*s['rate_table_multiplier_m2_s']
    pressure_factor = s['pascal_per_bar']
    phase_facts = {row['id']:row for row in facts['species']}
    molar_mass_co2 = float(phase_facts['carbon_dioxide']['molar_mass_g_mol'])
    molar_mass_cao = float(phase_facts['lime']['molar_mass_g_mol'])
    hold = s['isothermal_open_hold']
    calcium_initial = s['sample_nominal_cao_mass_g']/molar_mass_cao
    carbonate_initial = s['sample_nominal_cao_mass_g']*hold['inventory_g_co2_per_g_cao']/molar_mass_co2
    lime_initial = calcium_initial-carbonate_initial
    carrier_flow = s['source_volumetric_flow_ml_min']/s['seconds_per_minute']/s['source_molar_volume_ml_mol']
    rate_rows=[];comparisons=[];hold_rows=[]
    for table in source['table_rows']:
        model=RecordedCalciteSteamPlateau(table['k2_printed']*rate_factor,
            table['k3_printed']*rate_factor,table['K1_per_bar']/pressure_factor)
        temperature=table['temperature_c']+s['kelvin_offset']
        standard=reaction.standard(temperature)
        phases=standard['phases']; dh=standard['reaction']['enthalpy_j_mol']
        ds=standard['reaction']['entropy_j_mol_k']; rgas=reaction.gas_constant_j_mol_k
        # Independent Cp integral uses source coefficients, not standard().
        dh_independent=0.;ds_independent=0.
        for name,nu in reaction.stoichiometry.items():
            p=reaction.phases[name];a,b,c,d,e=p.coefficients
            cp=lambda t:a+b*t+c/t**2+d/t**.5+e*t*t
            dh_independent+=nu*(p.reference_enthalpy_j_mol+quad(cp,p.reference_temperature_k,temperature,**options)[0])
            ds_independent+=nu*(p.reference_entropy_j_mol_k+quad(lambda t:cp(t)/t,p.reference_temperature_k,temperature,**options)[0])
        for pressure_bar,observed,dx,dy in source['appendix_rows']:
            pressure_pa=pressure_bar*pressure_factor
            rate=model.rate_mol_s(pressure_pa)
            with localcontext() as ctx:
                ctx.prec=parameters['decimal_digits'];D=lambda value:Decimal(str(value))
                z=D(table['K1_per_bar'])*D(pressure_bar)
                direct=D(s['site_density_mol_m2'])*D(s['rate_table_multiplier_m2_s'])*(
                    D(table['k2_printed'])+D(table['k3_printed'])*z)/(1+z)
            rate_error=abs(rate-float(direct))
            rate_rows.append({'temperature_c':table['temperature_c'],'pressure_bar':pressure_bar,
                'rate_mol_s':rate,'decimal_rate_difference_mol_s':rate_error,
                'pressure_derivative_mol_s_pa':model.pressure_derivative_mol_s_pa(pressure_pa),
                'within_numeric_rate_budget':rate_error<=budgets['rate_mol_s']})
            if table['temperature_c']==source['appendix_temperature_c']:
                nominal_at_pressure_bounds=[model.rate_mol_s((pressure_bar+sign*dx)*pressure_factor) for sign in [-1,1]]
                corners=[]
                for sk,s2,s3,sp in itertools.product([-1,1],repeat=4):
                    perturbed=RecordedCalciteSteamPlateau((table['k2_printed']+s2*table['k2_margin'])*rate_factor,
                        (table['k3_printed']+s3*table['k3_margin'])*rate_factor,
                        (table['K1_per_bar']+sk*table['K1_margin'])/pressure_factor)
                    corners.append(perturbed.rate_mol_s((pressure_bar+sp*dx)*pressure_factor))
                comparisons.append({'pressure_bar':pressure_bar,'observed_rate_mol_s':observed,
                    'source_pressure_margin_bar':dx,'source_rate_margin_mol_s':dy,
                    'predicted_rate_mol_s':rate,'central_relative_residual':(rate-observed)/observed,
                    'nominal_rate_bounds_from_pressure':nominal_at_pressure_bounds,
                    'nominal_curve_intersects_observation_rectangle':nominal_at_pressure_bounds[0]<=observed+dy and nominal_at_pressure_bounds[1]>=observed-dy,
                    'parameter_box_rate_bounds':[min(corners),max(corners)],
                    'parameter_box_intersects_observation_rectangle':min(corners)<=observed+dy and max(corners)>=observed-dy,
                    'parameter_box_is_confidence_interval':False})
            duration=hold['duration_s'];extent=rate*duration
            total_out=carrier_flow+rate
            pco2=hold['total_pressure_pa']*rate/total_out
            affinity=reaction.affinity(temperature,pco2)
            outlet_dilution=math.log1p(rate/carrier_flow)
            # Same-temperature Ar/water species have equal in/out molar flows.
            # Their standard H/S cancel; only dilution mixing entropy remains.
            carrier_entropy_rate=rgas*carrier_flow*outlet_dilution
            gas_entropy_out_rate=rate*(phases['carbon_dioxide']['entropy_j_mol_k']-
                rgas*math.log(pco2/reaction.standard_pressure_pa))
            solid_entropy_rate=rate*(phases['lime']['entropy_j_mol_k']-phases['calcite']['entropy_j_mol_k'])
            supplied_heat=extent*dh
            heat_independent=extent*dh_independent
            entropy=duration*(solid_entropy_rate+gas_entropy_out_rate+carrier_entropy_rate)-supplied_heat/temperature
            entropy_by_affinity=duration*(rate*affinity['affinity_j_mol_extent']/temperature+carrier_entropy_rate)
            entropy_by_integrals=duration*(rate*(ds_independent-rgas*math.log(pco2/reaction.standard_pressure_pa))+carrier_entropy_rate)-heat_independent/temperature
            extent_quad=quad(lambda time:model.rate_mol_s(pressure_pa),0,duration,**options)[0]
            initial_h=carbonate_initial*phases['calcite']['enthalpy_j_mol']+lime_initial*phases['lime']['enthalpy_j_mol']
            initial_s=carbonate_initial*phases['calcite']['entropy_j_mol_k']+lime_initial*phases['lime']['entropy_j_mol_k']
            trajectory=[]
            for time in hold['time_points_s']:
                xi=rate*time
                calcite=carbonate_initial-xi;lime=lime_initial+xi
                hs=calcite*phases['calcite']['enthalpy_j_mol']+lime*phases['lime']['enthalpy_j_mol']
                ss=calcite*phases['calcite']['entropy_j_mol_k']+lime*phases['lime']['entropy_j_mol_k']
                trajectory.append({'time_s':time,'extent_mol':xi,'calcite_mol':calcite,'lime_mol':lime,
                    'co2_emitted_mol':xi,'heat_supplied_j':xi*dh,
                    'heat_minus_solid_and_outflow_enthalpy_j':xi*dh-(hs-initial_h+xi*phases['carbon_dioxide']['enthalpy_j_mol']),
                    'entropy_production_j_k':ss-initial_s+time*(gas_entropy_out_rate+carrier_entropy_rate)-xi*dh/temperature,
                    'calcium_residual_mol':calcite+lime-calcium_initial,
                    'carbon_residual_mol':calcite+xi-carbonate_initial,
                    'oxygen_residual_mol':3*calcite+lime+2*xi-(3*carbonate_initial+lime_initial)})
            errors={'extent_mol':abs(extent-extent_quad),
                    'energy_j':max(abs(supplied_heat-heat_independent),*(abs(p['heat_minus_solid_and_outflow_enthalpy_j']) for p in trajectory)),
                    'entropy_j_k':max(abs(entropy-entropy_by_affinity),abs(entropy-entropy_by_integrals))}
            hold_rows.append({'temperature_c':table['temperature_c'],'water_pressure_bar':pressure_bar,
                'rate_mol_s':rate,'extent_mol':extent,'fraction_of_initial_carbonate':extent/carbonate_initial,
                'within_declared_initial_plateau_fraction':extent/carbonate_initial<=hold['maximum_fraction_of_initial_carbonate'],
                'outlet_co2_pressure_pa':pco2,'equilibrium_co2_pressure_pa':affinity['equilibrium_gas_pressure_pa'],
                'forward_affinity_j_mol':affinity['affinity_j_mol_extent'],
                'outlet_water_dilution_fraction':carrier_flow/total_out,
                'source_inlet_flow_approximation_relative_difference':rate/carrier_flow,
                'supplied_heat_j':supplied_heat,'entropy_production_j_k':entropy,
                'numerical_errors':errors,'within_numeric_budgets':all(errors[k]<=budgets[k] for k in errors),
                'trajectory':trajectory})
    # At fixed T write R=(a+b*p)/(1+K*p). All observation and parameter
    # box inequalities are linear in (a,b,K). Monotonicity is ensured here
    # by the printed saturated-rate lower bound exceeding dry-rate upper.
    setting=s['joint_source_box_review'];rs=setting['rate_scale_mol_s'];ps=setting['pressure_scale_bar']
    table=next(row for row in source['table_rows'] if row['temperature_c']==source['appendix_temperature_c'])
    a_bounds=[(table['k2_printed']+sign*table['k2_margin'])*rate_factor/rs for sign in [-1,1]]
    high_bounds=[(table['k3_printed']+sign*table['k3_margin'])*rate_factor/rs for sign in [-1,1]]
    k_bounds=[(table['K1_per_bar']+sign*table['K1_margin'])*ps for sign in [-1,1]]
    A=[];B=[]
    for p,y,dx,dy in source['appendix_rows']:
        lowp=(p-dx)/ps;highp=(p+dx)/ps;lowy=(y-dy)/rs;highy=(y+dy)/rs
        A.extend([[1,lowp,-highy*lowp],[-1,-highp,lowy*highp]])
        B.extend([highy,-lowy])
    A.extend([[0,1,-high_bounds[1]],[0,-1,high_bounds[0]]]);B.extend([0,0])
    search=linprog([0,0,0],A_ub=A,b_ub=B,bounds=[a_bounds,(None,None),k_bounds],
        method=setting['linear_program_method'],options={
        'primal_feasibility_tolerance':setting['primal_feasibility_tolerance'],
        'dual_feasibility_tolerance':setting['dual_feasibility_tolerance']})
    feasibility={'solver_success':bool(search.success),'solver_message':search.message,
                 'data_constrained_parameter_search':True,'used_as_nominal_model':False,
                 'is_independent_validation':False,'is_confidence_region':False}
    if search.success:
        a,b,k=map(float,search.x)
        with localcontext() as ctx:
            ctx.prec=parameters['decimal_digits']
            slacks=[Decimal(str(rhs))-sum(Decimal(str(v))*Decimal(str(x)) for v,x in zip(row,search.x,strict=True))
                    for row,rhs in zip(A,B,strict=True)]
        feasible_model=RecordedCalciteSteamPlateau(a*rs,b/k*rs,k/ps/pressure_factor)
        rectangles=[]
        for p,y,dx,dy in source['appendix_rows']:
            low=feasible_model.rate_mol_s((p-dx)*pressure_factor)
            high=feasible_model.rate_mol_s((p+dx)*pressure_factor)
            rectangles.append({'pressure_bar':p,'predicted_rate_bounds_mol_s':[low,high],
                                'overlap_slack_mol_s':min(y+dy-low,high-(y-dy))})
        feasibility.update({'scaled_solution_a_b_K':[a,b,k],
            'dry_rate_mol_s':a*rs,'saturated_rate_mol_s':b/k*rs,'adsorption_coefficient_per_bar':k/ps,
            'minimum_decimal_scaled_inequality_slack':str(min(slacks)),
            'within_scaled_roundoff_budget':min(slacks)>=-Decimal(str(setting['scaled_inequality_roundoff_budget'])),
            'saturated_lower_exceeds_dry_upper':high_bounds[0]>a_bounds[1],
            'rectangle_slacks':rectangles})
    result={'parameters':s,'source_file':s['source_file'],'rate_reproduction':comparisons,
        'joint_parameter_box_feasibility':feasibility,
        'source_comparison_is_independent_validation':False,
        'rate_arithmetic':rate_rows,'conditional_holds':hold_rows,
        'summary':{'source_observations':len(comparisons),
            'nominal_observation_rectangles_intersected':sum(c['nominal_curve_intersects_observation_rectangle'] for c in comparisons),
            'parameter_box_rectangles_intersected':sum(c['parameter_box_intersects_observation_rectangle'] for c in comparisons),
            'maximum_source_central_relative_residual':max(abs(c['central_relative_residual']) for c in comparisons),
            'all_rate_numeric_budgets':all(c['within_numeric_rate_budget'] for c in rate_rows),
            'all_hold_numeric_budgets':all(c['within_numeric_budgets'] for c in hold_rows),
            'all_hold_forward_affinities_positive':all(c['forward_affinity_j_mol']>0 for c in hold_rows),
            'all_hold_entropy_productions_nonnegative':all(c['entropy_production_j_k']>=0 for c in hold_rows),
            'all_holds_within_declared_initial_plateau_fraction':all(c['within_declared_initial_plateau_fraction'] for c in hold_rows),
            'maximum_carbonate_fraction':max(c['fraction_of_initial_carbonate'] for c in hold_rows),
            'initial_carbonate_mol':carbonate_initial,'initial_lime_mol':lime_initial},
        'scope':'Fixed specimen plateau and conditional same-temperature net-reaction calorimeter; no intrinsic area scaling, inverse reaction or transient intermediate storage.',
        'material_qualified':False,'training_eligible':False}
    out=root/s['output_directory'];out.mkdir(parents=True,exist_ok=True)
    (out/'review.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result['summary']))


if __name__=='__main__':
    main()
