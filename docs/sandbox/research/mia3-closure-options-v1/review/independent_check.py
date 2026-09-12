"""Independent source-table arithmetic and bounded CLI evidence; no model imports."""
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/sandbox/research/mia3-closure-options-v1'
SOURCE = ROOT / 'docs/sandbox/research/material-closure-next-v1/AREIAS2025_MIA3_TABLE6.json'
PYTHON = '/private/tmp/brick-water-backend-probe/venv/bin/python'
# Independently read from the supplied original Table 6 image, MIA3 column.
READINGS = {1150: ('1.65', '0.06'), 1160: ('2.05', '0.15'),
            1170: ('3.06', '0.15'), 1180: ('3.61', '0.12')}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def rational(entry: dict[str, str]) -> Fraction:
    return Fraction(entry['exact_fraction'])


def run_cli(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PYTHON, '-I', str(BASE / 'baseline.py'), '--output', str(output)],
                          cwd=HERE, text=True, capture_output=True, check=False, timeout=30)


source = json.loads(SOURCE.read_bytes())
saved = json.loads((BASE / 'BASELINE_RESULT.json').read_bytes())
assert digest(ROOT / source['original_pdf_path']) == source['original_pdf_sha256']
assert digest(Path(source['private_render'])) == source['private_render_sha256']
assert digest(SOURCE) == saved['input_sha256']
assert digest(BASE / 'BASELINE_PREREGISTRATION.md') == saved['preregistration_sha256']
assert digest(BASE / 'baseline.py') == saved['script_sha256']
for temperature, (value, uncertainty) in READINGS.items():
    row, = [r for r in source['observations'] if r['quantity'] == 'linear_shrinkage_percent'
            and int(r['firing_temperature_c']) == temperature]
    assert (row['printed_value'], row['printed_plus_minus']) == (value, uncertainty)
    assert row['statistical_meaning_of_plus_minus'] is None

# Lagrange two-node interpolation/extrapolation independently recomputes the line.
errors = []
comparisons = []
for record in saved['predictions']:
    temperature = record['temperature_c']
    estimate = (Fraction(1170 - temperature, 20) * Fraction(READINGS[1150][0])
                + Fraction(temperature - 1150, 20) * Fraction(READINGS[1170][0]))
    observed = Fraction(READINGS[temperature][0])
    error = estimate - observed
    assert rational(record['observed_shrinkage_percent']) == observed
    assert rational(record['predicted_shrinkage_percent']) == estimate
    assert rational(record['signed_error_percentage_points']) == error
    assert rational(record['absolute_error_percentage_points']) == abs(error)
    assert rational(record['absolute_relative_error_percent']) == 100 * abs(error / observed)
    assert record['source_printed_plus_minus'] == READINGS[temperature][1]
    assert record['plus_minus_statistical_interpretation'] is None
    errors.append(error)
    comparisons.append({'temperature_c': temperature, 'predicted_percent': str(estimate),
                        'signed_error_percentage_points': str(error)})
assert rational(saved['a_percent']) == Fraction(33, 20)
assert rational(saved['b_percentage_points_per_c']) == Fraction(141, 2000)
assert rational(saved['mae_percentage_points']) == sum(abs(e) for e in errors) / 2
mse = sum(e ** 2 for e in errors) / 2
assert rational(saved['mse_squared_percentage_points']) == mse
with localcontext() as context:
    context.prec = 50
    rmse = (Decimal(mse.numerator) / Decimal(mse.denominator)).sqrt()
assert Decimal(saved['rmse_percentage_points_decimal_display']) == rmse

output = HERE / 'rerun_result.json'
first = run_cli(output)
assert first.returncode == 0, first.stderr
rerun = json.loads(output.read_bytes())
assert {k: v for k, v in saved.items() if k != 'executed_at_utc'} == {
    k: v for k, v in rerun.items() if k != 'executed_at_utc'}
before = digest(output)
second = run_cli(output)
assert second.returncode != 0 and 'FileExistsError' in second.stderr
assert digest(output) == before

report = {'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
          'interpreter': sys.version, 'status': 'independent_arithmetic_and_cli_checks_passed',
          'reviewed_hashes': {str(p.relative_to(ROOT)): digest(p) for p in
                             (SOURCE, BASE / 'BASELINE_PREREGISTRATION.md', BASE / 'baseline.py',
                              BASE / 'BASELINE_RESULT.json', BASE / 'REPORT.md')},
          'original_pdf_and_render_hashes_match': True, 'table_shrinkage_values_match': True,
          'comparisons': comparisons, 'rmse_percentage_points': str(rmse),
          'rerun_matches_all_fields_except_execution_time': True,
          'existing_output_refused_and_unchanged': True,
          'first_run': {'returncode': first.returncode, 'stdout': first.stdout, 'stderr': first.stderr},
          'second_run': {'returncode': second.returncode, 'stdout': second.stdout, 'stderr': second.stderr},
          'external_preregistration_timestamp_verified': False,
          'scientific_acceptance_assessed': False, 'full_material_or_free_sintering_approved': False}
with (HERE / 'CHECK_RESULT.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': report['status'], 'comparisons': comparisons}, indent=2))
