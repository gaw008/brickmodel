"""Implementation provenance is separate from physical water reference states."""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class WaterImplementation:
    schema: str
    provider_id: str
    provider_version: str
    source_ids: tuple[str, ...]
    canonical_descriptor: str

    def __post_init__(self):
        if self.schema != 'water_implementation_v1':
            raise ValueError('unsupported_water_implementation_schema')
        value=json.loads(self.canonical_descriptor)
        if json.dumps(value,sort_keys=True,separators=(',',':')) != self.canonical_descriptor:
            raise ValueError('canonical_water_descriptor_required')
        if (type(self.provider_id) is not str or not self.provider_id or type(self.provider_version) is not str or not self.provider_version
            or type(self.source_ids) is not tuple or not self.source_ids
            or any(type(x) is not str or not x or x!=x.strip() for x in self.source_ids)
            or len(set(self.source_ids))!=len(self.source_ids)):
            raise ValueError('water_implementation_identity_required')

    @property
    def canonical_json(self):
        return json.dumps({'schema':self.schema,'provider_id':self.provider_id,
            'provider_version':self.provider_version,'source_ids':self.source_ids,
            'definition':json.loads(self.canonical_descriptor)},sort_keys=True,separators=(',',':'))

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_json.encode()).hexdigest()
