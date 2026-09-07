from pathlib import Path
import ast
p=Path('/private/tmp/brick-heos-stage5/sludge_sandbox')
f=p/'water_implementation.py';s=f.read_text().replace("if not self.provider_id or not self.provider_version or not self.source_ids or type(self.source_ids) is not tuple:","if (type(self.provider_id) is not str or not self.provider_id or type(self.provider_version) is not str or not self.provider_version\n            or type(self.source_ids) is not tuple or not self.source_ids\n            or any(type(x) is not str or not x or x!=x.strip() for x in self.source_ids)\n            or len(set(self.source_ids))!=len(self.source_ids)):")
s=s.replace("    @property\n    def sha256(self):\n        return hashlib.sha256(self.canonical_descriptor.encode()).hexdigest()", """    @property
    def canonical_json(self):
        return json.dumps({'schema':self.schema,'provider_id':self.provider_id,
            'provider_version':self.provider_version,'source_ids':self.source_ids,
            'definition':json.loads(self.canonical_descriptor)},sort_keys=True,separators=(',',':'))

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_json.encode()).hexdigest()""")
f.write_text(s)
f=p/'water_heos.py';s=f.read_text().replace('import hashlib,json,math','import hashlib,json,sys,importlib.metadata')
s=s.replace("'public_state_schema':", "'ideal_adapter_sha256':hashlib.sha256(Path(__file__).with_name('water_properties.py').read_bytes()).hexdigest(),\n            'descriptor_code_sha256':hashlib.sha256(Path(__file__).with_name('water_implementation.py').read_bytes()).hexdigest(),\n            'hybrid_runtime':{'python':sys.version,'packages':{name:importlib.metadata.version(name) for name in ('iapws','numpy','scipy')}},\n            'public_state_schema':")
s=s.replace("or self.source_asset_sha256.get('water_implementation_v1.json')!=self.implementation.sha256", "or dict(self.source_asset_sha256)!=(dict(self._ideal.source_asset_sha256)|{'water_implementation_v1.json':self.implementation.sha256})")
f.write_text(s)
for name in ('phase_storage.py','rigid_water_gas.py','water_chemical_potential.py','deforming_solid_storage.py'):
    f=p/name;s=f.read_text();prefix='from sludge_sandbox.water_properties import is_water_provider\n'
    if s.startswith(prefix):
        s=s[len(prefix):];lines=s.splitlines(keepends=True);body=ast.parse(s).body
        at=body[0].end_lineno if isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str) else 0
        lines.insert(at,prefix);s=''.join(lines)
    f.write_text(s)
