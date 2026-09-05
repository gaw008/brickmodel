"""Strict immutable inputs for the synthetic B2 concentration-inventory model."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
VERSION = 'B2-1.0.1'
SCOPE = 'synthetic_prescribed_temperature_equimolar'


def canonical(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')


def strict_json(text, *, size_limit=65536, depth_limit=8):
    if len(text.encode('utf-8')) > size_limit:
        raise ValueError('input_size')
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d: raise ValueError('duplicate_key')
            d[k] = v
        return d
    def invalid(_): raise ValueError('nonfinite')
    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('json_syntax') from None
    def check(x, depth):
        if depth > depth_limit: raise ValueError('input_depth')
        if isinstance(x, float) and not math.isfinite(x): raise ValueError('nonfinite')
        if isinstance(x, dict):
            for v in x.values(): check(v, depth+1)
        elif isinstance(x, list):
            for v in x: check(v, depth+1)
    check(data, 0)
    return data


def keys(d, expected):
    if type(d) is not dict or set(d) != set(expected.split()): raise ValueError('schema_fields')


def number(x, lo, hi):
    if type(x) not in (int, float) or not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError('numeric_domain')


def validate(d):
    keys(d, 'schema_version scope scenario_id provenance base_context_id mapping_status temperature reaction transport geometry boundary initial numerics diagnostic_thresholds')
    for k, v in {'schema_version': VERSION, 'scope': SCOPE, 'provenance':'synthetic_assumption',
                 'base_context_id':'synthetic_fixed_matrix_v1','mapping_status':'unknown_real_material'}.items():
        if d[k] != v: raise ValueError('unsupported_scope')
    if type(d['scenario_id']) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',d['scenario_id']): raise ValueError('identifier')
    schemas = {'temperature':'T_ref_K interpolation knots','reaction':'K_ref theta Gamma',
               'transport':'d_ref m Bi_ref','geometry':'kind length_ratio porosity_mode',
               'boundary':'mode reservoir_ratio','initial':'u v f',
               'numerics':'n_cells tau_end sample_dtau max_dtau dt_scale'}
    for k, schema in schemas.items(): keys(d[k],schema)
    for group, domains in {'reaction':{'K_ref':(0,10),'theta':(0,6),'Gamma':(.25,8)},
                           'transport':{'d_ref':(.5,2),'m':(0,1),'Bi_ref':(0,10)},
                           'geometry':{'length_ratio':(1,2)},
                           'numerics':{'n_cells':(7,31),'tau_end':(0,20),'sample_dtau':(.1,.1),'max_dtau':(0,.02),'dt_scale':(.25,1)},
                           'initial':{'u':(1,1),'v':(0,0),'f':(1,1)},
                           'temperature':{'T_ref_K':(600,600)}}.items():
        for k, (lo,hi) in domains.items(): number(d[group][k],lo,hi)
    t,r,tr,g,b,n = (d[k] for k in ('temperature','reaction','transport','geometry','boundary','numerics'))
    if type(n['n_cells']) is not int or n['n_cells'] not in (7,15,31) or n['dt_scale'] not in (1,.5,.25): raise ValueError('numerics')
    if n['tau_end'] <= 0 or n['max_dtau'] <= 0 or tr['m'] not in (0,1): raise ValueError('numeric_domain')
    if g['kind'] != 'symmetric_half_slab' or g['porosity_mode'] != 'fixed': raise ValueError('geometry')
    if b['mode'] not in ('infinite','finite','sealed'): raise ValueError('boundary')
    if b['mode'] == 'finite': number(b['reservoir_ratio'],.25,10)
    elif b['reservoir_ratio'] is not None: raise ValueError('reservoir')
    if b['mode'] == 'sealed':
        if tr['Bi_ref'] != 0: raise ValueError('sealed_film')
    elif tr['Bi_ref'] < .1: raise ValueError('film')
    if t['interpolation'] != 'piecewise_linear' or type(t['knots']) is not list or not 2 <= len(t['knots']) <= 8: raise ValueError('temperature')
    last = -1
    for k in t['knots']:
        keys(k,'tau T_K'); number(k['tau'],0,n['tau_end']); number(k['T_K'],450,750)
        if k['tau'] <= last: raise ValueError('temperature_knots')
        last = k['tau']
        kt = r['K_ref']*math.exp(r['theta']*(1-600/k['T_K']))
        dt = tr['d_ref']*(k['T_K']/600)**tr['m']
        if kt > 20 or not 0 < dt <= 4: raise ValueError('coefficient_domain')
    if t['knots'][0]['tau'] != 0 or last != n['tau_end']: raise ValueError('temperature_endpoints')
    if type(d['diagnostic_thresholds']) is not list or d['diagnostic_thresholds'] != [.95,.99]: raise ValueError('thresholds')


@dataclass(frozen=True)
class Scenario:
    _content: bytes

    @classmethod
    def from_dict(cls, data):
        # Canonical roundtrip rejects non-JSON and retains numeric types.
        clean = strict_json(canonical(data).decode())
        validate(clean)
        return cls(canonical(clean))

    def to_dict(self): return json.loads(self._content)
    def canonical(self): return self._content
    @property
    def id(self): return self.to_dict()['scenario_id']


def load_scenario(path):
    from paths import safe_file
    return Scenario.from_dict(strict_json(safe_file(path).read_text(encoding='utf-8')))
