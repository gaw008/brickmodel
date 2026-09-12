"""Compare an already locked prediction with the frozen figure extraction."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

FACTS_SHA256 = 'fa6ac791f8cd1c66df5818ace034fdf52269f46647fcba1551004c92502c4018'


def compare(prediction, facts, table_rows):
    if prediction['schema'] != 'nowicki_oxygen_times_result_v1' or prediction['temperature_c'] != 500.:
        raise ValueError('the predeclared 500 C prediction is required')
    predicted = prediction['predictions']
    observed = facts['observations']
    levels = [.1,.2,.3,.4,.5,.6,.7,.8]
    if [r['alpha_plot'] for r in predicted] != levels or [r['alpha_plot'] for r in observed] != levels:
        raise ValueError('the original eight ordered conversion levels are required')
    rows = []
    for p, o in zip(predicted, observed, strict=True):
        lo, hi = o['time_bounds_s']
        actual, center = p['time_s'], o['time_s']
        if not all(math.isfinite(v) for v in (lo,hi,actual,center)) or not 0 <= lo <= center <= hi:
            raise ValueError('invalid original figure reading interval or prediction')
        rows.append(dict(alpha_plot=p['alpha_plot'], predicted_time_s=actual,
            observed_time_s=center, reading_interval_s=[lo,hi], residual_s=actual-center,
            inside_reading_interval=lo <= actual <= hi,
            outside_interval_s=max(lo-actual,actual-hi,0.),
            source_observation=o))
    fitted = [r for r in table_rows if r['gas']=='O2' and r['temperature_C']=='500'
              and r['model']=='shrinking_core' and r['gas_mole_fraction']=='0.1']
    if len(fitted) != 1:
        raise ValueError('one original secondary fitted-constant row required')
    rate = prediction['model']['rate_s_inv']
    published = float(fitted[0]['rate_constant_s_inv'])
    errors = [r['residual_s'] for r in rows]
    return dict(schema='nowicki_oxygen_comparison_v1', status='comparison_completed', points=rows,
        overall=dict(n=8, mae_s=sum(abs(e) for e in errors)/8,
            rmse_s=math.sqrt(sum(e*e for e in errors)/8),
            max_abs_s=max(map(abs,errors)), bias_s=sum(errors)/8,
            inside_reading_intervals=sum(r['inside_reading_interval'] for r in rows)),
        secondary_author_fitted_constant=dict(predicted_s_inv=rate, published_s_inv=published,
            residual_s_inv=rate-published, relative_difference=(rate-published)/published,
            source_row=fitted[0], used_for_prediction=False),
        qualification=dict(new_blind_holdout=False, independent_replicates=False,
            statistical_confidence_interval=False, material_acceptance_threshold=None,
            mass_or_energy_validation=False,
            meaning='fixed source-condition figure-coordinate comparison; reading envelope is not experiment scatter'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prediction', required=True, type=Path)
    parser.add_argument('--prediction-sha256', required=True)
    parser.add_argument('--facts', required=True, type=Path)
    parser.add_argument('--table', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raw = args.prediction.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.prediction_sha256:
        raise ValueError('locked prediction changed')
    prediction = json.loads(raw)
    fact_bytes = args.facts.read_bytes()
    if hashlib.sha256(fact_bytes).hexdigest() != FACTS_SHA256:
        raise ValueError('reviewed extraction changed')
    table_bytes = args.table.read_bytes()
    if hashlib.sha256(table_bytes).hexdigest() != prediction['training']['upstream_table_csv']['sha256']:
        raise ValueError('original table bytes changed')
    table = list(csv.DictReader(table_bytes.decode().splitlines()))
    result = compare(prediction, json.loads(fact_bytes), table)
    result['inputs'] = dict(prediction_sha256=args.prediction_sha256,
        facts_sha256=FACTS_SHA256, table_sha256=hashlib.sha256(table_bytes).hexdigest(),
        comparison_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with args.output.open('x') as stream:
        stream.write(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
