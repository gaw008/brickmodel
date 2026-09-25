"""Independent source differences and Gibbs/Maxwell identities at fixed T/P."""
import argparse
import json
from pathlib import Path

from mpmath import mp

from carbon_calcium_pressure_setup import build
from carbon_calcium_pressure_decimal_reference import reconstruct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    policy = json.loads((root/settings['model_parameters']).read_text())
    model,_,_ = build(root,policy)
    mp.dps = settings['decimal_digits']
    budget, records = settings['budgets'], []
    for inventory in policy['inventories']:
        inputs = [inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        for pressure in settings['pressure_points_pa']:
            for temperature in settings['temperature_points_k']:
                candidate = model.at_temperature_pressure(temperature,pressure,*inputs)
                phases = (candidate['calcium_phase'],candidate['carbon_phase'])
                for step_pair in settings['difference_steps']:
                    t,p = mp.mpf(temperature),mp.mpf(pressure)
                    dt,dp = mp.mpf(step_pair['temperature_k']),p*mp.mpf(step_pair['pressure_fraction'])
                    neighbors = []
                    states = []
                    for tt,pp in [(t-dt,p),(t+dt,p),(t,p-dp),(t,p+dp)]:
                        runtime = model.at_temperature_pressure(float(tt),float(pp),*inputs)
                        neighbors.append((runtime['calcium_phase'],runtime['carbon_phase']))
                        states.append(reconstruct(model,tt,pp,inventory,runtime,settings))
                    tm,tp,pm,pp = states
                    dhdt = (tp['enthalpy']-tm['enthalpy'])/(2*dt)
                    dsdt = (tp['entropy']-tm['entropy'])/(2*dt)
                    dvdt = (tp['volume']-tm['volume'])/(2*dt)
                    dgdt = (tp['gibbs']-tm['gibbs'])/(2*dt)
                    dvdp = (pp['volume']-pm['volume'])/(2*dp)
                    dhdp = (pp['enthalpy']-pm['enthalpy'])/(2*dp)
                    dsdp = (pp['entropy']-pm['entropy'])/(2*dp)
                    dgdp = (pp['gibbs']-pm['gibbs'])/(2*dp)
                    amount_t = max(abs(mp.mpf(candidate['amount_temperature_derivatives_mol_k'][name])
                        -(tp['amounts'][name]-tm['amounts'][name])/(2*dt)) for name in candidate['amounts_mol'])
                    amount_p = max(abs(mp.mpf(candidate['amount_pressure_derivatives_mol_pa'][name])
                        -(pp['amounts'][name]-pm['amounts'][name])/(2*dp)) for name in candidate['amounts_mol'])
                    # This reference uses independently recomposed source finite
                    # differences, not the runtime reaction-basis derivative.
                    cv = dhdt + t*dvdt*dvdt/dvdp
                    errors = {
                        'enthalpy_temperature_j_k':abs(mp.mpf(candidate['equilibrium_cp_j_k'])-dhdt),
                        'entropy_temperature_j_k':abs(mp.mpf(candidate['equilibrium_cp_j_k'])-t*dsdt),
                        'volume_temperature_m3_k':abs(mp.mpf(candidate['volume_temperature_derivative_m3_k'])-dvdt),
                        'volume_pressure_m3_pa':abs(mp.mpf(candidate['volume_pressure_derivative_m3_pa'])-dvdp),
                        'enthalpy_pressure_m3':abs(dhdp-(mp.mpf(candidate['total_volume_m3'])-t*mp.mpf(candidate['volume_temperature_derivative_m3_k']))),
                        'entropy_pressure_m3_k':abs(dsdp+mp.mpf(candidate['volume_temperature_derivative_m3_k'])),
                        'gibbs_temperature_j_k':abs(dgdt+mp.mpf(candidate['entropy_j_k'])),
                        'gibbs_pressure_m3':abs(dgdp-mp.mpf(candidate['total_volume_m3'])),
                        'amount_temperature_mol_k':amount_t,'amount_pressure_mol_pa':amount_p,
                        'cv_identity_j_k':abs(mp.mpf(candidate['equilibrium_cv_j_k'])-cv)}
                    flags = {key:bool(value <= budget[key]) for key,value in errors.items()}
                    flags['same_phase'] = all(pair==phases for pair in neighbors)
                    flags['positive_cv'] = bool(cv>0)
                    flags['negative_volume_pressure'] = bool(dvdp<0)
                    records.append({'inventory':inventory['name'],'temperature_k':temperature,'pressure_pa':pressure,
                        'phases':phases,'difference_steps':step_pair,'errors':{k:float(v) for k,v in errors.items()},
                        'reference_cv_j_k':str(cv),'reference_volume_pressure_m3_pa':str(dvdp),'within_budgets':flags})
                print(json.dumps({'inventory':inventory['name'],'temperature_k':temperature,'pressure_pa':pressure,
                                  'last_within_budgets':all(records[-1]['within_budgets'].values())}),flush=True)
    result = {'settings':settings,'records':records,
        'all_requested_derivative_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__':main()
