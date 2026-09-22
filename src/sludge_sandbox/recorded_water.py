"""Local IAPWS source record with no content-digest execution or attestation.

The existing WaterProperties constructor keeps its historical source policy.
This separate constructor reuses its physical initialization and evaluations;
it records the supplied facts and actual runtime rather than verifying bytes.
It is deliberately not admitted to the legacy exact-type wet-host protocol.
"""
from dataclasses import dataclass, field
import importlib
import json
from pathlib import Path

from .water_properties import NumericalLimits, WaterProperties


@dataclass(frozen=True, init=False)
class RecordedWaterProperties(WaterProperties):
    source_record: dict = field(repr=False)

    def __init__(self, facts_path: Path, numerical_limits: NumericalLimits):
        facts = json.loads(facts_path.read_text())
        backend = importlib.import_module('iapws')
        self._initialize(backend, facts, {}, numerical_limits)
        object.__setattr__(self, 'source_record', {
            'facts_path': str(facts_path), 'facts': facts,
            'runtime_module': str(Path(backend.__file__).resolve()),
            'runtime_version': backend.__version__,
            'source_policy': 'explicit_local_record_no_content_attestation',
            'asset_identity_verified': False,
        })

    def liquid_at_temperature(self,temperature_k):
        return lambda pressure_pa:self.state_tp(temperature_k,pressure_pa,phase='liquid')
