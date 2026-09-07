from pathlib import Path
p=Path('/private/tmp/brick-heos-stage3/heos_candidate.py')
s=p.read_text().replace('from dataclasses import dataclass','from contextlib import contextmanager\nfrom dataclasses import dataclass')
s=s.replace('import math\n','import math\nimport warnings\n')
s=s.replace('    def __init__(self, manifest, water_sources):','''    def __setattr__(self, name, value):
        if getattr(self, '_sealed', False):
            raise AttributeError('immutable_HEOS_candidate')
        object.__setattr__(self, name, value)

    @property
    def last_coexistence(self):
        with self._lock:
            return json.loads(json.dumps(self._coexistence))

    def __init__(self, manifest, water_sources):''')
s=s.replace("        base = Path(CoolProp.__file__).resolve().parent", """        base = Path(CoolProp.__file__).resolve().parent
        if Path(CP.__file__).resolve() != base / 'CoolProp.abi3.so':
            raise WaterSourceError('heos_loaded_extension_path_mismatch')
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != expected['adapter_sha256']:
            raise WaterSourceError('heos_adapter_source_changed')
        if json.loads(CP.get_config_as_json_string()) != expected['config']:
            raise WaterSourceError('heos_config_changed')
        self._config = json.dumps(expected['config'], sort_keys=True)
        self._fluid_digest = expected['fluid_canonical_sha256']
        self._coexistence = []""")
s=s.replace("        for name, sha in expected['files'].items():", """        current_files={str(x.relative_to(base)) for x in base.rglob('*') if x.is_file() and x.suffix in ('.py','.so')}
        if current_files != set(expected['files']):
            raise WaterSourceError('heos_runtime_file_set_changed')
        for name, sha in expected['files'].items():""")
s=s.replace("            require(abs(anchor - old) <= .002, 'heos_ideal_reference_anchor_mismatch')", """            require(abs(anchor - old) <= .002, 'heos_ideal_reference_anchor_mismatch')
            native_phi = original._model._phi0(647.096/t, 1e-8/322.)
            self._entropy_anchor = self._r * (647.096/t*native_phi['fiot']-native_phi['fio'])
            entropy = self._r * (647.096/t*c.dalpha0_dTau()-c.alpha0())
            require(abs(entropy-self._entropy_anchor)*t <= .002, 'heos_ideal_entropy_anchor_mismatch')""")
s=s.replace("        self.identity = hashlib.sha256(self.descriptor_json.encode()).hexdigest()", """        self.identity = hashlib.sha256(self.descriptor_json.encode()).hexdigest()
        self._sealed = True

    @contextmanager
    def _transaction(self):
        with self._lock:
            if json.dumps(json.loads(self._cp.get_config_as_json_string()),sort_keys=True) != self._config:
                raise WaterSourceError('heos_runtime_config_changed')
            if digest(json.loads(self._cp.get_fluid_param_string('Water','JSON'))) != self._fluid_digest:
                raise WaterSourceError('heos_runtime_fluid_changed')
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter('always')
                yield
            if emitted:
                raise WaterNumericalError('heos_native_warning:'+str(emitted[0].message))
            if json.dumps(json.loads(self._cp.get_config_as_json_string()),sort_keys=True) != self._config:
                raise WaterSourceError('heos_runtime_config_changed')""")
s=s.replace('                self.last_coexistence=[]','                self._coexistence.clear()').replace('self.last_coexistence.append(', 'self._coexistence.append(')
# Only public numerical transactions, not diagnostic getter/context-manager internals.
s=s.replace('        with self._lock:\n            try:\n                # QT', '        with self._transaction():\n            try:\n                # QT')
s=s.replace('        with self._lock:\n            liquid,vapor=', '        with self._transaction():\n            liquid,vapor=')
p.write_text(s)
