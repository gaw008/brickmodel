"""Optional offline evidence recheck; missing cache is a hard error, never a skip."""
from pathlib import Path
from decimal import Decimal
import argparse,hashlib,json


def verify(repository: Path) -> None:
    rows=json.loads(Path(__file__).with_name('gas_molar_mass_facts.json').read_text())
    for row in rows:
        source=repository/row['cache_path']
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['cache_sha256']:
            raise ValueError('cached_source_changed:'+row['species_id'])
        if row['locator'] not in json.loads(raw)['response']:
            raise ValueError('source_locator_missing')
        printed=Decimal(row['locator'].rsplit(':',1)[1].strip())
        if printed/1000!=Decimal(str(row['nominal_molar_mass_kg_mol'])):
            raise ValueError('source_molar_mass_conversion_mismatch')
    print('Verified two cached source identities, locators and nominal conversions; uncertainty remains unquantified.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repository',type=Path)
    verify(p.parse_args().repository)
