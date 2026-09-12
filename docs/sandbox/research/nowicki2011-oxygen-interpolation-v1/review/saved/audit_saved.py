"""One passive audit; standard library only, never import model or comparator."""
import csv
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
RUN = Path('/private/tmp/brick-nowicki-oxygen-v1/installed-execution01')
PHASE = ROOT/'docs/sandbox/research/nowicki2011-oxygen-interpolation-v1'
DATA = ROOT/'data/sandbox/research/nowicki2011-oxygen-interpolation-v1'
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a, b, tolerance=2e-11):
    assert math.isclose(a, b, rel_tol=1e-13, abs_tol=tolerance), (a, b)


def main():
    began = time.perf_counter()
    prediction, comparison = read(RUN/'prediction.json'), read(RUN/'comparison.json')
    lock, execution = read(RUN/'PREDICTION_LOCK.json'), read(RUN/'COMPARISON_EXECUTION.json')
    training, source, facts = (read(DATA/name) for name in ('training.json', 'source_metadata.json', 'facts.json'))
    code_freeze = read(PHASE/'review/code/FREEZE.json')
    compare_freeze = read(PHASE/'review/code/COMPARE_FREEZE.json')
    assert sha(RUN/'prediction.json') == lock['prediction_sha256'] == comparison['inputs']['prediction_sha256'] == '818b5a237d7958360f82730dc15baed0ec3a96092f51b6c9a4ffdc43457419bc'
    assert sha(DATA/'facts.json') == comparison['inputs']['facts_sha256'] == 'fa6ac791f8cd1c66df5818ace034fdf52269f46647fcba1551004c92502c4018'
    assert sha(PHASE/'compare.py') == comparison['inputs']['comparison_script_sha256'] == compare_freeze['compare_sha256']
    for path, digest in code_freeze['source_sha256'].items():
        assert sha(ROOT/path) == digest, path
    assert sha(DATA/'training.json') == prediction['identity']['training_sha256']
    assert sha(DATA/'source_metadata.json') == prediction['identity']['source_metadata_sha256']
    assert sha(ROOT/'src/sludge_sandbox/nowicki_oxidation.py') == prediction['identity']['module_sha256']
    assert prediction['training'] == training and prediction['source'] == source
    assert source['id'] == facts['source']['id'] == training['source_id']
    assert facts['source']['pdf_sha256'] == source['sha256'] == sha(ROOT/source['local_raw_path'])
    assert facts['source']['pdf_bytes'] == (ROOT/source['local_raw_path']).stat().st_size
    assert sha(ROOT/facts['source']['registry_path']) == facts['source']['registry_sha256']
    assert sha(ROOT/facts['method']['script']) == facts['method']['script_sha256']
    assert sha(DATA/facts['method']['selected_vectors_file']) == facts['method']['selected_vectors_sha256']
    assert facts['plot']['figure'] == '2(a)' and facts['plot']['temperature_c'] == 500
    assert facts['plot']['gas_label'] == 'Oxygen 10 vol.% in Ar' and facts['plot']['line_style'] == 'solid'
    for record in (lock, execution):
        assert record['returncode'] == 0 and record['hard_timeout_seconds'] == 10
        assert 0 <= record['elapsed_seconds'] < 10
    command = execution['command']
    assert command[command.index('--prediction-sha256')+1] == lock['prediction_sha256']
    for flag, path in [('--prediction', RUN/'prediction.json'), ('--facts', DATA/'facts.json'),
                       ('--table', ROOT/training['upstream_table_csv']['path']), ('--output', RUN/'comparison.json')]:
        assert command[command.index(flag)+1] == str(path)
    for name in ('stderr.log', 'comparison-stdout.log', 'comparison-stderr.log'):
        assert not (RUN/name).read_bytes()
    mtimes = {name: (RUN/name).stat().st_mtime_ns for name in ('prediction.json', 'PREDICTION_LOCK.json', 'comparison.json', 'COMPARISON_EXECUTION.json')}
    assert mtimes['prediction.json'] <= mtimes['PREDICTION_LOCK.json'] <= mtimes['comparison.json'] <= mtimes['COMPARISON_EXECUTION.json']
    assert prediction['schema'] == 'nowicki_oxygen_times_result_v1' and prediction['temperature_c'] == 500.
    assert prediction['temperature_k'] == 773.15
    levels = [i/10 for i in range(1, 9)]
    assert [r['alpha_plot'] for r in prediction['predictions']] == levels
    assert [r['alpha_plot'] for r in facts['observations']] == levels
    assert [r['alpha_plot'] for r in comparison['points']] == levels
    assert [r['temperature_c'] for r in training['rows']] == ['450', '550']

    # Independent 70-digit line coefficients, rather than the implementation's
    # binary64 weighted interpolation. No 500 C table constant enters here.
    with localcontext() as context:
        context.prec = 70
        low, high = training['rows']
        t0, t1 = Decimal(low['temperature_k']), Decimal(high['temperature_k'])
        k0, k1 = Decimal(low['ks_s_inv']), Decimal(high['ks_s_inv'])
        t = Decimal('773.15')
        slope = (k1.ln()-k0.ln())/(1/t1-1/t0)
        intercept = k0.ln()-slope/t0
        rate = (intercept+slope/t).exp()
        weight = (1/t-1/t0)/(1/t1-1/t0)
        high_precision_times, high_precision_rates, high_precision_phi = [], [], []
        for number in range(1, 9):
            alpha = Decimal(number)/10
            cube = 1-alpha
            root = Decimal(1)
            for _ in range(40):
                root = (2*root+cube/(root*root))/3
            phi = 1-root
            high_precision_phi.append(phi)
            high_precision_times.append(phi/rate)
            high_precision_rates.append(3*rate*root*root)
    close(float(rate), prediction['model']['rate_s_inv'], 1e-17)
    close(float(weight), prediction['model']['inverse_temperature_weight'], 1e-14)
    rows = []
    errors, precision_errors = [], []
    x_ticks, y_ticks = facts['calibration']['x_ticks'], facts['calibration']['y_ticks']
    x0, x1 = x_ticks[0]['x_pt'], x_ticks[-1]['x_pt']
    y0, y1 = y_ticks[0]['y_pt'], y_ticks[-1]['y_pt']
    for i, (p, observation, recorded) in enumerate(zip(prediction['predictions'], facts['observations'], comparison['points'], strict=True)):
        assert recorded['source_observation'] == observation
        assert recorded['reading_interval_s'] == observation['time_bounds_s']
        close(recorded['predicted_time_s'], p['time_s'])
        assert recorded['observed_time_s'] == observation['time_s']
        numerical_error = abs(Decimal(str(p['time_s']))-high_precision_times[i])
        assert numerical_error < Decimal('1e-6')
        precision_errors.append(float(numerical_error))
        close(float(high_precision_phi[i]), p['phi'])
        close(float(high_precision_rates[i]), p['coordinate_rate_s_inv'], 1e-16)
        lo, hi = observation['time_bounds_s']
        raw_lo, raw_hi = observation['time_bounds_unrounded_s']
        assert lo == math.floor(raw_lo) and hi == math.ceil(raw_hi)
        assert observation['time_s'] == round(observation['time_from_vector_centerline_s'])
        x, y = observation['pdf_page_top_left_pt']
        close((x-x0)*18000/(x1-x0), observation['time_from_vector_centerline_s'], 1e-8)
        close((y0-y)/(y0-y1), p['alpha_plot'], 1e-12)
        residual = p['time_s']-observation['time_s']
        inside = lo <= p['time_s'] <= hi
        outside = max(lo-p['time_s'], p['time_s']-hi, 0.)
        close(residual, recorded['residual_s'])
        assert inside == recorded['inside_reading_interval']
        close(outside, recorded['outside_interval_s'])
        errors.append(residual)
        rows.append(dict(alpha_plot=p['alpha_plot'], predicted_time_s=p['time_s'],
            decimal_reference_time_s=str(high_precision_times[i]), observed_time_s=observation['time_s'],
            reading_interval_s=[lo, hi], residual_s=residual, inside_reading_interval=inside,
            outside_interval_s=outside, numerical_difference_s=float(numerical_error)))
    overall = dict(n=8, mae_s=math.fsum(map(abs, errors))/8,
        rmse_s=math.sqrt(math.fsum(e*e for e in errors)/8), max_abs_s=max(map(abs, errors)),
        bias_s=math.fsum(errors)/8, inside_reading_intervals=sum(r['inside_reading_interval'] for r in rows))
    for key, value in overall.items():
        close(value, comparison['overall'][key])
    assert all(e < 0 for e in errors) and overall['inside_reading_intervals'] == 3

    # Read the secondary author fit only after finishing the independent model
    # calculation and the primary observed-time comparisons above.
    table_path = ROOT/training['upstream_table_csv']['path']
    assert sha(table_path) == training['upstream_table_csv']['sha256'] == comparison['inputs']['table_sha256']
    with table_path.open(newline='') as stream:
        table_rows = list(csv.DictReader(stream))
    secondary_rows = [r for r in table_rows if r['temperature_C'] == '500' and r['gas'] == 'O2'
                      and r['gas_mole_fraction'] == '0.1' and r['model'] == 'shrinking_core']
    assert len(secondary_rows) == 1
    published = Decimal(secondary_rows[0]['rate_constant_s_inv'])
    secondary = comparison['secondary_author_fitted_constant']
    assert secondary['source_row'] == secondary_rows[0] and secondary['used_for_prediction'] is False
    close(secondary['predicted_s_inv'], float(rate), 1e-17)
    close(secondary['published_s_inv'], float(published), 1e-17)
    relative = (prediction['model']['rate_s_inv']-float(published))/float(published)
    close(secondary['relative_difference'], relative)
    close(secondary['residual_s_inv'], prediction['model']['rate_s_inv']-float(published), 1e-17)
    assert comparison['status'] == 'comparison_completed'
    qualification = comparison['qualification']
    assert qualification['material_acceptance_threshold'] is None
    assert not any(qualification[k] for k in ['new_blind_holdout', 'independent_replicates', 'statistical_confidence_interval', 'mass_or_energy_validation'])
    assert not prediction['qualification']['experimental_validation_performed']
    assert not prediction['qualification']['full_material_package']
    assert prediction['qualification']['reaction_heat'] is None
    assert prediction['qualification']['oxygen_consumption'] is None
    assert 'Eq1' in prediction['qualification']['response']
    result = dict(verdict='saved_locked_prediction_and_comparison_verified_no_material_pass',
        decimal_rate_s_inv=str(rate), saved_rate_s_inv=prediction['model']['rate_s_inv'],
        max_independent_time_difference_s=max(precision_errors), points=rows, overall=overall,
        secondary_relative_difference=relative, all_center_residuals_negative=True,
        prediction_execution=lock, comparison_execution=execution, observed_local_mtime_ns=mtimes,
        source_sha256={str(path.relative_to(ROOT)):sha(path) for path in [DATA/'facts.json', DATA/'training.json', DATA/'source_metadata.json', table_path, PHASE/'compare.py', ROOT/source['local_raw_path'], ROOT/facts['source']['registry_path'], ROOT/facts['method']['script'], DATA/facts['method']['selected_vectors_file']]},
        original_saved_sha256={str(p.relative_to(RUN)):sha(p) for p in sorted(RUN.iterdir()) if p.is_file()},
        audit_seconds=time.perf_counter()-began,
        limitations=['No CLI, comparator, optimizer, solver, or PDF extractor was run or imported.',
                     'Geometry-to-number mapping and saved source identities were checked; curve selection and full reading-envelope construction rely on the separate source audit.',
                     'Local modification times and execution records are consistent with locking before comparison; they are not external timestamp attestation or independent wall-clock measurement.',
                     'Three of eight within a declared reading envelope is a descriptive result, not an acceptance percentage or experiment uncertainty model.'])
    (HERE/'AUDIT.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['points', 'source_sha256', 'original_saved_sha256', 'prediction_execution', 'comparison_execution']}, indent=2))


if __name__ == '__main__':
    main()
