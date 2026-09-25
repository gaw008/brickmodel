"""Compare zero-flow temperature-pressure limits of two explicitly distinct closures."""
import argparse
import json
from pathlib import Path
import mpmath as mp


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();p=json.loads(args.parameters.read_text());mp.mp.dps=p['decimal_precision']
    rows=[]
    for case in p['cases']:
        ratio=mp.mpf(case['right_temperature_k'])/mp.mpf(case['left_temperature_k'])
        # n*T constant follows directly by integrating the stated source zero-flux force.
        source_pressure_ratio=mp.mpf(1)
        kinetic_pressure_ratio=mp.sqrt(ratio)
        error=abs(source_pressure_ratio-kinetic_pressure_ratio)
        rows.append({**case,'source_zero_flux_right_over_left_pressure_decimal':str(source_pressure_ratio),
            'ideal_knudsen_right_over_left_pressure_decimal':str(kinetic_pressure_ratio),
            'absolute_pressure_ratio_difference_decimal':str(error),
            'same_limit_within_budget':bool(error<=mp.mpf(p['pressure_ratio_absolute_budget']))})
    result={'settings':p,'records':rows,'all_limits_match':all(row['same_limit_within_budget'] for row in rows),
        'admitted_as_full_thermalized_knudsen_replacement':False,'production_model_changed':False,
        'material_qualified':False,'training_eligible':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
