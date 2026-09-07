"""Measure the existing source models at their shared endpoint, without joining them."""
from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.thermochemistry import load_thermochemistry


def main():
    low = IdealWaterVapor(ROOT / 'data/sandbox/water')
    high = load_thermochemistry(ROOT / 'data/sandbox/thermochemistry/nist_gases_v1.json').species('H2O')
    temperature = 500.0
    fields = ('enthalpy_j_mol', 'internal_energy_j_mol', 'cp_j_mol_k', 'cv_j_mol_k')
    values = {name: {'low': getattr(low, name)(temperature), 'high': getattr(high, name)(temperature)} for name in fields}
    for value in values.values():
        value['high_minus_low'] = value['high'] - value['low']
    files = [Path(__file__).relative_to(ROOT), Path('src/sludge_sandbox/ideal_water_vapor.py'),
             Path('src/sludge_sandbox/water_properties.py'), Path('src/sludge_sandbox/thermochemistry.py'),
             Path('data/sandbox/thermochemistry/nist_gases_v1.json')]
    result = dict(qualification='endpoint_discrepancy_measurement_only_no_join_or_accuracy_claim',
        temperature_k=temperature, values=values, low_domain_k=low.temperature_range_k,
        high_domain_k=high.temperature_range_k, low_source_ids=low.source_ids,
        high_source_ids=high.source_ids, water_asset_sha256=dict(low.source_asset_sha256),
        code_and_input_sha256={str(p): sha256((ROOT / p).read_bytes()).hexdigest() for p in files})
    Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(values, indent=2))


if __name__ == '__main__':
    main()
