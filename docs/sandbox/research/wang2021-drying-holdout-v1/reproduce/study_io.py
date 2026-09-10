"""Explicit data split, immutable file binding and descriptive errors."""
from pathlib import Path
import csv
import hashlib
import json
import math
import platform
import scipy
import mpmath
import numpy
from wang_d1 import NUMERICAL_ALLOWANCE


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.partial')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def binding(csv_path, prereg):
    local = Path(__file__).resolve().parent
    files = [Path(csv_path).resolve(), Path(prereg).resolve()]
    files += [local/n for n in ('wang_d1.py','study_io.py','train.py','holdout.py','independent_check.py')]
    return {'files': {str(p):sha(p) for p in files}, 'python':platform.python_version(),
            'numpy':numpy.__version__, 'scipy':scipy.__version__, 'mpmath':mpmath.__version__}


def check_binding(record):
    for path, digest in record['files'].items():
        if sha(path) != digest:
            raise ValueError('frozen input or implementation changed: '+path)
    if (platform.python_version(), numpy.__version__, scipy.__version__, mpmath.__version__) != (record['python'],record['numpy'],record['scipy'],record['mpmath']):
        raise ValueError('numeric runtime changed')


def load_curves(path, temperatures):
    """Filter temperature field before parsing MR or other value columns.

    Wang's existing CSV has no embedded newlines/quoted temperature columns.
    Unselected raw lines are discarded; their MR fields are never parsed.
    Whole-file hashing is opaque integrity work, not observation inspection.
    """
    curves = {}
    with Path(path).open(newline='') as stream:
        header = next(csv.reader([next(stream)]))
        temperature_index = header.index('temperature_C')
        for line in stream:
            temperature = int(line.split(',',temperature_index+1)[temperature_index])
            if temperature not in temperatures:
                continue
            row = dict(zip(header,next(csv.reader([line])),strict=True))
            t = float(row['time_min']); rh = int(row['relative_humidity_percent'])
            if not math.isfinite(t) or t < 0 or rh not in (30,40,50,60):
                raise ValueError('invalid selected observation metadata')
            if t == 0:
                continue
            y, e = float(row['moisture_ratio']), float(row['readout_bound_MR'])
            if not all(map(math.isfinite,(y,e))) or e < 0:
                raise ValueError('invalid selected observation value')
            curves.setdefault((temperature,rh),[]).append(dict(row, time_s=t*60, observed=y, readout_bound=e))
    expected={(t,h) for t in temperatures for h in (30,40,50,60)}
    if set(curves) != expected:
        raise ValueError('complete selected curves required')
    for rows in curves.values():
        times=[r['time_s'] for r in rows]
        if times != sorted(set(times)):
            raise ValueError('unique increasing selected time samples required')
    return curves


def metrics(curves, predict):
    rows=[]; conditions=[]
    for (t,h), obs in sorted(curves.items()):
        predicted, diagnostic = predict(t,h/100,[x['time_s'] for x in obs])
        residual=[]
        for item, y in zip(obs,predicted,strict=True):
            error=float(y)-item['observed']; residual.append(error)
            rows.append(dict(item, temperature_C=t, relative_humidity_percent=h,
                prediction=float(y), residual=error,
                outside_readout_bound=max(0.,abs(error)-item['readout_bound']),
                outside_readout_plus_numeric=max(0.,abs(error)-item['readout_bound']-NUMERICAL_ALLOWANCE)))
        conditions.append({'temperature_C':t,'rh_percent':h,'n':len(obs),
            'rmse':math.sqrt(sum(x*x for x in residual)/len(obs)),
            'mae':sum(abs(x) for x in residual)/len(obs),'max_abs':max(map(abs,residual)),
            'bias':sum(residual)/len(obs),'modes':diagnostic['modes'],'tail_bound':diagnostic['tail_bound'],'log_tail_bound':diagnostic['log_tail_bound'],'tail_underflow':diagnostic['tail_underflow'],'independent_max_abs_delta':diagnostic.get('independent_max_abs_delta')})
    residual=[x['residual'] for x in rows]
    return {'points':rows,'conditions':conditions,'overall':{
        'n':len(rows),'rmse':math.sqrt(sum(x*x for x in residual)/len(rows)),
        'mae':sum(map(abs,residual))/len(rows),'max_abs':max(map(abs,residual)),
        'bias':sum(residual)/len(rows),
        'all_points_within_readout_plus_numeric':all(x['outside_readout_plus_numeric']==0 for x in rows)},
        'qualification':'digitized center comparison; readout bound is not experimental confidence; effective model only'}
